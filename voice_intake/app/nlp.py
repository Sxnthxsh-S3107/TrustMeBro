"""NLP normalization and entity extraction module for Voice Intake.
Supports English, Tamil script, and Tanglish (phonetic Tamil in Latin script).
"""

import re
import unicodedata
from typing import Dict, List, Optional, Tuple, Any

# =====================================================================
# Centralized Dictionaries & Phrase Patterns
# =====================================================================

CHIEF_COMPLAINT_PATTERNS = {
    "chest pain": {
        "en": [
            r"\bchest\s+pain\b",
            r"\bpain\s+in\s+(?:my\s+)?chest\b",
            r"\bchest\s+hurts?\b",
            r"\bchest\s+hurting\b",
            r"\bchest\s+ache\b",
            r"\bheart\s+pain\b",
            r"\bchest\s+pressure\b",
            r"\bpressure\s+in\s+chest\b",
            r"\bdiscomfort\s+in\s+chest\b",
        ],
        "ta_script": [
            r"நெஞ்சு\s*வலி",
            r"நெஞ்சு\s*வலிக்குது",
            r"நெஞ்சு\s*வலிக்கிறது",
            r"நெஞ்சில்\s*வலி",
            r"மார்பு\s*வலி",
            r"மார்\s*வலி",
        ],
        "ta_tanglish": [
            r"\bnenju\s*vali\b",
            r"\bnenju\s*valikuthu\b",
            r"\bnenju\s*valikudhu\b",
            r"\bnenjula\s*vali\b",
            r"\bchest\s*vali\b",
            r"\bmarbu\s*vali\b",
            r"\bmarpu\s*vali\b",
        ],
    },
    "headache": {
        "en": [
            r"\bheadache\b",
            r"\bhead\s+pain\b",
            r"\bpain\s+in\s+(?:my\s+)?head\b",
            r"\bhead\s+hurts?\b",
            r"\bhead\s+hurting\b",
            r"\bhead\s+ache\b",
            r"\bmigraine\b",
        ],
        "ta_script": [
            r"தலை\s*வலி",
            r"தலை\s*வலிக்குது",
            r"தலை\s*வலிக்கிறது",
            r"தலையில\s*வலி",
            r"தலைவலி",
        ],
        "ta_tanglish": [
            r"\bthalai\s*vali\b",
            r"\bthalai\s*valikuthu\b",
            r"\bthalai\s*valikudhu\b",
            r"\bthala\s*vali\b",
            r"\bthala\s*valikuthu\b",
            r"\bthala\s*valikudhu\b",
            r"\bthalayila\s*vali\b",
            r"\bheadache\s*irukku\b",
        ],
    },
    "abdominal pain": {
        "en": [
            r"\babdominal\s+pain\b",
            r"\bstomach\s+pain\b",
            r"\bstomach\s+ache\b",
            r"\bpain\s+in\s+(?:my\s+)?stomach\b",
            r"\bpain\s+in\s+(?:my\s+)?abdomen\b",
            r"\bbelly\s+pain\b",
            r"\bbelly\s+ache\b",
            r"\btummy\s+pain\b",
            r"\btummy\s+ache\b",
            r"\bstomach\s+hurts?\b",
        ],
        "ta_script": [
            r"வயிற்று\s*வலி",
            r"வயிற்று\s*வலிக்குது",
            r"வயிற்று\s*வலிக்கிறது",
            r"வயிறு\s*வலி",
            r"வயிறு\s*வலிக்குது",
            r"வயிறு\s*வலிக்கிறது",
            r"வயித்து\s*வலி",
            r"வயித்துல\s*வலி",
            r"வயிற்றுவலி",
        ],
        "ta_tanglish": [
            r"\bvayiru\s*vali\b",
            r"\bvayiru\s*valikuthu\b",
            r"\bvayiru\s*valikudhu\b",
            r"\bvayithu\s*vali\b",
            r"\bvayithu\s*valikuthu\b",
            r"\bvayithula\s*vali\b",
            r"\bstomach\s*vali\b",
        ],
    },
    "breathing difficulty": {
        "en": [
            r"\bbreathing\s+difficulty\b",
            r"\bdifficulty\s+(?:in\s+)?breathing\b",
            r"\bshortness\s+of\s+breath\b",
            r"\btrouble\s+breathing\b",
            r"\bcannot\s+breathe\b",
            r"\bcan\'?t\s+breathe\b",
            r"\bhard\s+to\s+breathe\b",
            r"\bbreathless(?:ness)?\b",
            r"\bchoking\s+sensation\b",
        ],
        "ta_script": [
            r"மூச்சு\s*திணறல்",
            r"மூச்சு\s*திணறுது",
            r"மூச்சு\s*விட\s*சிரமம்",
            r"மூச்சு\s*விட\s*கஷ்டம்",
            r"மூச்சு\s*வாங்க\s*முடியல",
            r"மூச்சு\s*விட\s*முடியல",
            r"மூச்சு\s*அடைக்குது",
            r"மூச்சுதிணறல்",
        ],
        "ta_tanglish": [
            r"\bmoochu\s*thinaral\b",
            r"\bmoochu\s*thinarudhu\b",
            r"\bmoochu\s*thinaruthu\b",
            r"\bmoochu\s*kashtama\s*irukku\b",
            r"\bmoochu\s*vida\s*kashtam\b",
            r"\bmoochu\s*vida\s*mudiyala\b",
            r"\bmoochu\s*vaanga\s*mudiyala\b",
        ],
    },
}

