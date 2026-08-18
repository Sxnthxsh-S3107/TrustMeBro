"""Automated Speech Recognition (ASR) abstraction layer for Voice Intake.
Supports OpenAI Whisper API and Mock ASR for deterministic offline testing.
"""

import os
import io
import time
from abc import ABC, abstractmethod
from typing import Optional, Union, BinaryIO
import requests
from dotenv import load_dotenv

load_dotenv()


class ASRService(ABC):
    """Abstract interface for Speech-to-Text services."""

    @abstractmethod
    def transcribe(
        self,
        audio_data: Union[bytes, BinaryIO],
        language: str = "en",
        filename: str = "audio.webm",
        content_type: Optional[str] = None
    ) -> str:
        """
        Transcribe audio input to native raw text.
        :param audio_data: Raw audio bytes or file-like binary stream.
        :param language: Language code ('en' for English, 'ta' for Tamil).
        :param filename: Audio filename / extension (e.g. 'audio.webm', 'audio.wav').
        :param content_type: MIME type of audio (e.g. 'audio/webm', 'audio/wav').
        :return: Verbatim text transcript in the spoken language.
        """
        pass


class WhisperASRService(ASRService):
    """Production ASR implementation connecting to OpenAI Whisper API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.api_url = "https://api.openai.com/v1/audio/transcriptions"

    def transcribe(
        self,
        audio_data: Union[bytes, BinaryIO],
        language: str = "en",
        filename: str = "recording.webm",
        content_type: Optional[str] = None
    ) -> str:
        # Re-check env var if not passed in init
        api_key = self.api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY is not configured on the server. "
                "To transcribe live microphone audio, please add OPENAI_API_KEY=your_key to your .env file "
                "and restart the server."
            )

        # Resolve MIME type
        if not content_type:
            ext = os.path.splitext(filename)[1].lower()
            mime_map = {
                ".webm": "audio/webm",
                ".wav": "audio/wav",
                ".mp4": "audio/mp4",
                ".m4a": "audio/m4a",
                ".mp3": "audio/mpeg",
                ".ogg": "audio/ogg",
            }
            content_type = mime_map.get(ext, "audio/webm")

        # Prepare file tuple: (filename, bytes_stream, content_type)
        if isinstance(audio_data, bytes):
            if len(audio_data) < 100:
                raise ValueError("Audio recording is empty or too short. Please speak and try again.")
            file_tuple = (filename, io.BytesIO(audio_data), content_type)
        else:
            file_tuple = (filename, audio_data, content_type)

        headers = {
            "Authorization": f"Bearer {api_key}",
        }

        # Whisper supports language parameter: 'en' for English, 'ta' for Tamil
        whisper_lang = "ta" if language == "ta" else "en"

        data = {
            "model": "whisper-1",
            "language": whisper_lang,
        }

        files = {
            "file": file_tuple,
        }

        start_time = time.time()
        try:
            response = requests.post(self.api_url, headers=headers, data=data, files=files, timeout=30)
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Network error communicating with Whisper API: {str(e)}")

        duration_ms = int((time.time() - start_time) * 1000)

        if response.status_code != 200:
            err_msg = response.text
            try:
                err_json = response.json()
                if "error" in err_json and "message" in err_json["error"]:
                    err_msg = err_json["error"]["message"]
            except Exception:
                pass
            raise RuntimeError(f"Whisper API error (HTTP {response.status_code}): {err_msg}")

        result_json = response.json()
        raw_transcript = result_json.get("text", "").strip()
        print(f"[ASR] Whisper transcription completed in {duration_ms}ms (length: {len(raw_transcript)} chars)")
        return raw_transcript


import base64


class AI4BharatASRService(ASRService):
    """
    Lightweight Cloud ASR implementation connecting to AI4Bharat / Bhashini Indic ASR API.
    Provides high-accuracy regional language speech recognition (Tamil, Hindi, English, etc.)
    without requiring heavy local model weights on low-resource Android devices.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        user_id: Optional[str] = None,
        api_url: Optional[str] = None
    ):
        self.api_key = api_key or os.getenv("AI4BHARAT_API_KEY") or os.getenv("BHASHINI_API_KEY")
        self.user_id = user_id or os.getenv("AI4BHARAT_USER_ID") or os.getenv("BHASHINI_USER_ID")
        self.api_url = api_url or os.getenv(
            "AI4BHARAT_API_URL",
            "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"
        )
        # Default Bhashini serviceId for Indic Conformer ASR
        self.service_id = os.getenv("AI4BHARAT_SERVICE_ID", "ai4bharat/conformer-multilingual-dravidian-gpu--t4")

    def transcribe(
        self,
        audio_data: Union[bytes, BinaryIO],
        language: str = "en",
        filename: str = "recording.webm",
        content_type: Optional[str] = None
    ) -> str:
        api_key = self.api_key or os.getenv("AI4BHARAT_API_KEY") or os.getenv("BHASHINI_API_KEY")
        if not api_key:
            raise ValueError(
                "AI4BHARAT_API_KEY is not configured on the server. "
                "To use AI4Bharat Indic ASR, please add AI4BHARAT_API_KEY=your_key to your .env file "
                "and set ASR_BACKEND=ai4bharat."
            )

        # Read audio bytes
        if isinstance(audio_data, bytes):
            raw_bytes = audio_data
        else:
            raw_bytes = audio_data.read()

        if len(raw_bytes) < 100:
            raise ValueError("Audio recording is empty or too short. Please speak and try again.")

        audio_b64 = base64.b64encode(raw_bytes).decode("utf-8")
        target_lang = "ta" if language == "ta" else "en"

        headers = {
            "Authorization": api_key,
            "Content-Type": "application/json",
        }
        if self.user_id:
            headers["userID"] = self.user_id

        payload = {
            "pipelineTasks": [
                {
                    "taskType": "asr",
                    "config": {
                        "language": {
                            "sourceLanguage": target_lang
                        },
                        "serviceId": self.service_id,
                        "audioFormat": "wav" if filename.endswith(".wav") else "webm",
                        "samplingRate": 16000
                    }
                }
            ],
            "inputData": {
                "audio": [
                    {
                        "audioContent": audio_b64
                    }
                ]
            }
        }

        start_time = time.time()
        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Network error communicating with AI4Bharat/Bhashini API: {str(e)}")

        duration_ms = int((time.time() - start_time) * 1000)

        if response.status_code != 200:
            err_msg = response.text
            try:
                err_json = response.json()
                if "message" in err_json:
                    err_msg = err_json["message"]
            except Exception:
                pass
            raise RuntimeError(f"AI4Bharat API error (HTTP {response.status_code}): {err_msg}")

        result_json = response.json()
        
        # Parse transcript from standard Dhruva / Bhashini response structure
        raw_transcript = ""
        try:
            pipeline_response = result_json.get("pipelineResponse", [])
            if pipeline_response and len(pipeline_response) > 0:
                output = pipeline_response[0].get("output", [])
                if output and len(output) > 0:
                    raw_transcript = output[0].get("source", "") or output[0].get("target", "")
            if not raw_transcript:
                # Direct fallback format
                raw_transcript = result_json.get("text", "") or result_json.get("transcript", "")
        except Exception:
            raw_transcript = str(result_json)

        raw_transcript = raw_transcript.strip()
        print(f"[ASR] AI4Bharat transcription completed in {duration_ms}ms (length: {len(raw_transcript)} chars)")
        return raw_transcript


