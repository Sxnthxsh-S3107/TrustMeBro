/**
 * ttsService.js
 *
 * Unified Text-to-Speech service for RuralCare / LifeLine.
 *
 * Strategy:
 *   English  → browser SpeechSynthesis (en-IN → en-GB → en-US → any en)
 *   Tamil    → browser SpeechSynthesis if a native ta-IN voice is present
 *              otherwise → POST /tts backend (Google Cloud TTS) → HTMLAudioElement
 *
 * The caller (PatientConsultation.jsx) only receives:
 *   onStart()
 *   onEnd()
 *   onError(err)
 *
 * It does not care which path was taken.
 *
 * Security: No Google credentials are sent to or stored in the browser.
 * The /tts backend endpoint handles all cloud authentication server-side.
 */

// ── Voice registry (browser SpeechSynthesis) ─────────────────────────────────
let voices = [];

const loadVoices = () => {
  if (typeof window !== "undefined" && window.speechSynthesis) {
    voices = window.speechSynthesis.getVoices();
  }
};

loadVoices();

if (typeof window !== "undefined" && window.speechSynthesis) {
  window.speechSynthesis.onvoiceschanged = () => {
    loadVoices();
  };
}

// ── Current cloud audio element (for cancel/cleanup) ─────────────────────────
let currentCloudAudio = null;

// ── Audio blob cache: avoids re-fetching the same question from the backend ──
// Key: `${language}::${text}`, Value: Blob URL string
const audioCache = new Map();

// ── Public helpers ────────────────────────────────────────────────────────────

/** Returns all loaded browser voices. */
export const getAvailableVoices = () => voices;

/** True if a native Tamil voice is available in this browser. */
export const hasTamilVoice = () =>
  voices.some((v) => v.lang.toLowerCase().startsWith("ta"));

/**
 * Finds the best browser voice for the given language code.
 *   ta / ta-IN  → ta-IN  → any ta-*  → null (never falls back to English)
 *   en / en-*   → en-IN  → en-GB  → en-US  → any en-*
 */
export const findVoice = (language) => {
  const lang = language.toLowerCase();

  if (lang === "ta" || lang.startsWith("ta")) {
    return (
      voices.find((v) => v.lang.toLowerCase() === "ta-in") ||
      voices.find((v) => v.lang.toLowerCase().startsWith("ta")) ||
      null
    );
  }

  return (
    voices.find((v) => v.lang.toLowerCase().includes("en-in")) ||
    voices.find((v) => v.lang.toLowerCase().includes("en-gb")) ||
    voices.find((v) => v.lang.toLowerCase().includes("en-us")) ||
    voices.find((v) => v.lang.toLowerCase().startsWith("en")) ||
    null
  );
};

/**
 * Cancels any active speech — both browser SpeechSynthesis and cloud HTMLAudioElement.
 */
export const stop = () => {
  // Stop browser TTS
  if (typeof window !== "undefined" && window.speechSynthesis) {
    try {
      window.speechSynthesis.cancel();
    } catch (_) {}
  }

  // Stop cloud audio
  if (currentCloudAudio) {
    try {
      currentCloudAudio.pause();
      currentCloudAudio.src = "";
      currentCloudAudio = null;
    } catch (_) {}
  }
};

// ── Internal: browser SpeechSynthesis path ───────────────────────────────────

function speakViaBrowser(text, language, voice, callbacks) {
  const { onStart, onEnd, onError } = callbacks;

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.voice = voice;
  utterance.lang = language.startsWith("ta") ? "ta-IN" : "en-US";
  utterance.rate = 0.95;

  utterance.onstart = () => {
    if (onStart) onStart();
  };

  utterance.onend = () => {
    if (onEnd) onEnd();
  };

  utterance.onerror = (event) => {
    // "interrupted" fires when we call speechSynthesis.cancel() — safe to ignore
    if (event.error === "interrupted") return;
    console.warn("[ttsService:browser] SpeechSynthesis error:", event.error);
    if (onError) onError(new Error(event.error || "browser_tts_error"));
  };

  try {
    window.speechSynthesis.speak(utterance);
  } catch (e) {
    console.error("[ttsService:browser] speak() threw:", e);
    if (onError) onError(e);
  }
}

