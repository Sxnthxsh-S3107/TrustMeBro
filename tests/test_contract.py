"""
tests/test_contract.py
----------------------
Tests for Public Contract Schema, Invariants, JSON Serializability, and Determinism.
"""

import json
import inspect
import pytest
from rules_engine.red_flags import check_red_flags, validate_intake
from rules_engine.constants import Priority, Source
from rules_engine.models import build_response


def test_public_output_contract_structure():
    """Verify that output contains all required fields and matches the contract specification."""
    payload = {
        "patient_id": "P001",
        "age": 45,
        "chest_pain": False,
        "breathing_difficulty": False,
        "spo2": 98.0,
    }
    res = check_red_flags(payload)

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
    json_str = json.dumps(res)
    deserialized = json.loads(json_str)
    assert deserialized["priority"] in ["EMERGENCY", "NO_HARD_RED_FLAG", "ESCALATE"]


def test_strict_invariant_emergency_closes_llm_path():
    """The safety engine must NEVER return priority=EMERGENCY with llm_allowed=True."""
    res = build_response(
        priority=Priority.EMERGENCY,
        source=Source.HARD_RULE,
        rule_triggered=True,
        llm_allowed=True,  # Attempted override must be blocked by builder
    )
    assert res["priority"] == Priority.EMERGENCY.value
    assert res["llm_allowed"] is False


def test_determinism_invariant():
    """Identical input MUST produce identical output across multiple evaluations."""
    payload = {
        "patient_id": "DET_001",
        "age": 52,
        "chest_pain": True,
        "breathing_difficulty": True,
        "spo2": 89.0,
        "systolic_bp": 85.0,
    }

    first_res = check_red_flags(payload)
    for _ in range(10):
        next_res = check_red_flags(payload)
        assert first_res == next_res


def test_zero_external_ai_dependencies():
    """Verify that rules_engine contains zero AI/ML/LLM framework imports."""
    import rules_engine
    import rules_engine.red_flags
    import rules_engine.rules
    import rules_engine.validators
    import rules_engine.security
    import rules_engine.confidence_gate
    import rules_engine.constants
    import rules_engine.models

    forbidden_modules = [
        "openai",
        "google.genai",
        "google.generativeai",
        "anthropic",
        "torch",
        "tensorflow",
        "transformers",
        "sklearn",
        "langchain",
    ]

    for mod in [
        rules_engine,
        rules_engine.red_flags,
        rules_engine.rules,
        rules_engine.validators,
        rules_engine.security,
        rules_engine.confidence_gate,
        rules_engine.constants,
        rules_engine.models,
    ]:
        source_code = inspect.getsource(mod)
        for forbidden in forbidden_modules:
            assert f"import {forbidden}" not in source_code
            assert f"from {forbidden}" not in source_code