class MockASRService(ASRService):
    """Deterministic Mock ASR service for offline testing and unit tests."""

    def __init__(self, default_response: Optional[str] = None):
        self.default_response = default_response
        self._preset_responses = []
        self._last_language = None

    def set_next_response(self, text: str):
        """Queue a specific response for the next transcription."""
        self._preset_responses.append(text)

    def set_responses(self, texts: list):
        """Queue a list of responses."""
        self._preset_responses.extend(texts)

    def transcribe(
        self,
        audio_data: Union[bytes, BinaryIO],
        language: str = "en",
        filename: str = "audio.webm",
        content_type: Optional[str] = None
    ) -> str:
        self._last_language = language
        if self._preset_responses:
            return self._preset_responses.pop(0)

        if self.default_response is not None:
            return self.default_response

        # In testing mode without pre-queued response:
        raise RuntimeError(
            f"MockASRService: No response queued for language='{language}'. "
            "Use asr_service.set_next_response(...) in test fixtures."
        )


def get_asr_service(backend_type: Optional[str] = None, api_key: Optional[str] = None) -> ASRService:
    """
    Factory function to retrieve appropriate ASR backend.
    Supports 'ai4bharat', 'whisper', and 'mock'.
    Defaults based on ASR_BACKEND env var or available API keys.
    """
    backend = (backend_type or os.getenv("ASR_BACKEND", "")).lower().strip()
    openai_key = api_key or os.getenv("OPENAI_API_KEY")
    ai4bharat_key = api_key or os.getenv("AI4BHARAT_API_KEY") or os.getenv("BHASHINI_API_KEY")

    if backend == "mock":
        return MockASRService()
    if backend in ["ai4bharat", "bhashini", "indic"]:
        return AI4BharatASRService(api_key=ai4bharat_key)
    if backend == "whisper":
        return WhisperASRService(api_key=openai_key)

    # Auto-detection when ASR_BACKEND is not explicitly set
    if ai4bharat_key and not openai_key:
        return AI4BharatASRService(api_key=ai4bharat_key)
    return WhisperASRService(api_key=openai_key)

