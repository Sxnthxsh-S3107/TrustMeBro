"""Unit tests for NLP normalization and extraction across English, Tamil script, and Tanglish.
"""

import pytest
from voice_intake.app.nlp import (
    extract_chief_complaint,
    extract_yes_no,
    extract_duration,
    extract_medications,
    extract_medical_history,
)


# =====================================================================
# 1. Chief Complaint Normalization Tests
# =====================================================================

def test_chest_pain_extraction():
    # English
    complaint, status, _ = extract_chief_complaint("I have chest pain")
    assert complaint == "chest pain"
    assert status == "confident"

    # Tamil Script
    complaint, status, _ = extract_chief_complaint("எனக்கு நெஞ்சு வலி இருக்கு")
    assert complaint == "chest pain"
    assert status == "confident"

    complaint, status, _ = extract_chief_complaint("நெஞ்சு வலிக்குது")
    assert complaint == "chest pain"
    assert status == "confident"

    # Tanglish
    complaint, status, _ = extract_chief_complaint("Enakku nenju vali irukku")
    assert complaint == "chest pain"
    assert status == "confident"

    complaint, status, _ = extract_chief_complaint("nenju valikuthu")
    assert complaint == "chest pain"
    assert status == "confident"


def test_headache_extraction():
    # English
    complaint, status, _ = extract_chief_complaint("I have a headache")
    assert complaint == "headache"
    assert status == "confident"

    # Tamil Script
    complaint, status, _ = extract_chief_complaint("எனக்கு தலை வலி")
    assert complaint == "headache"
    assert status == "confident"

    complaint, status, _ = extract_chief_complaint("தலை வலிக்குது")
    assert complaint == "headache"
    assert status == "confident"

    # Tanglish
    complaint, status, _ = extract_chief_complaint("Enakku thalai vali")
    assert complaint == "headache"
    assert status == "confident"

    complaint, status, _ = extract_chief_complaint("thala valikuthu")
    assert complaint == "headache"
    assert status == "confident"


def test_abdominal_pain_extraction():
    # English
    complaint, status, _ = extract_chief_complaint("I have stomach pain")
    assert complaint == "abdominal pain"
    assert status == "confident"

    complaint, status, _ = extract_chief_complaint("severe abdominal pain")
    assert complaint == "abdominal pain"
    assert status == "confident"

    # Tamil Script
    complaint, status, _ = extract_chief_complaint("எனக்கு வயிற்று வலி")
    assert complaint == "abdominal pain"
    assert status == "confident"

    complaint, status, _ = extract_chief_complaint("வயிறு வலிக்குது")
    assert complaint == "abdominal pain"
    assert status == "confident"

    # Tanglish
    complaint, status, _ = extract_chief_complaint("Enakku vayiru vali")
    assert complaint == "abdominal pain"
    assert status == "confident"

    complaint, status, _ = extract_chief_complaint("vayiru valikuthu")
    assert complaint == "abdominal pain"
    assert status == "confident"


def test_breathing_difficulty_extraction():
    # English
    complaint, status, _ = extract_chief_complaint("I have difficulty breathing")
    assert complaint == "breathing difficulty"
    assert status == "confident"

    complaint, status, _ = extract_chief_complaint("shortness of breath")
    assert complaint == "breathing difficulty"
    assert status == "confident"

    # Tamil Script
    complaint, status, _ = extract_chief_complaint("எனக்கு மூச்சு திணறல்")
    assert complaint == "breathing difficulty"
    assert status == "confident"

    complaint, status, _ = extract_chief_complaint("மூச்சு விட கஷ்டம்")
    assert complaint == "breathing difficulty"
    assert status == "confident"

    # Tanglish
    complaint, status, _ = extract_chief_complaint("Enakku moochu thinaral")
    assert complaint == "breathing difficulty"
    assert status == "confident"

    complaint, status, _ = extract_chief_complaint("moochu kashtama irukku")
    assert complaint == "breathing difficulty"
    assert status == "confident"


# =====================================================================
# 2. Yes / No Normalization Tests
# =====================================================================

def test_yes_no_normalization():
    # English True
    assert extract_yes_no("yes") is True
    assert extract_yes_no("yeah") is True
    assert extract_yes_no("yep") is True
    assert extract_yes_no("sure") is True

    # English False
    assert extract_yes_no("no") is False
    assert extract_yes_no("nope") is False
    assert extract_yes_no("nah") is False

    # Tamil Script True
    assert extract_yes_no("ஆம்") is True
    assert extract_yes_no("ஆமாம்") is True
    assert extract_yes_no("ஆமா") is True
    assert extract_yes_no("சரி") is True

    # Tamil Script False
    assert extract_yes_no("இல்லை") is False
    assert extract_yes_no("இல்ல") is False
    assert extract_yes_no("இல்லவே இல்லை") is False

    # Tanglish True
    assert extract_yes_no("aama") is True
    assert extract_yes_no("aamaam") is True
    assert extract_yes_no("ama") is True

    # Tanglish False
    assert extract_yes_no("illa") is False
    assert extract_yes_no("illai") is False
    assert extract_yes_no("ille") is False

    # Ambiguous / Unrecognized
    assert extract_yes_no("maybe sometimes") is None
    assert extract_yes_no("I don't know") is None


