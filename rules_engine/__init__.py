"""
LifeLine Safety Rule Engine (Person 1)
--------------------------------------
Deterministic, standalone, safety-critical pre-LLM triage gate.

Public Interface:
    from rules_engine.red_flags import check_red_flags, validate_intake
    result = check_red_flags(patient_data)
"""

from rules_engine.red_flags import check_red_flags
from rules_engine.validators import validate_intake, parse_tristate, parse_numeric_vital, parse_age
from rules_engine.constants import Priority, Source, RuleId
from rules_engine.models import TriState, build_response

__all__ = [
    "check_red_flags",
    "validate_intake",
    "Priority",
    "Source",
    "RuleId",
    "TriState",
    "build_response",
    "parse_tristate",
    "parse_numeric_vital",
    "parse_age",
]

__version__ = "1.0.0"
