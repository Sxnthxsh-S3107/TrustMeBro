"""
tests/test_unknown.py
---------------------
Tests for Missing Information, Ambiguous Data, and Strict Tri-State Invariants.
"""

import pytest
from rules_engine.red_flags import check_red_flags
from rules_engine.constants import Priority
from rules_engine.validators import parse_tristate, parse_numeric_vital
from rules_engine.models import TriState


def test_missing_critical_chest_pain_discriminators():
    """Chest pain with unknown dyspnea, fainting, and BP must trigger ESCALATE with uncertain=True."""
    payload = {
        "patient_id": "P005",
        "age": 52,
        "chest_pain": True,
        "breathing_difficulty": "unknown",
        "fainting": "unknown",
        "sweating": "unknown",
        "systolic_bp": "unknown",
    }
    res = check_red_flags(payload)
    assert res["priority"] == Priority.ESCALATE.value
    assert res["uncertain"] is True
    assert res["llm_allowed"] is False
    assert res["rule_triggered"] is False


def test_malformed_boolean_values_treated_as_unknown():
    """Malformed strings like 'maybe' or 'not sure' must NEVER silently become False."""
    assert parse_tristate("maybe") == TriState.UNKNOWN
    assert parse_tristate("not sure") == TriState.UNKNOWN
    assert parse_tristate("eighty") == TriState.UNKNOWN
    assert parse_tristate(None) == TriState.UNKNOWN
    assert parse_tristate("") == TriState.UNKNOWN

    # Verified explicit booleans
    assert parse_tristate("true") == TriState.TRUE
    assert parse_tristate("yes") == TriState.TRUE
    assert parse_tristate("false") == TriState.FALSE
    assert parse_tristate("no") == TriState.FALSE


def test_malformed_numeric_vitals():
    """String representations like 'eighty' must not be parsed into numeric 80."""
    assert parse_numeric_vital("eighty", "spo2") is None
    assert parse_numeric_vital("normal", "heart_rate") is None
    assert parse_numeric_vital(-5, "heart_rate") is None  # Out of physiological range
    assert parse_numeric_vital(150, "spo2") is None       # SpO2 > 100% impossible
    assert parse_numeric_vital(True, "spo2") is None      # Boolean True != 1.0


def test_missing_irrelevant_field_does_not_block():
    """Unasked fields for a benign presentation should not unnecessarily block the pipeline."""
    payload = {
        "patient_id": "P006",
        "age": 30,
        "chief_complaint": "mild skin rash on forearm",
        "chest_pain": False,
        "breathing_difficulty": False,
        "unconscious": False,
        "altered_mental_status": False,
        "active_convulsion": False,
        "severe_bleeding": False,
        "sudden_one_sided_weakness": False,
        "facial_or_tongue_swelling": False,
        "spo2": 98.0,
        "heart_rate": 72,
        "respiratory_rate": 16,
        "systolic_bp": 120,
        "temperature": 36.6,
    }
    res = check_red_flags(payload)
    assert res["priority"] == Priority.NO_HARD_RED_FLAG.value
    assert res["llm_allowed"] is True
