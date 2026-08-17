import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from ..db import get_db, ReassignmentLog
from ..queue_store import get_patient
from .auth import require_doctor

router = APIRouter()

@router.post("/reassign")
def reassign_doctor(
    patient_id: str,
    new_doctor: str,
    db: Session = Depends(get_db),
    changed_by: str = Depends(require_doctor),   # comes from token now, not frontend input
):
    patient = get_patient(db, patient_id)
    if not patient:
        return {"error": "patient not found"}

    old_doctor = patient.assigned_doctor
    patient.assigned_doctor = new_doctor
    db.commit()

    log_entry = ReassignmentLog(
        id=str(uuid.uuid4()),
        patient_id=patient_id,
        old_doctor=old_doctor,
        new_doctor=new_doctor,
        changed_by=changed_by,
        timestamp=datetime.utcnow(),
    )
    db.add(log_entry)
    db.commit()

    return {"status": "reassigned", "patient_id": patient_id, "new_doctor": new_doctor, "changed_by": changed_by}

@router.get("/reassign/log")
def get_reassignment_log(db: Session = Depends(get_db)):
    logs = db.query(ReassignmentLog).all()
    return [
        {
            "patient_id": l.patient_id,
            "old_doctor": l.old_doctor,
            "new_doctor": l.new_doctor,
            "changed_by": l.changed_by,
            "timestamp": l.timestamp.isoformat(),
        }
        for l in logs
    ]