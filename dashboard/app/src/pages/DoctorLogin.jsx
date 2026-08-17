import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { loginDoctor } from "../services/api";

export default function DoctorLogin() {
  const [doctorId, setDoctorId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await loginDoctor(doctorId, password);
      navigate("/doctor/dashboard");
    } catch (err) {
      setError("Invalid login credentials. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container" style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh" }}>
      <div className="auth-container" style={{ width: "100%" }}>
        <h2 style={{ textAlign: "center", marginBottom: "1.5rem" }}>Doctor Login</h2>
        <p style={{ textAlign: "center", color: "var(--text-secondary)", marginBottom: "2rem" }}>
          RuralCare System Authentication
        </p>

        {error && <div style={{ color: "var(--red-flag-bg)", marginBottom: "1rem", fontWeight: "bold" }}>{error}</div>}

        <form onSubmit={handleLogin}>
          <div className="form-group">
            <label className="form-label">Doctor ID</label>
            <input 
              type="text" 
              className="form-input" 
              value={doctorId}
              onChange={(e) => setDoctorId(e.target.value)}
              placeholder="e.g. dr_a"
              required 
            />
          </div>
          <div className="form-group">
            <label className="form-label">Password</label>
            <input 
              type="password" 
              className="form-input" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="e.g. pass123"
              required 
            />
          </div>
          <button type="submit" className="btn btn-primary" style={{ width: "100%" }} disabled={loading}>
            {loading ? "Logging in..." : "Login"}
          </button>
        </form>

        <div style={{ marginTop: "2rem", padding: "1rem", background: "#f5f5f5", borderRadius: "8px", fontSize: "0.875rem" }}>
          <strong>Demo Credentials:</strong>
          <br/>
          Doctor ID: dr_a / dr_b / dr_c<br/>
          Password: pass123
        </div>
      </div>
    </div>
  );
}
