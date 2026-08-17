import React from "react";
import { useParams, Link } from "react-router-dom";
import { CheckCircle } from "lucide-react";

export default function PatientStatus() {
  const { id } = useParams();

  return (
    <div className="container" style={{ textAlign: "center", paddingTop: "10vh" }}>
      <CheckCircle size={64} color="var(--priority-routine-text)" style={{ marginBottom: "1.5rem" }} />
      <h1 style={{ marginBottom: "1rem" }}>Consultation Submitted</h1>
      <p style={{ fontSize: "1.25rem", color: "var(--text-secondary)", marginBottom: "2rem" }}>
        Your case has been received and is being analyzed.
      </p>

      <div className="card" style={{ maxWidth: "400px", margin: "0 auto 3rem auto", padding: "2rem" }}>
        <h3 style={{ color: "var(--text-secondary)", marginBottom: "0.5rem" }}>Your Queue Reference ID</h3>
        <div style={{ fontSize: "2.5rem", fontWeight: "bold", letterSpacing: "2px", color: "var(--primary-color)" }}>
          {id}
        </div>
        <div style={{ marginTop: "1.5rem", padding: "0.75rem", background: "#f5f5f5", borderRadius: "4px" }}>
          <strong>Status:</strong> WAITING FOR DOCTOR REVIEW
        </div>
      </div>

      <Link to="/" className="btn btn-secondary">Return to Home</Link>
    </div>
  );
}
