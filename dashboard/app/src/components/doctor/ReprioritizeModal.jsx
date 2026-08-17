import React, { useState } from "react";
import { overridePriority } from "../../services/api";

export default function ReprioritizeModal({ patient, onClose, onSuccess }) {
  const [newPriority, setNewPriority] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!newPriority) return;
    setLoading(true);
    try {
      await overridePriority(patient.patientId, newPriority);
      onSuccess();
    } catch (err) {
      alert("Failed to override priority.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <h2>Re-prioritise Patient: {patient.patientId}</h2>
        <p style={{ marginBottom: "1rem", color: "var(--text-secondary)" }}>
          Original priority was set to <strong>{patient.priority}</strong> by the decision engine.
        </p>

        {patient.redFlag && (
          <div className="red-flag-alert" style={{ width: "100%", marginBottom: "1rem" }}>
            ⚠ WARNING: A safety red flag is active for this patient.
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Select New Priority</label>
            <select 
              className="form-input" 
              value={newPriority} 
              onChange={(e) => setNewPriority(e.target.value)}
              required
            >
              <option value="" disabled>Select...</option>
              <option value="emergency">EMERGENCY</option>
              <option value="same-day">SAME-DAY</option>
              <option value="routine">ROUTINE</option>
            </select>
          </div>
          
          <div style={{ display: "flex", gap: "1rem", justifyContent: "flex-end" }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading || !newPriority}>
              {loading ? "Saving..." : "Confirm Override"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
