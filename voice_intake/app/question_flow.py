"""Question flow and session state management for Voice Intake.
Provides deterministic base questions, complaint-driven adaptive follow-ups,
ambiguity clarification, and multi-session isolation.
"""

import os
import sys
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import threading

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from voice_intake.app.nlp import (
        extract_chief_complaint,
        extract_yes_no,
        extract_duration,
        extract_medications,
        extract_medical_history,
    )
except ImportError:
    from nlp import (
        extract_chief_complaint,
        extract_yes_no,
        extract_duration,
        extract_medications,
        extract_medical_history,
    )

# =====================================================================
# Question Definitions (English & Tamil)
# =====================================================================

BASE_QUESTIONS = [
    {
        "id": "chief_complaint",
        "en": "What is bothering you?",
        "ta": "உங்களுக்கு என்ன பிரச்சனை?",
    },
    {
        "id": "duration",
        "en": "When did it start?",
        "ta": "இது எப்போது தொடங்கியது?",
    },
    {
        "id": "medications",
        "en": "Are you taking any medications?",
        "ta": "நீங்கள் ஏதேனும் மருந்துகள் எடுத்துக்கொள்கிறீர்களா?",
    },
    {
        "id": "history",
        "en": "Do you have any relevant medical history?",
        "ta": "உங்களுக்கு ஏதேனும் முக்கியமான மருத்துவ வரலாறு உள்ளதா?",
    },
]

ADAPTIVE_QUESTIONS = {
    "chest pain": [
        {
            "id": "radiating_pain",
            "en": "Does the pain spread to your arm, shoulder, jaw, or back?",
            "ta": "வலி உங்கள் கை, தோள், தாடை அல்லது முதுகுக்கு பரவுகிறதா?",
        },
        {
            "id": "sweating",
            "en": "Are you experiencing sweating?",
            "ta": "உங்களுக்கு வியர்வை அதிகமாக வருகிறதா?",
        },
    ],
    "headache": [
        {
            "id": "dizziness",
            "en": "Are you experiencing dizziness?",
            "ta": "உங்களுக்கு தலைச்சுற்றல் இருக்கிறதா?",
        },
        {
            "id": "vision_problems",
            "en": "Are you having vision problems?",
            "ta": "உங்களுக்கு பார்வையில் ஏதேனும் பிரச்சனை இருக்கிறதா?",
        },
    ],
    "abdominal pain": [
        {
            "id": "vomiting",
            "en": "Are you experiencing vomiting?",
            "ta": "உங்களுக்கு வாந்தி வருகிறதா?",
        },
        {
            "id": "diarrhea",
            "en": "Are you experiencing diarrhea?",
            "ta": "உங்களுக்கு வயிற்றுப்போக்கு இருக்கிறதா?",
        },
    ],
    "breathing difficulty": [
        {
            "id": "chest_tightness",
            "en": "Are you experiencing chest tightness?",
            "ta": "உங்களுக்கு மார்பு இறுக்கமாக இருக்கிறதா?",
        },
    ],
}

CLARIFICATION_QUESTION = {
    "id": "chief_complaint_clarification",
    "en": "Can you tell me where you are feeling the problem?",
    "ta": "உங்களுக்கு எந்த இடத்தில் பிரச்சனை இருக்கிறது என்று சொல்ல முடியுமா?",
}

AMBIGUOUS_RETRY_QUESTION = {
    "id": "yes_no_retry",
    "en": "Please answer yes or no.",
    "ta": "தயவுசெய்து ஆம் அல்லது இல்லை என்று பதிலளிக்கவும்.",
}