# Ambiguous / Non-specific phrases
AMBIGUOUS_PATTERNS = [
    r"\bdon'?t\s+feel\s+well\b",
    r"\bnot\s+feeling\s+well\b",
    r"\bnot\s+feeling\s+good\b",
    r"\bsomething\s+is\s+wrong\b",
    r"\bfeeling\s+sick\b",
    r"\bunwell\b",
    r"\bjust\s+sick\b",
    r"உடம்பு\s*சரியில்ல(?:ை)?",
    r"உடம்பு\s*முடியல",
    r"சரியில்ல(?:ை)?",
    r"\budambu\s*mudiyala\b",
    r"\budambu\s*sari\s*illa\b",
    r"\budambu\s*sariyilla\b",
    r"\bsari\s*illa\b",
    r"\bsariyilla\b",
]

# Adversarial Urgency phrases (should not inflate triage level directly)
ADVERSARIAL_URGENCY_PATTERNS = [
    r"\bi\s+need\s+(?:the\s+)?doctor\s+immediately\b",
    r"\bvery\s+serious\s+problem\b",
    r"\bemergency\b",
    r"\bi\s+am\s+suffering\s+badly\b",
    r"\bdying\b",
    r"\bhurry\s+up\b",
    r"\burgent\b",
    r"டாக்டர்\s*உடனே\s*வேணும்",
    r"அவசரம்",
    r"மிகவும்\s*தீவிரமான\s*பிரச்சனை",
    r"\bdoctor\s*udane\s*venum\b",
    r"\bemergency\s*ah\s*irukku\b",
    r"\bromba\s*kashtama\s*irukku\b",
]

# Ambiguous Yes/No expressions
AMBIGUOUS_YES_NO_PATTERNS = [
    r"\bi\s+don'?t\s+know\b",
    r"\bnot\s+sure\b",
    r"\bmaybe\b",
    r"\bcan'?t\s+say\b",
    r"\bpossibly\b",
    r"தெரியல(?:ை)?",
    r"\btheriyala\b",
    r"\btherila\b",
]

