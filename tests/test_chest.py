"""
tests/test_chest.py
-------------------
Tests for High-Risk Chest Symptom Pattern rules (RF_CHEST_001).
"""

import pytest
from rules_engine.red_flags import check_red_flags
from rules_engine.constants import Priority, RuleId


def test_isolated_chest_pain_with_negative_discriminators_not_emergency():
    """Isolated chest pain with confirmed negative high-risk features does not trigger emergency."""
    res = check_red_flags({
        "age": 45,
        "chest_pain": True,
        "breathing_difficulty": False,
        "fainting": False,
        "sweating": False,
        "radiating_pain": False,
        "systolic_bp": 125,
        "spo2": 98.0,
    })
    assert RuleId.RF_CHEST_001 not in res["rule_ids"]
    assert res["priority"] == Priority.NO_HARD_RED_FLAG.value
    assert res["llm_allowed"] is True


def test_chest_pain_with_dyspnea():
    res = check_red_flags({
        "age": 52,
        "chest_pain": True,
        "breathing_difficulty": True,
    })
    assert res["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_CHEST_001 in res["rule_ids"]
    assert res["llm_allowed"] is False


def test_chest_pain_with_fainting():
    res = check_red_flags({
        "age": 58,
        "chest_pain": True,
        "fainting": True,
    })
    assert res["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_CHEST_001 in res["rule_ids"]


def test_chest_pain_with_sweating():
    res = check_red_flags({
        "age": 60,
        "chest_pain": True,
        "sweating": True,
    })
    assert res["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_CHEST_001 in res["rule_ids"]


def test_chest_pain_with_hypotension():
    res = check_red_flags({
        "age": 55,
        "chest_pain": True,
        "systolic_bp": 85,
    })
    assert res["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_CHEST_001 in res["rule_ids"]
    assert RuleId.RF_VIT_SBP in res["rule_ids"]
