"""
rules_engine/rules.py
---------------------
Inspectable, deterministic red-flag safety rules for Person 1's LifeLine Safety Engine.

Clinical Foundations:
  - Primary: WHO/ICRC/MSF Interagency Integrated Triage Tool (IITT) Adult (>=12 years)
  - Secondary: WHO Basic Emergency Care (BEC) Toolkit

Design Guidelines:
  - Strict non-diagnostic rationales (e.g., 'Acute focal neurological red flag detected', NOT 'Stroke')
  - Strict tri-state logic: True triggers, False does not, Unknown does not trigger emergency but is handled by confidence gate
  - Run ALL rules (no short-circuiting) so complete multi-system emergencies are audited.
  - 100% Deterministic Python - Zero ML/LLM/External APIs.
"""

from typing import Any, Callable, Dict, List, Optional, Tuple
from rules_engine.constants import (
    Priority,
    RuleId,
    SPO2_RED_THRESHOLD,
    RR_LOW_RED_THRESHOLD,
    RR_HIGH_RED_THRESHOLD,
    HR_LOW_RED_THRESHOLD,
    HR_HIGH_RED_THRESHOLD,
    SBP_LOW_RED_THRESHOLD,
    TEMP_LOW_RED_THRESHOLD,
    TEMP_HIGH_RED_THRESHOLD,
    GCS_SEVERE_THRESHOLD,
    OB_SBP_SEVERE_THRESHOLD,
    OB_DBP_SEVERE_THRESHOLD,
)
from rules_engine.models import TriState
from rules_engine.validators import parse_numeric_vital, parse_tristate


