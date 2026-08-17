import axios from "axios";

// ─────────────────────────────────────────────────────────────────────────────
// API CLIENT CONFIGURATION
//
// We use Vite's built-in proxy (configured in vite.config.js) so all requests
// go through the same origin (localhost:5173). This eliminates CORS preflight
// failures entirely during development.
//
// The proxy routes:
//   /intake/*   → http://127.0.0.1:5000  (Person 2 Flask)
//   /transcribe → http://127.0.0.1:5000  (Person 2 Flask)
//   /triage     → http://127.0.0.1:8000  (Person 3 FastAPI)
//   /my-queue   → http://127.0.0.1:8000  (Person 3 FastAPI)
//   /login      → http://127.0.0.1:8000  (Person 3 FastAPI)
//   /override   → http://127.0.0.1:8000  (Person 3 FastAPI)
//
// In production, replace these with actual service hostnames.
// ─────────────────────────────────────────────────────────────────────────────

// Person 3 Decision Engine — uses relative URL so Vite proxy forwards to :8000
export const decisionApi = axios.create({
  baseURL: "/",
});

// Person 2 Voice Intake — uses relative URL so Vite proxy forwards to :5000
export const voiceApi = axios.create({
  baseURL: "/",
});

// Inject bearer token for all Decision Engine requests (doctor auth)
decisionApi.interceptors.request.use((config) => {
  const token = localStorage.getItem("doctor_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Doctor Auth ──

export const loginDoctor = async (doctorId, password) => {
  const response = await decisionApi.post(
    `/login?doctor_id=${doctorId}&password=${password}`
  );
  if (response.data?.token) {
    localStorage.setItem("doctor_token", response.data.token);
    localStorage.setItem("doctor_id", response.data.doctor_id);
    localStorage.setItem("doctor_name", response.data.name);
  }
  return response.data;
};

export const logoutDoctor = () => {
  localStorage.removeItem("doctor_token");
  localStorage.removeItem("doctor_id");
  localStorage.removeItem("doctor_name");
};

// ── Voice Intake APIs (Person 2) ──

export const startIntake = async (language) => {
  const response = await voiceApi.post("/intake/start", { language });
  return response.data;
};

export const submitIntakeAnswerText = async (sessionId, text) => {
  const response = await voiceApi.post("/intake/answer", {
    session_id: sessionId,
    text,
  });
  return response.data;
};

export const transcribeAudio = async (sessionId, language, blob) => {
  const formData = new FormData();
  // Field name must be "audio" — this is what Person 2's /transcribe expects
  const filename = blob.name || "recording.webm";
  formData.append("audio", blob, filename);
  formData.append("session_id", sessionId);
  formData.append("language", language);

  const response = await voiceApi.post("/transcribe", formData, {
    // Do NOT set Content-Type manually — let the browser set the boundary
    headers: { "Content-Type": undefined },
  });
  return response.data;
};

export const getIntakeResult = async (sessionId) => {
  const response = await voiceApi.get(`/intake/result?session_id=${sessionId}`);
  return response.data;
};

// ── Triage / Decision Engine APIs (Person 3) ──

export const submitToDecisionEngine = async (intakeJson) => {
  // The Person 2 canonical JSON is sent directly to Person 3's /triage.
  // Person 3 then calls Person 1 internally.
  const response = await decisionApi.post("/triage", intakeJson);
  return response.data;
};

export const getMyQueue = async () => {
  const response = await decisionApi.get("/my-queue");
  return response.data;
};

export const overridePriority = async (patientId, newPriority, reason) => {
  const doctorId = localStorage.getItem("doctor_id");
  const response = await decisionApi.post(
    `/override?patient_id=${patientId}&new_priority=${newPriority}&doctor_id=${doctorId}`,
    reason ? { reason } : {}
  );
  return response.data;
};

export const getOverrideLog = async () => {
  const response = await decisionApi.get("/override/log");
  return response.data;
};