# Yes / No Patterns
YES_PATTERNS = {
    "en": [r"\byes\b", r"\byeah\b", r"\byep\b", r"\byup\b", r"\bsure\b", r"\btrue\b", r"\bcorrect\b", r"\bi\s+do\b", r"\bi\s+have\b"],
    "ta_script": [r"ஆம்", r"ஆமாம்", r"ஆமா", r"சரி", r"இருக்கிறது", r"இருக்கு", r"உண்டு"],
    "ta_tanglish": [r"\baama\b", r"\baamaam\b", r"\baamam\b", r"\bama\b", r"\bsari\b", r"\birukku\b", r"\byes\b"],
}

NO_PATTERNS = {
    "en": [
        r"\bno\b",
        r"\bnope\b",
        r"\bnah\b",
        r"\bnot\s+really\b",
        r"\bnot\s+at\s+all\b",
        r"\bfalse\b",
        r"\bnegative\b",
        r"\bnone\b",
        r"\bi\s+don'?t\s+(?:have|experience|feel)\b",
    ],
    "ta_script": [r"இல்லை", r"இல்ல", r"இல்லவே\s*இல்லை", r"கிடையாது", r"எதுவும்\s*இல்லை"],
    "ta_tanglish": [r"\billa\b", r"\billai\b", r"\bille\b", r"\bkedayathu\b", r"\bkidaiyathu\b", r"\bedhum\s*illa\b", r"\bno\b"],
}

# Duration Patterns
NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "ஒன்று": 1, "ஒரு": 1, "இரண்டு": 2, "ரெண்டு": 2, "மூன்று": 3, "மூணு": 3,
    "நான்கு": 4, "நாலு": 4, "ஐந்து": 5, "அஞ்சு": 5,
    "onnu": 1, "oru": 1, "rendu": 2, "erandu": 2, "moonu": 3, "naalu": 4, "anju": 5
}


