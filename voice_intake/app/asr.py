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
    Defaults to WhisperASRService unless ASR_BACKEND=mock is explicitly set.
    """
    backend = backend_type or os.getenv("ASR_BACKEND", "").lower()
    openai_key = api_key or os.getenv("OPENAI_API_KEY")

    if backend == "mock":
        return MockASRService()
    return WhisperASRService(api_key=openai_key)
