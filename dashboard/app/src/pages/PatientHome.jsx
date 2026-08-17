import React from "react";
import { Link } from "react-router-dom";
import { HeartPulse, Stethoscope, Clock } from "lucide-react";

export default function PatientHome() {
  return (
    <div className="container" style={{ textAlign: "center", paddingTop: "5vh" }}>
      <HeartPulse size={64} color="var(--primary-color)" style={{ marginBottom: "1rem" }} />
      <h1 style={{ fontSize: "3rem", marginBottom: "0.5rem" }}>RuralCare</h1>
      <p style={{ fontSize: "1.25rem", color: "var(--text-secondary)", marginBottom: "3rem", maxWidth: "600px", margin: "0 auto 3rem auto" }}>
        Smart healthcare triage for faster medical attention. Tell us what's wrong, and we'll ensure you see the right doctor quickly.
      </p>

      <div style={{ display: "flex", flexDirection: "column", gap: "1rem", maxWidth: "400px", margin: "0 auto" }}>
        <Link to="/patient/consultation" className="btn btn-primary" style={{ fontSize: "1.25rem", padding: "1rem" }}>
          Start Consultation
        </Link>
        <Link to="/doctor/login" className="btn btn-secondary">
          Doctor Login
        </Link>
      </div>

      <div style={{ display: "flex", justifyContent: "center", gap: "3rem", marginTop: "5rem", color: "var(--text-secondary)" }}>
        <div style={{ textAlign: "center", maxWidth: "200px" }}>
          <Stethoscope size={32} style={{ marginBottom: "1rem" }} />
          <h3>Expert Triage</h3>
          <p>Your symptoms are analyzed by our advanced safety engine.</p>
        </div>
        <div style={{ textAlign: "center", maxWidth: "200px" }}>
          <Clock size={32} style={{ marginBottom: "1rem" }} />
          <h3>Save Time</h3>
          <p>Get placed in the right queue before you even sit down.</p>
        </div>
      </div>
    </div>
  );
}
