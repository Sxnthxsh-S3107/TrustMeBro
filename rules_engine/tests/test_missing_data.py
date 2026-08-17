"""
Tests for missing information, ambiguous values, and pediatric scoping.
"""

import pytest
from rules_engine.red_flags import check_red_flags
from rules_engine.constants import Priority, RuleId


def test_missing_critical_chest_pain_discriminators():
    """
    If chest pain is reported positive, but all safety discriminators
    (dyspnea, fainting, sweating) are UNKNOWN/missing, the system must NOT
    assume they are false. It must ESCALATE with uncertain=True and llm_allowed=False.
    """
    data = {
        "patient_id": "P002",
        "age": 52,
        "chest_pain": True,
        "breathing_difficulty": "unknown",
        "fainting": "unknown",
        "sweating": "unknown",
    }
    res = check_red_flags(data)
    assert res["priority"] == Priority.ESCALATE.value
    assert res["uncertain"] is True
    assert res["llm_allowed"] is False
    assert res["rule_triggered"] is False
    assert "chest pain" in res["rationale"].lower()


def test_missing_critical_airway_swelling_discriminators():
    """
    If facial or tongue swelling is present, but breathing difficulty and stridor are UNKNOWN,
    system must ESCALATE with uncertain=True.
    """
    data = {
        "age": 25,
        "facial_or_tongue_swelling": True,
        "breathing_difficulty": None,
        "stridor": "unknown",
    }
    res = check_red_flags(data)
    assert res["priority"] == Priority.ESCALATE.value
    assert res["uncertain"] is True
    assert res["llm_allowed"] is False


def test_pediatric_scope_under_12_non_emergency():
    """
    Patients under 12 years old must not have adult triage rules applied silently.
    Must return ESCALATE with pediatric_rule_not_supported=True and llm_allowed=False.
    """
    data = {
        "patient_id": "PED_01",
        "age": 8,
        "chief_complaint": "ear pain",
        "chest_pain": False,
        "breathing_difficulty": False,
        "unconscious": False,
        "spo2": 99.0,
    }
    res = check_red_flags(data)
    assert res["priority"] == Priority.ESCALATE.value
    assert res["uncertain"] is True
    assert res["pediatric_rule_not_supported"] is True
    assert res["llm_allowed"] is False
    assert "pediatric" in res["rationale"].lower()


def test_pediatric_with_immediate_emergency_red_flag():
    """
    If a pediatric patient has an absolute universal red flag (e.g. active convulsion),
    EMERGENCY is triggered immediately and pediatric_rule_not_supported is flagged.
    """
    data = {
        "patient_id": "PED_02",
        "age": 4,
        "active_convulsion": True,
    }
    res = check_red_flags(data)
    assert res["priority"] == Priority.EMERGENCY.value
    assert res["rule_triggered"] is True
    assert RuleId.RF_CONV_001 in res["rule_ids"]
    assert res["pediatric_rule_not_supported"] is True
    assert res["llm_allowed"] is False


def test_adult_age_boundary():
    """Patients age 12 and above are processed under the adult IITT ruleset."""
    data_12 = {
        "age": 12,
        "chest_pain": False,
        "breathing_difficulty": False,
        "spo2": 98.0,
    }
    res_12 = check_red_flags(data_12)
    assert res_12["pediatric_rule_not_supported"] is False
    assert res_12["priority"] == Priority.NO_HARD_RED_FLAG.value
    assert res_12["llm_allowed"] is True


def test_null_and_malformed_inputs():
    """System must gracefully handle None, empty dicts, and corrupt payloads without throwing."""
    # None input
    res_none = check_red_flags(None)
    assert res_none["priority"] == Priority.ESCALATE.value
    assert res_none["uncertain"] is True
    assert res_none["llm_allowed"] is False

    # Malformed JSON string
    res_bad_json = check_red_flags("{malformed_json: true,}")
    assert res_bad_json["priority"] == Priority.ESCALATE.value
    assert res_bad_json["uncertain"] is True
    assert res_bad_json["llm_allowed"] is False

    # Non-dict JSON root
    res_array_json = check_red_flags("[1, 2, 3]")
    assert res_array_json["priority"] == Priority.ESCALATE.value
    assert res_array_json["uncertain"] is True
    assert res_array_json["llm_allowed"] is False
