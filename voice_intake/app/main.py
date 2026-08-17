"""Flask REST API and standalone server for Voice Intake + NLP module.
Provides session-isolated endpoints, configurable CORS, and standalone UI serving.
"""

import os
import sys
from pathlib import Path

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv

try:
    from voice_intake.app.question_flow import SessionManager
    from voice_intake.app.asr import get_asr_service, WhisperASRService, MockASRService
except ImportError:
    from question_flow import SessionManager
    from asr import get_asr_service, WhisperASRService, MockASRService

load_dotenv()

# Initialize Flask app with disabled static cache for development
app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

# Initialize Session Manager and ASR Service
session_manager = SessionManager()
asr_service = get_asr_service()

# CORS configuration
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")


@app.after_request
def apply_cors_and_cache_headers(response):
    """Apply configurable CORS and no-cache headers."""
    origin = request.headers.get("Origin")
    if CORS_ORIGINS == "*":
        response.headers["Access-Control-Allow-Origin"] = "*"
    elif origin and any(o.strip() == origin for o in CORS_ORIGINS.split(",")):
        response.headers["Access-Control-Allow-Origin"] = origin
    else:
        response.headers["Access-Control-Allow-Origin"] = CORS_ORIGINS.split(",")[0].strip()

    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"

    # Disable caching so browser changes reflect instantly
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# =====================================================================
# Static & Health Endpoints
# =====================================================================

@app.route("/", methods=["GET"])
def index():
    """Serve standalone test UI."""
    return send_from_directory(app.static_folder, "index.html")


@app.route("/health", methods=["GET", "OPTIONS"])
def health_check():
    """Service health and diagnostic status."""
    if request.method == "OPTIONS":
        return "", 200

    backend_name = "whisper" if isinstance(asr_service, WhisperASRService) else "mock"
    has_api_key = bool(os.getenv("OPENAI_API_KEY"))
    return jsonify({
        "status": "ok",
        "service": "voice_intake",
        "asr_backend": backend_name,
        "whisper_configured": has_api_key,
        "supported_languages": ["en", "ta"]
    }), 200


@app.route("/languages", methods=["GET", "OPTIONS"])
def get_languages():
    """Return supported intake languages."""
    if request.method == "OPTIONS":
        return "", 200

    return jsonify({
        "languages": [
            {"code": "en", "label": "🇬🇧 English", "name": "English"},
            {"code": "ta", "label": "தமிழ் Tamil", "name": "Tamil"}
        ]
    }), 200


# =====================================================================
# Intake Session Endpoints
# =====================================================================

@app.route("/intake/start", methods=["POST", "OPTIONS"])
def start_session():
    """
    Initialize a new independent intake session.
    Body JSON: {"language": "en" | "ta", "patient_id": optional}
    """
    if request.method == "OPTIONS":
        return "", 200

    data = request.get_json(silent=True) or {}
    language = data.get("language", "en")
    patient_id = data.get("patient_id")

    if language not in ["en", "ta"]:
        return jsonify({"error": "Unsupported language. Supported: ['en', 'ta']"}), 400

    session = session_manager.create_session(language=language, patient_id=patient_id)
    first_q = session.get_current_question()

    return jsonify({
        "session_id": session.session_id,
        "language": session.language,
        "status": session.status,
        "first_question": first_q
    }), 201


