"""
tests/test_circulation.py
-------------------------
Tests for Circulation red-flag rules (RF_CIRC_001, RF_VIT_SBP, RF_VIT_HR).
"""

import pytest
from rules_engine.red_flags import check_red_flags
from rules_engine.constants import Priority, RuleId


def test_severe_bleeding():
    res = check_red_flags({"age": 40, "severe_bleeding": True})
    assert res["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_CIRC_001 in res["rule_ids"]
    assert res["llm_allowed"] is False


def test_uncontrolled_bleeding():
    res = check_red_flags({"age": 35, "uncontrolled_bleeding": True})
    assert res["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_CIRC_001 in res["rule_ids"]
    assert res["llm_allowed"] is False


def test_systolic_bp_boundaries():
    # SBP = 89 mmHg -> Shock / Hypotension EMERGENCY
    res_89 = check_red_flags({"age": 30, "systolic_bp": 89, "chest_pain": False, "breathing_difficulty": False})
    assert res_89["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_VIT_SBP in res_89["rule_ids"]
    assert res_89["llm_allowed"] is False

    # SBP = 90 mmHg -> Normal threshold
    res_90 = check_red_flags({"age": 30, "systolic_bp": 90, "chest_pain": False, "breathing_difficulty": False})
    assert RuleId.RF_VIT_SBP not in res_90["rule_ids"]


def test_heart_rate_boundaries():
    # HR = 59 bpm -> Bradycardia EMERGENCY
    res_59 = check_red_flags({"age": 30, "heart_rate": 59, "chest_pain": False, "breathing_difficulty": False})
    assert res_59["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_VIT_HR in res_59["rule_ids"]

    # HR = 60 bpm -> Normal boundary
    res_60 = check_red_flags({"age": 30, "heart_rate": 60, "chest_pain": False, "breathing_difficulty": False})
    assert RuleId.RF_VIT_HR not in res_60["rule_ids"]

    # HR = 130 bpm -> Normal boundary
    res_130 = check_red_flags({"age": 30, "heart_rate": 130, "chest_pain": False, "breathing_difficulty": False})
    assert RuleId.RF_VIT_HR not in res_130["rule_ids"]

    # HR = 131 bpm -> Tachycardia EMERGENCY
    res_131 = check_red_flags({"age": 30, "heart_rate": 131, "chest_pain": False, "breathing_difficulty": False})
    assert res_131["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_VIT_HR in res_131["rule_ids"]
