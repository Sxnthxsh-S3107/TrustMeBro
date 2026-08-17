"""
tests/test_pediatric.py
-----------------------
Tests for Pediatric Boundary & Age Handling.
"""

import pytest
from rules_engine.red_flags import check_red_flags
from rules_engine.constants import Priority, RuleId


def test_pediatric_non_emergency_escalates():
    """Children under 12 without emergency red flags must escalate for human evaluation."""
    payload = {
        "patient_id": "PED_01",
        "age": 4,
        "chief_complaint": "ear pain and mild fever",
        "chest_pain": False,
        "breathing_difficulty": False,
        "unconscious": False,
        "spo2": 98.0,
    }
    res = check_red_flags(payload)
    assert res["priority"] == Priority.ESCALATE.value
    assert res["pediatric_rule_not_supported"] is True
    assert res["uncertain"] is True
    assert res["llm_allowed"] is False
    assert "pediatric" in res["rationale"].lower()


def test_pediatric_universal_emergency():
    """Universal emergencies (e.g. unresponsiveness or active convulsions) fire immediately in children."""
    payload = {
        "patient_id": "PED_02",
        "age": 4,
        "unconscious": True,
    }
    res = check_red_flags(payload)
    assert res["priority"] == Priority.EMERGENCY.value
    assert res["rule_triggered"] is True
    assert RuleId.RF_NEURO_001 in res["rule_ids"]
    assert res["pediatric_rule_not_supported"] is True
    assert res["llm_allowed"] is False


def test_unknown_age_does_not_assume_adult():
    """If age is null/unknown, the engine must not assume adult; must escalate conservatively."""
    payload = {
        "patient_id": "UNK_01",
        "age": None,
        "chest_pain": False,
        "breathing_difficulty": False,
        "spo2": 98.0,
    }
    res = check_red_flags(payload)
    assert res["priority"] == Priority.ESCALATE.value
    assert res["uncertain"] is True
    assert res["llm_allowed"] is False


def test_adult_age_boundary_at_12():
    """Age 12 is the adult/older child IITT protocol boundary."""
    payload = {
        "patient_id": "ADULT_01",
        "age": 12,
        "chest_pain": False,
        "breathing_difficulty": False,
        "spo2": 98.0,
    }
    res = check_red_flags(payload)
    assert res["pediatric_rule_not_supported"] is False
    assert res["priority"] == Priority.NO_HARD_RED_FLAG.value
    assert res["llm_allowed"] is True
