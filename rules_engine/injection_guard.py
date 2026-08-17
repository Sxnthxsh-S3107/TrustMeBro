"""
rules_engine/injection_guard.py
-------------------------------
Backwards-compatibility bridge re-exporting security scanner functions.
"""

from rules_engine.security import scan_security_alerts as scan_for_injections

__all__ = [
    "scan_for_injections",
]
