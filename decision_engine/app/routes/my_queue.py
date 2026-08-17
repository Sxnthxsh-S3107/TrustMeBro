import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import get_db, Patient
from .auth import require_doctor

router = APIRouter()

def _serialize_patient(p):
    """Serialize a Patient ORM row into the canonical triage response contract."""
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

@router.get("/my-queue")
def get_my_queue(db: Session = Depends(get_db), doctor_id: str = Depends(require_doctor)):
    patients = db.query(Patient).filter(Patient.assigned_doctor == doctor_id).all()
    PRIORITY_ORDER = {"emergency": 0, "same-day": 1, "routine": 2}
    patients_sorted = sorted(patients, key=lambda p: (PRIORITY_ORDER.get(p.priority, 3), p.timestamp))

    return [_serialize_patient(p) for p in patients_sorted]