def normalize_text(text: str) -> str:
    """Normalize input text by standardizing unicode, lowercasing, and stripping whitespace."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    return text.strip().lower()


def extract_chief_complaint(text: str) -> Tuple[str, str, float]:
    """
    Extract canonical chief complaint from raw transcript.
    Returns: (canonical_complaint, status, confidence)
    status is one of: 'confident', 'ambiguous', 'unknown'
    """
    normalized = normalize_text(text)
    if not normalized:
        return ("unknown", "unknown", 0.0)

    # First check for specific complaints
    matched_complaints = []
    for complaint, lang_groups in CHIEF_COMPLAINT_PATTERNS.items():
        for lang_key, patterns in lang_groups.items():
            for pat in patterns:
                if re.search(pat, normalized, re.IGNORECASE):
                    matched_complaints.append(complaint)
                    break
            if complaint in matched_complaints:
                break

    if matched_complaints:
        # If single confident match
        return (matched_complaints[0], "confident", 0.95)

    # Check if input is ambiguous / non-specific
    for pat in AMBIGUOUS_PATTERNS:
        if re.search(pat, normalized, re.IGNORECASE):
            return ("unknown", "ambiguous", 0.3)

    # Check if purely adversarial urgency without identifiable symptoms
    for pat in ADVERSARIAL_URGENCY_PATTERNS:
        if re.search(pat, normalized, re.IGNORECASE):
            return ("unknown", "ambiguous", 0.2)

    return ("unknown", "unknown", 0.0)


def extract_yes_no(text: str) -> Optional[bool]:
    """
    Parse a Yes/No response into True/False.
    Returns None if ambiguous or unrecognized.
    """
    normalized = normalize_text(text)
    if not normalized:
        return None

    # Check if explicitly ambiguous
    for pat in AMBIGUOUS_YES_NO_PATTERNS:
        if re.search(pat, normalized, re.IGNORECASE):
            return None

    # Check No first (avoids false positive on phrases like 'no yes')
    for lang_key, patterns in NO_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, normalized, re.IGNORECASE):
                return False

    for lang_key, patterns in YES_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, normalized, re.IGNORECASE):
                return True

    return None


def extract_duration(text: str) -> str:
    """
    Extract normalized duration (e.g., '2 hours', '1 day', '30 minutes')
    from English, Tamil script, or Tanglish.
    Preserves original cleaned text if format is non-standard.
    """
    normalized = normalize_text(text)
    if not normalized:
        return "unknown"

    # Pattern: Yesterday / நேற்று / nethu
    if re.search(r"\b(?:since\s+)?yesterday\b|நேற்ற(?:ிலிருந்து|ு)|\bnethu(?:la\s+irundhu)?\b", normalized, re.IGNORECASE):
        return "1 day"

    # Pattern: Just now / இப்போதான் / ippodhan
    if re.search(r"\bjust\s+now\b|இப்போ(?:து)?தான்|\bippo(?:dhan)?\b", normalized, re.IGNORECASE):
        return "just now"

    # Number + Unit matching in English / Tanglish / Tamil
    # Convert word numbers to digits
    words = normalized.split()
    converted_words = []
    for w in words:
        if w in NUMBER_WORDS:
            converted_words.append(str(NUMBER_WORDS[w]))
        else:
            converted_words.append(w)
    converted_text = " ".join(converted_words)

    # Hours regex (e.g. 2 hours, 2 hrs, 2 மணி, 2 mani)
    match_hour = re.search(r"(\d+)\s*(?:hours?|hrs?|மணி\s*(?:நேரமா(?:க)?|நேரம்)?|mani\s*(?:neram(?:a)?|nerama)?|hours\s*ah)", converted_text, re.IGNORECASE)
    if match_hour:
        num = match_hour.group(1)
        return f"{num} hour" if num == "1" else f"{num} hours"

    # Days regex (e.g. 3 days, 3 நாட்கள், 3 naal)
    match_day = re.search(r"(\d+)\s*(?:days?|நாட்கள்|நாட்களாக|நாள்|naatkal|naal|naala)", converted_text, re.IGNORECASE)
    if match_day:
        num = match_day.group(1)
        return f"{num} day" if num == "1" else f"{num} days"

    # Minutes regex (e.g. 30 minutes, 30 mins, 30 நிமிடங்கள், 30 nimisham)
    match_min = re.search(r"(\d+)\s*(?:minutes?|mins?|நிமிடங்கள்|நிமிடம்|nimisham|nimisam)", converted_text, re.IGNORECASE)
    if match_min:
        num = match_min.group(1)
        return f"{num} minute" if num == "1" else f"{num} minutes"

    # Weeks regex
    match_week = re.search(r"(\d+)\s*(?:weeks?|வாரங்கள்|வாரம்|vaaram)", converted_text, re.IGNORECASE)
    if match_week:
        num = match_week.group(1)
        return f"{num} week" if num == "1" else f"{num} weeks"

    # If simple digit was provided
    match_digit = re.search(r"\b(\d+)\b", converted_text)
    if match_digit and ("hour" in converted_text or "மணி" in converted_text or "mani" in converted_text):
        return f"{match_digit.group(1)} hours"

    # Fallback to cleaned original response
    return text.strip()


def extract_medications(text: str) -> List[str]:
    """
    Extract mentioned medications or ['none'].
    """
    normalized = normalize_text(text)
    if not normalized:
        return ["none"]

    # Check for negative answers
    negative_patterns = [
        r"\bno\s+medications?\b",
        r"\bno\s+medicine\b",
        r"\bnone\b",
        r"\bnothing\b",
        r"\bnot\s+taking\s+any(?:thing)?\b",
        r"எந்த\s*மருந்தும்\s*எடுக்கவில்ல(?:ை)?",
        r"மருந்து\s*எதுவும்\s*இல்ல(?:ை)?",
        r"மருந்து\s*இல்ல(?:ை)?",
        r"எதுவும்\s*இல்ல(?:ை)?",
        r"இல்ல(?:ை)?",
        r"\bmedicine\s*edukkala\b",
        r"\bmarundhu\s*edukala\b",
        r"\bmarundhu\s*edhuvum\s*illa\b",
        r"\bedhum\s*illa\b",
        r"\bno\b",
    ]
    for pat in negative_patterns:
        if re.search(pat, normalized, re.IGNORECASE):
            return ["none"]

    # Known common medication terms
    known_meds = [
        ("insulin", [r"\binsulin\b", r"இன்சுலின்", r"\binsulin\b"]),
        ("paracetamol", [r"\bparacetamol\b", r"பாராசிட்டமால்", r"\bcrocin\b", r"\bdolo\b", r"\bdolo\s*650\b"]),
        ("aspirin", [r"\baspirin\b", r"ஆஸ்பிரின்"]),
        ("metformin", [r"\bmetformin\b", r"மெட்பார்மின்"]),
        ("bp tablet", [r"\bbp\s+tablet\b", r"\bbp\s+medicine\b", r"பிபி\s*மாத்திரை", r"\bbp\s*mathirai\b", r"\bblood\s*pressure\s*tablet\b"]),
        ("sugar tablet", [r"\bsugar\s+tablet\b", r"\bsugar\s+medicine\b", r"சர்க்கரை\s*மாத்திரை", r"\bsugar\s*mathirai\b"]),
        ("inhaler", [r"\binhaler\b", r"இன்ஹேலர்"]),
        ("atenolol", [r"\batenolol\b"]),
        ("amoxicillin", [r"\bamoxicillin\b"]),
        ("cetirizine", [r"\bcetirizine\b"]),
    ]

    found = []
    for canonical_name, patterns in known_meds:
        for pat in patterns:
            if re.search(pat, normalized, re.IGNORECASE):
                found.append(canonical_name)
                break

    if found:
        return found

    # If specific text provided that isn't negative, retain cleaned phrase
    cleaned = text.strip()
    if cleaned.lower() not in ["no", "none", "na", "nil"]:
        return [cleaned]
    return ["none"]


def extract_medical_history(text: str) -> str:
    """
    Extract normalized medical history (e.g. 'diabetic', 'hypertension', 'none').
    """
    normalized = normalize_text(text)
    if not normalized:
        return "none"

    # Check for negative answers
    negative_patterns = [
        r"\bnone\b",
        r"\bno\s+history\b",
        r"\bno\s+medical\s+history\b",
        r"\bnothing\b",
        r"\bno\s+previous\s+problem\b",
        r"எதுவும்\s*இல்ல(?:ை)?",
        r"மருத்துவ\s*வரலாறு\s*இல்ல(?:ை)?",
        r"இல்ல(?:ை)?",
        r"\bedhum\s*illa\b",
        r"\bhistory\s*edhum\s*illa\b",
        r"\bno\b",
    ]
    for pat in negative_patterns:
        if re.search(pat, normalized, re.IGNORECASE):
            return "none"

    # Diabetes
    if re.search(r"\bdiabet(?:es|ic)\b|\bsugar\b|சர்க்கரை\s*நோய்|\bsugar\s*irukku\b", normalized, re.IGNORECASE):
        return "diabetic"

    # Hypertension / High BP
    if re.search(r"\bhypertension\b|\bhigh\s*blood\s*pressure\b|\bhigh\s*bp\b|\bbp\b|ரத்த\s*அழுத்தம்|\bbp\s*irukku\b", normalized, re.IGNORECASE):
        return "hypertension"

    # Asthma
    if re.search(r"\basthma\b|\bwheezing\b|ஆஸ்துமா|\basthma\s*irukku\b", normalized, re.IGNORECASE):
        return "asthma"

    # Heart disease
    if re.search(r"\bheart\s*(?:disease|problem|attack)\b|இதய\s*நோய்|\bheart\s*problem\b", normalized, re.IGNORECASE):
        return "heart disease"

    # Fallback to cleaned text if specific
    return text.strip()
