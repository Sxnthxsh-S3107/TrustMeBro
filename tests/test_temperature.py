"""
tests/test_temperature.py
-------------------------
Tests for Body Temperature red-flag rules (RF_TEMP_001).
"""

import pytest
from rules_engine.red_flags import check_red_flags
from rules_engine.constants import Priority, RuleId


def test_temperature_hypothermia_boundary():
    # 35.9°C -> Hypothermia EMERGENCY
    res_low = check_red_flags({"age": 30, "temperature": 35.9, "chest_pain": False, "breathing_difficulty": False})
    assert res_low["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_TEMP_001 in res_low["rule_ids"]
    assert res_low["llm_allowed"] is False

    # 36.0°C -> Normal boundary
    res_36 = check_red_flags({"age": 30, "temperature": 36.0, "chest_pain": False, "breathing_difficulty": False})
    assert RuleId.RF_TEMP_001 not in res_36["rule_ids"]


def test_temperature_hyperpyrexia_boundary():
    # 39.0°C -> Normal boundary
    res_39 = check_red_flags({"age": 30, "temperature": 39.0, "chest_pain": False, "breathing_difficulty": False})
    assert RuleId.RF_TEMP_001 not in res_39["rule_ids"]

    # 39.1°C -> Hyperpyrexia EMERGENCY
    res_high = check_red_flags({"age": 30, "temperature": 39.1, "chest_pain": False, "breathing_difficulty": False})
    assert res_high["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_TEMP_001 in res_high["rule_ids"]
    assert res_high["llm_allowed"] is False
