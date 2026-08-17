"""
Comprehensive unit tests for LifeLine hardcoded deterministic red-flag rules.
"""

import pytest
from rules_engine.red_flags import check_red_flags
from rules_engine.constants import Priority, RuleId


# =============================================================================
# 1. AIRWAY & BREATHING TESTS
# =============================================================================

def test_rule_stridor():
    data = {"age": 30, "stridor": True}
    res = check_red_flags(data)
    assert res["priority"] == Priority.EMERGENCY.value
    assert res["rule_triggered"] is True
    assert RuleId.RF_AIRWAY_001 in res["rule_ids"]
    assert res["llm_allowed"] is False


def test_rule_severe_respiratory_distress():
    data = {"age": 45, "severe_respiratory_distress": True}
    res = check_red_flags(data)
    assert res["priority"] == Priority.EMERGENCY.value
    assert res["rule_triggered"] is True
    assert RuleId.RF_RESP_001 in res["rule_ids"]
    assert res["llm_allowed"] is False


def test_rule_central_cyanosis():
    data = {"age": 50, "central_cyanosis": True}
    res = check_red_flags(data)
    assert res["priority"] == Priority.EMERGENCY.value
    assert res["rule_triggered"] is True
    assert RuleId.RF_RESP_001 in res["rule_ids"]
    assert res["llm_allowed"] is False


# =============================================================================
# 2. ALTERED MENTAL STATUS & CONSCIOUSNESS
# =============================================================================

def test_rule_unconscious():
    data = {"age": 60, "unconscious": True}
    res = check_red_flags(data)
    assert res["priority"] == Priority.EMERGENCY.value
    assert res["rule_triggered"] is True
    assert RuleId.RF_NEURO_001 in res["rule_ids"]
    assert res["llm_allowed"] is False


def test_rule_avpu_impaired():
    # AVPU 'V' (Voice), 'P' (Pain), 'U' (Unresponsive) must trigger EMERGENCY
    for state in ["V", "P", "U"]:
        data = {"age": 35, "avpu": state}
        res = check_red_flags(data)
        assert res["priority"] == Priority.EMERGENCY.value
        assert RuleId.RF_NEURO_001 in res["rule_ids"]
        assert res["llm_allowed"] is False

    # AVPU 'A' (Alert) alone should not trigger RF_NEURO_001
    data_alert = {
        "age": 35,
        "avpu": "A",
        "chest_pain": False,
        "breathing_difficulty": False,
    }
    res_alert = check_red_flags(data_alert)
    assert RuleId.RF_NEURO_001 not in res_alert["rule_ids"]


