import React from "react";
import { PRIORITY } from "../../adapters/triageAdapter";
import { AlertTriangle, Clock, Activity, FileText, ShieldAlert } from "lucide-react";

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

      <div style={{ display: "grid", gap: "0.75rem", marginBottom: "1.5rem", marginTop: "0.5rem" }}>
        {/* ① Chief Complaint */}
        <div>
          <strong><Activity size={16} style={{ verticalAlign: "middle", marginRight: "6px" }} />Chief Complaint:</strong>
          <p style={{ marginTop: "4px" }}>{patient.chiefComplaint}</p>
        </div>
        
        {/* ② Duration */}
        <div>
          <strong><Clock size={16} style={{ verticalAlign: "middle", marginRight: "6px" }} />Duration:</strong>
          <p style={{ marginTop: "4px" }}>{patient.duration}</p>
        </div>

        {/* ③ Red Flags */}
        <div>
          <strong><ShieldAlert size={16} style={{ verticalAlign: "middle", marginRight: "6px" }} />Red Flags:</strong>
          {patient.redFlag ? (
            <div style={{ marginTop: "4px" }}>
              <div className="red-flag-alert" style={{ display: "inline-flex", padding: "0.25rem 0.5rem", fontSize: "0.875rem", marginBottom: "4px" }}>
                <AlertTriangle size={14} />
                ⚠ RED FLAG DETECTED
              </div>
              {patient.safetyRedFlags && patient.safetyRedFlags.length > 0 ? (
                <ul style={{ listStyleType: "none", paddingLeft: "4px", margin: "4px 0" }}>
                  {patient.safetyRedFlags.map((rf, idx) => (
                    <li key={idx} style={{ color: "var(--priority-emergency-text)", fontWeight: "500", fontSize: "0.95rem" }}>
                      [{rf.rule_id}] {rf.message}
                    </li>
                  ))}
                </ul>
              ) : (
                <p style={{ color: "var(--priority-emergency-text)", fontWeight: "500", marginTop: "4px" }}>
                  Emergency rules triggered.
                </p>
              )}
            </div>
          ) : (
            <p style={{ marginTop: "4px", color: "var(--text-secondary)" }}>No red flags detected</p>
          )}
        </div>

        {/* ④ Relevant History */}
        <div>
          <strong><FileText size={16} style={{ verticalAlign: "middle", marginRight: "6px" }} />Relevant History:</strong>
          <p style={{ marginTop: "4px" }}>{patient.history}</p>
        </div>
      </div>

      {/* ⑤ Priority Rationale */}
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
