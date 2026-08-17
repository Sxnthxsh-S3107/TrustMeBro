"""
rules_engine/confidence_gate.py
-------------------------------
Safety Confidence & Data Completeness Evaluator for LifeLine.

Responsibilities:
  1. Separate safety confidence from LLM confidence (Zero LLM confidence logic here).
  2. Enforce strict tri-state safety checks: missing/unknown != false.
  3. Detect ambiguous or incomplete safety-critical symptom constellations.
  4. Enforce Pediatric Scope Guard (< 12 years).
  5. Handle Unknown Age safely (Never assume adult if age is missing).
  6. Determine whether it is safe to allow the downstream LLM to run.
"""

from typing import Any, Dict, List, Optional, Tuple
from rules_engine.models import TriState
from rules_engine.validators import parse_age, parse_tristate
from rules_engine.constants import PEDIATRIC_AGE_LIMIT


def evaluate_pediatric_scope(intake_data: Dict[str, Any]) -> Tuple[bool, bool, Optional[str]]:
    """
    Check if patient is pediatric (< 12 years) or if age is unknown.
    
    Returns:
      (is_pediatric: bool, age_unknown: bool, rationale: Optional[str])
    """
    age_raw = intake_data.get("age")
    age = parse_age(age_raw)
    
    if age is None:
        # Age is missing or invalid -> Do not silently assume adult
        return (
            False,
            True,
            "Patient age is unrecorded or invalid. Prototype safety rules require verified age to apply adult thresholds safely."
        )
    
    if age < PEDIATRIC_AGE_LIMIT:
        return (
            True,
            False,
            f"Patient is pediatric (age {age} < {PEDIATRIC_AGE_LIMIT} years). Prototype safety engine implements "
            "the WHO IITT Adult (>=12) protocol. Pediatric cases require human clinical evaluation under pediatric protocol."
        )
    
    return False, False, None


def evaluate_critical_missing_data(intake_data: Dict[str, Any]) -> Tuple[bool, List[str], Optional[str]]:
    """
    Evaluate whether critical safety-relevant symptom fields are UNKNOWN / missing
    in a way that prevents safe determination of non-emergency status.
    
    Returns:
      (is_uncertain: bool, missing_fields: List[str], rationale: Optional[str])
    """
    missing_fields: List[str] = []
    
    # 1. Chest pain constellation safety check
    chest_pain = parse_tristate(intake_data.get("chest_pain"))
    if chest_pain.is_true():
        dyspnea = parse_tristate(intake_data.get("breathing_difficulty"))
        syncope = parse_tristate(intake_data.get("fainting"))
        sweating = parse_tristate(intake_data.get("sweating"))
        sbp = intake_data.get("systolic_bp")
        
        # If chest pain is positive but ALL high-risk discriminator questions are UNKNOWN
        if dyspnea.is_unknown() and syncope.is_unknown() and sweating.is_unknown() and (sbp is None or sbp == "unknown"):
            missing_fields.extend(["breathing_difficulty", "fainting", "sweating", "systolic_bp"])
            return (
                True,
                missing_fields,
                "Patient reports chest pain, but critical associated red-flag safety features "
                "(breathing difficulty, fainting, sweating, blood pressure) are unknown or unrecorded."
            )

    # 2. Allergic / airway swelling constellation
    swelling = parse_tristate(intake_data.get("facial_or_tongue_swelling"))
    if swelling.is_true():
        dyspnea = parse_tristate(intake_data.get("breathing_difficulty"))
        stridor = parse_tristate(intake_data.get("stridor"))
        if dyspnea.is_unknown() and stridor.is_unknown():
            missing_fields.extend(["breathing_difficulty", "stridor"])
            return (
                True,
                missing_fields,
                "Patient reports facial/tongue swelling, but airway patency and breathing difficulty "
                "are unknown or unrecorded."
            )

    # 3. Neurological symptom constellation
    sudden_neuro = parse_tristate(intake_data.get("sudden_one_sided_weakness"))
    speech = parse_tristate(intake_data.get("speech_difficulty"))
    if (sudden_neuro.is_unknown() and speech.is_unknown()) and (
        intake_data.get("chief_complaint") and any(
            w in str(intake_data.get("chief_complaint")).lower()
            for w in ["weakness", "numbness", "paralysis", "speech", "slurred", "confusion"]
        )
    ):
        missing_fields.extend(["sudden_one_sided_weakness", "speech_difficulty"])
        return (
            True,
            missing_fields,
            "Chief complaint suggests acute neurological symptoms, but focal weakness and speech "
            "status are unassessed."
        )

    # 4. Pregnancy with unassessed severe symptoms
    pregnant = parse_tristate(intake_data.get("pregnant"))
    if pregnant.is_true():
        bleeding = parse_tristate(intake_data.get("severe_bleeding"))
        abdo_pain = parse_tristate(intake_data.get("severe_abdominal_pain"))
        if bleeding.is_unknown() and abdo_pain.is_unknown():
            missing_fields.extend(["severe_bleeding", "severe_abdominal_pain"])
            return (
                True,
                missing_fields,
                "Patient is pregnant with acute presentation, but obstetric safety discriminators "
                "(bleeding, severe abdominal pain) are unassessed."
            )

    return False, [], None
