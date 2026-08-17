"""
tests/test_convulsions.py
-------------------------
Tests for Active Convulsions red-flag rules (RF_CONV_001).
"""

import pytest
from rules_engine.red_flags import check_red_flags
from rules_engine.constants import Priority, RuleId


def test_active_convulsion():
    res = check_red_flags({"age": 25, "active_convulsion": True})
    assert res["priority"] == Priority.EMERGENCY.value
    assert res["rule_triggered"] is True
    assert RuleId.RF_CONV_001 in res["rule_ids"]
    assert res["llm_allowed"] is False


def test_actively_seizing():
    res = check_red_flags({"age": 30, "actively_seizing": True})
    assert res["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_CONV_001 in res["rule_ids"]
    assert res["llm_allowed"] is False
