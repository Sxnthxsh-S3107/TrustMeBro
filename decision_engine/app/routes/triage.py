from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import get_db
from ..queue_store import add_patient
from ..llm_classifier import classify
from ..doctor_assignment import assign_doctor

from rules_engine.red_flags import check_red_flags

router = APIRouter()


@router.post("/triage")
def triage_patient(intake: dict, db: Session = Depends(get_db)):
    """
    Main triage pipeline:
      1. Person 1 deterministic safety rules run FIRST.
      2. If EMERGENCY or ESCALATE → bypass LLM, assign hard priority.
      3. If NO_HARD_RED_FLAG → allow LLM classification.

    Person 1 returns priority as one of:
      "EMERGENCY"        → mandatory hard red flag detected. LLM must NOT run.
      "ESCALATE"         → uncertainty/pediatric/missing safety data. LLM must NOT run.
                           Minimum priority = same-day (never routine).
      "NO_HARD_RED_FLAG" → safe to pass to LLM classifier.
    """
    patient_id = intake.get("patient_id") or intake.get("session_id")

    # ── STEP 1: Prepare intake for Person 1 ──
    # Person 2's voice intake collects follow_up_answers as a nested dict.
    # Person 1's rules read flat fields. Map them here at the integration boundary.
    # Also provide a default adult age so Person 1 can apply adult IITT thresholds.
    # (Person 2's voice flow is for adult rural clinic patients; age is not collected.)
    follow_up = intake.get("follow_up_answers") or {}
    chief_complaint_raw = str(intake.get("chief_complaint") or "").lower()

    # Build safety_intake with all fields Person 1's rules may read
    safety_intake = dict(intake)

    # Default age = 35 (adult) if not provided — allows Person 1 adult rules to fire
    if not safety_intake.get("age"):
        safety_intake["age"] = 35

    # Map Person 2 follow_up_answers into flat fields Person 1 expects
    if follow_up.get("sweating") is True:
        safety_intake["sweating"] = True
    if follow_up.get("radiating_pain") is True:
        safety_intake["radiating_pain"] = True
    if follow_up.get("chest_tightness") is True:
        safety_intake["breathing_difficulty"] = True
    if follow_up.get("dizziness") is True:
        safety_intake["dizziness"] = True

    # Map chief_complaint keywords to Person 1's boolean fields
    if "chest pain" in chief_complaint_raw:
        safety_intake["chest_pain"] = True
    if "breathing" in chief_complaint_raw or "breathless" in chief_complaint_raw or "shortness of breath" in chief_complaint_raw:
        safety_intake["breathing_difficulty"] = True
    if "bleed" in chief_complaint_raw or "bleeding" in chief_complaint_raw:
        safety_intake["uncontrolled_bleeding"] = True
    if "convuls" in chief_complaint_raw or "seizure" in chief_complaint_raw or "fit" in chief_complaint_raw:
        safety_intake["active_convulsion"] = True
    if "weakness" in chief_complaint_raw or "droop" in chief_complaint_raw:
        safety_intake["sudden_one_sided_weakness"] = True
    if "speech" in chief_complaint_raw or "slurred" in chief_complaint_raw:
        safety_intake["speech_difficulty"] = True
    if "unconscious" in chief_complaint_raw or "not responding" in chief_complaint_raw:
        safety_intake["unconscious"] = True

    # Also map sweating from chief complaint text
    if "sweat" in chief_complaint_raw:
        safety_intake["sweating"] = True

    # ── STEP 2: Person 1 Safety Engine (deterministic, always runs first) ──
    safety_result = check_red_flags(safety_intake)

    p1_priority    = safety_result.get("priority", "NO_HARD_RED_FLAG")   # str enum value
    llm_allowed    = safety_result.get("llm_allowed", True)
    rule_triggered = safety_result.get("rule_triggered", False)
    red_flags_list = safety_result.get("red_flags", [])
    security_alerts= safety_result.get("security_alerts", [])
    p1_rationale   = safety_result.get("rationale", "")

    # ── STEP 2: Route by Person 1 result ──
    if p1_priority == "EMERGENCY" or not llm_allowed:
        # Hard emergency OR uncertainty/pediatric — LLM path is closed
        if p1_priority == "EMERGENCY":
            priority = "emergency"
            rationale = p1_rationale or "Mandatory emergency red flag detected by safety rules."
        elif p1_priority == "ESCALATE":
            # ESCALATE means uncertain/missing data — minimum same-day, never routine
            priority = "same-day"
            rationale = p1_rationale or "Clinical uncertainty detected; escalated to same-day for safety."
        else:
            # Defensive fallback for any unrecognised non-llm_allowed state
            priority = "same-day"
            rationale = p1_rationale or "Safety engine blocked LLM; assigned same-day."

        confidence = "high"
        source = "rule_engine"
        red_flag = rule_triggered

    else:
        # ── STEP 3: LLM classification (only runs when Person 1 says it is safe) ──
        try:
            classification = classify(intake)
            priority   = classification.get("priority", "same-day")
            rationale  = classification.get("rationale", "LLM classification result.")
            confidence = classification.get("confidence", "medium")
        except Exception as exc:
            # LLM failure → escalate to same-day, never silently become routine
            print(f"[LLM] classify() error: {exc}")
            priority   = "same-day"
            rationale  = f"LLM classifier failed: {exc}. Defaulted to same-day for safety."
            confidence = "low"

        source   = "llm"
        red_flag = False

        # Confidence gate: if LLM confidence is 'low', minimum priority is same-day
        if confidence == "low" and priority == "routine":
            priority = "same-day"
            rationale += " (Confidence gate: low-confidence routine escalated to same-day.)"

    # ── STEP 4: Doctor Assignment ──
    assigned_doctor, assignment_reason = assign_doctor(db, intake)

    # ── STEP 5: Persist and return ──
    # Fields that go into the DB (must match Patient model columns)
    db_record = {
        "patient_id":        patient_id,
        "priority":          priority,
        "rationale":         rationale,
        "confidence":        confidence,
        "source":            source,
        "chief_complaint":   intake.get("chief_complaint"),
        "duration":          intake.get("duration"),
        "red_flag":          red_flag,
        "relevant_history":  intake.get("history"),
        "assigned_doctor":   assigned_doctor,
        "assignment_reason": assignment_reason,
    }

    add_patient(db, db_record)

    # Return full response including Person 1 safety metadata (not stored in DB,
    # but needed by the doctor dashboard for red-flag display and audit)
    return {
        **db_record,
        "safety_red_flags":  red_flags_list,
        "security_alerts":   security_alerts,
        "p1_priority":       p1_priority,
    }