import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getOverrideLog } from "../services/api";

export default function OverrideHistory() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchLogs() {
      try {
        const data = await getOverrideLog();
        // Sort newest first
        const sorted = data.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
        setLogs(sorted);
      } catch (err) {
        console.error("Failed to fetch logs", err);
      } finally {
        setLoading(false);
      }
    }
    fetchLogs();
  }, []);

  return (
    <div className="container">
      <div className="dashboard-header">
        <h1>Override History</h1>
        <Link to="/doctor/dashboard" className="btn btn-secondary">Back to Dashboard</Link>
      </div>

      {loading ? (
        <p>Loading history...</p>
      ) : logs.length === 0 ? (
        <div className="card">No overrides have been recorded yet.</div>
      ) : (
        <div style={{ display: "grid", gap: "1rem" }}>
          {logs.map(log => (
            <div key={log.timestamp} className="card" style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <strong>Patient: {log.patient_id}</strong>
                <span style={{ color: "var(--text-secondary)", fontSize: "0.875rem" }}>
                  {new Date(log.timestamp).toLocaleString()}
                </span>
              </div>
              <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
                <span>Old Priority: <strong style={{ color: "var(--text-secondary)" }}>{log.old_priority}</strong></span>
                <span>→</span>
                <span>New Priority: <strong>{log.new_priority}</strong></span>
              </div>
              <div style={{ marginTop: "0.5rem", fontSize: "0.875rem", color: "var(--text-secondary)" }}>
                Overridden by: <strong>{log.doctor_id}</strong>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