def test_rule_gcs_severe():
    data = {"age": 28, "gcs": 7}
    res = check_red_flags(data)
    assert res["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_NEURO_001 in res["rule_ids"]


def test_rule_altered_mental_status():
    data = {"age": 70, "altered_mental_status": True}
    res = check_red_flags(data)
    assert res["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_NEURO_002 in res["rule_ids"]


# =============================================================================
# 3. ACTIVE CONVULSIONS
# =============================================================================

def test_rule_active_convulsion():
    data = {"age": 25, "active_convulsion": True}
    res = check_red_flags(data)
    assert res["priority"] == Priority.EMERGENCY.value
    assert res["rule_triggered"] is True
    assert RuleId.RF_CONV_001 in res["rule_ids"]
    assert res["llm_allowed"] is False


# =============================================================================
# 4. MAJOR BLEEDING
# =============================================================================

def test_rule_severe_bleeding():
    data = {"age": 40, "severe_bleeding": True}
    res = check_red_flags(data)
    assert res["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_CIRC_001 in res["rule_ids"]
    assert res["llm_allowed"] is False


# =============================================================================
# 5. ACUTE NEUROLOGICAL RED FLAGS
# =============================================================================

def test_rule_focal_neurological():
    # Test unilateral weakness
    data1 = {"age": 62, "sudden_one_sided_weakness": True}
    res1 = check_red_flags(data1)
    assert res1["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_NEURO_FOCAL in res1["rule_ids"]

    # Test acute speech difficulty
    data2 = {"age": 55, "speech_difficulty": True}
    res2 = check_red_flags(data2)
    assert res2["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_NEURO_FOCAL in res2["rule_ids"]

    # Test facial weakness
    data3 = {"age": 58, "facial_weakness": True}
    res3 = check_red_flags(data3)
    assert res3["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_NEURO_FOCAL in res3["rule_ids"]

    # Test sudden vision change
    data4 = {"age": 48, "sudden_vision_change": True}
    res4 = check_red_flags(data4)
    assert res4["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_NEURO_FOCAL in res4["rule_ids"]


# =============================================================================
# 6. HIGH-RISK VITAL SIGNS & BOUNDARY TESTS (WHO IITT Adult >=12)
# =============================================================================

def test_vitals_spo2_boundary():
    # SpO2 < 92% is Red
    # 91.0% -> EMERGENCY
    res_below = check_red_flags({"age": 30, "spo2": 91.0, "chest_pain": False, "breathing_difficulty": False})
    assert res_below["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_VIT_SPO2 in res_below["rule_ids"]

    # 92.0% -> Not triggering SpO2 emergency
    res_at = check_red_flags({"age": 30, "spo2": 92.0, "chest_pain": False, "breathing_difficulty": False})
    assert RuleId.RF_VIT_SPO2 not in res_at["rule_ids"]

    # 93.0% -> Not triggering SpO2 emergency
    res_above = check_red_flags({"age": 30, "spo2": 93.0, "chest_pain": False, "breathing_difficulty": False})
    assert RuleId.RF_VIT_SPO2 not in res_above["rule_ids"]


def test_vitals_heart_rate_boundary():
    # HR < 60 or HR > 130 is Red
    # 59 bpm -> EMERGENCY
    res_low = check_red_flags({"age": 30, "heart_rate": 59, "chest_pain": False, "breathing_difficulty": False})
    assert res_low["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_VIT_HR in res_low["rule_ids"]

    # 60 bpm -> Normal boundary
    res_60 = check_red_flags({"age": 30, "heart_rate": 60, "chest_pain": False, "breathing_difficulty": False})
    assert RuleId.RF_VIT_HR not in res_60["rule_ids"]

    # 130 bpm -> Normal boundary
    res_130 = check_red_flags({"age": 30, "heart_rate": 130, "chest_pain": False, "breathing_difficulty": False})
    assert RuleId.RF_VIT_HR not in res_130["rule_ids"]

    # 131 bpm -> EMERGENCY
    res_high = check_red_flags({"age": 30, "heart_rate": 131, "chest_pain": False, "breathing_difficulty": False})
    assert res_high["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_VIT_HR in res_high["rule_ids"]


def test_vitals_respiratory_rate_boundary():
    # RR < 10 or RR > 30 is Red
    # 9 /min -> EMERGENCY
    res_low = check_red_flags({"age": 30, "respiratory_rate": 9, "chest_pain": False, "breathing_difficulty": False})
    assert res_low["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_VIT_RR in res_low["rule_ids"]

    # 10 /min -> Normal
    res_10 = check_red_flags({"age": 30, "respiratory_rate": 10, "chest_pain": False, "breathing_difficulty": False})
    assert RuleId.RF_VIT_RR not in res_10["rule_ids"]

    # 30 /min -> Normal
    res_30 = check_red_flags({"age": 30, "respiratory_rate": 30, "chest_pain": False, "breathing_difficulty": False})
    assert RuleId.RF_VIT_RR not in res_30["rule_ids"]

    # 31 /min -> EMERGENCY
    res_high = check_red_flags({"age": 30, "respiratory_rate": 31, "chest_pain": False, "breathing_difficulty": False})
    assert res_high["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_VIT_RR in res_high["rule_ids"]


def test_vitals_systolic_bp_boundary():
    # SBP < 90 is Red (Shock)
    # 89 mmHg -> EMERGENCY
    res_low = check_red_flags({"age": 30, "systolic_bp": 89, "chest_pain": False, "breathing_difficulty": False})
    assert res_low["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_VIT_SBP in res_low["rule_ids"]

    # 90 mmHg -> Normal
    res_90 = check_red_flags({"age": 30, "systolic_bp": 90, "chest_pain": False, "breathing_difficulty": False})
    assert RuleId.RF_VIT_SBP not in res_90["rule_ids"]


def test_vitals_temperature_boundary():
    # Temp < 36.0°C or > 39.0°C is Red
    # 35.9°C -> EMERGENCY
    res_low = check_red_flags({"age": 30, "temperature": 35.9, "chest_pain": False, "breathing_difficulty": False})
    assert res_low["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_TEMP_001 in res_low["rule_ids"]

    # 36.0°C -> Normal
    res_36 = check_red_flags({"age": 30, "temperature": 36.0, "chest_pain": False, "breathing_difficulty": False})
    assert RuleId.RF_TEMP_001 not in res_36["rule_ids"]

    # 39.0°C -> Normal
    res_39 = check_red_flags({"age": 30, "temperature": 39.0, "chest_pain": False, "breathing_difficulty": False})
    assert RuleId.RF_TEMP_001 not in res_39["rule_ids"]

    # 39.1°C -> EMERGENCY
    res_high = check_red_flags({"age": 30, "temperature": 39.1, "chest_pain": False, "breathing_difficulty": False})
    assert res_high["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_TEMP_001 in res_high["rule_ids"]


# =============================================================================
# 7. ACUTE CHEST SYNDROMES
# =============================================================================

def test_chest_pain_combinations():
    # Chest pain + breathing difficulty -> EMERGENCY
    data1 = {"age": 55, "chest_pain": True, "breathing_difficulty": True}
    res1 = check_red_flags(data1)
    assert res1["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_CHEST_001 in res1["rule_ids"]

    # Chest pain + syncope/fainting -> EMERGENCY
    data2 = {"age": 55, "chest_pain": True, "fainting": True}
    res2 = check_red_flags(data2)
    assert res2["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_CHEST_001 in res2["rule_ids"]

    # Chest pain + diaphoresis/sweating -> EMERGENCY
    data3 = {"age": 55, "chest_pain": True, "sweating": True}
    res3 = check_red_flags(data3)
    assert res3["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_CHEST_001 in res3["rule_ids"]


# =============================================================================
# 8. ANAPHYLAXIS, TRAUMA, POISONING, PREGNANCY
# =============================================================================

def test_anaphylaxis_pattern():
    data = {
        "age": 22,
        "facial_or_tongue_swelling": True,
        "breathing_difficulty": True,
    }
    res = check_red_flags(data)
    assert res["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_ALLERGY_001 in res["rule_ids"]


def test_trauma_and_burns():
    data = {"age": 35, "major_trauma": True}
    res = check_red_flags(data)
    assert res["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_TRAUMA_001 in res["rule_ids"]


def test_poisoning_and_snakebite():
    data = {"age": 42, "snakebite": True}
    res = check_red_flags(data)
    assert res["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_TOX_001 in res["rule_ids"]


def test_obstetric_complications():
    data = {
        "age": 26,
        "pregnant": True,
        "severe_bleeding": True,
    }
    res = check_red_flags(data)
    assert res["priority"] == Priority.EMERGENCY.value
    assert RuleId.RF_OB_001 in res["rule_ids"]


# =============================================================================
# 9. MULTIPLE RULES TRIGGERING SIMULTANEOUSLY
# =============================================================================

def test_multiple_rules_simultaneous():
    """Verify that when multiple red flags exist, all rule IDs are aggregated."""
    data = {
        "age": 60,
        "unconscious": True,           # RF_NEURO_001
        "active_convulsion": True,     # RF_CONV_001
        "severe_bleeding": True,       # RF_CIRC_001
        "spo2": 85.0,                  # RF_VIT_SPO2
    }
    res = check_red_flags(data)
    assert res["priority"] == Priority.EMERGENCY.value
    assert res["rule_triggered"] is True
    assert res["llm_allowed"] is False

    expected_rules = {RuleId.RF_NEURO_001, RuleId.RF_CONV_001, RuleId.RF_CIRC_001, RuleId.RF_VIT_SPO2}
    assert expected_rules.issubset(set(res["rule_ids"]))


# =============================================================================
# 10. BENIGN / ROUTINE NEGATIVE TESTS
# =============================================================================

def test_routine_benign_case():
    """Verify normal presentation produces NO_HARD_RED_FLAG and llm_allowed=True."""
    data = {
        "patient_id": "P099",
        "age": 34,
        "sex": "female",
        "chief_complaint": "mild cough for 3 days",
        "chest_pain": False,
        "breathing_difficulty": False,
        "sweating": False,
        "fainting": False,
        "unconscious": False,
        "altered_mental_status": False,
        "active_convulsion": False,
        "severe_bleeding": False,
        "sudden_one_sided_weakness": False,
        "facial_weakness": False,
        "speech_difficulty": False,
        "sudden_vision_change": False,
        "facial_or_tongue_swelling": False,
        "major_trauma": False,
        "pregnant": False,
        "spo2": 98.0,
        "heart_rate": 76.0,
        "systolic_bp": 118.0,
        "diastolic_bp": 78.0,
        "temperature": 36.8,
        "respiratory_rate": 16.0,
    }
    res = check_red_flags(data)
    assert res["priority"] == Priority.NO_HARD_RED_FLAG.value
    assert res["rule_triggered"] is False
    assert len(res["rule_ids"]) == 0
    assert len(res["red_flags"]) == 0
    assert res["uncertain"] is False
    assert res["llm_allowed"] is True
    assert "No mandatory emergency red flag was detected" in res["rationale"]


def test_non_diagnostic_rationales():
    """Verify that rationales describe clinical patterns rather than diagnosing diseases."""
    data_neuro = {"age": 60, "sudden_one_sided_weakness": True, "speech_difficulty": True}
    res_neuro = check_red_flags(data_neuro)
    
    # Must NOT diagnose 'stroke' or 'infarction'
    full_text = (res_neuro["rationale"] + " " + " ".join(res_neuro["red_flags"])).lower()
    assert "stroke" not in full_text
    assert "infarction" not in full_text
    assert "neurological" in full_text
