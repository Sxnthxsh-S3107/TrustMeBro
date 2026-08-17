"""Static demo doctor profiles + capability keyword mapping."""

DOCTORS = {
    "dr_a": {"name": "Dr. A", "capabilities": ["fever", "infection", "elderly", "general"]},
    "dr_b": {"name": "Dr. B", "capabilities": ["respiratory", "chest", "chronic", "cough", "breathless"]},
    "dr_c": {"name": "Dr. C", "capabilities": ["injury", "pain", "wound", "fracture", "general"]},
}

# keyword → doctor capability weight boost
CAPABILITY_KEYWORDS = {
    "fever": "dr_a", "infection": "dr_a", "elderly": "dr_a",
    "cold": "dr_a", "weakness": "dr_a",
    "chest": "dr_b", "respiratory": "dr_b", "breathless": "dr_b",
    "cough": "dr_b", "chronic": "dr_b", "asthma": "dr_b",
    "injury": "dr_c", "pain": "dr_c", "wound": "dr_c",
    "fracture": "dr_c", "accident": "dr_c",
}