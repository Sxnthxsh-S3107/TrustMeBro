import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import PatientHome from "./pages/PatientHome";
import PatientConsultation from "./pages/PatientConsultation";
import PatientStatus from "./pages/PatientStatus";
import DoctorLogin from "./pages/DoctorLogin";
import DoctorDashboard from "./pages/DoctorDashboard";
import OverrideHistory from "./pages/OverrideHistory";

const ProtectedRoute = ({ children }) => {
  const token = localStorage.getItem("doctor_token");
  if (!token) {
    return <Navigate to="/doctor/login" />;
  }
  return children;
};

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<PatientHome />} />
        <Route path="/patient/consultation" element={<PatientConsultation />} />
        <Route path="/patient/status/:id" element={<PatientStatus />} />
        
        <Route path="/doctor/login" element={<DoctorLogin />} />
        <Route 
          path="/doctor/dashboard" 
          element={
            <ProtectedRoute>
              <DoctorDashboard />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/doctor/history" 
          element={
            <ProtectedRoute>
              <OverrideHistory />
            </ProtectedRoute>
          } 
        />
      </Routes>
    </Router>
  );
}

export default App;
