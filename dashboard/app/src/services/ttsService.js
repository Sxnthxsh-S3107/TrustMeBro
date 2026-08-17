/**
 * ttsService.js
 * 
 * Encapsulates all browser-native SpeechSynthesis (Text-to-Speech) functionality.
 * Designed for offline capability, low latency, and zero external dependencies.
 */

let voices = [];

const loadVoices = () => {
  if (typeof window !== "undefined" && window.speechSynthesis) {
    voices = window.speechSynthesis.getVoices();
    console.log("[ttsService] Loaded voices:", voices.length);
  }
};

// Initial load
loadVoices();

if (typeof window !== "undefined" && window.speechSynthesis) {
  // Chrome and some other browsers load voices asynchronously
  window.speechSynthesis.onvoiceschanged = () => {
    loadVoices();
  };
}

/**
 * Get all loaded voices.
 */
export const getAvailableVoices = () => {
  return voices;
};

/**
 * Checks if a Tamil-capable voice is available on the device.
 */
export const hasTamilVoice = () => {
  return voices.some((v) => v.lang.toLowerCase().startsWith("ta"));
};

/**
 * Finds the best voice matching the target language.
 * 
 * - For Tamil (ta): Prefer "ta-IN", or any "ta" voice.
 * - For English (en): Prefer "en-IN", then "en-GB", then "en-US", then any "en" voice.
 */
export const findVoice = (language) => {
  const langLower = language.toLowerCase();
  
  if (langLower === "ta" || langLower.startsWith("ta")) {
    // Tamil Voice Search
    const taIn = voices.find((v) => v.lang.toLowerCase() === "ta-in");
    if (taIn) return taIn;
    
    const taAny = voices.find((v) => v.lang.toLowerCase().startsWith("ta"));
    return taAny || null;
  }
  
  // English Voice Search
  const enIn = voices.find((v) => v.lang.toLowerCase().includes("en-in"));
  if (enIn) return enIn;
  
  const enGb = voices.find((v) => v.lang.toLowerCase().includes("en-gb"));
  if (enGb) return enGb;
  
  const enUs = voices.find((v) => v.lang.toLowerCase().includes("en-us"));
  if (enUs) return enUs;
  
  const enAny = voices.find((v) => v.lang.toLowerCase().startsWith("en"));
  return enAny || null;
};

/**
 * Stop any ongoing speech synthesis immediately.
 */
export const stop = () => {
  if (typeof window !== "undefined" && window.speechSynthesis) {
    try {
      window.speechSynthesis.cancel();
    } catch (e) {
      console.error("[ttsService] Stop error:", e);
    }
  }
};

/**
 * Speaks the given text using browser SpeechSynthesis.
 * 
 * @param {string} text - The text to speak (the question).
 * @param {string} language - The language code ('en' or 'ta').
 * @param {object} callbacks - Event callbacks.
 * @param {function} callbacks.onStart - Called when speech starts.
 * @param {function} callbacks.onEnd - Called when speech ends successfully.
 * @param {function} callbacks.onError - Called when an error occurs or Tamil voice is missing.
 */
export const speak = (text, language, callbacks = {}) => {
  const { onStart, onEnd, onError } = callbacks;
  
  if (typeof window === "undefined" || !window.speechSynthesis) {
    if (onError) onError(new Error("speech_synthesis_unsupported"));
    return;
  }

  // 1. Cancel any active or queued speech
  stop();

  // 2. Select appropriate voice
  const isTa = language === "ta";
  const voice = findVoice(language);

  // If patient selected Tamil but no Tamil voice is found, fail early
  if (isTa && !voice) {
    console.warn("[ttsService] No Tamil voice found.");
    if (onError) onError(new Error("tamil_voice_unavailable"));
    return;
  }

  // 3. Create the utterance
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.voice = voice;
  utterance.lang = isTa ? "ta-IN" : "en-US";
  
  // Moderate, natural speed
  utterance.rate = 0.95; 

  // 4. Attach event handlers
  utterance.onstart = () => {
    console.log("[ttsService] Speech started:", text);
    if (onStart) onStart();
  };

  utterance.onend = () => {
    console.log("[ttsService] Speech ended.");
    if (onEnd) onEnd();
  };

  utterance.onerror = (event) => {
    console.warn("[ttsService] Speech error:", event);
    // Standard browsers might fire 'interrupted' if we cancel, ignore those
    if (event.error === "interrupted") return;
    if (onError) onError(event);
  };

  // 5. Trigger Speech
  try {
    window.speechSynthesis.speak(utterance);
  } catch (e) {
    console.error("[ttsService] speak throw:", e);
    if (onError) onError(e);
  }
};