class RedFlagRule:
    """Represents an explicit, inspectable safety rule."""
    
    def __init__(
        self,
        rule_id: str,
        category: str,
        name: str,
        clinical_reference: str,
        priority: Priority,
        rationale: str,
        evaluator: Callable[[Dict[str, Any]], Tuple[bool, Optional[str]]],
    ):
        self.rule_id = rule_id
        self.category = category
        self.name = name
        self.clinical_reference = clinical_reference
        self.priority = priority
        self.rationale = rationale
        self.evaluator = evaluator

    def evaluate(self, intake_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Evaluate this rule against structured patient intake facts."""
        return self.evaluator(intake_data)


# -----------------------------------------------------------------------------
# 1. AIRWAY RULES (WHO IITT Adult Red Criteria)
# -----------------------------------------------------------------------------

def _eval_airway_compromise(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    stridor = parse_tristate(data.get("stridor"))
    airway_swelling = parse_tristate(data.get("airway_swelling"))
    facial_tongue = parse_tristate(data.get("facial_or_tongue_swelling"))
    dyspnea = parse_tristate(data.get("breathing_difficulty"))
    
    if stridor.is_true():
        return True, "Stridor (acute upper airway obstruction sound) detected."
    if airway_swelling.is_true():
        return True, "Airway swelling or mass with acute airway compromise detected."
    if facial_tongue.is_true() and dyspnea.is_true():
        return True, "Significant facial/tongue swelling combined with acute breathing difficulty detected."
    return False, None


# -----------------------------------------------------------------------------
# 2. BREATHING RULES (WHO IITT Adult Red Criteria)
# -----------------------------------------------------------------------------

def _eval_respiratory_distress(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    severe_resp = parse_tristate(data.get("severe_respiratory_distress"))
    cyanosis = parse_tristate(data.get("central_cyanosis"))
    dyspnea = parse_tristate(data.get("breathing_difficulty"))
    severity = str(data.get("severity", "")).lower()
    
    if severe_resp.is_true():
        return True, "Severe respiratory distress detected."
    if cyanosis.is_true():
        return True, "Central cyanosis (hypoxemia indicator) detected."
    if dyspnea.is_true() and severity in ("severe", "critical", "emergency"):
        return True, "Severe breathing difficulty reported."
    return False, None


def _eval_vital_spo2(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    spo2 = parse_numeric_vital(data.get("spo2"), "spo2")
    if spo2 is not None and spo2 < SPO2_RED_THRESHOLD:
        return True, f"Critical hypoxemia: Oxygen saturation (SpO2) {spo2:.1f}% is below {SPO2_RED_THRESHOLD:.0f}%."
    return False, None


def _eval_vital_rr(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    rr = parse_numeric_vital(data.get("respiratory_rate"), "respiratory_rate")
    if rr is not None:
        if rr < RR_LOW_RED_THRESHOLD:
            return True, f"Bradypnea / respiratory depression: Respiratory rate {int(rr)} /min is below {int(RR_LOW_RED_THRESHOLD)}."
        if rr > RR_HIGH_RED_THRESHOLD:
            return True, f"Severe adult tachypnea: Respiratory rate {int(rr)} /min is above {int(RR_HIGH_RED_THRESHOLD)}."
    return False, None


# -----------------------------------------------------------------------------
# 3. CIRCULATION RULES (WHO IITT Adult Red Criteria)
# -----------------------------------------------------------------------------

def _eval_heavy_bleeding(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    severe_bleeding = parse_tristate(data.get("severe_bleeding"))
    heavy_bleeding = parse_tristate(data.get("heavy_bleeding"))
    uncontrolled = parse_tristate(data.get("uncontrolled_bleeding"))
    
    if severe_bleeding.is_true() or heavy_bleeding.is_true() or uncontrolled.is_true():
        return True, "Heavy or uncontrolled external bleeding detected."
    return False, None


def _eval_vital_sbp(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    sbp = parse_numeric_vital(data.get("systolic_bp"), "systolic_bp")
    if sbp is not None and sbp < SBP_LOW_RED_THRESHOLD:
        return True, f"Severe adult hypotension / decompensated shock: Systolic BP {int(sbp)} mmHg is below {int(SBP_LOW_RED_THRESHOLD)} mmHg."
    return False, None


def _eval_vital_hr(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    hr = parse_numeric_vital(data.get("heart_rate"), "heart_rate")
    if hr is not None:
        if hr < HR_LOW_RED_THRESHOLD:
            return True, f"Severe adult bradycardia: Heart rate {int(hr)} bpm is below {int(HR_LOW_RED_THRESHOLD)} bpm."
        if hr > HR_HIGH_RED_THRESHOLD:
            return True, f"Severe adult tachycardia: Heart rate {int(hr)} bpm is above {int(HR_HIGH_RED_THRESHOLD)} bpm."
    return False, None


# -----------------------------------------------------------------------------
# 4. CONSCIOUSNESS & NEUROLOGICAL RULES (WHO IITT / BEC)
# -----------------------------------------------------------------------------

def _eval_unresponsiveness(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    unconscious = parse_tristate(data.get("unconscious"))
    avpu = str(data.get("avpu", "")).strip().upper()
    gcs = parse_numeric_vital(data.get("gcs"), "gcs")
    
    if unconscious.is_true():
        return True, "Patient is unresponsive or unconscious."
    if avpu in ("V", "P", "U"):
        return True, f"Impaired level of consciousness detected (AVPU: {avpu} != Alert)."
    if gcs is not None and gcs <= GCS_SEVERE_THRESHOLD:
        return True, f"Severe depression of consciousness detected (GCS {int(gcs)} <= {GCS_SEVERE_THRESHOLD})."
    return False, None


def _eval_altered_mental_status(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    ams = parse_tristate(data.get("altered_mental_status"))
    confusion = parse_tristate(data.get("acute_confusion"))
    
    if ams.is_true():
        return True, "Acute altered mental status detected."
    if confusion.is_true():
        return True, "Sudden acute onset confusion or lethargy detected."
    return False, None


def _eval_focal_neurological(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    weakness = parse_tristate(data.get("sudden_one_sided_weakness"))
    facial = parse_tristate(data.get("facial_weakness"))
    speech = parse_tristate(data.get("speech_difficulty"))
    vision = parse_tristate(data.get("sudden_vision_change"))
    
    detected: List[str] = []
    if weakness.is_true():
        detected.append("sudden one-sided weakness")
    if facial.is_true():
        detected.append("acute facial weakness")
    if speech.is_true():
        detected.append("acute speech difficulty")
    if vision.is_true():
        detected.append("sudden vision change")
        
    if detected:
        return True, f"Acute focal neurological red flag detected ({', '.join(detected)})."
    return False, None


# -----------------------------------------------------------------------------
# 5. CONVULSIONS (WHO IITT Adult Red Criteria)
# -----------------------------------------------------------------------------

def _eval_active_convulsion(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    convulsion = parse_tristate(data.get("active_convulsion"))
    seizing = parse_tristate(data.get("actively_seizing"))
    
    if convulsion.is_true() or seizing.is_true():
        return True, "Active convulsion or ongoing seizure activity detected."
    return False, None


# -----------------------------------------------------------------------------
# 6. TEMPERATURE RULES (WHO IITT Adult Red Criteria)
# -----------------------------------------------------------------------------

def _eval_vital_temp(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    temp = parse_numeric_vital(data.get("temperature"), "temperature")
    if temp is not None:
        if temp < TEMP_LOW_RED_THRESHOLD:
            return True, f"Severe hypothermia: Body temperature {temp:.1f}°C is below {TEMP_LOW_RED_THRESHOLD:.1f}°C."
        if temp > TEMP_HIGH_RED_THRESHOLD:
            return True, f"Hyperpyrexia: Body temperature {temp:.1f}°C is above {TEMP_HIGH_RED_THRESHOLD:.1f}°C."
    return False, None


# -----------------------------------------------------------------------------
# 7. HIGH-RISK TRAUMA (WHO IITT Adult Red Trauma Criteria)
# -----------------------------------------------------------------------------

def _eval_high_risk_trauma(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    trauma = parse_tristate(data.get("major_trauma"))
    penetrating = parse_tristate(data.get("penetrating_injury"))
    burn = parse_tristate(data.get("severe_burn"))
    
    if trauma.is_true():
        return True, "Major high-energy trauma reported."
    if penetrating.is_true():
        return True, "Penetrating injury to head, neck, chest, or abdomen reported."
    if burn.is_true():
        return True, "Severe or extensive burn injury reported."
    return False, None


# -----------------------------------------------------------------------------
# 8. TOXIC EXPOSURE / POISONING (WHO IITT Red Criteria)
# -----------------------------------------------------------------------------

def _eval_toxic_exposure(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    poisoning = parse_tristate(data.get("poisoning"))
    chemical = parse_tristate(data.get("chemical_exposure"))
    snakebite = parse_tristate(data.get("snakebite"))
    
    if poisoning.is_true():
        return True, "Acute poisoning or toxic ingestion reported."
    if chemical.is_true():
        return True, "Dangerous chemical exposure reported."
    if snakebite.is_true():
        return True, "Snakebite with potential envenomation reported."
    return False, None


# -----------------------------------------------------------------------------
# 9. ACUTE CHEST SYNDROME (WHO BEC Red Pattern)
# -----------------------------------------------------------------------------

def _eval_chest_syndrome(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    chest_pain = parse_tristate(data.get("chest_pain"))
    if not chest_pain.is_true():
        return False, None
        
    dyspnea = parse_tristate(data.get("breathing_difficulty"))
    fainting = parse_tristate(data.get("fainting"))
    sweating = parse_tristate(data.get("sweating"))
    radiating = parse_tristate(data.get("radiating_pain"))
    sbp = parse_numeric_vital(data.get("systolic_bp"), "systolic_bp")
    
    high_risk_features: List[str] = []
    if dyspnea.is_true():
        high_risk_features.append("breathing difficulty")
    if fainting.is_true():
        high_risk_features.append("fainting/syncope")
    if sweating.is_true():
        high_risk_features.append("sweating/diaphoresis")
    if radiating.is_true():
        high_risk_features.append("radiating pain")
    if sbp is not None and sbp < SBP_LOW_RED_THRESHOLD:
        high_risk_features.append(f"hypotension (SBP {int(sbp)})")
        
    if high_risk_features:
        return True, f"High-risk chest symptom pattern detected (chest pain with {', '.join(high_risk_features)})."
    return False, None


# -----------------------------------------------------------------------------
# 10. ANAPHYLAXIS PATTERN (WHO BEC Red Pattern)
# -----------------------------------------------------------------------------

def _eval_anaphylaxis_pattern(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    swelling = parse_tristate(data.get("facial_or_tongue_swelling"))
    airway_swelling = parse_tristate(data.get("airway_swelling"))
    hives = parse_tristate(data.get("generalized_hives"))
    dyspnea = parse_tristate(data.get("breathing_difficulty"))
    stridor = parse_tristate(data.get("stridor"))
    wheezing = parse_tristate(data.get("wheezing"))
    sbp = parse_numeric_vital(data.get("systolic_bp"), "systolic_bp")
    
    mucocutaneous = swelling.is_true() or airway_swelling.is_true() or hives.is_true()
    respiratory_or_circ = (
        dyspnea.is_true() or 
        stridor.is_true() or 
        wheezing.is_true() or 
        (sbp is not None and sbp < SBP_LOW_RED_THRESHOLD)
    )
    
    if mucocutaneous and respiratory_or_circ:
        return True, "Allergic reaction with airway, respiratory, or circulatory compromise pattern detected."
    return False, None


# -----------------------------------------------------------------------------
# 11. OBSTETRIC RED FLAGS (WHO BEC Obstetric Red Flags)
# -----------------------------------------------------------------------------

def _eval_obstetric_red_flags(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    pregnant = parse_tristate(data.get("pregnant"))
    if not pregnant.is_true():
        return False, None
        
    bleeding = parse_tristate(data.get("severe_bleeding")) or parse_tristate(data.get("heavy_bleeding"))
    abdo_pain = parse_tristate(data.get("severe_abdominal_pain"))
    convulsion = parse_tristate(data.get("active_convulsion")) or parse_tristate(data.get("actively_seizing"))
    sbp = parse_numeric_vital(data.get("systolic_bp"), "systolic_bp")
    dbp = parse_numeric_vital(data.get("diastolic_bp"), "diastolic_bp")
    
    ob_issues: List[str] = []
    if bleeding.is_true():
        ob_issues.append("severe bleeding in pregnancy")
    if abdo_pain.is_true():
        ob_issues.append("severe abdominal pain in pregnancy")
    if convulsion.is_true():
        ob_issues.append("active seizure in pregnancy")
    if (sbp is not None and sbp >= OB_SBP_SEVERE_THRESHOLD) or (dbp is not None and dbp >= OB_DBP_SEVERE_THRESHOLD):
        ob_issues.append(f"severe hypertension in pregnancy ({int(sbp or 0)}/{int(dbp or 0)} mmHg)")
        
    if ob_issues:
        return True, f"Obstetric emergency red flag detected ({', '.join(ob_issues)})."
    return False, None


# -----------------------------------------------------------------------------
# MASTER RULE REGISTRY
# -----------------------------------------------------------------------------

MASTER_RULES: List[RedFlagRule] = [
    # Airway
    RedFlagRule(
        rule_id=RuleId.RF_AIRWAY_001,
        category="airway",
        name="Airway Compromise / Stridor",
        clinical_reference="WHO/ICRC/MSF IITT Adult (>=12)",
        priority=Priority.EMERGENCY,
        rationale="Airway compromise, stridor, or acute obstruction detected.",
        evaluator=_eval_airway_compromise,
    ),
    # Breathing
    RedFlagRule(
        rule_id=RuleId.RF_RESP_001,
        category="breathing",
        name="Severe Respiratory Distress / Cyanosis",
        clinical_reference="WHO/ICRC/MSF IITT Adult (>=12)",
        priority=Priority.EMERGENCY,
        rationale="Severe respiratory distress or central cyanosis detected.",
        evaluator=_eval_respiratory_distress,
    ),
    RedFlagRule(
        rule_id=RuleId.RF_VIT_SPO2,
        category="breathing",
        name="Critical Hypoxemia (SpO2 < 92%)",
        clinical_reference="WHO/ICRC/MSF IITT Adult (>=12)",
        priority=Priority.EMERGENCY,
        rationale="Oxygen saturation (SpO2) < 92% detected (WHO IITT adult red threshold).",
        evaluator=_eval_vital_spo2,
    ),
    RedFlagRule(
        rule_id=RuleId.RF_VIT_RR,
        category="breathing",
        name="Severe Respiratory Rate Abnormality (RR < 10 or > 30)",
        clinical_reference="WHO/ICRC/MSF IITT Adult (>=12)",
        priority=Priority.EMERGENCY,
        rationale="Extreme adult respiratory rate (< 10 or > 30 /min) detected (WHO IITT adult red threshold).",
        evaluator=_eval_vital_rr,
    ),
    # Circulation
    RedFlagRule(
        rule_id=RuleId.RF_CIRC_001,
        category="circulation",
        name="Heavy / Uncontrolled Bleeding",
        clinical_reference="WHO/ICRC/MSF IITT Adult (>=12)",
        priority=Priority.EMERGENCY,
        rationale="Heavy or uncontrolled external bleeding detected.",
        evaluator=_eval_heavy_bleeding,
    ),
    RedFlagRule(
        rule_id=RuleId.RF_VIT_SBP,
        category="circulation",
        name="Severe Hypotension / Shock (SBP < 90)",
        clinical_reference="WHO/ICRC/MSF IITT Adult (>=12)",
        priority=Priority.EMERGENCY,
        rationale="Systolic blood pressure < 90 mmHg indicating shock detected (WHO IITT adult red threshold).",
        evaluator=_eval_vital_sbp,
    ),
    RedFlagRule(
        rule_id=RuleId.RF_VIT_HR,
        category="circulation",
        name="Severe Heart Rate Abnormality (HR < 60 or > 130)",
        clinical_reference="WHO/ICRC/MSF IITT Adult (>=12)",
        priority=Priority.EMERGENCY,
        rationale="Extreme adult heart rate (< 60 or > 130 bpm) detected (WHO IITT adult red threshold).",
        evaluator=_eval_vital_hr,
    ),
    # Consciousness / Neurological
    RedFlagRule(
        rule_id=RuleId.RF_NEURO_001,
        category="consciousness",
        name="Unresponsiveness / Impaired AVPU / Low GCS",
        clinical_reference="WHO/ICRC/MSF IITT Adult (>=12)",
        priority=Priority.EMERGENCY,
        rationale="Unresponsive, AVPU != Alert, or GCS <= 8 detected.",
        evaluator=_eval_unresponsiveness,
    ),
    RedFlagRule(
        rule_id=RuleId.RF_NEURO_002,
        category="consciousness",
        name="Acute Altered Mental Status / Confusion",
        clinical_reference="WHO/ICRC/MSF IITT Adult (>=12)",
        priority=Priority.EMERGENCY,
        rationale="Acute altered mental status or acute confusion detected.",
        evaluator=_eval_altered_mental_status,
    ),
    RedFlagRule(
        rule_id=RuleId.RF_NEURO_FOCAL,
        category="focal_neurological",
        name="Acute Focal Neurological Deficit",
        clinical_reference="WHO Basic Emergency Care (BEC)",
        priority=Priority.EMERGENCY,
        rationale="Acute focal neurological red flag detected (sudden weakness, facial weakness, speech difficulty, or vision loss).",
        evaluator=_eval_focal_neurological,
    ),
    # Convulsions
    RedFlagRule(
        rule_id=RuleId.RF_CONV_001,
        category="convulsions",
        name="Active Convulsions",
        clinical_reference="WHO/ICRC/MSF IITT Adult (>=12)",
        priority=Priority.EMERGENCY,
        rationale="Active convulsion or ongoing seizure activity detected.",
        evaluator=_eval_active_convulsion,
    ),
    # Temperature
    RedFlagRule(
        rule_id=RuleId.RF_TEMP_001,
        category="temperature",
        name="Extreme Temperature (< 36.0°C or > 39.0°C)",
        clinical_reference="WHO/ICRC/MSF IITT Adult (>=12)",
        priority=Priority.EMERGENCY,
        rationale="Extreme body temperature (< 36.0°C or > 39.0°C) detected (WHO IITT adult red threshold).",
        evaluator=_eval_vital_temp,
    ),
    # Trauma
    RedFlagRule(
        rule_id=RuleId.RF_TRAUMA_001,
        category="trauma",
        name="High-Risk Trauma / Penetrating Injury / Burns",
        clinical_reference="WHO/ICRC/MSF IITT Adult (>=12)",
        priority=Priority.EMERGENCY,
        rationale="Major trauma, penetrating injury, or severe burn detected.",
        evaluator=_eval_high_risk_trauma,
    ),
    # Toxic Exposure
    RedFlagRule(
        rule_id=RuleId.RF_TOX_001,
        category="toxic_exposure",
        name="Poisoning / Toxic Exposure / Snakebite",
        clinical_reference="WHO/ICRC/MSF IITT Adult (>=12)",
        priority=Priority.EMERGENCY,
        rationale="Poisoning, chemical exposure, or snakebite envenomation detected.",
        evaluator=_eval_toxic_exposure,
    ),
    # High-Risk Chest Syndrome
    RedFlagRule(
        rule_id=RuleId.RF_CHEST_001,
        category="chest",
        name="High-Risk Chest Symptom Pattern",
        clinical_reference="WHO Basic Emergency Care (BEC)",
        priority=Priority.EMERGENCY,
        rationale="High-risk chest symptom pattern detected.",
        evaluator=_eval_chest_syndrome,
    ),
    # Allergic / Anaphylaxis
    RedFlagRule(
        rule_id=RuleId.RF_ALLERGY_001,
        category="allergy",
        name="Allergic Reaction with Compromise Pattern",
        clinical_reference="WHO Basic Emergency Care (BEC)",
        priority=Priority.EMERGENCY,
        rationale="Allergic reaction with airway, respiratory, or circulatory compromise pattern detected.",
        evaluator=_eval_anaphylaxis_pattern,
    ),
    # Obstetric Red Flags
    RedFlagRule(
        rule_id=RuleId.RF_OB_001,
        category="obstetric",
        name="Obstetric Emergency Red Flag",
        clinical_reference="WHO Basic Emergency Care (BEC)",
        priority=Priority.EMERGENCY,
        rationale="Obstetric emergency red flag detected in pregnancy.",
        evaluator=_eval_obstetric_red_flags,
    ),
]


# Universal emergency rules that apply across all age groups (including pediatric patients)
UNIVERSAL_EMERGENCY_RULES = {
    RuleId.RF_AIRWAY_001,
    RuleId.RF_RESP_001,
    RuleId.RF_CIRC_001,
    RuleId.RF_NEURO_001,
    RuleId.RF_CONV_001,
    RuleId.RF_TRAUMA_001,
    RuleId.RF_TOX_001,
    RuleId.RF_NEURO_FOCAL,
    RuleId.RF_ALLERGY_001,
    RuleId.RF_OB_001,
}


def evaluate_all_rules(intake_data: Dict[str, Any]) -> Tuple[List[str], List[str], List[str]]:
    """
    Deterministically evaluate ALL registered red-flag safety rules against the patient facts.
    
    Returns:
      (triggered_rule_ids: List[str], red_flag_descriptions: List[str], rule_rationales: List[str])
    """
    triggered_rule_ids: List[str] = []
    red_flag_descriptions: List[str] = []
    rule_rationales: List[str] = []
    
    for rule in MASTER_RULES:
        is_triggered, description = rule.evaluate(intake_data)
        if is_triggered:
            triggered_rule_ids.append(rule.rule_id)
            if description:
                red_flag_descriptions.append(description)
            rule_rationales.append(f"[{rule.rule_id}]: {rule.rationale}")
            
    return triggered_rule_ids, red_flag_descriptions, rule_rationales
