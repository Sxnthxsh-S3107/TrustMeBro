from sqlalchemy.orm import Session
from .db import Patient

PRIORITY_ORDER = {"emergency": 0, "same-day": 1, "routine": 2}

def add_patient(db: Session, patient_data: dict) -> Patient:
    patient = Patient(**patient_data)
    db.merge(patient)   # merge = insert or update if patient_id already exists
    db.commit()
    return patient

def get_sorted_queue(db: Session) -> list[Patient]:
    patients = db.query(Patient).all()
    return sorted(
        patients,
        key=lambda p: (PRIORITY_ORDER.get(p.priority, 3), p.timestamp)
    )

def get_patient(db: Session, patient_id: str) -> Patient | None:
    return db.query(Patient).filter(Patient.patient_id == patient_id).first()

def update_priority(db: Session, patient_id: str, new_priority: str) -> Patient | None:
    patient = get_patient(db, patient_id)
    if not patient:
        return None
    patient.priority = new_priority
    db.commit()
    return patient