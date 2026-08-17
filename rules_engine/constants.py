"""
rules_engine/constants.py
-------------------------
Clinically sourced threshold constants, priority definitions, and stable rule IDs
for Person 1's LifeLine Safety Rule Engine.

Primary Clinical Reference:
    WHO/ICRC/MSF Interagency Integrated Triage Tool (IITT) Adult (>=12 years)
Secondary Reference:
    WHO Basic Emergency Care (BEC) Toolkit

100% Deterministic Python - Zero ML/LLM/External APIs.
"""

from enum import Enum


# -----------------------------------------------------------------------------
# TRIAGE PRIORITIES & SOURCES
# -----------------------------------------------------------------------------

class Priority(str, Enum):
    """Triage priority levels produced by the safety engine."""
    EMERGENCY = "EMERGENCY"
    ESCALATE = "ESCALATE"
    NO_HARD_RED_FLAG = "NO_HARD_RED_FLAG"


class Source(str, Enum):
    """Source of the triage decision."""
    HARD_RULE = "HARD_RULE"
    SAFETY_ENGINE = "SAFETY_ENGINE"


# -----------------------------------------------------------------------------
# STABLE RULE IDENTIFIERS
# -----------------------------------------------------------------------------

class RuleId:
    # Airway
    RF_AIRWAY_001 = "RF_AIRWAY_001"

    # Breathing
    RF_RESP_001 = "RF_RESP_001"
    RF_VIT_SPO2 = "RF_VIT_SPO2"
    RF_VIT_RR = "RF_VIT_RR"

    # Circulation
    RF_CIRC_001 = "RF_CIRC_001"
    RF_VIT_SBP = "RF_VIT_SBP"
    RF_VIT_HR = "RF_VIT_HR"

    # Consciousness / Neurological
    RF_NEURO_001 = "RF_NEURO_001"
    RF_NEURO_002 = "RF_NEURO_002"
    RF_NEURO_FOCAL = "RF_NEURO_FOCAL"

    # Convulsions
    RF_CONV_001 = "RF_CONV_001"

    # Temperature
    RF_TEMP_001 = "RF_TEMP_001"

    # High-Risk Trauma
    RF_TRAUMA_001 = "RF_TRAUMA_001"

    # Toxic Exposure / Poisoning
    RF_TOX_001 = "RF_TOX_001"

    # Acute Chest Syndrome
    RF_CHEST_001 = "RF_CHEST_001"

    # Allergic / Anaphylaxis Pattern
    RF_ALLERGY_001 = "RF_ALLERGY_001"

    # Obstetric Red Flags
    RF_OB_001 = "RF_OB_001"


# -----------------------------------------------------------------------------
# CLINICAL VITAL SIGN THRESHOLDS (WHO IITT Adult >= 12 Years)
# -----------------------------------------------------------------------------

# Oxygen Saturation (%)
SPO2_RED_THRESHOLD = 92.0  # SpO2 < 92% is Red

# Respiratory Rate (breaths/min)
RR_LOW_RED_THRESHOLD = 10.0   # RR < 10 is Red
RR_HIGH_RED_THRESHOLD = 30.0  # RR > 30 is Red

# Heart Rate (beats/min)
HR_LOW_RED_THRESHOLD = 60.0   # HR < 60 is Red
HR_HIGH_RED_THRESHOLD = 130.0 # HR > 130 is Red

# Systolic Blood Pressure (mmHg)
SBP_LOW_RED_THRESHOLD = 90.0  # SBP < 90 is Red (Shock)

# Obstetric Severe Hypertension (mmHg)
OB_SBP_SEVERE_THRESHOLD = 160.0 # SBP >= 160 is Severe Hypertension in Pregnancy
OB_DBP_SEVERE_THRESHOLD = 110.0 # DBP >= 110 is Severe Hypertension in Pregnancy

# Body Temperature (°C)
TEMP_LOW_RED_THRESHOLD = 36.0  # Temp < 36.0°C is Red (Hypothermia)
TEMP_HIGH_RED_THRESHOLD = 39.0 # Temp > 39.0°C is Red (Hyperpyrexia)

# Glasgow Coma Scale (GCS)
GCS_SEVERE_THRESHOLD = 8  # GCS <= 8 indicates severe consciousness impairment

# Age Boundary for Adult IITT Protocol (Years)
PEDIATRIC_AGE_LIMIT = 12  # Patients < 12 require pediatric triage protocol


# -----------------------------------------------------------------------------
# PHYSIOLOGICAL PLAUSIBILITY RANGES (For Numeric Sanity Checks)
# -----------------------------------------------------------------------------

PHYSIOLOGICAL_LIMITS = {
    "spo2": (0.0, 100.0),
    "heart_rate": (20.0, 300.0),
    "respiratory_rate": (4.0, 80.0),
    "systolic_bp": (30.0, 300.0),
    "diastolic_bp": (20.0, 200.0),
    "temperature": (25.0, 45.0),
    "gcs": (3.0, 15.0),
    "age": (0.0, 130.0),
}
