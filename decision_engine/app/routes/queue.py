from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import get_db
from ..queue_store import get_sorted_queue

router = APIRouter()

@router.get("/queue")
def get_queue(db: Session = Depends(get_db)):
    patients = get_sorted_queue(db)
    return [
        {
            "patient_id": p.patient_id,
            "priority": p.priority,
            "rationale": p.rationale,
            "confidence": p.confidence,
            "source": p.source,
            "chief_complaint": p.chief_complaint,
            "duration": p.duration,
            "red_flag": p.red_flag,
            "relevant_history": p.relevant_history,
            "assigned_doctor": p.assigned_doctor,          # NEW
            "assignment_reason": p.assignment_reason,       # NEW
        }
        for p in patients
    ]