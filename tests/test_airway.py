"""
tests/test_airway.py
--------------------
Tests for Airway compromise red-flag rules (RF_AIRWAY_001).
"""

import pytest
from rules_engine.red_flags import check_red_flags
from rules_engine.constants import Priority, RuleId


def test_stridor_triggers_emergency():
    """Stridor indicates acute upper airway obstruction and must trigger EMERGENCY."""
    res = check_red_flags({"age": 35, "stridor": True})
    assert res["priority"] == Priority.EMERGENCY.value
    assert res["rule_triggered"] is True
    assert RuleId.RF_AIRWAY_001 in res["rule_ids"]
    assert res["llm_allowed"] is False


def test_airway_swelling_triggers_emergency():
    """Airway swelling with compromise must trigger EMERGENCY."""
    res = check_red_flags({"age": 42, "airway_swelling": True})
    assert res["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_AIRWAY_001 in res["rule_ids"]
    assert res["llm_allowed"] is False


def test_facial_tongue_swelling_with_dyspnea():
    """Facial/tongue swelling combined with acute breathing difficulty indicates airway risk."""
    res = check_red_flags({
        "age": 28,
        "facial_or_tongue_swelling": True,
        "breathing_difficulty": True,
    })
    assert res["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_AIRWAY_001 in res["rule_ids"]
    assert res["llm_allowed"] is False


def test_isolated_lip_swelling_without_dyspnea_not_airway_emergency():
    """Isolated swelling without respiratory compromise should not trigger airway emergency."""
    res = check_red_flags({
        "age": 30,
        "facial_or_tongue_swelling": True,
        "breathing_difficulty": False,
        "stridor": False,
        "airway_swelling": False,
    })
    assert RuleId.RF_AIRWAY_001 not in res["rule_ids"]
