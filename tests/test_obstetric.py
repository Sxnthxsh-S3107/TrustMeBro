"""
tests/test_obstetric.py
-----------------------
Tests for Obstetric Red Flags (RF_OB_001).
"""

import pytest
from rules_engine.red_flags import check_red_flags
from rules_engine.constants import Priority, RuleId


def test_pregnancy_with_severe_bleeding():
    res = check_red_flags({
        "age": 28,
        "pregnant": True,
        "severe_bleeding": True,
    })
    assert res["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_OB_001 in res["rule_ids"]
    assert res["llm_allowed"] is False


def test_pregnancy_with_severe_abdominal_pain():
    res = check_red_flags({
        "age": 24,
        "pregnant": True,
        "severe_abdominal_pain": True,
    })
    assert res["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_OB_001 in res["rule_ids"]


def test_pregnancy_with_severe_hypertension():
    res = check_red_flags({
        "age": 31,
        "pregnant": True,
        "systolic_bp": 165,
        "diastolic_bp": 112,
    })
    assert res["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_OB_001 in res["rule_ids"]


def test_non_pregnant_with_mild_symptoms_not_obstetric_emergency():
    res = check_red_flags({
        "age": 29,
        "pregnant": False,
        "chest_pain": False,
        "breathing_difficulty": False,
        "spo2": 99.0,
    })
    assert RuleId.RF_OB_001 not in res["rule_ids"]
