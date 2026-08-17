"""
rules_engine/models.py
----------------------
Data models, strict Tri-State representation, and output response builders
for Person 1's LifeLine Safety Rule Engine.

100% Deterministic Python - Zero ML/LLM/External APIs.
"""

from typing import Any, Dict, List, Optional, Union
from enum import Enum
from rules_engine.constants import Priority, Source


class TriState(Enum):
    """
    Strict tri-state logic for safety-critical clinical symptoms:
      - TRUE: Explicitly confirmed positive
      - FALSE: Explicitly confirmed negative
      - UNKNOWN: Missing, null, unasked, ambiguous, or unparseable
    """
    TRUE = "true"
    FALSE = "false"
    UNKNOWN = "unknown"

    def is_true(self) -> bool:
        return self == TriState.TRUE

    def is_false(self) -> bool:
        return self == TriState.FALSE

    def is_unknown(self) -> bool:
        return self == TriState.UNKNOWN


def build_response(
    priority: Union[Priority, str],
    source: Union[Source, str],
    rule_triggered: bool,
    rule_ids: Optional[List[str]] = None,
    red_flags: Optional[List[str]] = None,
    rationale: str = "",
    uncertain: bool = False,
    pediatric_rule_not_supported: bool = False,
    llm_allowed: bool = False,
    security_alerts: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Construct the standard JSON-serializable output contract for LifeLine.
    
    NON-NEGOTIABLE SAFETY INVARIANT:
      If priority == "EMERGENCY" or priority == "ESCALATE",
      llm_allowed MUST ALWAYS be False.
      It is structurally impossible to return (EMERGENCY and llm_allowed=True).
    """
    priority_val = priority.value if isinstance(priority, Priority) else str(priority)
    source_val = source.value if isinstance(source, Source) else str(source)
    
    # Enforce non-overridable invariant
    if priority_val in (Priority.EMERGENCY.value, Priority.ESCALATE.value):
        computed_llm_allowed = False
    else:
        computed_llm_allowed = bool(llm_allowed)

    return {
        "priority": priority_val,
        "source": source_val,
        "rule_triggered": bool(rule_triggered),
        "rule_ids": list(rule_ids or []),
        "red_flags": list(red_flags or []),
        "rationale": str(rationale),
        "uncertain": bool(uncertain),
        "pediatric_rule_not_supported": bool(pediatric_rule_not_supported),
        "llm_allowed": computed_llm_allowed,
        "security_alerts": list(security_alerts or []),
    }