@app.route("/intake/question", methods=["GET", "OPTIONS"])
def get_current_question():
    """
    Get current active question for the session.
    Query: ?session_id=<id>
    """
    if request.method == "OPTIONS":
        return "", 200

    session_id = request.args.get("session_id")
    if not session_id:
        return jsonify({"error": "Missing session_id query parameter"}), 400

    session = session_manager.get_session(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    current_q = session.get_current_question()
    return jsonify({
        "session_id": session.session_id,
        "question": current_q,
        "status": session.status
    }), 200


@app.route("/transcribe", methods=["POST", "OPTIONS"])
def transcribe_audio():
    """
    Transcribe uploaded audio file without advancing session state.
    Accepts multipart/form-data with 'audio' file, optional 'language' and 'session_id'.
    """
    if request.method == "OPTIONS":
        return "", 200

    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided in request. Expected form field 'audio'."}), 400

    audio_file = request.files["audio"]
    session_id = request.form.get("session_id")
    language = request.form.get("language")

    # Inherit language from session if available
    if session_id:
        session = session_manager.get_session(session_id)
        if session and not language:
            language = session.language

    language = language if language in ["en", "ta"] else "en"

    try:
        audio_bytes = audio_file.read()
        filename = audio_file.filename or "recording.webm"
        content_type = audio_file.content_type or "audio/webm"

        # Diagnostic log
        print(f"[ASR] Received audio: language={language}, filename={filename}, mime_type={content_type}, size={len(audio_bytes)} bytes")

        if len(audio_bytes) < 100:
            return jsonify({
                "error": "NO_SPEECH_DETECTED",
                "success": False,
                "transcript": "",
                "message": "No speech detected or recording is empty. Please speak into the microphone and try again."
            }), 400

        transcript = asr_service.transcribe(
            audio_bytes,
            language=language,
            filename=filename,
            content_type=content_type
        )

        if not transcript or not transcript.strip():
            return jsonify({
                "error": "NO_SPEECH_DETECTED",
                "success": False,
                "transcript": "",
                "message": "No speech detected. Please speak clearly into the microphone and try again."
            }), 400

        return jsonify({
            "transcript": transcript.strip(),
            "language": language,
            "success": True
        }), 200
    except ValueError as ve:
        print(f"[ASR] Configuration/validation error: {ve}")
        return jsonify({"error": str(ve), "error_type": "config_error", "success": False}), 400
    except Exception as e:
        print(f"[ASR] Transcription failed: {e}")
        return jsonify({"error": str(e), "error_type": "transcription_error", "success": False}), 500


@app.route("/intake/answer", methods=["POST", "OPTIONS"])
def submit_answer():
    """
    Submit an answer (as text or recorded audio file) for the current active question.
    Accepts JSON: {"session_id": "...", "text": "..."}
    OR Multipart Form: 'session_id', 'text' OR 'audio' file.
    """
    if request.method == "OPTIONS":
        return "", 200

    raw_text = None
    session_id = None

    # Check JSON body
    if request.is_json:
        data = request.get_json() or {}
        session_id = data.get("session_id")
        raw_text = data.get("text")
    else:
        session_id = request.form.get("session_id")
        raw_text = request.form.get("text")

        # If audio uploaded, transcribe it
        if not raw_text and "audio" in request.files:
            audio_file = request.files["audio"]
            session = session_manager.get_session(session_id) if session_id else None
            lang = session.language if session else "en"
            try:
                audio_bytes = audio_file.read()
                filename = audio_file.filename or "recording.webm"
                content_type = audio_file.content_type or "audio/webm"
                print(f"[ASR] Intake answer audio received: lang={lang}, size={len(audio_bytes)} bytes")
                raw_text = asr_service.transcribe(audio_bytes, language=lang, filename=filename, content_type=content_type)
            except ValueError as ve:
                return jsonify({"error": str(ve), "error_type": "config_error", "success": False}), 400
            except Exception as e:
                return jsonify({"error": f"Audio transcription failed: {str(e)}", "error_type": "transcription_error", "success": False}), 500

    if not session_id:
        return jsonify({"error": "Missing session_id", "success": False}), 400

    session = session_manager.get_session(session_id)
    if not session:
        return jsonify({"error": "Session not found", "success": False}), 404

    if session.status == "completed":
        return jsonify({
            "session_id": session.session_id,
            "status": "completed",
            "message": "Intake session is already completed",
            "intake_result": session.to_contract_dict()
        }), 200

    if raw_text is None or not str(raw_text).strip():
        return jsonify({
            "error": "NO_ANSWER_PROVIDED",
            "message": "An answer is required before proceeding.",
            "success": False
        }), 400

    result = session.process_answer(str(raw_text).strip())
    result["raw_answer_received"] = str(raw_text).strip()

    return jsonify(result), 200


@app.route("/intake/result", methods=["GET", "OPTIONS"])
def get_intake_result():
    """
    Retrieve final structured JSON conforming strictly to contracts/intake_schema.json.
    Query: ?session_id=<id>
    """
    if request.method == "OPTIONS":
        return "", 200

    session_id = request.args.get("session_id")
    if not session_id:
        return jsonify({"error": "Missing session_id query parameter"}), 400

    session = session_manager.get_session(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    return jsonify(session.to_contract_dict()), 200


@app.route("/intake/reset", methods=["POST", "OPTIONS"])
def reset_session():
    """
    Reset session state while retaining session_id and language.
    Body JSON: {"session_id": "..."}
    """
    if request.method == "OPTIONS":
        return "", 200

    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    if not session_id:
        return jsonify({"error": "Missing session_id"}), 400

    new_session = session_manager.reset_session(session_id)
    if not new_session:
        return jsonify({"error": "Session not found"}), 404

    return jsonify({
        "session_id": new_session.session_id,
        "language": new_session.language,
        "status": new_session.status,
        "first_question": new_session.get_current_question()
    }), 200


# =====================================================================
# Main Server Runner
# =====================================================================

if __name__ == "__main__":
    port = int(os.getenv("VOICE_INTAKE_PORT", 5000))
    print(f"Starting Voice Intake + NLP Server on http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