# =====================================================================
# 3. Ambiguity & Adversarial Urgency Tests
# =====================================================================

def test_ambiguous_phrases():
    complaint, status, _ = extract_chief_complaint("I don't feel well")
    assert complaint == "unknown"
    assert status == "ambiguous"

    complaint, status, _ = extract_chief_complaint("உடம்பு சரியில்லை")
    assert complaint == "unknown"
    assert status == "ambiguous"

    complaint, status, _ = extract_chief_complaint("udambu mudiyala")
    assert complaint == "unknown"
    assert status == "ambiguous"


def test_adversarial_urgency_isolation():
    # Urgency without symptom -> marked ambiguous, not given artificial clinical symptom
    complaint, status, _ = extract_chief_complaint("I need the doctor immediately")
    assert complaint == "unknown"
    assert status == "ambiguous"

    complaint, status, _ = extract_chief_complaint("Very serious problem")
    assert complaint == "unknown"
    assert status == "ambiguous"

    complaint, status, _ = extract_chief_complaint("Emergency")
    assert complaint == "unknown"
    assert status == "ambiguous"

    complaint, status, _ = extract_chief_complaint("I am suffering badly")
    assert complaint == "unknown"
    assert status == "ambiguous"

    # Urgency combined with actual symptom -> correctly extracts the symptom
    complaint, status, _ = extract_chief_complaint("Emergency! I need a doctor, I have chest pain!")
    assert complaint == "chest pain"
    assert status == "confident"


# =====================================================================
# 4. Duration Extraction Tests
# =====================================================================

def test_duration_extraction():
    # English
    assert extract_duration("It started two hours ago") == "2 hours"
    assert extract_duration("Since yesterday") == "1 day"
    assert extract_duration("3 days") == "3 days"
    assert extract_duration("30 minutes") == "30 minutes"
    assert extract_duration("just now") == "just now"

    # Tamil Script
    assert extract_duration("இரண்டு மணி நேரமாக") == "2 hours"
    assert extract_duration("2 மணி நேரம்") == "2 hours"
    assert extract_duration("நேற்றிலிருந்து") == "1 day"
    assert extract_duration("3 நாட்களாக") == "3 days"
    assert extract_duration("30 நிமிடங்கள்") == "30 minutes"

    # Tanglish
    assert extract_duration("rendu mani nerama") == "2 hours"
    assert extract_duration("2 hours ah") == "2 hours"
    assert extract_duration("nethula irundhu") == "1 day"
    assert extract_duration("moonu naal") == "3 days"


# =====================================================================
# 5. Medication Extraction Tests
# =====================================================================

def test_medication_extraction():
    # Positive English
    assert extract_medications("I take insulin") == ["insulin"]
    assert extract_medications("paracetamol") == ["paracetamol"]
    assert "aspirin" in extract_medications("I am taking aspirin daily")

    # Positive Tamil Script & Tanglish
    assert extract_medications("நான் இன்சுலின் எடுத்துக்கொள்கிறேன்") == ["insulin"]
    assert extract_medications("insulin poduren") == ["insulin"]
    assert extract_medications("bp tablet poduren") == ["bp tablet"]

    # Negative English
    assert extract_medications("No medications") == ["none"]
    assert extract_medications("none") == ["none"]
    assert extract_medications("not taking anything") == ["none"]

    # Negative Tamil Script & Tanglish
    assert extract_medications("எந்த மருந்தும் எடுக்கவில்லை") == ["none"]
    assert extract_medications("மருந்து எதுவும் இல்லை") == ["none"]
    assert extract_medications("medicine edukkala") == ["none"]
    assert extract_medications("edhum illa") == ["none"]


# =====================================================================
# 6. Medical History Extraction Tests
# =====================================================================

def test_medical_history_extraction():
    # Diabetes
    assert extract_medical_history("I have diabetes") == "diabetic"
    assert extract_medical_history("I am diabetic") == "diabetic"
    assert extract_medical_history("சர்க்கரை நோய்") == "diabetic"
    assert extract_medical_history("sugar irukku") == "diabetic"

    # Hypertension
    assert extract_medical_history("I have high blood pressure") == "hypertension"
    assert extract_medical_history("hypertension") == "hypertension"
    assert extract_medical_history("ரத்த அழுத்தம்") == "hypertension"
    assert extract_medical_history("bp irukku") == "hypertension"

    # Asthma
    assert extract_medical_history("asthma") == "asthma"
    assert extract_medical_history("ஆஸ்துமா") == "asthma"

    # Negative / None
    assert extract_medical_history("none") == "none"
    assert extract_medical_history("no medical history") == "none"
    assert extract_medical_history("எதுவும் இல்லை") == "none"
    assert extract_medical_history("edhum illa") == "none"
