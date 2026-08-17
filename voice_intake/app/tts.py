"""
tts.py — Backend Text-to-Speech service for RuralCare / LifeLine.

Provider hierarchy (set via TTS_PROVIDER env var):

  gtts   (DEFAULT) — Google Translate TTS via the `gtts` package.
                     No credentials required. Works out of the box.
                     Returns MP3 audio for any Tamil / English text.

  google            — Google Cloud Text-to-Speech (official).
                     Requires GOOGLE_APPLICATION_CREDENTIALS.
                     Higher quality, production-grade, rate-limit safe.

  mock              — Returns a valid 1-second silent WAV.
                     Use in CI / offline environments where no network
                     access is available. Produces no audible sound.

Security: No credentials are ever forwarded to the browser.
The browser only calls POST /tts on this same server.
"""

import io
import os
import struct


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_print(msg: str) -> None:
    """Print that never crashes on narrow-codepage terminals (Windows cp1252)."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", errors="replace").decode("ascii"))


def generate_silent_wav(duration_seconds: int = 1, sample_rate: int = 8000) -> bytes:
    """
    Generates a valid silent PCM WAV byte stream — always playable in every browser.
    Used as the last-resort fallback when all TTS providers fail.
    """
    num_samples = duration_seconds * sample_rate
    num_channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * (bits_per_sample // 8)
    block_align = num_channels * (bits_per_sample // 8)
    data_size = num_samples * block_align
    file_size = 36 + data_size
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", file_size, b"WAVE",
        b"fmt ", 16, 1, num_channels, sample_rate,
        byte_rate, block_align, bits_per_sample,
        b"data", data_size,
    )
    return header + b"\x00" * data_size


# ── TTS service ───────────────────────────────────────────────────────────────

class TTSServiceBackend:
    """
    Unified backend TTS service.

    Always returns (audio_bytes: bytes, mime_type: str).

    Priority when `TTS_PROVIDER=gtts`:
      1. gTTS (Google Translate TTS — real audio, no credentials)
      2. Silent WAV fallback (if gTTS call fails, e.g. no network)

    Priority when `TTS_PROVIDER=google`:
      1. Google Cloud TTS (MP3, high quality)
      2. gTTS fallback
      3. Silent WAV fallback

    Priority when `TTS_PROVIDER=mock`:
      1. Silent WAV (always, no network call)
    """

    def __init__(self) -> None:
        self.provider = os.getenv("TTS_PROVIDER", "gtts").lower()
        self.google_client = None

        if self.provider == "google":
            creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
            if creds_path and os.path.exists(creds_path):
                try:
                    from google.cloud import texttospeech  # type: ignore
                    self.google_client = texttospeech.TextToSpeechClient()
                    _safe_print("[TTS] Google Cloud TTS client initialised.")
                except Exception as exc:
                    _safe_print(f"[TTS] Google Cloud TTS init failed: {exc}")
            else:
                _safe_print(
                    "[TTS] GOOGLE_APPLICATION_CREDENTIALS not set/found. "
                    "Will fall back to gTTS."
                )
        elif self.provider == "gtts":
            _safe_print("[TTS] Provider = gTTS (Google Translate, no credentials required).")
        else:
            _safe_print("[TTS] Provider = mock (silent WAV — no audible output).")

    # ── Public ────────────────────────────────────────────────────────────────

    def synthesize(self, text: str, language_code: str = "ta-IN") -> tuple:
        """
        Synthesise `text` in `language_code`.
        Returns (audio_bytes, mime_type).
        """
        if self.provider == "mock":
            _safe_print("[TTS] mock → returning silent WAV.")
            return generate_silent_wav(), "audio/wav"

        if self.provider == "google" and self.google_client is not None:
            try:
                return self._google_cloud_synthesize(text, language_code)
            except Exception as exc:
                _safe_print(f"[TTS] Google Cloud failed, trying gTTS: {exc}")

        # gTTS path (default, or Cloud TTS fallback)
        try:
            return self._gtts_synthesize(text, language_code)
        except Exception as exc:
            _safe_print(f"[TTS] gTTS failed, returning silent WAV: {exc}")
            return generate_silent_wav(), "audio/wav"

    # ── Private ───────────────────────────────────────────────────────────────

    def _gtts_synthesize(self, text: str, language_code: str) -> tuple:
        """Uses the gTTS package (Google Translate TTS). No credentials required."""
        from gtts import gTTS  # type: ignore

        # gTTS uses ISO 639-1 codes: "ta" for Tamil, "en" for English
        lang = "ta" if language_code.lower().startswith("ta") else "en"

        _safe_print(f"[TTS] gTTS synthesising: lang={lang}")
        tts = gTTS(text=text, lang=lang, slow=False)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        audio_bytes = buf.read()
        _safe_print(f"[TTS] gTTS done: {len(audio_bytes)} bytes MP3.")
        return audio_bytes, "audio/mpeg"

    def _google_cloud_synthesize(self, text: str, language_code: str) -> tuple:
        """Uses the official Google Cloud Text-to-Speech API."""
        from google.cloud import texttospeech  # type: ignore

        synthesis_input = texttospeech.SynthesisInput(text=text)
        if language_code.lower().startswith("ta"):
            voice_name, lang = "ta-IN-Standard-A", "ta-IN"
        else:
            voice_name, lang = "en-IN-Standard-A", "en-IN"

        voice = texttospeech.VoiceSelectionParams(language_code=lang, name=voice_name)
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        response = self.google_client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        _safe_print(
            f"[TTS] Google Cloud MP3: {len(response.audio_content)} bytes, voice={voice_name}"
        )
        return response.audio_content, "audio/mpeg"
