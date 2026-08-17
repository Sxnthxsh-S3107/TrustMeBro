/**
 * Adapts Person 3 Decision Engine's API values to UI presentation values.
 * 
 * Person 3 Priority uses: 'emergency', 'same-day', 'routine'
 * We present them as constants.
 */

export const PRIORITY = {
  EMERGENCY: "EMERGENCY",
  SAME_DAY: "SAME-DAY",
  ROUTINE: "ROUTINE",
};

export const parsePriority = (backendPriority) => {
  if (!backendPriority) return PRIORITY.ROUTINE;
  switch (backendPriority.toLowerCase()) {
    case "emergency":
      return PRIORITY.EMERGENCY;
    case "same-day":
      return PRIORITY.SAME_DAY;
    case "routine":
    default:
      return PRIORITY.ROUTINE;
  }
};

export const formatPriorityToBackend = (uiPriority) => {
  switch (uiPriority) {
    case PRIORITY.EMERGENCY:
      return "emergency";
    case PRIORITY.SAME_DAY:
      return "same-day";
    case PRIORITY.ROUTINE:
    default:
      return "routine";
  }
};

/**
 * Ensures a patient item has safe default values for the UI.
 */
export const normalizePatientCard = (patient) => {
  return {
    patientId: patient.patient_id || "Unknown",
    priority: parsePriority(patient.priority),
    rationale: patient.rationale || "No rationale provided by decision engine.",
    chiefComplaint: patient.chief_complaint || "Not specified",
    duration: patient.duration || "Not specified",
    redFlag: Boolean(patient.red_flag),
    safetyRedFlags: patient.safety_red_flags || [],
    history: patient.relevant_history || "None",
    assignedDoctor: patient.assigned_doctor,
    assignmentReason: patient.assignment_reason,
  };
};
