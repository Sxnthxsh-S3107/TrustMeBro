from .doctors import DOCTORS, CAPABILITY_KEYWORDS
from .db import Patient
from sqlalchemy.orm import Session
from sqlalchemy import func

def get_workload(db: Session) -> dict:
    """Count active (non-completed) patients per doctor as a workload proxy."""
    counts = db.query(Patient.assigned_doctor, func.count(Patient.patient_id)) \
        .filter(Patient.assigned_doctor.isnot(None)) \
        .group_by(Patient.assigned_doctor).all()
    workload = {doc_id: 0 for doc_id in DOCTORS}
    for doc_id, count in counts:
        workload[doc_id] = count
    return workload

def score_doctor(doctor_id: str, text_blob: str) -> int:
    score = 0
    for keyword, mapped_doc in CAPABILITY_KEYWORDS.items():
        if keyword in text_blob and mapped_doc == doctor_id:
            score += 2
    return score

def assign_doctor(db: Session, intake: dict) -> tuple[str, str]:
    text_blob = " ".join([
        str(intake.get("chief_complaint", "")),
        str(intake.get("history", "")),
    ]).lower()

    workload = get_workload(db)

    scores = {}
    for doc_id in DOCTORS:
        capability_score = score_doctor(doc_id, text_blob)
        workload_score = -workload[doc_id]   # lower workload = higher net score
        scores[doc_id] = capability_score + workload_score

    best_doctor = max(scores, key=scores.get)
    matched_keywords = [k for k, v in CAPABILITY_KEYWORDS.items() if v == best_doctor and k in text_blob]

    if matched_keywords:
        reason = f"Matched keywords {matched_keywords} → {DOCTORS[best_doctor]['name']} (workload={workload[best_doctor]})"
    else:
        reason = f"No strong symptom match — assigned {DOCTORS[best_doctor]['name']} based on lowest current workload ({workload[best_doctor]})"

    return best_doctor, reason