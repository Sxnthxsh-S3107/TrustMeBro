"""
tests/test_breathing.py
-----------------------
Tests for Breathing red-flag rules (RF_RESP_001, RF_VIT_SPO2, RF_VIT_RR).
"""

import pytest
from rules_engine.red_flags import check_red_flags
from rules_engine.constants import Priority, RuleId


def test_severe_respiratory_distress():
    res = check_red_flags({"age": 45, "severe_respiratory_distress": True})
    assert res["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_RESP_001 in res["rule_ids"]
    assert res["llm_allowed"] is False


def test_central_cyanosis():
    res = check_red_flags({"age": 50, "central_cyanosis": True})
    assert res["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_RESP_001 in res["rule_ids"]
    assert res["llm_allowed"] is False


def test_spo2_threshold_boundaries():
    # SpO2 = 91% (below 92%) -> EMERGENCY
    res_91 = check_red_flags({"age": 30, "spo2": 91.0, "chest_pain": False, "breathing_difficulty": False})
    assert res_91["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_VIT_SPO2 in res_91["rule_ids"]
    assert res_91["llm_allowed"] is False

    # SpO2 = 92% (at threshold) -> Normal / not triggering SpO2 emergency
    res_92 = check_red_flags({"age": 30, "spo2": 92.0, "chest_pain": False, "breathing_difficulty": False})
    assert RuleId.RF_VIT_SPO2 not in res_92["rule_ids"]

    # SpO2 = 93% (above threshold) -> Normal
    res_93 = check_red_flags({"age": 30, "spo2": 93.0, "chest_pain": False, "breathing_difficulty": False})
    assert RuleId.RF_VIT_SPO2 not in res_93["rule_ids"]


def test_respiratory_rate_boundaries():
    # RR = 9 /min -> Low RR emergency
    res_9 = check_red_flags({"age": 30, "respiratory_rate": 9, "chest_pain": False, "breathing_difficulty": False})
    assert res_9["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_VIT_RR in res_9["rule_ids"]

    # RR = 10 /min -> Normal boundary
    res_10 = check_red_flags({"age": 30, "respiratory_rate": 10, "chest_pain": False, "breathing_difficulty": False})
    assert RuleId.RF_VIT_RR not in res_10["rule_ids"]

    # RR = 30 /min -> Normal boundary
    res_30 = check_red_flags({"age": 30, "respiratory_rate": 30, "chest_pain": False, "breathing_difficulty": False})
    assert RuleId.RF_VIT_RR not in res_30["rule_ids"]

    # RR = 31 /min -> Tachypnea emergency
    res_31 = check_red_flags({"age": 30, "respiratory_rate": 31, "chest_pain": False, "breathing_difficulty": False})
    assert res_31["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_VIT_RR in res_31["rule_ids"]
