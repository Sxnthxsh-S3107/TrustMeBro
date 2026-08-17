import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import get_db
from ..queue_store import get_sorted_queue

router = APIRouter()

def _serialize_patient(p):
    """Serialize a Patient ORM row into the canonical triage response contract."""
    # Parse safety_red_flags from JSON text back to list
    safety_red_flags = []
    if p.safety_red_flags:
        try:
            safety_red_flags = json.loads(p.safety_red_flags)
        except (json.JSONDecodeError, TypeError):
            safety_red_flags = []

    return {
        "patient_id": p.patient_id,
        "chief_complaint": p.chief_complaint,
        "duration": p.duration,
        "red_flag": p.red_flag,
        "safety_red_flags": safety_red_flags,
        "relevant_history": p.relevant_history,
        "priority": p.priority,
        "rationale": p.rationale,
        "confidence": p.confidence,
        "source": p.source,
        "assigned_doctor": p.assigned_doctor,
        "assignment_reason": p.assignment_reason,
    }

@router.get("/queue")
def get_queue(db: Session = Depends(get_db)):
    patients = get_sorted_queue(db)
    return [_serialize_patient(p) for p in patients]