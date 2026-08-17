"""Unit tests for question flow state machine, adaptive branching, and schema conformity.
"""

import json
import os
import jsonschema
import pytest
from voice_intake.app.question_flow import IntakeSession, SessionManager

CONTRACT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../contracts/intake_schema.json"))


def load_intake_schema():
    with open(CONTRACT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_english_chest_pain_flow():
    schema = load_intake_schema()
    session = IntakeSession(session_id="test-en-001", language="en")

    # Q1: Chief Complaint
    q1 = session.get_current_question()
    assert q1["question_id"] == "chief_complaint"
    assert "bothering you" in q1["question_text"]
    res1 = session.process_answer("I have severe chest pain")
    assert res1["extracted"]["chief_complaint"] == "chest pain"

    # Q2: Duration
    q2 = session.get_current_question()
    assert q2["question_id"] == "duration"
    assert "When did it start" in q2["question_text"]
    res2 = session.process_answer("It started two hours ago")
    assert res2["extracted"]["duration"] == "2 hours"

    # Q3: Medications
    q3 = session.get_current_question()
    assert q3["question_id"] == "medications"
    assert "medications" in q3["question_text"]
    res3 = session.process_answer("No medications")
    assert res3["extracted"]["medications"] == ["none"]

    # Q4: History
    q4 = session.get_current_question()
    assert q4["question_id"] == "history"
    assert "medical history" in q4["question_text"]
    res4 = session.process_answer("I have diabetes")
    assert res4["extracted"]["history"] == "diabetic"

    # Adaptive Follow-up 1: Radiating Pain
    q_ad1 = session.get_current_question()
    assert q_ad1["question_id"] == "radiating_pain"
    assert q_ad1["is_adaptive"] is True
    assert "Does the pain spread" in q_ad1["question_text"]
    res_ad1 = session.process_answer("yes")
    assert res_ad1["extracted"]["radiating_pain"] is True

    # Adaptive Follow-up 2: Sweating
    q_ad2 = session.get_current_question()
    assert q_ad2["question_id"] == "sweating"
    assert q_ad2["is_adaptive"] is True
    assert "sweating" in q_ad2["question_text"]
    res_ad2 = session.process_answer("no")
    assert res_ad2["extracted"]["sweating"] is False

    # Session Completed
    assert session.status == "completed"
    assert session.get_current_question() is None

    final_payload = session.to_contract_dict()
    assert final_payload["session_id"] == "test-en-001"
    assert final_payload["language"] == "en"
    assert final_payload["chief_complaint"] == "chest pain"
    assert final_payload["duration"] == "2 hours"
    assert final_payload["medications"] == ["none"]
    assert final_payload["history"] == "diabetic"
    assert final_payload["follow_up_answers"] == {"radiating_pain": True, "sweating": False}
    assert "chest pain" in final_payload["raw_transcript"]
    assert final_payload["raw_transcripts"]["chief_complaint"] == "I have severe chest pain"

    # Validate against JSON Schema
    jsonschema.validate(instance=final_payload, schema=schema)


def test_tamil_session_flow():
    schema = load_intake_schema()
    session = IntakeSession(session_id="test-ta-001", language="ta")

    # Q1: Chief Complaint (Tamil)
    q1 = session.get_current_question()
    assert q1["language"] == "ta"
    assert "உங்களுக்கு என்ன பிரச்சனை" in q1["question_text"]
    res1 = session.process_answer("எனக்கு நெஞ்சு வலி இருக்கு")
    assert res1["extracted"]["chief_complaint"] == "chest pain"

    # Q2: Duration (Tamil)
    q2 = session.get_current_question()
    assert "இது எப்போது தொடங்கியது" in q2["question_text"]
    res2 = session.process_answer("இரண்டு மணி நேரமாக")
    assert res2["extracted"]["duration"] == "2 hours"

    # Q3: Medications (Tamil)
    q3 = session.get_current_question()
    assert "நீங்கள் ஏதேனும் மருந்துகள்" in q3["question_text"]
    res3 = session.process_answer("எந்த மருந்தும் எடுக்கவில்லை")
    assert res3["extracted"]["medications"] == ["none"]

    # Q4: History (Tamil)
    q4 = session.get_current_question()
    assert "மருத்துவ வரலாறு" in q4["question_text"]
    res4 = session.process_answer("எனக்கு சர்க்கரை நோய் இருக்கு")
    assert res4["extracted"]["history"] == "diabetic"

    # Adaptive Follow-up 1 (Tamil)
    q_ad1 = session.get_current_question()
    assert q_ad1["question_id"] == "radiating_pain"
    assert "வலி உங்கள் கை" in q_ad1["question_text"]
    res_ad1 = session.process_answer("ஆமாம்")
    assert res_ad1["extracted"]["radiating_pain"] is True

    # Adaptive Follow-up 2 (Tamil)
    q_ad2 = session.get_current_question()
    assert q_ad2["question_id"] == "sweating"
    assert "வியர்வை" in q_ad2["question_text"]
    res_ad2 = session.process_answer("இல்லை")
    assert res_ad2["extracted"]["sweating"] is False

    # Check contract conformity
    final_payload = session.to_contract_dict()
    assert final_payload["language"] == "ta"
    assert final_payload["chief_complaint"] == "chest pain"
    assert final_payload["raw_transcripts"]["chief_complaint"] == "எனக்கு நெஞ்சு வலி இருக்கு"
    assert final_payload["raw_transcripts"]["duration"] == "இரண்டு மணி நேரமாக"
    assert final_payload["raw_transcripts"]["medications"] == "எந்த மருந்தும் எடுக்கவில்லை"
    assert final_payload["raw_transcripts"]["history"] == "எனக்கு சர்க்கரை நோய் இருக்கு"

    jsonschema.validate(instance=final_payload, schema=schema)


def test_headache_adaptive_questions():
    session = IntakeSession(session_id="test-headache", language="en")
    session.process_answer("I have a headache")
    session.process_answer("1 day")
    session.process_answer("paracetamol")
    session.process_answer("none")

    # Adaptive 1: dizziness
    q_ad1 = session.get_current_question()
    assert q_ad1["question_id"] == "dizziness"
    session.process_answer("yes")

    # Adaptive 2: vision_problems
    q_ad2 = session.get_current_question()
    assert q_ad2["question_id"] == "vision_problems"
    session.process_answer("no")

    assert session.status == "completed"
    assert session.follow_up_answers == {"dizziness": True, "vision_problems": False}


def test_abdominal_pain_adaptive_questions():
    session = IntakeSession(session_id="test-ab-pain", language="en")
    session.process_answer("stomach pain")
    session.process_answer("3 hours")
    session.process_answer("none")
    session.process_answer("none")

    # Adaptive 1: vomiting
    q_ad1 = session.get_current_question()
    assert q_ad1["question_id"] == "vomiting"
    session.process_answer("yes")

    # Adaptive 2: diarrhea
    q_ad2 = session.get_current_question()
    assert q_ad2["question_id"] == "diarrhea"
    session.process_answer("no")

    assert session.status == "completed"
    assert session.follow_up_answers == {"vomiting": True, "diarrhea": False}


def test_breathing_difficulty_adaptive_question():
    session = IntakeSession(session_id="test-breath", language="en")
    session.process_answer("difficulty breathing")
    session.process_answer("30 minutes")
    session.process_answer("inhaler")
    session.process_answer("asthma")

    # Adaptive 1: chest_tightness
    q_ad1 = session.get_current_question()
    assert q_ad1["question_id"] == "chest_tightness"
    session.process_answer("yes")

    assert session.status == "completed"
    assert session.follow_up_answers == {"chest_tightness": True}


def test_ambiguity_clarification_flow():
    session = IntakeSession(session_id="test-ambig", language="en")

    # Ambiguous initial complaint
    res1 = session.process_answer("I don't feel well")
    assert res1["status"] == "ambiguous"

    # System prompts clarification question
    q_clarify = session.get_current_question()
    assert q_clarify["is_clarification"] is True
    assert "where you are feeling the problem" in q_clarify["question_text"]

    # Clarifying response gives actual symptom
    res_clarify = session.process_answer("My head hurts, headache")
    assert session.chief_complaint == "headache"

    # Moves to Question 2 (duration)
    q2 = session.get_current_question()
    assert q2["question_id"] == "duration"


def test_session_manager_isolation():
    manager = SessionManager()
    session_en = manager.create_session(language="en")
    session_ta = manager.create_session(language="ta")

    assert session_en.session_id != session_ta.session_id
    assert session_en.language == "en"
    assert session_ta.language == "ta"

    # Progress session_en
    session_en.process_answer("I have chest pain")

    # Verify session_ta is unaffected
    assert session_ta.chief_complaint == "unknown"
    assert session_ta.base_step_index == 0

    # Retrieve and verify
    retrieved = manager.get_session(session_en.session_id)
    assert retrieved.chief_complaint == "chest pain"
