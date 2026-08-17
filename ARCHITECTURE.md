# LifeLine Safety Rule Engine Architecture (Person 1)

## 1. System Overview & Safety Boundary

LifeLine is a pre-consultation triage system designed for overloaded rural Primary Health Centres (PHCs). The core architectural principle of LifeLine is the **Hybrid Safety Architecture**:

> **Hardcoded safety rules run before the LLM. If a mandatory red flag is triggered, the case is EMERGENCY and the LLM must never get an opportunity to downgrade it (`llm_allowed = false`).**

```text
                 PATIENT
                    |
              Voice / Text
                    |
             Structured Facts
                    |
                    v
        +-----------------------+
        |   LIFELINE SAFETY     |
        |      RULE ENGINE      |
        |                       |
        |   HARD CODED RULES    |
        |   NON-OVERRIDABLE     |
        +-----------+-----------+
                    |
             Red flag found?
                /       \
              YES        NO
               |          |
               v          v
          EMERGENCY      LLM
             STOP          |
                         Soft
                       prioritisation
                           |
                           v
                  Emergency / Same-day
                       / Routine
                           |
                           v
                    Doctor Dashboard
                           |
                    Explicit Override
                           |
                       Audit Log
```

> **Rules end at the hard safety gate. The LLM begins only when no mandatory hard red flag has been triggered.**

---

## 2. Component Boundaries & Team Responsibilities

| Component / Layer | Owner | Role & Responsibility | Allowed Technologies |
| :--- | :--- | :--- | :--- |
| **Intake / Voice Layer** | Person 2 | Regional speech recognition (ASR), translation, structured clinical facts extraction. | Whisper, regional speech models, JSON extractors |
| **Safety Rule Engine** | **Person 1 (This Module)** | **Deterministic safety gate, red-flag detection, non-overridable triage termination, prompt-injection isolation, confidence gating.** | **100% Deterministic Python (Standard Library only). Zero ML/LLM/APIs.** |
| **Decision Engine / LLM** | Person 3 | Soft classification for non-emergency cases (Routine vs Same-Day), doctor dashboard, explicit doctor override logging. | LLM (e.g. Gemini), backend web framework, database |

---

## 3. Core Safety Invariants

1. **Non-Overridable Emergency Gate**:
   When `check_red_flags()` evaluates an emergency condition:
   $$\text{Priority} = \text{EMERGENCY} \implies \text{llm\_allowed} = \text{False}$$
   Downstream systems must respect this flag and directly place the patient at top queue priority without invoking an LLM.

2. **Strict Tri-State Logic**:
   Clinical features are evaluated under three explicit states:
   - `True` (Explicit positive)
   - `False` (Explicit negative)
   - `Unknown` (Missing, null, unasked, unparseable)
   
   *Missing fields and `unknown` NEVER silently convert to `false`.*

3. **Pediatric Scope Limitation (< 12 Years)**:
   This prototype implements the adult/older child ($\ge 12$ years) triage ruleset derived from WHO IITT. Adult vital sign and respiratory thresholds cannot be safely applied to children under 12. Unrecognized pediatric presentations return `priority="ESCALATE"`, `pediatric_rule_not_supported=true`, and `llm_allowed=false` to mandate direct human clinical review.

4. **Prompt-Injection Defense**:
   - `PATIENT TEXT = DATA`
   - `PATIENT TEXT ≠ INSTRUCTIONS`
   Rules run strictly on structured boolean/numeric facts. Free text is audited for malicious payloads in `security_alerts`, but cannot alter rule evaluations.

5. **No Medical Diagnosis or Prescription**:
   Rationales describe observed clinical red-flag patterns (e.g., *"Acute focal neurological deficit detected"*) rather than diagnosing medical conditions (*"Stroke detected"*). The module never recommends medications, treatments, or dosages.

---

## 4. Authoritative Clinical References

The rules are grounded directly in international emergency and triage standards:

1. **WHO/ICRC/MSF Interagency Integrated Triage Tool (IITT)** - Adult / Older Child ($\ge 12$ years):
   - Airway: Airway compromise, stridor, acute obstruction.
   - Breathing: Severe respiratory distress, central cyanosis, $RR < 10$ or $RR > 30$ /min, $\text{SpO}_2 < 92\%$.
   - Circulation: Heavy/uncontrolled bleeding, $\text{SBP} < 90\text{ mmHg}$, $HR < 60$ or $HR > 130\text{ bpm}$.
   - Consciousness: Unresponsive, AVPU score other than Alert (V/P/U), GCS $\le 8$, acute altered mental status.
   - Convulsions: Active fitting / status epilepticus.
   - Temperature: Extreme hypothermia ($< 36.0^\circ\text{C}$) or hyperpyrexia ($> 39.0^\circ\text{C}$).
   - High-Risk Trauma: Major trauma, penetrating torso/neck injury, severe burns.
   - Toxic Exposure: Poisoning, organophosphate exposure, snakebite envenomation.

2. **WHO Basic Emergency Care (BEC)**:
   - Acute chest syndrome with high-risk features (chest pain + dyspnea / syncope / sweating / hypotension).
   - Acute focal neurological red flags (sudden weakness, facial droop, speech difficulty, vision loss).
   - Anaphylaxis patterns (facial/tongue swelling + respiratory/circulatory compromise).
   - Obstetric emergency red flags (pregnancy + severe bleeding / abdominal pain / seizures / severe hypertension $\ge 160/110$).

---

## 5. Public Integration Interface

Person 3 or any backend developer can drop this package into their codebase and import it directly:

```python
from rules_engine.red_flags import check_red_flags, validate_intake

# 1. Evaluate structured intake facts
result = check_red_flags(patient_intake_data)

# 2. Gate downstream LLM processing
if not result["llm_allowed"]:
    if result["priority"] == "EMERGENCY":
        # Direct immediate clinic escalation
        queue_patient_immediate_emergency(patient_id, result)
    else:
        # Escalate for staff triage / missing data review
        route_to_human_triage_station(patient_id, result)
else:
    # Safe to invoke LLM for soft classification (Routine / Same-Day)
    llm_classification = invoke_triage_llm(patient_intake_data)
```

### Standard Output Schema (JSON Contract)

```json
{
  "priority": "EMERGENCY",
  "source": "HARD_RULE",
  "rule_triggered": true,
  "rule_ids": ["RF_RESP_001", "RF_VIT_SPO2"],
  "red_flags": [
    "Severe respiratory distress detected.",
    "Critical hypoxemia: Oxygen saturation (SpO2) 88.0% is below 92%."
  ],
  "rationale": "A mandatory emergency red flag was detected: [RF_RESP_001]: Severe respiratory distress or central cyanosis detected | [RF_VIT_SPO2]: Oxygen saturation (SpO2) < 92% detected",
  "uncertain": false,
  "pediatric_rule_not_supported": false,
  "llm_allowed": false,
  "security_alerts": []
}
```
