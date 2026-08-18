import React, { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Mic, Check, Upload, Volume2 } from "lucide-react";
import {
  startIntake,
  submitIntakeAnswerText,
  transcribeAudio,
  getIntakeResult,
  submitToDecisionEngine,
} from "../services/api";
import { speak, stop as stopSpeech, clearAudioCache } from "../services/ttsService";

// ──────────────────────────────────────────────────────────────────────────────
// STATE MACHINE STATES:
//
// IDLE                - Language selection screen.
// ASKING              - Fetching the question from Person 2 API.
// SPEAKING            - Browser Text-to-Speech is actively reading the question.
// WAITING_FOR_PATIENT - Speaking finished. Patient's turn to answer (speak/type).
// RECORDING           - Active patient voice recording.
// PROCESSING          - Transcribing (Whisper fallback) or submitting answer.
// COMPLETED           - Session complete, redirected.
// ERROR               - Connection/backend failure.
// ──────────────────────────────────────────────────────────────────────────────

export default function PatientConsultation() {
  const [state, setState] = useState("IDLE"); // IDLE | ASKING | SPEAKING | WAITING_FOR_PATIENT | RECORDING | PROCESSING | COMPLETED | ERROR
  const [language, setLanguage] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [transcript, setTranscript] = useState("");
  const [extractedData, setExtractedData] = useState({});
  const [showManual, setShowManual] = useState(false);
  const [manualText, setManualText] = useState("");
  
  // TTS Fallback States
  const [autoplayBlocked, setAutoplayBlocked] = useState(false);

  const navigate = useNavigate();

  // Refs — escape stale closures inside callbacks
  const transcriptRef = useRef("");
  const languageRef = useRef("en");
  const sessionIdRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const speechRecognizerRef = useRef(null);
  const recognizerLangRef = useRef("en-IN");
  const isRecordingRef = useRef(false);
  const stateRef = useRef("IDLE");

  // WebSpeech coordination refs to prevent race conditions
  const webSpeechHasResultRef = useRef(false);
  const webSpeechActiveRef = useRef(false);
  const whisperFallbackTriggeredRef = useRef(false);
  const audioBlobRef = useRef(null);
  const triggerWhisperFallbackRef = useRef(null);

  // Keep stateRef synced with state for async callback checks
  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  const setTranscriptSync = (val) => {
    transcriptRef.current = val;
    setTranscript(val);
  };

  const triggerWhisperFallback = async () => {
    if (whisperFallbackTriggeredRef.current) return;
    whisperFallbackTriggeredRef.current = true;

    const audioBlob = audioBlobRef.current;
    if (!audioBlob || audioBlob.size < 500) {
      setState("WAITING_FOR_PATIENT");
      alert(
        languageRef.current === "ta"
          ? "குரல் கண்டறியப்படவில்லை. மீண்டும் மைக் அழுத்திப் பேசவும்."
          : "No speech detected. Please speak closer to the microphone."
      );
      return;
    }

    setState("PROCESSING");
    try {
      const resp = await transcribeAudio(
        sessionIdRef.current,
        languageRef.current,
        audioBlob
      );
      if (resp && resp.success && resp.transcript) {
        setTranscriptSync(resp.transcript);
      } else {
        alert(
          languageRef.current === "ta"
            ? "குரல் கண்டறியப்படவில்லை. மீண்டும் முயற்சிக்கவும் அல்லது கீழே தட்டச்சு செய்யவும்."
            : "Speech not recognized. Please try again or use the text fallback."
        );
      }
    } catch (e) {
      console.error("[/transcribe] error:", e?.response?.data || e.message);
      alert(
        languageRef.current === "ta"
          ? "குரல் சேவையுடன் இணைக்க முடியவில்லை. தட்டச்சு மூலம் தொடரவும்."
          : "Transcription service error. Please use the text input below to continue."
      );
    } finally {
      setState("WAITING_FOR_PATIENT");
    }
  };

  // Sync the helper ref to avoid stale closures in useEffect
  triggerWhisperFallbackRef.current = triggerWhisperFallback;

  // Initialise Web SpeechRecognition on mount
  useEffect(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      console.warn("[WebSpeech] Not supported in this browser.");
      return;
    }

    const recognizer = new SR();
    recognizer.interimResults = true;
    recognizer.continuous = false;
    recognizer.maxAlternatives = 1;

    recognizer.onstart = () => {
      console.log("[WebSpeech] Listening started");
    };

    recognizer.onaudiostart = () => {
      console.log("[WebSpeech] Audio acquisition started");
    };

    recognizer.onsoundstart = () => {
      console.log("[WebSpeech] Sound detection started");
    };

    recognizer.onspeechstart = () => {
      console.log("[WebSpeech] Speech detection started");
    };

    recognizer.onspeechend = () => {
      console.log("[WebSpeech] Speech ended");
    };

    recognizer.onsoundend = () => {
      console.log("[WebSpeech] Sound ended");
    };

    recognizer.onaudioend = () => {
      console.log("[WebSpeech] Audio acquisition ended");
    };

    recognizer.onresult = (event) => {
      let finalTranscript = "";
      let interimTranscript = "";
      for (let i = 0; i < event.results.length; ++i) {
        const transcriptSegment = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcriptSegment;
        } else {
          interimTranscript += transcriptSegment;
        }
      }
      const combined = (finalTranscript + interimTranscript).trim();
      if (combined) {
        setTranscriptSync(combined);
      }
      if (finalTranscript.trim()) {
        webSpeechHasResultRef.current = true;
      }
    };

    recognizer.onend = () => {
      console.log("[WebSpeech] Stopped. HasResult:", webSpeechHasResultRef.current);
      webSpeechActiveRef.current = false;
      
      // If the recognizer stopped automatically while we are still recording (silence timeout)
      if (isRecordingRef.current) {
        stopRecording();
      }

      if (webSpeechHasResultRef.current) {
        setState("WAITING_FOR_PATIENT");
      } else {
        // No result from Web Speech, fall back to Whisper once MediaRecorder finishes
        if (mediaRecorderRef.current && mediaRecorderRef.current.state === "inactive") {
          triggerWhisperFallbackRef.current && triggerWhisperFallbackRef.current();
        }
      }
    };

    recognizer.onerror = (event) => {
      console.warn("[WebSpeech] error:", event.error);
      
      let userMessage = "";
      switch (event.error) {
        case "not-allowed":
          userMessage = languageRef.current === "ta"
            ? "ஒலிவாங்கி அனுமதி தேவை. தயவுசெய்து ஒலிவாங்கி அணுகலை அனுமதிக்கவும்."
            : "Microphone permission is required. Please allow microphone access.";
          break;
        case "service-not-allowed":
          userMessage = languageRef.current === "ta"
            ? "குரல் சேவை அனுமதிக்கப்படவில்லை. தட்டச்சு மூலம் தொடரவும்."
            : "Speech recognition service is not allowed. Please type instead.";
          break;
        case "no-speech":
          userMessage = languageRef.current === "ta"
            ? "குரல் கண்டறியப்படவில்லை. மீண்டும் மைக் அழுத்திப் பேசவும்."
            : "No speech detected. Please try again.";
          break;
        case "audio-capture":
          userMessage = languageRef.current === "ta"
            ? "ஒலிவாங்கி வன்பொருள் பிழை. மீண்டும் முயற்சிக்கவும்."
            : "Audio capture failed. Please ensure your microphone is connected.";
          break;
        case "network":
          userMessage = languageRef.current === "ta"
            ? "இணைய இணைப்பு பிழை. தட்டச்சு மூலம் தொடரவும்."
            : "Voice service is temporarily unavailable due to a network error. You can try again or type.";
          break;
        case "aborted":
          // Ignore manual stops
          break;
        case "language-not-supported":
          if (recognizerLangRef.current === "en-IN") {
            recognizerLangRef.current = "en-US";
          } else if (recognizerLangRef.current === "en-US") {
            recognizerLangRef.current = "en-GB";
          }
          break;
        default:
          userMessage = languageRef.current === "ta"
            ? "குரல் அங்கீகாரம் தற்காலிகமாக தோல்வியடைந்தது. தட்டச்சு மூலம் தொடரவும்."
            : "Voice recognition temporarily failed. You can try again or use text.";
      }
      
      if (userMessage) {
        alert(userMessage);
      }
    };

    speechRecognizerRef.current = recognizer;

    // Cleanup: cancel any active speech and release cached audio blob URLs
    return () => {
      stopSpeech();
      clearAudioCache();
    };
  }, []);

  /**
   * Triggers the browser text-to-speech for the question.
   */
  const triggerTTS = (text, lang) => {
    // Clear previous fallback banners
    setAutoplayBlocked(false);

    // Immediately enter SPEAKING so microphone is locked
    setState("SPEAKING");

    speak(text, lang, {
      onStart: () => {
        setState("SPEAKING");
      },
      onEnd: () => {
        setState("WAITING_FOR_PATIENT");
      },
      onError: (err) => {
        const msg = err?.message || "";
        console.warn("[PatientConsultation] TTS error:", msg);
        if (msg === "autoplay_blocked") {
          // Browser blocked autoplay — show tap-to-hear banner
          setAutoplayBlocked(true);
        }
        // For all errors (including cloud failures): question stays visible,
        // patient's turn is unblocked so consultation can continue.
        setState("WAITING_FOR_PATIENT");
      },
    });
  };

  const handleStart = async (selectedLang) => {
    setState("ASKING");
    setLanguage(selectedLang);
    languageRef.current = selectedLang;
    recognizerLangRef.current = selectedLang === "ta" ? "ta-IN" : "en-IN";
    
    try {
      const data = await startIntake(selectedLang);
      setSessionId(data.session_id);
      sessionIdRef.current = data.session_id;
      setCurrentQuestion(data.first_question);
      
      // Auto-speak the first question
      triggerTTS(data.first_question.question_text, selectedLang);
    } catch (err) {
      console.error("[intake/start] failed:", err);
      setState("ERROR");
      alert("Failed to connect to voice intake backend. Please ensure Person 2 is running on port 5000.");
    }
  };

  const startRecording = async () => {
    if (stateRef.current !== "WAITING_FOR_PATIENT") return;
    
    // Cancel any active speech if recording starts
    stopSpeech();

    setState("RECORDING");
    isRecordingRef.current = true;
    setTranscriptSync("");

    // Reset WebSpeech coordination variables
    webSpeechHasResultRef.current = false;
    webSpeechActiveRef.current = false;
    whisperFallbackTriggeredRef.current = false;
    audioBlobRef.current = null;

    // 1. Web Speech Recognition (live track)
    if (speechRecognizerRef.current) {
      try {
        speechRecognizerRef.current.abort();
      } catch (_) {}

      try {
        speechRecognizerRef.current.lang = recognizerLangRef.current;
        speechRecognizerRef.current.start();
        webSpeechActiveRef.current = true;
      } catch (e) {
        console.warn("[WebSpeech] start error:", e.message);
      }
    }

    // 2. MediaRecorder (Whisper fallback)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const mediaRecorder = new MediaRecorder(stream);

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());

        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        audioBlobRef.current = audioBlob;

        console.log("[MediaRecorder] stopped. WebSpeech active:", webSpeechActiveRef.current, "HasResult:", webSpeechHasResultRef.current);

        // Web Speech failed/empty or wasn't even supported -> Fallback to Whisper
        if (!webSpeechActiveRef.current && !webSpeechHasResultRef.current) {
          triggerWhisperFallbackRef.current && triggerWhisperFallbackRef.current();
        }
      };

      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start();
    } catch (err) {
      console.error("[MediaRecorder] failed:", err);
      isRecordingRef.current = false;
      setState("WAITING_FOR_PATIENT");
      alert("Microphone not available. Please use the text input below.");
    }
  };

  const stopRecording = () => {
    isRecordingRef.current = false;
    if (speechRecognizerRef.current) {
      try { speechRecognizerRef.current.stop(); } catch (_) {}
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
  };

  const toggleRecording = () => {
    if (state === "RECORDING") {
      stopRecording();
    } else if (state === "WAITING_FOR_PATIENT") {
      startRecording();
    }
  };

  const handleAudioUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    stopSpeech();
    setState("PROCESSING");
    
    try {
      const resp = await transcribeAudio(sessionIdRef.current, languageRef.current, file);
      if (resp?.success && resp.transcript) {
        setTranscriptSync(resp.transcript);
      } else {
        alert("Audio file transcription failed. Please try again.");
      }
    } catch (err) {
      console.error("[/transcribe upload] error:", err?.response?.data || err.message);
      alert("Could not transcribe the uploaded file.");
    } finally {
      setState("WAITING_FOR_PATIENT");
    }
    e.target.value = null;
  };

  const handleApplyManualText = () => {
    if (manualText.trim()) {
      setTranscriptSync(manualText.trim());
      setShowManual(false);
      setManualText("");
    }
  };

  const handleAnswerSubmit = async () => {
    const currentTranscript = transcriptRef.current.trim();
    if (!currentTranscript) return;

    stopSpeech();
    setState("PROCESSING");
    
    try {
      const data = await submitIntakeAnswerText(sessionIdRef.current, currentTranscript);

      if (data.extracted) {
        setExtractedData((prev) => ({ ...prev, ...data.extracted }));
      }

      if (data.status === "completed" || !data.next_question) {
        setState("COMPLETED");
        clearAudioCache();
        const finalJson = await getIntakeResult(sessionIdRef.current);
        await submitToDecisionEngine(finalJson);
        navigate(`/patient/status/${sessionIdRef.current}`);
      } else {
        setCurrentQuestion(data.next_question);
        setTranscriptSync("");
        // Auto-play the next adaptive question
        triggerTTS(data.next_question.question_text, languageRef.current);
      }
    } catch (err) {
      console.error("[intake/answer or triage] error:", err?.response?.data || err.message);
      alert("Failed to submit. Please ensure all backends are running.");
      setState("WAITING_FOR_PATIENT");
    }
  };

  const handleReplay = () => {
    if (!currentQuestion) return;
    triggerTTS(currentQuestion.question_text, languageRef.current);
  };

  // ── UI STRINGS ──
  const isTa = language === "ta";
  const t = {
    title: isTa ? "குரல் பதிவு" : "Voice Intake",
    micIdle: isTa ? "🎙️ உங்கள் முறை (பேச அழுத்தவும்)" : "🎙️ Your turn (Tap to speak)",
    micRecording: isTa ? "🔴 கேட்கிறது... (நிறுத்த அழுத்தவும்)" : "🔴 Listening... (Tap to stop)",
    micTranscribing: isTa ? "⏳ செயலாக்குகிறது..." : "⏳ Processing...",
    placeholder: isTa ? "உங்கள் வார்த்தைகள் இங்கே தோன்றும்..." : "Your spoken answer will appear here...",
    continueBtn: isTa ? "அடுத்து செல்லவும்" : "Continue",
    retryBtn: isTa ? "மீண்டும்" : "Clear",
    manualBtn: isTa ? "⌨️ தட்டச்சு செய்யவும்" : "⌨️ Type instead",
    uploadBtn: isTa ? "📁 கோப்பை பதிவேற்ற" : "📁 Upload Audio",
    extractedTitle: isTa ? "கண்டறியப்பட்ட மருத்துவத் தகவல்கள்" : "Extracted Clinical Data",
    complaint: isTa ? "பிரச்சனை" : "Complaint",
    duration: isTa ? "கால அளவு" : "Duration",
    history: isTa ? "வரலாறு" : "History",
    question: isTa ? "கேள்வி" : "Question",
    followUp: isTa ? "கூடுதல் கேள்வி" : "Follow-up",
    replay: isTa ? "🔊 கேள்வியை மீண்டும் கேட்க" : "🔊 Replay Question",
    speaking: isTa ? "🔊 கேள்வி கேட்கப்படுகிறது..." : "🔊 AI is speaking...",
    autoplayBlocked: isTa ? "🔊 ஆடியோ தடுக்கப்பட்டுள்ளது. கேள்வியைக் கேட்க இங்கே தட்டவும்." : "🔊 Autoplay is blocked. Tap here to hear the question.",
    tamilVoiceMissing: isTa ? "தமிழ் குரல் இந்த சாதனத்தில் கிடைக்கவில்லை. கேள்வியை திரையில் படிக்கவும்." : "Tamil voice is not available on this device. Please read the question.",
  };

  const showLangSelection = state === "IDLE" || !language;

  // ── LANGUAGE SELECTION SCREEN ──
  if (showLangSelection) {
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "70vh", padding: "2rem" }}>
        <h1 style={{ marginBottom: "0.5rem", fontSize: "2.2rem", fontWeight: "700" }}>Choose your language</h1>
        <p style={{ color: "#64748b", marginBottom: "3rem", fontSize: "1.2rem" }}>உங்கள் மொழியைத் தேர்ந்தெடுக்கவும்</p>
        <div style={{ display: "flex", gap: "2rem", flexWrap: "wrap", justifyContent: "center" }}>
          <button
            onClick={() => handleStart("en")}
            style={{ padding: "1.5rem 2.5rem", fontSize: "1.4rem", borderRadius: "12px", border: "2px solid #3b82f6", background: "white", cursor: "pointer", minWidth: "180px", fontWeight: "600", color: "#1e40af" }}
          >
            🇬🇧 English
          </button>
          <button
            onClick={() => handleStart("ta")}
            style={{ padding: "1.5rem 2.5rem", fontSize: "1.4rem", borderRadius: "12px", border: "2px solid #10b981", background: "white", cursor: "pointer", minWidth: "180px", fontWeight: "600", color: "#065f46" }}
          >
            🇮🇳 தமிழ் (Tamil)
          </button>
        </div>
      </div>
    );
  }

  // ── INTAKE FLOW SCREEN ──
  const isSpeaking = state === "SPEAKING";
  const isProcessing = state === "PROCESSING";
  const isAsking = state === "ASKING";
  const isWaiting = state === "WAITING_FOR_PATIENT";
  const isRecording = state === "RECORDING";

  return (
    <div style={{ maxWidth: "720px", margin: "0 auto", padding: "1.5rem 1rem 5rem 1rem" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "2rem", paddingBottom: "1rem", borderBottom: "2px solid #e2e8f0" }}>
        <h2 style={{ margin: 0 }}>{t.title}</h2>
        <span style={{ fontSize: "0.8rem", background: "#f1f5f9", border: "1px solid #cbd5e1", borderRadius: "6px", padding: "4px 10px", color: "#64748b" }}>
          Session: {sessionId?.substring(0, 8)}…
        </span>
      </div>

      {/* Question Card */}
      {currentQuestion ? (
        <div style={{ background: "white", borderRadius: "16px", border: "1px solid #e2e8f0", padding: "2.5rem 1.5rem", textAlign: "center", marginBottom: "1.5rem", boxShadow: "0 2px 8px rgba(0,0,0,0.06)" }}>
          <div style={{ color: "#3b82f6", fontWeight: "700", fontSize: "0.85rem", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "1rem" }}>
            {currentQuestion.is_adaptive ? t.followUp : t.question}
          </div>
          
          <h2 style={{ fontSize: "1.7rem", fontWeight: "600", color: "#0f172a", marginBottom: "1.5rem", lineHeight: 1.4 }}>
            {currentQuestion.question_text}
          </h2>

          {/* Autoplay / Tamil Voice missing Warning Banners */}
          {autoplayBlocked && (
            <div 
              onClick={handleReplay}
              style={{ padding: "0.75rem 1rem", background: "#fffbeb", border: "1px solid #fef3c7", borderRadius: "8px", color: "#b45309", marginBottom: "1.5rem", fontSize: "0.95rem", cursor: "pointer", fontWeight: "600" }}
            >
              {t.autoplayBlocked}
            </div>
          )}



          {/* Status Label (AI is speaking vs Patient's turn) */}
          <div style={{ marginBottom: "2rem", minHeight: "2rem" }}>
            {isSpeaking ? (
              <span style={{ fontSize: "1.1rem", fontWeight: "700", color: "#3b82f6", background: "#eff6ff", padding: "6px 16px", borderRadius: "20px", display: "inline-flex", alignItems: "center", gap: "8px" }}>
                <Volume2 size={18} className="speaking-mic-icon" /> {t.speaking}
              </span>
            ) : isWaiting ? (
              <span style={{ fontSize: "1.1rem", fontWeight: "600", color: "#059669", background: "#ecfdf5", padding: "6px 16px", borderRadius: "20px" }}>
                {t.micIdle}
              </span>
            ) : isRecording ? (
              <span style={{ fontSize: "1.1rem", fontWeight: "700", color: "#ef4444", background: "#fef2f2", padding: "6px 16px", borderRadius: "20px", animation: "pulse 1.5s infinite" }}>
                {t.micRecording}
              </span>
            ) : (
              <span style={{ fontSize: "1.1rem", color: "#64748b" }}>
                {t.micTranscribing}
              </span>
            )}
          </div>

          {/* Large Microphone Button */}
          <button
            onClick={toggleRecording}
            disabled={isSpeaking || isProcessing || isAsking}
            style={{
              width: "130px", height: "130px", borderRadius: "50%", margin: "0 auto",
              background: isRecording ? "#ef4444" : (isSpeaking || isProcessing || isAsking) ? "#cbd5e1" : "#3b82f6",
              display: "flex", alignItems: "center", justifyContent: "center", border: "none",
              cursor: (isSpeaking || isProcessing || isAsking) ? "default" : "pointer",
              boxShadow: isRecording
                ? "0 0 0 8px rgba(239,68,68,0.2), 0 4px 16px rgba(239,68,68,0.3)"
                : (isSpeaking || isProcessing || isAsking) ? "none" : "0 4px 16px rgba(59,130,246,0.3)",
              transition: "all 0.2s ease",
              outline: "none"
            }}
          >
            <Mic size={54} color="white" />
          </button>

          {/* Replay Question Button */}
          {(isSpeaking || isWaiting) && (
            <button
              onClick={handleReplay}
              style={{
                marginTop: "1.5rem", padding: "6px 16px", borderRadius: "8px",
                border: "1.5px solid #3b82f6", background: "white", color: "#3b82f6",
                cursor: "pointer", fontSize: "0.95rem", fontWeight: "600",
                display: "inline-flex", alignItems: "center", gap: "6px"
              }}
            >
              {t.replay}
            </button>
          )}

          {/* Transcript Display */}
          <div style={{
            minHeight: "80px", margin: "1.5rem 0", padding: "1rem 1.2rem",
            background: "#f8fafc", borderRadius: "10px",
            border: transcript ? "1.5px solid #93c5fd" : "1.5px dashed #cbd5e1",
            fontSize: "1.1rem",
            color: transcript ? "#1e293b" : "#94a3b8",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontStyle: transcript ? "italic" : "normal",
            transition: "border-color 0.2s",
          }}>
            {isProcessing
              ? t.micTranscribing
              : transcript
                ? `"${transcript}"`
                : t.placeholder}
          </div>

          {/* Action Buttons */}
          <div style={{ display: "flex", justifyContent: "center", gap: "1rem", marginBottom: "1.5rem" }}>
            <button
              onClick={() => setTranscriptSync("")}
              disabled={!transcript || isProcessing || isSpeaking}
              style={{ padding: "0.75rem 1.5rem", borderRadius: "8px", border: "1.5px solid #e2e8f0", background: "white", cursor: (transcript && !isProcessing && !isSpeaking) ? "pointer" : "not-allowed", color: "#475569", opacity: (transcript && !isProcessing && !isSpeaking) ? 1 : 0.5, fontWeight: "500", fontSize: "1rem" }}
            >
              {t.retryBtn}
            </button>
            <button
              onClick={handleAnswerSubmit}
              disabled={!transcript || isProcessing || isSpeaking || isRecording || isAsking}
              style={{ padding: "0.75rem 2rem", borderRadius: "8px", border: "none", background: (transcript && !isProcessing && !isSpeaking && !isRecording && !isAsking) ? "#3b82f6" : "#93c5fd", color: "white", cursor: (transcript && !isProcessing && !isSpeaking && !isRecording && !isAsking) ? "pointer" : "not-allowed", fontWeight: "700", fontSize: "1rem" }}
            >
              {isProcessing ? t.micTranscribing : t.continueBtn + " ✓"}
            </button>
          </div>

          {/* Fallback Option Toggles */}
          <div style={{ display: "flex", justifyContent: "center", gap: "2rem", marginTop: "1rem" }}>
            <button
              onClick={() => !isSpeaking && !isProcessing && !isRecording && setShowManual((v) => !v)}
              disabled={isSpeaking || isProcessing || isRecording}
              style={{ background: "none", border: "none", color: (isSpeaking || isProcessing || isRecording) ? "#cbd5e1" : "#3b82f6", cursor: (isSpeaking || isProcessing || isRecording) ? "default" : "pointer", fontSize: "0.95rem", fontWeight: "500", padding: "4px" }}
            >
              ⌨️ {t.manualBtn}
            </button>
            <label style={{ color: (isSpeaking || isProcessing || isRecording) ? "#cbd5e1" : "#3b82f6", cursor: (isSpeaking || isProcessing || isRecording) ? "default" : "pointer", fontSize: "0.95rem", fontWeight: "500" }}>
              <input
                type="file"
                accept="audio/*,.webm,.wav,.mp3,.m4a,.ogg"
                style={{ display: "none" }}
                disabled={isSpeaking || isProcessing || isRecording}
                onChange={handleAudioUpload}
              />
              📁 {t.uploadBtn}
            </label>
          </div>

          {showManual && !isSpeaking && !isProcessing && !isRecording && (
            <div style={{ display: "flex", gap: "0.75rem", marginTop: "1rem", maxWidth: "440px", margin: "1rem auto 0 auto" }}>
              <input
                type="text"
                value={manualText}
                onChange={(e) => setManualText(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleApplyManualText()}
                placeholder={isTa ? "ஆங்கிலம் / தமிழ் / Tanglish..." : "Type answer in English / Tamil / Tanglish..."}
                style={{ flex: 1, padding: "0.75rem", borderRadius: "8px", border: "1.5px solid #e2e8f0", fontSize: "1rem", outline: "none" }}
              />
              <button
                onClick={handleApplyManualText}
                style={{ padding: "0.75rem 1.2rem", borderRadius: "8px", border: "none", background: "#3b82f6", color: "white", cursor: "pointer", fontWeight: "600" }}
              >
                {isTa ? "சேர்" : "Apply"}
              </button>
            </div>
          )}
        </div>
      ) : (
        <div style={{ textAlign: "center", padding: "4rem", color: "#64748b" }}>
          <p>⏳ Loading session...</p>
        </div>
      )}

      {/* Extracted Clinical Data */}
      {Object.keys(extractedData).some(k => extractedData[k] && extractedData[k] !== "-") && (
        <div style={{ background: "#f0f9ff", border: "1px solid #bae6fd", borderRadius: "12px", padding: "1.2rem 1.5rem" }}>
          <h4 style={{ color: "#0369a1", margin: "0 0 0.75rem 0", fontSize: "0.9rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>
            {t.extractedTitle}
          </h4>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem", fontSize: "0.95rem" }}>
            {extractedData.chief_complaint && <div><strong style={{ color: "#475569" }}>{t.complaint}:</strong> {extractedData.chief_complaint}</div>}
            {extractedData.duration && <div><strong style={{ color: "#475569" }}>{t.duration}:</strong> {extractedData.duration}</div>}
            {extractedData.history && <div><strong style={{ color: "#475569" }}>{t.history}:</strong> {extractedData.history}</div>}
          </div>
        </div>
      )}
    </div>
  );
}