// ── Internal: cloud TTS path (/tts backend → HTMLAudioElement) ───────────────

async function speakViaCloud(text, language, callbacks) {
  const { onStart, onEnd, onError } = callbacks;

  const cacheKey = `${language}::${text}`;

  try {
    let blobUrl = audioCache.get(cacheKey);

    if (!blobUrl) {
      // Fetch audio from the backend (credentials stay server-side)
      const response = await fetch("/tts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, language: language === "ta" ? "ta-IN" : "en-IN" }),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.error || `HTTP ${response.status}`);
      }

      const blob = await response.blob();

      // Validate that we received actual audio
      if (!blob.type.startsWith("audio/")) {
        throw new Error(`Unexpected content-type: ${blob.type}`);
      }

      blobUrl = URL.createObjectURL(blob);
      audioCache.set(cacheKey, blobUrl);
    }

    // Stop any previously playing audio
    if (currentCloudAudio) {
      currentCloudAudio.pause();
      currentCloudAudio.src = "";
    }

    const audio = new Audio(blobUrl);
    currentCloudAudio = audio;

    audio.onplay = () => {
      if (onStart) onStart();
    };

    audio.onended = () => {
      currentCloudAudio = null;
      if (onEnd) onEnd();
    };

    audio.onerror = (e) => {
      currentCloudAudio = null;
      console.error("[ttsService:cloud] HTMLAudioElement error:", e);
      if (onError) onError(new Error("cloud_audio_playback_error"));
    };

    audio.play().catch((e) => {
      // Autoplay policy block
      console.warn("[ttsService:cloud] play() rejected:", e);
      currentCloudAudio = null;
      if (onError) onError(new Error("autoplay_blocked"));
    });
  } catch (e) {
    console.error("[ttsService:cloud] fetch/decode error:", e);
    if (onError) onError(e);
  }
}

// ── Public API ────────────────────────────────────────────────────────────────

/**
 * Speak the given text in the given language.
 *
 * @param {string} text      The question text (Tamil Unicode or English).
 * @param {string} language  "en" or "ta"
 * @param {object} callbacks { onStart, onEnd, onError }
 */
export const speak = (text, language, callbacks = {}) => {
  const { onStart, onEnd, onError } = callbacks;

  if (typeof window === "undefined" || !window.speechSynthesis) {
    if (onError) onError(new Error("speech_synthesis_unsupported"));
    return;
  }

  // Cancel any ongoing speech (browser or cloud) before starting new
  stop();

  const isTa = language === "ta" || language.startsWith("ta");

  if (isTa) {
    const nativeVoice = findVoice("ta");

    if (nativeVoice) {
      // ✅ Native Tamil voice available — use fast browser path
      console.log("[ttsService] Tamil: native browser voice →", nativeVoice.name);
      speakViaBrowser(text, language, nativeVoice, { onStart, onEnd, onError });
    } else {
      // ☁️ No native Tamil voice — fall back to cloud backend
      console.log("[ttsService] Tamil: no native voice, using cloud backend /tts");
      speakViaCloud(text, language, { onStart, onEnd, onError });
    }
  } else {
    // English — always use browser SpeechSynthesis
    const voice = findVoice("en");
    console.log("[ttsService] English: browser voice →", voice?.name || "system default");
    speakViaBrowser(text, "en", voice, { onStart, onEnd, onError });
  }
};

/**
 * Clear the audio blob URL cache.
 * Call this when a consultation session ends to release memory.
 */
export const clearAudioCache = () => {
  audioCache.forEach((url) => URL.revokeObjectURL(url));
  audioCache.clear();
};
