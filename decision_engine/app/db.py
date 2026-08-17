import os
from sqlalchemy import create_engine, Column, String, Boolean, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Patient(Base):
    __tablename__ = "patients"

    patient_id = Column(String, primary_key=True)
    priority = Column(String, nullable=False)          # emergency / same-day / routine
    rationale = Column(String)
    confidence = Column(String)
    source = Column(String)                            # "rule_engine" or "llm"
    chief_complaint = Column(String)
    duration = Column(String)
    red_flag = Column(Boolean, default=False)
    relevant_history = Column(String)
    assigned_doctor = Column(String, nullable=True)
    assignment_reason = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)


class OverrideLog(Base):
    __tablename__ = "override_log"

    id = Column(String, primary_key=True)              # e.g. uuid
    patient_id = Column(String, nullable=False)
    old_priority = Column(String)
    new_priority = Column(String)
    doctor_id = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)


class ReassignmentLog(Base):
    __tablename__ = "reassignment_log"

    id = Column(String, primary_key=True)
    patient_id = Column(String, nullable=False)
    old_doctor = Column(String)
    new_doctor = Column(String)
    changed_by = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    reassignment_reason = Column(String, nullable=True)


# creates tables if they don't exist yet
Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()