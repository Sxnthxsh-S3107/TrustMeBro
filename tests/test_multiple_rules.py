"""
tests/test_multiple_rules.py
----------------------------
Tests for Simultaneous Multiple Emergency Rules Aggregation.
"""

import pytest
from rules_engine.red_flags import check_red_flags
from rules_engine.constants import Priority, RuleId


def test_multiple_simultaneous_emergencies_collected():
    """
    Test 4 from specification:
    Low SpO2 (88%) + hypotension (SBP 82) + tachycardia (HR 140) + severe bleeding.
    Engine must run ALL rules and collect ALL triggered rule IDs.
    """
    payload = {
        "patient_id": "MULTI_001",
        "age": 45,
        "spo2": 88.0,
        "systolic_bp": 82.0,
        "heart_rate": 140.0,
        "severe_bleeding": True,
        "chest_pain": False,
        "breathing_difficulty": True,
    }
    res = check_red_flags(payload)
    assert res["priority"] == Priority.EMERGENCY.value
    assert res["rule_triggered"] is True
    assert res["llm_allowed"] is False

    expected_rules = {
        RuleId.RF_VIT_SPO2,
        RuleId.RF_VIT_SBP,
        RuleId.RF_VIT_HR,
        RuleId.RF_CIRC_001,
    }
    assert expected_rules.issubset(set(res["rule_ids"]))
    assert len(res["red_flags"]) >= 4


def test_neurological_and_airway_multisystem():
    """Unconscious patient with stridor and hypothermia."""
    payload = {
        "patient_id": "MULTI_002",
        "age": 65,
        "unconscious": True,
        "stridor": True,
        "temperature": 34.5,
    }
    res = check_red_flags(payload)
    assert res["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_NEURO_001 in res["rule_ids"]
    assert RuleId.RF_AIRWAY_001 in res["rule_ids"]
    assert RuleId.RF_TEMP_001 in res["rule_ids"]
    assert res["llm_allowed"] is False
