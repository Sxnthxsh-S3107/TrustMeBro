"""
tests/test_neurological.py
--------------------------
Tests for Consciousness and Focal Neurological red-flag rules (RF_NEURO_001, RF_NEURO_002, RF_NEURO_FOCAL).
"""

import pytest
from rules_engine.red_flags import check_red_flags
from rules_engine.constants import Priority, RuleId


def test_unconscious():
    res = check_red_flags({"age": 55, "unconscious": True})
    assert res["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_NEURO_001 in res["rule_ids"]
    assert res["llm_allowed"] is False


def test_avpu_impaired_states():
    # 'V' (Voice), 'P' (Pain), 'U' (Unresponsive) must trigger EMERGENCY
    for state in ["V", "P", "U"]:
        res = check_red_flags({"age": 40, "avpu": state})
        assert res["priority"] == Priority.EMERGENCY.value
        assert RuleId.RF_NEURO_001 in res["rule_ids"]

    # 'A' (Alert) should not trigger RF_NEURO_001
    res_alert = check_red_flags({"age": 40, "avpu": "A", "chest_pain": False, "breathing_difficulty": False})
    assert RuleId.RF_NEURO_001 not in res_alert["rule_ids"]


def test_gcs_severe():
    res = check_red_flags({"age": 30, "gcs": 7})
    assert res["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_NEURO_001 in res["rule_ids"]


def test_altered_mental_status():
    res = check_red_flags({"age": 68, "altered_mental_status": True})
    assert res["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_NEURO_002 in res["rule_ids"]


def test_acute_confusion():
    res = check_red_flags({"age": 72, "acute_confusion": True})
    assert res["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_NEURO_002 in res["rule_ids"]


def test_focal_neurological_patterns():
    # Test individual focal deficits
    cases = [
        {"sudden_one_sided_weakness": True},
        {"facial_weakness": True},
        {"speech_difficulty": True},
        {"sudden_vision_change": True},
    ]
    for case in cases:
        payload = {"age": 55, **case}
        res = check_red_flags(payload)
        assert res["priority"] == Priority.EMERGENCY.value
        assert RuleId.RF_NEURO_FOCAL in res["rule_ids"]
        assert res["llm_allowed"] is False

        # Non-diagnostic guarantee: must never output 'stroke' or 'infarction'
        full_text = (res["rationale"] + " " + " ".join(res["red_flags"])).lower()
        assert "stroke" not in full_text
        assert "infarction" not in full_text
