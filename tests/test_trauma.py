"""
tests/test_trauma.py
--------------------
Tests for High-Risk Trauma red-flag rules (RF_TRAUMA_001).
"""

import pytest
from rules_engine.red_flags import check_red_flags
from rules_engine.constants import Priority, RuleId


def test_major_trauma():
    res = check_red_flags({"age": 35, "major_trauma": True})
    assert res["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_TRAUMA_001 in res["rule_ids"]
    assert res["llm_allowed"] is False


def test_penetrating_injury():
    res = check_red_flags({"age": 28, "penetrating_injury": True})
    assert res["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_TRAUMA_001 in res["rule_ids"]


def test_severe_burn():
    res = check_red_flags({"age": 45, "severe_burn": True})
    assert res["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_TRAUMA_001 in res["rule_ids"]
