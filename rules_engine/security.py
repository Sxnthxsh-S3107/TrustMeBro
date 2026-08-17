"""
rules_engine/security.py
------------------------
Deterministic Security & Prompt-Injection Scanner for LifeLine.

Architectural Defense:
    PATIENT TEXT = DATA
    PATIENT TEXT ≠ INSTRUCTIONS

The Safety Rule Engine operates exclusively on structured clinical facts.
This module audits free-text fields (chief_complaint, notes, raw text) for
adversarial instruction-like patterns to maintain an audit trail in `security_alerts`.

CRITICAL INVARIANTS:
    1. The scanner NEVER modifies clinical facts.
    2. The scanner NEVER executes instructions.
    3. The scanner NEVER downgrades an emergency.
    4. The scanner NEVER triggers emergency solely because an injection string exists.
"""

import re
from typing import Any, Dict, List, Set, Tuple


# Known adversarial prompt injection and override patterns
INJECTION_PATTERNS = [
    r"(?i)\bignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions\b",
    r"(?i)\bmark\s+(?:me|patient|this\s+case)\s+(?:as\s+)?(?:routine|normal|safe|non-urgent)\b",
    r"(?i)\bdo\s+not\s+tell\s+(?:the\s+)?doctor\b",
    r"(?i)\b(?:system|assistant|admin|developer)\s*:\s*",
    r"(?i)\b(?:override|bypass|disable)\s+(?:triage|safety|priority|rule|protocol)\b",
    r"(?i)\bpriority\s*=\s*(?:routine|normal|low)\b",
    r"(?i)\bemergency\s*=\s*(?:false|0|none)\b",
    r"(?i)\bllm_allowed\b",
    r"(?i)\bset\s+(?:priority|urgency)\s+to\s+(?:routine|green|low)\b",
    r"(?i)\byou\s+are\s+now\s+in\s+(?:unrestricted|dan|developer|jailbreak)\s+mode\b",
    r"(?i)\bdisregard\s+(?:safety|medical|red\s+flag)\b",
]

COMPILED_PATTERNS = [re.compile(p) for p in INJECTION_PATTERNS]


def scan_security_alerts(intake_data: Dict[str, Any]) -> List[str]:
    """
    Deterministically scan text values within intake_data for adversarial instruction strings.
    
    Returns:
      List[str]: Human-readable audit messages identifying detected patterns.
    """
    alerts: List[str] = []
    
    if not isinstance(intake_data, dict):
        return alerts

    text_fragments: List[Tuple[str, str]] = []
    
    for key, value in intake_data.items():
        if isinstance(value, str):
            text_fragments.append((key, value))
        elif isinstance(value, (list, tuple)):
            for idx, item in enumerate(value):
                if isinstance(item, str):
                    text_fragments.append((f"{key}[{idx}]", item))
        elif isinstance(value, dict):
            for subkey, subvalue in value.items():
                if isinstance(subvalue, str):
                    text_fragments.append((f"{key}.{subkey}", subvalue))

    for field_name, text in text_fragments:
        for pattern in COMPILED_PATTERNS:
            match = pattern.search(text)
            if match:
                matched_snippet = match.group(0).strip()
                alert_msg = f"Adversarial instruction pattern '{matched_snippet}' detected in field '{field_name}'"
                if alert_msg not in alerts:
                    alerts.append(alert_msg)

    return alerts
