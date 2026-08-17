from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import get_db
from ..queue_store import add_patient
from ..llm_classifier import classify
from ..doctor_assignment import assign_doctor   # NEW

def check_red_flags(intake_json: dict) -> dict:
    return {"flagged": False, "reason": None}

router = APIRouter()

@router.post("/triage")
def triage_patient(intake: dict, db: Session = Depends(get_db)):
    patient_id = intake.get("patient_id")
    red_flag_result = check_red_flags(intake)

    if red_flag_result["flagged"]:
        priority = "emergency"
        rationale = red_flag_result["reason"]
        confidence = "high"
        source = "rule_engine"
        red_flag = True
    else:
        classification = classify(intake)
        priority = classification["priority"]
        rationale = classification["rationale"]
        confidence = classification["confidence"]
        source = "llm"
        red_flag = False

    # NEW — doctor assignment happens after priority is set, never overrides it
    assigned_doctor, assignment_reason = assign_doctor(db, intake)

    patient_data = {
        "patient_id": patient_id,
        "priority": priority,
        "rationale": rationale,
        "confidence": confidence,
        "source": source,
        "chief_complaint": intake.get("chief_complaint"),
        "duration": intake.get("duration"),
        "red_flag": red_flag,
        "relevant_history": intake.get("history"),
        "assigned_doctor": assigned_doctor,          # NEW
        "assignment_reason": assignment_reason,       # NEW
    }

    add_patient(db, patient_data)
    return patient_data