class IntakeSession:
    """Represents a single independent patient intake session."""

    def __init__(self, session_id: str, language: str = "en", patient_id: Optional[str] = None):
        self.session_id = session_id
        self.language = language if language in ["en", "ta"] else "en"
        self.patient_id = patient_id
        self.status = "in_progress"  # 'in_progress', 'completed', 'ambiguous'

        # Clinical extracted data
        self.chief_complaint = "unknown"
        self.duration = ""
        self.medications = []
        self.history = "none"
        self.follow_up_answers = {}

        # Raw responses per question and full transcript
        self.raw_transcripts = {}
        self.raw_transcript_list = []

        # Flow tracking
        self.base_step_index = 0  # 0 to len(BASE_QUESTIONS) - 1
        self.adaptive_step_index = 0
        self.adaptive_questions_queue = []
        self.is_clarifying_complaint = False
        self.clarification_attempts = 0

    @property
    def raw_transcript(self) -> str:
        """Joined raw transcript of all patient responses."""
        return " ".join(self.raw_transcript_list)

    def get_current_question(self) -> Optional[Dict[str, Any]]:
        """Return the current active question object formatted for the selected language."""
        if self.status == "completed":
            return None

        if self.is_clarifying_complaint:
            q_text = CLARIFICATION_QUESTION["ta"] if self.language == "ta" else CLARIFICATION_QUESTION["en"]
            return {
                "question_id": CLARIFICATION_QUESTION["id"],
                "question_text": q_text,
                "language": self.language,
                "is_adaptive": False,
                "is_clarification": True,
            }

        # Check if we are still in base questions
        if self.base_step_index < len(BASE_QUESTIONS):
            q = BASE_QUESTIONS[self.base_step_index]
            q_text = q["ta"] if self.language == "ta" else q["en"]
            return {
                "question_id": q["id"],
                "question_text": q_text,
                "language": self.language,
                "is_adaptive": False,
                "is_clarification": False,
            }

        # Check adaptive questions
        if self.adaptive_step_index < len(self.adaptive_questions_queue):
            q = self.adaptive_questions_queue[self.adaptive_step_index]
            q_text = q["ta"] if self.language == "ta" else q["en"]
            return {
                "question_id": q["id"],
                "question_text": q_text,
                "language": self.language,
                "is_adaptive": True,
                "is_clarification": False,
            }

        # If all questions answered
        self.status = "completed"
        return None

    def process_answer(self, raw_answer: str) -> Dict[str, Any]:
        """
        Process the patient's answer to the current active question.
        Updates internal state, extracts entities, and advances the question flow.
        """
        raw_text = raw_answer.strip() if raw_answer else ""
        current_q = self.get_current_question()

        if not current_q or self.status == "completed":
            return self.to_contract_dict()

        if not raw_text:
            return {
                "session_id": self.session_id,
                "error": "NO_ANSWER_PROVIDED",
                "message": "Please provide an answer before continuing.",
                "extracted": {},
                "next_question": current_q,
                "status": self.status,
            }

        q_id = current_q["question_id"]
        # Record raw answer
        self.raw_transcripts[q_id] = raw_text
        self.raw_transcript_list.append(raw_text)

        extraction_result = {}

        # 1. Processing Ambiguity Clarification
        if self.is_clarifying_complaint:
            complaint, conf_status, conf = extract_chief_complaint(raw_text)
            self.chief_complaint = complaint
            self.is_clarifying_complaint = False
            self.base_step_index = 1  # Move to duration question
            self._queue_adaptive_questions()
            extraction_result = {"chief_complaint": self.chief_complaint, "status": conf_status}

        # 2. Processing Base Question 1 (Chief Complaint)
        elif q_id == "chief_complaint":
            complaint, conf_status, conf = extract_chief_complaint(raw_text)
            if conf_status in ["ambiguous", "unknown"] and self.clarification_attempts < 1:
                self.is_clarifying_complaint = True
                self.clarification_attempts += 1
                extraction_result = {
                    "chief_complaint": "unknown",
                    "status": "ambiguous",
                    "requires_clarification": True,
                }
                return {
                    "session_id": self.session_id,
                    "extracted": extraction_result,
                    "next_question": self.get_current_question(),
                    "status": "ambiguous",
                }
            else:
                self.chief_complaint = complaint
                self.base_step_index += 1
                self._queue_adaptive_questions()
                extraction_result = {"chief_complaint": self.chief_complaint, "status": conf_status}

        # 3. Processing Base Question 2 (Duration)
        elif q_id == "duration":
            extracted_dur = extract_duration(raw_text)
            self.duration = extracted_dur
            self.base_step_index += 1
            extraction_result = {"duration": self.duration}

        # 4. Processing Base Question 3 (Medications)
        elif q_id == "medications":
            extracted_meds = extract_medications(raw_text)
            self.medications = extracted_meds
            self.base_step_index += 1
            extraction_result = {"medications": self.medications}

        # 5. Processing Base Question 4 (History)
        elif q_id == "history":
            extracted_hist = extract_medical_history(raw_text)
            self.history = extracted_hist
            self.base_step_index += 1
            extraction_result = {"history": self.history}

        # 6. Processing Adaptive Questions
        elif current_q.get("is_adaptive"):
            yes_no_val = extract_yes_no(raw_text)
            if yes_no_val is None:
                # If ambiguous answer, ask again / do not advance
                retry_text = AMBIGUOUS_RETRY_QUESTION["ta"] if self.language == "ta" else AMBIGUOUS_RETRY_QUESTION["en"]
                return {
                    "session_id": self.session_id,
                    "extracted": {q_id: None, "status": "ambiguous_yes_no"},
                    "next_question": {
                        "question_id": q_id,
                        "question_text": f"{current_q['question_text']} ({retry_text})",
                        "language": self.language,
                        "is_adaptive": True,
                        "is_retry": True,
                    },
                    "status": "in_progress",
                }
            self.follow_up_answers[q_id] = yes_no_val
            self.adaptive_step_index += 1
            extraction_result = {q_id: yes_no_val}

        # Check if finished
        next_q = self.get_current_question()
        if not next_q:
            self.status = "completed"

        return {
            "session_id": self.session_id,
            "extracted": extraction_result,
            "next_question": next_q,
            "status": self.status,
            "intake_result": self.to_contract_dict() if self.status == "completed" else None,
        }

    def _queue_adaptive_questions(self):
        """Queue complaint-specific follow-up questions."""
        if self.chief_complaint in ADAPTIVE_QUESTIONS:
            self.adaptive_questions_queue = list(ADAPTIVE_QUESTIONS[self.chief_complaint])
        else:
            self.adaptive_questions_queue = []

    def to_contract_dict(self) -> Dict[str, Any]:
        """Generate final dictionary strictly conforming to contracts/intake_schema.json."""
        return {
            "session_id": self.session_id,
            "patient_id": self.patient_id,
            "language": self.language,
            "chief_complaint": self.chief_complaint if self.chief_complaint else "unknown",
            "duration": self.duration if self.duration else "unknown",
            "medications": self.medications if self.medications else ["none"],
            "history": self.history if self.history else "none",
            "follow_up_answers": self.follow_up_answers,
            "raw_transcript": self.raw_transcript,
            "raw_transcripts": self.raw_transcripts,
            "status": self.status,
        }


class SessionManager:
    """Thread-safe multi-session manager for independent patient intake sessions."""

    def __init__(self):
        self._sessions: Dict[str, IntakeSession] = {}
        self._lock = threading.Lock()

    def create_session(self, language: str = "en", patient_id: Optional[str] = None) -> IntakeSession:
        """Create and register a new intake session."""
        session_id = str(uuid.uuid4())
        session = IntakeSession(session_id=session_id, language=language, patient_id=patient_id)
        with self._lock:
            self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[IntakeSession]:
        """Retrieve an existing intake session by session_id."""
        with self._lock:
            return self._sessions.get(session_id)

    def reset_session(self, session_id: str) -> Optional[IntakeSession]:
        """Reset an existing intake session, keeping language and session_id."""
        with self._lock:
            if session_id in self._sessions:
                lang = self._sessions[session_id].language
                pid = self._sessions[session_id].patient_id
                new_session = IntakeSession(session_id=session_id, language=lang, patient_id=pid)
                self._sessions[session_id] = new_session
                return new_session
        return None

    def delete_session(self, session_id: str) -> bool:
        """Remove a session from storage."""
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
        return False
