"""
tests/test_toxic_exposure.py
----------------------------
Tests for Poisoning & Toxic Exposure red-flag rules (RF_TOX_001).
"""

import pytest
from rules_engine.red_flags import check_red_flags
from rules_engine.constants import Priority, RuleId


def test_poisoning():
    res = check_red_flags({"age": 30, "poisoning": True})
    assert res["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_TOX_001 in res["rule_ids"]
    assert res["llm_allowed"] is False


def test_chemical_exposure():
    res = check_red_flags({"age": 42, "chemical_exposure": True})
    assert res["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_TOX_001 in res["rule_ids"]


def test_snakebite():
    res = check_red_flags({"age": 27, "snakebite": True})
    assert res["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_TOX_001 in res["rule_ids"]
