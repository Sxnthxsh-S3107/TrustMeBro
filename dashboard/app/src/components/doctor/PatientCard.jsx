import React from "react";
import { PRIORITY } from "../../adapters/triageAdapter";
import { AlertTriangle, Clock, Activity, FileText } from "lucide-react";

export default function PatientCard({ patient, onReprioritize }) {
  const badgeClass =
    patient.priority === PRIORITY.EMERGENCY
      ? "badge-emergency"
      : patient.priority === PRIORITY.SAME_DAY
      ? "badge-sameday"
      : "badge-routine";

  return (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "1rem" }}>
        <h3>Patient ID: {patient.patientId}</h3>
        <span className={`badge ${badgeClass}`}>{patient.priority}</span>
      </div>

      {patient.redFlag && (
        <div className="red-flag-alert">
          <AlertTriangle size={18} />
          ⚠ RED FLAG DETECTED
        </div>
      )}

      <div style={{ display: "grid", gap: "0.75rem", marginBottom: "1.5rem", marginTop: "0.5rem" }}>
        <div>
          <strong><Activity size={16} style={{ verticalAlign: "middle", marginRight: "6px" }} />Chief Complaint:</strong>
          <p style={{ marginTop: "4px" }}>{patient.chiefComplaint}</p>
        </div>
        
        <div>
          <strong><Clock size={16} style={{ verticalAlign: "middle", marginRight: "6px" }} />Duration:</strong>
          <p style={{ marginTop: "4px" }}>{patient.duration}</p>
        </div>
        
        <div>
          <strong><FileText size={16} style={{ verticalAlign: "middle", marginRight: "6px" }} />Relevant History:</strong>
          <p style={{ marginTop: "4px" }}>{patient.history}</p>
        </div>
      </div>

      <div style={{ background: "#f5f5f5", padding: "1rem", borderRadius: "4px", marginBottom: "1rem" }}>
        <strong>Priority Rationale:</strong>
        <p style={{ marginTop: "4px", color: "var(--text-secondary)" }}>{patient.rationale}</p>
      </div>

      <div style={{ display: "flex", gap: "1rem" }}>
        <button 
          className="btn btn-secondary" 
          onClick={() => onReprioritize(patient)}
        >
          Re-prioritise
        </button>
      </div>
    </div>
  );
}
