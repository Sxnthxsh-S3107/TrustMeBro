"""
rules_engine/red_flags.py
-------------------------
Main entry point and public interface for Person 1's LifeLine Safety Rule Engine.

Public Interface:
    from rules_engine.red_flags import check_red_flags, validate_intake
    result = check_red_flags(patient_data)

Core Safety Principles:
    1. 100% Deterministic Python - Zero ML, LLM, or probabilistic models.
    2. Hardcoded safety rules run BEFORE the LLM.
    3. If priority == "EMERGENCY" or "ESCALATE", llm_allowed MUST BE False.
    4. Tri-state logic: Missing/unknown values NEVER silently become False.
    5. Non-diagnostic: Detects red-flag clinical patterns, never outputs disease diagnosis.
    6. Non-prescriptive: Never outputs medication or treatment advice.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
from rules_engine.constants import Priority, Source
from rules_engine.models import build_response
from rules_engine.validators import validate_intake
from rules_engine.security import scan_security_alerts
from rules_engine.confidence_gate import (
    evaluate_pediatric_scope,
    evaluate_critical_missing_data,
)
from rules_engine.rules import evaluate_all_rules


def check_red_flags(patient_data: Union[Dict[str, Any], str]) -> Dict[str, Any]:
    """
    Evaluate structured patient facts against hardcoded deterministic safety rules.
    
    Returns standard LifeLine safety response dictionary:
      - priority: "EMERGENCY" | "NO_HARD_RED_FLAG" | "ESCALATE"
      - source: "HARD_RULE" | "SAFETY_ENGINE"
      - rule_triggered: bool
      - rule_ids: List[str]
      - red_flags: List[str]
      - rationale: str
      - uncertain: bool
      - pediatric_rule_not_supported: bool
      - llm_allowed: bool
      - security_alerts: List[str]
    """
    # Step 1: Input Validation & Normalization
    is_valid, validation_errors, clean_data = validate_intake(patient_data)
    if not is_valid:
        return build_response(
            priority=Priority.ESCALATE,
            source=Source.SAFETY_ENGINE,
            rule_triggered=False,
            rule_ids=[],
            red_flags=[],
            rationale=f"Invalid intake payload: {'; '.join(validation_errors)}",
            uncertain=True,
            pediatric_rule_not_supported=False,
            llm_allowed=False,
            security_alerts=[],
        )

    # Step 2: Adversarial Security Audit Scan (Text = DATA, never instructions)
    security_alerts = scan_security_alerts(clean_data)

    # Step 3: Check Pediatric Scope & Age Availability
    is_pediatric, age_unknown, pediatric_rationale = evaluate_pediatric_scope(clean_data)

    # Step 4: Evaluate ALL Hard Red-Flag Rules (runs all rules without short-circuiting)
    triggered_rule_ids, red_flag_descriptions, rule_rationales = evaluate_all_rules(clean_data)

    # If any mandatory emergency red flag triggered -> IMMEDIATE EMERGENCY
    if triggered_rule_ids:
        combined_rationale = "A mandatory emergency red flag was detected: " + " | ".join(rule_rationales)
        return build_response(
            priority=Priority.EMERGENCY,
            source=Source.HARD_RULE,
            rule_triggered=True,
            rule_ids=triggered_rule_ids,
            red_flags=red_flag_descriptions,
            rationale=combined_rationale,
            uncertain=False,
            pediatric_rule_not_supported=is_pediatric,
            llm_allowed=False,  # HARD GATE: LLM PATH IS CLOSED
            security_alerts=security_alerts,
        )

    # Step 5: Pediatric Scope Handling (No emergency rule fired, but patient is pediatric < 12yo)
    if is_pediatric:
        return build_response(
            priority=Priority.ESCALATE,
            source=Source.SAFETY_ENGINE,
            rule_triggered=False,
            rule_ids=[],
            red_flags=[],
            rationale=pediatric_rationale or "Pediatric case requires human clinical evaluation.",
            uncertain=True,
            pediatric_rule_not_supported=True,
            llm_allowed=False,  # HARD GATE: LLM NOT ALLOWED FOR UNSUPPORTED PEDIATRIC SCOPE
            security_alerts=security_alerts,
        )

    # Step 6: Unknown Age Handling (No emergency rule fired, but age is missing/null)
    if age_unknown:
        return build_response(
            priority=Priority.ESCALATE,
            source=Source.SAFETY_ENGINE,
            rule_triggered=False,
            rule_ids=[],
            red_flags=[],
            rationale=pediatric_rationale or "Patient age is missing; cannot safely apply adult triage thresholds.",
            uncertain=True,
            pediatric_rule_not_supported=False,
            llm_allowed=False,  # HARD GATE: LLM NOT ALLOWED ON UNKNOWN AGE
            security_alerts=security_alerts,
        )

    # Step 7: Confidence Gate - Missing Safety-Critical Information
    is_uncertain, missing_fields, missing_rationale = evaluate_critical_missing_data(clean_data)
    if is_uncertain:
        return build_response(
            priority=Priority.ESCALATE,
            source=Source.SAFETY_ENGINE,
            rule_triggered=False,
            rule_ids=[],
            red_flags=[],
            rationale=missing_rationale or "Required safety information is incomplete.",
            uncertain=True,
            pediatric_rule_not_supported=False,
            llm_allowed=False,  # HARD GATE: LLM NOT ALLOWED ON MISSING SAFETY DATA
            security_alerts=security_alerts,
        )

    # Step 8: Safe Case - No Hard Red Flag Detected
    return build_response(
        priority=Priority.NO_HARD_RED_FLAG,
        source=Source.HARD_RULE,
        rule_triggered=False,
        rule_ids=[],
        red_flags=[],
        rationale="No mandatory emergency red flag was detected by the hard safety rules.",
        uncertain=False,
        pediatric_rule_not_supported=False,
        llm_allowed=True,  # SAFE: LLM IS ALLOWED TO RUN DOWNSTREAM
        security_alerts=security_alerts,
    )
