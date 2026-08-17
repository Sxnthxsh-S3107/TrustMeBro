import uuid

# demo doctor accounts — hackathon only, not real auth
DEMO_DOCTORS = {
    "dr_a": {"password": "pass123", "name": "Dr. A"},
    "dr_b": {"password": "pass123", "name": "Dr. B"},
    "dr_c": {"password": "pass123", "name": "Dr. C"},
}

# token -> doctor_id, in-memory session store
active_sessions: dict[str, str] = {}

def login(doctor_id: str, password: str) -> dict | None:
    account = DEMO_DOCTORS.get(doctor_id)
    if not account or account["password"] != password:
        return None
    token = str(uuid.uuid4())
    active_sessions[token] = doctor_id
    return {"token": token, "doctor_id": doctor_id, "name": account["name"]}

def get_doctor_from_token(token: str) -> str | None:
    return active_sessions.get(token)