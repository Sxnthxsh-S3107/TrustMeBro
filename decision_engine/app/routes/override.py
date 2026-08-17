import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from ..db import get_db, OverrideLog
from ..queue_store import update_priority, get_patient

router = APIRouter()

@router.post("/override")
def override_priority(patient_id: str, new_priority: str, doctor_id: str, db: Session = Depends(get_db)):
    old_patient = get_patient(db, patient_id)
    if not old_patient:
        return {"error": "patient not found"}

    old_priority = old_patient.priority
    patient = update_priority(db, patient_id, new_priority)

    log_entry = OverrideLog(
        id=str(uuid.uuid4()),
        patient_id=patient_id,
        old_priority=old_priority,
        new_priority=new_priority,
        doctor_id=doctor_id,
        timestamp=datetime.utcnow(),
    )
    db.add(log_entry)
    db.commit()

    return {"status": "overridden", "patient_id": patient_id, "new_priority": new_priority}

@router.get("/override/log")
def get_override_log(db: Session = Depends(get_db)):
    logs = db.query(OverrideLog).all()
    return [
        {
            "patient_id": l.patient_id,
            "old_priority": l.old_priority,
            "new_priority": l.new_priority,
            "doctor_id": l.doctor_id,
            "timestamp": l.timestamp.isoformat(),
        }
        for l in logs
    ]