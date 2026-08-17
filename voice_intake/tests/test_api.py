"""Unit and integration tests for Flask REST API endpoints and CORS.
"""

import json
import io
import pytest
from voice_intake.app.main import app, session_manager, asr_service
from voice_intake.app.asr import MockASRService


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["service"] == "voice_intake"
    assert "en" in data["supported_languages"]
    assert "ta" in data["supported_languages"]
    # Check CORS
    assert "Access-Control-Allow-Origin" in response.headers


def test_get_languages(client):
    response = client.get("/languages")
    assert response.status_code == 200
    data = response.get_json()
    assert "languages" in data
    codes = [l["code"] for l in data["languages"]]
    assert "en" in codes
    assert "ta" in codes
    assert len(codes) == 2  # strictly only en and ta for this milestone


def test_session_creation(client):
    # Valid English session
    res = client.post("/intake/start", json={"language": "en"})
    assert res.status_code == 201
    data = res.get_json()
    assert "session_id" in data
    assert data["language"] == "en"
    assert data["first_question"]["question_id"] == "chief_complaint"

    # Valid Tamil session
    res_ta = client.post("/intake/start", json={"language": "ta"})
    assert res_ta.status_code == 201
    data_ta = res_ta.get_json()
    assert data_ta["language"] == "ta"
    assert "உங்களுக்கு என்ன பிரச்சனை" in data_ta["first_question"]["question_text"]

    # Unsupported language
    res_err = client.post("/intake/start", json={"language": "hi"})
    assert res_err.status_code == 400


def test_full_intake_api_journey(client):
    # 1. Start Session
    res_start = client.post("/intake/start", json={"language": "en"})
    session_id = res_start.get_json()["session_id"]

    # 2. Get Question 1
    res_q1 = client.get(f"/intake/question?session_id={session_id}")
    assert res_q1.status_code == 200
    assert res_q1.get_json()["question"]["question_id"] == "chief_complaint"

    # 3. Answer Q1: Chief Complaint
    res_a1 = client.post("/intake/answer", json={
        "session_id": session_id,
        "text": "I have chest pain"
    })
    assert res_a1.status_code == 200
    assert res_a1.get_json()["extracted"]["chief_complaint"] == "chest pain"

    # 4. Answer Q2: Duration
    res_a2 = client.post("/intake/answer", json={
        "session_id": session_id,
        "text": "It started two hours ago"
    })
    assert res_a2.get_json()["extracted"]["duration"] == "2 hours"

    # 5. Answer Q3: Medications
    res_a3 = client.post("/intake/answer", json={
        "session_id": session_id,
        "text": "insulin"
    })
    assert res_a3.get_json()["extracted"]["medications"] == ["insulin"]

    # 6. Answer Q4: History
    res_a4 = client.post("/intake/answer", json={
        "session_id": session_id,
        "text": "diabetic"
    })
    assert res_a4.get_json()["extracted"]["history"] == "diabetic"

    # 7. Answer Adaptive 1: Radiating Pain
    res_ad1 = client.post("/intake/answer", json={
        "session_id": session_id,
        "text": "yes"
    })
    assert res_ad1.get_json()["extracted"]["radiating_pain"] is True

    # 8. Answer Adaptive 2: Sweating
    res_ad2 = client.post("/intake/answer", json={
        "session_id": session_id,
        "text": "no"
    })
    assert res_ad2.get_json()["extracted"]["sweating"] is False
    assert res_ad2.get_json()["status"] == "completed"

    # 9. Get Final Result
    res_result = client.get(f"/intake/result?session_id={session_id}")
    assert res_result.status_code == 200
    result_data = res_result.get_json()
    assert result_data["session_id"] == session_id
    assert result_data["chief_complaint"] == "chest pain"
    assert result_data["duration"] == "2 hours"
    assert result_data["medications"] == ["insulin"]
    assert result_data["history"] == "diabetic"
    assert result_data["follow_up_answers"] == {"radiating_pain": True, "sweating": False}
    assert result_data["status"] == "completed"


@pytest.fixture(autouse=True)
def ensure_mock_asr(monkeypatch):
    """Ensure MockASRService is active during tests."""
    import voice_intake.app.main as main_mod
    mock_service = MockASRService()
    monkeypatch.setattr(main_mod, "asr_service", mock_service)
    yield mock_service


def test_transcribe_endpoint_distinct_sentences(client, ensure_mock_asr):
    # Test 1: English headache
    ensure_mock_asr.set_next_response("I have a headache")
    data_en1 = {
        "audio": (io.BytesIO(b"dummy audio binary data 1234567890" * 10), "test1.webm"),
        "language": "en"
    }
    res1 = client.post("/transcribe", data=data_en1, content_type="multipart/form-data")
    assert res1.status_code == 200
    assert res1.get_json()["transcript"] == "I have a headache"

    # Test 2: English stomach pain
    ensure_mock_asr.set_next_response("I have stomach pain")
    data_en2 = {
        "audio": (io.BytesIO(b"dummy audio binary data 1234567890" * 10), "test2.webm"),
        "language": "en"
    }
    res2 = client.post("/transcribe", data=data_en2, content_type="multipart/form-data")
    assert res2.status_code == 200
    assert res2.get_json()["transcript"] == "I have stomach pain"

    # Test 3: Tamil headache
    ensure_mock_asr.set_next_response("எனக்கு தலை வலி")
    data_ta = {
        "audio": (io.BytesIO(b"dummy audio binary data 1234567890" * 10), "test3.webm"),
        "language": "ta"
    }
    res3 = client.post("/transcribe", data=data_ta, content_type="multipart/form-data")
    assert res3.status_code == 200
    assert res3.get_json()["transcript"] == "எனக்கு தலை வலி"


def test_invalid_session_handling(client):
    res_q = client.get("/intake/question?session_id=non-existent-id")
    assert res_q.status_code == 404

    res_a = client.post("/intake/answer", json={"session_id": "non-existent-id", "text": "test"})
    assert res_a.status_code == 404

    res_r = client.get("/intake/result?session_id=non-existent-id")
    assert res_r.status_code == 404
