"""
rules_engine/validators.py
--------------------------
Defensive input validation, Tri-State parsing, and numeric sanity checks
for Person 1's LifeLine Safety Rule Engine.

Core Principles:
  1. Never crash on malformed patient input.
  2. Missing, null, or unparseable clinical information NEVER silently becomes FALSE.
  3. Numeric fields are validated against physiological plausibility bounds.
  4. 100% Deterministic Python - Zero ML/LLM/External APIs.
"""

import json
from typing import Any, Dict, List, Optional, Tuple, Union
from rules_engine.models import TriState
from rules_engine.constants import PHYSIOLOGICAL_LIMITS


def parse_tristate(value: Any) -> TriState:
    """
    Safely parse any incoming value into strict TriState.
    
    Rules:
      - True (bool), "true", "yes", "y", "positive", "present", "1", 1 -> TriState.TRUE
      - False (bool), "false", "no", "n", "negative", "absent", "0", 0 -> TriState.FALSE
      - None, "", "unknown", "null", "none", "not sure", "maybe", "?", or any invalid string -> TriState.UNKNOWN
      
    CRITICAL SAFETY INVARIANT:
      Missing or unparseable values NEVER silently become False.
    """
    if value is None:
        return TriState.UNKNOWN
    
    if isinstance(value, bool):
        return TriState.TRUE if value else TriState.FALSE
    
    if isinstance(value, (int, float)):
        if value == 1:
            return TriState.TRUE
        if value == 0:
            return TriState.FALSE
        return TriState.UNKNOWN
    
    if isinstance(value, str):
        cleaned = value.strip().lower()
        if cleaned in ("true", "yes", "y", "positive", "present", "1"):
            return TriState.TRUE
        if cleaned in ("false", "no", "n", "negative", "absent", "0"):
            return TriState.FALSE
        # Any other string ("unknown", "maybe", "not sure", "eighty", "null", "") -> UNKNOWN
        return TriState.UNKNOWN
            
    return TriState.UNKNOWN


def parse_numeric_vital(value: Any, param_name: Optional[str] = None) -> Optional[float]:
    """
    Safely parse and validate numeric vital signs.
    
    Returns:
      float value if valid and physiologically plausible,
      or None if missing, malformed, non-numeric (e.g. 'eighty'), or physiologically impossible.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        # Prevent Python's True/False evaluating as 1.0/0.0
        return None
    
    parsed_val: Optional[float] = None
    
    if isinstance(value, (int, float)):
        parsed_val = float(value)
    elif isinstance(value, str):
        cleaned = value.strip()
        if not cleaned or cleaned.lower() in ("unknown", "none", "null", "n/a", "na", "?", "not sure"):
            return None
        try:
            parsed_val = float(cleaned)
        except (ValueError, TypeError):
            return None
    else:
        return None

    if parsed_val is None:
        return None

    # Physiological plausibility sanity check
    if param_name and param_name in PHYSIOLOGICAL_LIMITS:
        min_val, max_val = PHYSIOLOGICAL_LIMITS[param_name]
        if not (min_val <= parsed_val <= max_val):
            return None  # Out-of-range value is treated as invalid/unknown

    return parsed_val


def parse_age(value: Any) -> Optional[int]:
    """
    Safely parse patient age in whole years.
    Returns None if missing, unparseable, or out of realistic human age bounds [0, 130].
    """
    num = parse_numeric_vital(value, "age")
    if num is None:
        return None
    return int(num)


def validate_intake(intake_data: Any) -> Tuple[bool, List[str], Dict[str, Any]]:
    """
    Validate and defensively parse an intake payload.
    
    Accepts:
      - dict (standard python dictionary)
      - str (JSON-encoded string)
      
    Returns:
      (is_valid: bool, validation_errors: List[str], normalized_data: Dict[str, Any])
    """
    errors: List[str] = []
    
    if intake_data is None:
        return False, ["Intake payload is None."], {}
        
    if isinstance(intake_data, str):
        try:
            parsed = json.loads(intake_data)
            if not isinstance(parsed, dict):
                return False, ["Parsed JSON root must be an object (dictionary)."], {}
            normalized = parsed
        except Exception as err:
            return False, [f"Invalid JSON string payload: {str(err)}"], {}
    elif isinstance(intake_data, dict):
        normalized = dict(intake_data)
    else:
        return False, [f"Unsupported intake data type: {type(intake_data).__name__}"], {}
        
    return True, errors, normalized
