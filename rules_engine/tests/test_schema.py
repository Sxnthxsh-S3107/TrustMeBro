"""
Unit tests for schema parsing, TriState logic, and output contracts.
"""

import json
import pytest
from rules_engine.schemas import (
    Priority,
    Source,
    TriState,
    build_response,
    parse_age,
    parse_numeric,
    parse_tristate,
)
from rules_engine.red_flags import validate_intake, check_red_flags


def test_tristate_parsing_strictness():
    """Verify that missing/unknown values never become False."""
    # True values
    assert parse_tristate(True) == TriState.TRUE
    assert parse_tristate("true") == TriState.TRUE
    assert parse_tristate("YES") == TriState.TRUE
    assert parse_tristate(1) == TriState.TRUE
    assert parse_tristate("present") == TriState.TRUE

    # False values
    assert parse_tristate(False) == TriState.FALSE
    assert parse_tristate("false") == TriState.FALSE
    assert parse_tristate("no") == TriState.FALSE
    assert parse_tristate(0) == TriState.FALSE
    assert parse_tristate("absent") == TriState.FALSE

    # UNKNOWN values (Must NEVER be False)
    assert parse_tristate(None) == TriState.UNKNOWN
    assert parse_tristate("unknown") == TriState.UNKNOWN
    assert parse_tristate("Unknown") == TriState.UNKNOWN
    assert parse_tristate("") == TriState.UNKNOWN
    assert parse_tristate("?") == TriState.UNKNOWN
    assert parse_tristate("n/a") == TriState.UNKNOWN
    assert parse_tristate("maybe") == TriState.UNKNOWN
    assert parse_tristate(42) == TriState.UNKNOWN


def test_numeric_parsing():
    """Verify robust numeric vital sign parsing."""
    assert parse_numeric(95) == 95.0
    assert parse_numeric("95.5") == 95.5
    assert parse_numeric(None) is None
    assert parse_numeric("unknown") is None
    assert parse_numeric("invalid_string") is None
    assert parse_numeric(True) is None  # Boolean True should not be parsed as 1.0
    assert parse_numeric(False) is None


def test_age_parsing():
    """Verify safe age parsing in whole years."""
    assert parse_age(45) == 45
    assert parse_age("45") == 45
    assert parse_age(0) == 0
    assert parse_age(-5) is None
    assert parse_age(None) is None
    assert parse_age("unknown") is None


def test_output_contract_keys():
    """Verify that all required response keys are present and JSON serializable."""
    res = build_response(
        priority=Priority.NO_HARD_RED_FLAG,
        source=Source.HARD_RULE,
        rule_triggered=False,
        rule_ids=[],
        red_flags=[],
        rationale="All safe",
        uncertain=False,
        pediatric_rule_not_supported=False,
        llm_allowed=True,
        security_alerts=[],
    )

    required_keys = {
        "priority",
        "source",
        "rule_triggered",
        "rule_ids",
        "red_flags",
        "rationale",
        "uncertain",
        "pediatric_rule_not_supported",
        "llm_allowed",
        "security_alerts",
    }
    assert set(res.keys()) == required_keys

    # Must be 100% JSON serializable
    serialized = json.dumps(res)
    deserialized = json.loads(serialized)
    assert deserialized["priority"] == "NO_HARD_RED_FLAG"
    assert deserialized["llm_allowed"] is True


def test_emergency_invariants():
    """Verify that EMERGENCY or ESCALATE strictly enforces llm_allowed = False."""
    # Attempting to pass llm_allowed=True with EMERGENCY must be overridden to False
    res_emergency = build_response(
        priority=Priority.EMERGENCY,
        source=Source.HARD_RULE,
        rule_triggered=True,
        llm_allowed=True,  # Attempted override
    )
    assert res_emergency["priority"] == "EMERGENCY"
    assert res_emergency["llm_allowed"] is False

    # Attempting to pass llm_allowed=True with ESCALATE must be overridden to False
    res_escalate = build_response(
        priority=Priority.ESCALATE,
        source=Source.SAFETY_ENGINE,
        rule_triggered=False,
        uncertain=True,
        llm_allowed=True,  # Attempted override
    )
    assert res_escalate["priority"] == "ESCALATE"
    assert res_escalate["llm_allowed"] is False


def test_json_string_intake():
    """Verify check_red_flags accepts a raw JSON string as input."""
    payload = json.dumps({
        "patient_id": "P100",
        "age": 40,
        "chest_pain": False,
        "breathing_difficulty": False,
        "unconscious": True,
    })
    res = check_red_flags(payload)
    assert res["priority"] == "EMERGENCY"
    assert res["rule_triggered"] is True
    assert "RF_NEURO_001" in res["rule_ids"]
    assert res["llm_allowed"] is False
