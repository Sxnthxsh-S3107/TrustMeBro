import React, { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { getMyQueue, logoutDoctor } from "../services/api";
import { normalizePatientCard } from "../adapters/triageAdapter";
import PatientCard from "../components/doctor/PatientCard";
import ReprioritizeModal from "../components/doctor/ReprioritizeModal";

export default function DoctorDashboard() {
  const [queue, setQueue] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [reprioritizePatient, setReprioritizePatient] = useState(null);
  const navigate = useNavigate();

  const doctorName = localStorage.getItem("doctor_name");

  const fetchQueue = async () => {
    try {
      const data = await getMyQueue();
      setQueue(data.map(normalizePatientCard));
      setError(null);
    } catch (err) {
      if (err.response?.status === 401) {
        logoutDoctor();
        navigate("/doctor/login");
      } else {
        setError("Unable to connect to the triage service. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
    // Poll every 10 seconds
    const interval = setInterval(fetchQueue, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleLogout = () => {
    logoutDoctor();
    navigate("/doctor/login");
  };

  return (
    <div className="container">
      <div className="dashboard-header">
        <div>
          <h1>RuralCare Triage</h1>
          <p style={{ color: "var(--text-secondary)" }}>Logged in as: <strong>{doctorName}</strong></p>
        </div>
        <div style={{ display: "flex", gap: "1rem" }}>
          <Link to="/doctor/history" className="btn btn-secondary">Override History</Link>
          <button className="btn btn-secondary" onClick={handleLogout}>Logout</button>
        </div>
      </div>

      {error && (
        <div style={{ padding: "1rem", background: "var(--priority-emergency-bg)", color: "var(--priority-emergency-text)", borderRadius: "8px", marginBottom: "2rem" }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      <h2>Live Patient Queue</h2>
      <p style={{ marginBottom: "2rem", color: "var(--text-secondary)" }}>Auto-refreshing every 10 seconds.</p>

      {loading && queue.length === 0 ? (
        <p>Loading patient queue...</p>
      ) : queue.length === 0 ? (
        <div style={{ padding: "3rem", textAlign: "center", background: "var(--card-bg)", borderRadius: "8px", border: "1px dashed var(--border-color)" }}>
          <h3>No patients currently waiting.</h3>
          <p style={{ color: "var(--text-secondary)" }}>The queue is empty.</p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {queue.map(patient => (
            <PatientCard 
              key={patient.patientId} 
              patient={patient} 
              onReprioritize={setReprioritizePatient} 
            />
          ))}
        </div>
      )}

      {reprioritizePatient && (
        <ReprioritizeModal 
          patient={reprioritizePatient} 
          onClose={() => setReprioritizePatient(null)} 
          onSuccess={() => {
            setReprioritizePatient(null);
            fetchQueue();
          }}
        />
      )}
    </div>
  );
}
