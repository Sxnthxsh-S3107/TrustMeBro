import React, { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Mic, Check, Upload, Type } from "lucide-react";
import {
  startIntake,
  submitIntakeAnswerText,
  transcribeAudio,
  getIntakeResult,
  submitToDecisionEngine,
} from "../services/api";

// ──────────────────────────────────────────────────────────────────────────────
// ROOT CAUSE OF BUGS:
//
// BUG #1 ("Failed to submit answer") was caused downstream of BUG #2.
//        When /transcribe fails, no transcript is set, so submitIntakeAnswerText
//        is called with an empty string, causing a 400 from Person 2's backend.
//
// BUG #2 ("Error connecting to transcription service") was a React stale-closure
//        bug. The MediaRecorder.onstop callback was defined once and captured the
//        `transcript` state value at that moment (always ""). Even after Web
//        Speech set the transcript in state, the onstop closure still saw "".
//        So it ALWAYS fell through to the Whisper /transcribe path, which
//        fails when no OPENAI_API_KEY is configured (MockASRService).
//
// FIX: Use a mutable ref (transcriptRef) that is kept in sync with the transcript
//      state. The onstop closure reads transcriptRef.current (always current value)
//      instead of the stale state variable. This exactly mirrors how Person 2's
//      own mic.js handles it using a plain JS variable (capturedSpeechViaWebSpeech).
// ──────────────────────────────────────────────────────────────────────────────

export default function PatientConsultation() {
  const [language, setLanguage] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [transcript, setTranscript] = useState("");
  const [recordingState, setRecordingState] = useState("idle"); // idle | recording | transcribing
  const [extractedData, setExtractedData] = useState({});
  const [showManual, setShowManual] = useState(false);
  const [manualText, setManualText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const navigate = useNavigate();

  // Refs — these escape React's stale closure problem inside async callbacks
  const transcriptRef = useRef("");         // always current transcript value
  const languageRef = useRef("en");         // always current language
  const sessionIdRef = useRef(null);        // always current sessionId
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const speechRecognizerRef = useRef(null);
  const recognizerLangRef = useRef("en-US");
  const isRecordingRef = useRef(false);     // mirrors recordingState for closure safety

  // Keep refs in sync with state
  const setTranscriptSync = (val) => {
    transcriptRef.current = val;
    setTranscript(val);
  };

  // Initialise SpeechRecognition once on mount (not on every render)
  useEffect(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) return;

    const recognizer = new SR();
    recognizer.interimResults = true;
    recognizer.continuous = false;
    recognizer.maxAlternatives = 1;

    recognizer.onresult = (event) => {
      let finalTrans = "";
      let interimTrans = "";
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          finalTrans += event.results[i][0].transcript;
        } else {
          interimTrans += event.results[i][0].transcript;
        }
      }
      const liveText = (finalTrans || interimTrans).trim();
      if (liveText) {
        setTranscriptSync(liveText);
      }
    };

    recognizer.onend = () => {
      // Web Speech ended (either user stopped or browser auto-stopped)
      if (isRecordingRef.current) {
        stopRecording();
      }
    };

    recognizer.onerror = (event) => {
      console.warn("[WebSpeech] error:", event.error);
      // Not a fatal error — MediaRecorder is still running and will try Whisper if needed
    };

    speechRecognizerRef.current = recognizer;
  }, []); // only once

  const handleStart = async (selectedLang) => {
    setLanguage(selectedLang);
    languageRef.current = selectedLang;
    recognizerLangRef.current = selectedLang === "ta" ? "ta-IN" : "en-US";
    try {
      const data = await startIntake(selectedLang);
      setSessionId(data.session_id);
      sessionIdRef.current = data.session_id;
      setCurrentQuestion(data.first_question);
    } catch (err) {
      console.error("[intake/start] failed:", err);
      alert("Failed to connect to voice intake backend. Please ensure Person 2 is running on port 5000.");
      setLanguage(null);
    }
  };

  const startRecording = async () => {
    setRecordingState("recording");
    isRecordingRef.current = true;
    setTranscriptSync("");

    // ── TRACK 1: Web Speech API (live, instant, preferred) ──
    if (speechRecognizerRef.current) {
      try {
        speechRecognizerRef.current.lang = recognizerLangRef.current;
        speechRecognizerRef.current.start();
      } catch (e) {
        console.warn("[WebSpeech] start error:", e.message);
      }
    }

    // ── TRACK 2: MediaRecorder (audio blob for Whisper fallback ONLY) ──
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const mediaRecorder = new MediaRecorder(stream);

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());

        // ── KEY FIX: Read from ref, not from stale state closure ──
        // This mirrors the `capturedSpeechViaWebSpeech` flag in Person 2's mic.js
        if (transcriptRef.current.trim().length > 0) {
          // Web Speech already captured a good transcript — DO NOT call Whisper
          setRecordingState("idle");
          return;
        }

        // Web Speech produced nothing — fall back to Whisper via Person 2's /transcribe
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        if (audioBlob.size < 500) {
          setRecordingState("idle");
          alert("No speech detected. Please speak closer to the microphone.");
          return;
        }

        setRecordingState("transcribing");
        try {
          // Use Person 2's /transcribe endpoint — it handles Whisper backend, never expose API key to browser
          const resp = await transcribeAudio(
            sessionIdRef.current,
            languageRef.current,
            audioBlob
          );
          if (resp && resp.success && resp.transcript) {
            setTranscriptSync(resp.transcript);
          } else {
            console.warn("[transcribe] no transcript in response:", resp);
            alert(
              languageRef.current === "ta"
                ? "குரல் கண்டறியப்படவில்லை. மீண்டும் முயற்சிக்கவும் அல்லது கீழே தட்டச்சு செய்யவும்."
                : "Speech not recognized. Please try again or use the text fallback."
            );
          }
        } catch (e) {
          // Log the actual error from Person 2's backend for debugging
          console.error("[/transcribe] error:", e?.response?.data || e.message);
          alert(
            languageRef.current === "ta"
              ? "குரல் சேவையுடன் இணைக்க முடியவில்லை. தட்டச்சு மூலம் தொடரவும்."
              : "Transcription service error. Please use the text input below to continue."
          );
        } finally {
          setRecordingState("idle");
        }
      };

      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start();
    } catch (err) {
      console.error("[MediaRecorder] getUserMedia failed:", err);
      isRecordingRef.current = false;
      setRecordingState("idle");
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
    // Note: do NOT set recordingState here — onstop will do it after processing
  };

  const toggleRecording = () => {
    if (recordingState === "recording") {
      stopRecording();
    } else {
      startRecording();
    }
  };

  const handleAudioUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setRecordingState("transcribing");
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
      setRecordingState("idle");
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

    setIsSubmitting(true);
    try {
      // POST /intake/answer — Person 2 expects JSON: {session_id, text}
      const data = await submitIntakeAnswerText(sessionIdRef.current, currentTranscript);

      if (data.extracted) {
        setExtractedData((prev) => ({ ...prev, ...data.extracted }));
      }

      if (data.status === "completed" || !data.next_question) {
        // Session complete — fetch canonical JSON from Person 2 and send to Person 3
        const finalJson = await getIntakeResult(sessionIdRef.current);
        console.log("[Person 2 result]", finalJson);
        await submitToDecisionEngine(finalJson);
        navigate(`/patient/status/${sessionIdRef.current}`);
      } else {
        // Show next adaptive question
        setCurrentQuestion(data.next_question);
        setTranscriptSync("");
      }
    } catch (err) {
      // Log the actual HTTP error from Person 2 or Person 3
      console.error("[intake/answer or /triage] error:", err?.response?.status, err?.response?.data || err.message);
      const msg = err?.response?.data?.error || err?.response?.data?.message || err.message;
      alert(`Failed to submit: ${msg || "Please check the backend is running."}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  // ── UI STRINGS ──
  const isTa = language === "ta";
  const t = {
    title: isTa ? "குரல் பதிவு" : "Voice Intake",
    micIdle: isTa ? "பேச மைக் பொத்தானை அழுத்தவும்" : "Tap and speak naturally",
    micRecording: isTa ? "🔴 கேட்கிறது... (நிறுத்த அழுத்தவும்)" : "🔴 Listening... (Tap to stop)",
    micTranscribing: isTa ? "செயலாக்குகிறது..." : "Processing...",
    placeholder: isTa ? "உங்கள் வார்த்தைகள் இங்கே தோன்றும்..." : "Your spoken answer will appear here...",
    continueBtn: isTa ? "அடுத்து செல்லவும்" : "Continue",
    retryBtn: isTa ? "மீண்டும் முயற்சிக்கவும்" : "Retry",
    manualBtn: isTa ? "⌨️ தட்டச்சு செய்யவும்" : "⌨️ Type instead",
    uploadBtn: isTa ? "📁 கோப்பை பதிவேற்ற" : "📁 Upload Audio",
    extractedTitle: isTa ? "கண்டறியப்பட்ட மருத்துவத் தகவல்கள்" : "Extracted Clinical Data",
    complaint: isTa ? "பிரச்சனை" : "Complaint",
    duration: isTa ? "கால அளவு" : "Duration",
    history: isTa ? "வரலாறு" : "History",
    question: isTa ? "கேள்வி" : "Question",
    followUp: isTa ? "கூடுதல் கேள்வி" : "Follow-up",
  };

  const micLabel = recordingState === "recording"
    ? t.micRecording
    : recordingState === "transcribing"
      ? t.micTranscribing
      : t.micIdle;

  // ── LANGUAGE SELECTION SCREEN ──
  if (!language) {
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "70vh", padding: "2rem" }}>
        <h1 style={{ marginBottom: "0.5rem", fontSize: "2rem" }}>Choose your language</h1>
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
  return (
    <div style={{ maxWidth: "720px", margin: "0 auto", padding: "1.5rem 1rem 5rem 1rem" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "2rem", paddingBottom: "1rem", borderBottom: "2px solid #e2e8f0" }}>
        <h2 style={{ margin: 0 }}>{t.title}</h2>
        <span style={{ fontSize: "0.8rem", background: "#f1f5f9", border: "1px solid #cbd5e1", borderRadius: "6px", padding: "4px 10px", color: "#64748b" }}>
          {sessionId?.substring(0, 8)}…
        </span>
      </div>

      {/* Question Card */}
      {currentQuestion ? (
        <div style={{ background: "white", borderRadius: "16px", border: "1px solid #e2e8f0", padding: "2.5rem 1.5rem", textAlign: "center", marginBottom: "1.5rem", boxShadow: "0 2px 8px rgba(0,0,0,0.06)" }}>
          <div style={{ color: "#3b82f6", fontWeight: "700", fontSize: "0.85rem", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "1rem" }}>
            {currentQuestion.is_adaptive ? t.followUp : t.question}
          </div>
          <h2 style={{ fontSize: "1.6rem", fontWeight: "600", color: "#0f172a", marginBottom: "2.5rem", lineHeight: 1.4 }}>
            {currentQuestion.question_text}
          </h2>

          {/* Microphone Button */}
          <div
            onClick={recordingState === "transcribing" ? undefined : toggleRecording}
            style={{
              width: "130px", height: "130px", borderRadius: "50%", margin: "0 auto",
              background: recordingState === "recording" ? "#ef4444" : "#3b82f6",
              display: "flex", alignItems: "center", justifyContent: "center",
              cursor: recordingState === "transcribing" ? "default" : "pointer",
              boxShadow: recordingState === "recording"
                ? "0 0 0 8px rgba(239,68,68,0.2), 0 4px 16px rgba(239,68,68,0.3)"
                : "0 4px 16px rgba(59,130,246,0.3)",
              transition: "all 0.2s ease",
            }}
          >
            <svg width="60" height="60" viewBox="0 0 24 24" fill="white" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 1a4 4 0 0 1 4 4v6a4 4 0 0 1-8 0V5a4 4 0 0 1 4-4zm0 14a6 6 0 0 0 6-6H6a6 6 0 0 0 6 6zm-1 5v-2.06A8.001 8.001 0 0 1 4.06 11H2a10 10 0 0 0 9 9.95V21h-2v2h6v-2h-2v-.05A10 10 0 0 0 22 11h-2.06A8.001 8.001 0 0 1 13 17.94V20h-2z"/>
            </svg>
          </div>

          <p style={{ marginTop: "1.2rem", fontSize: "1rem", color: recordingState === "recording" ? "#ef4444" : "#64748b", fontWeight: recordingState === "recording" ? "700" : "400", minHeight: "1.5rem" }}>
            {micLabel}
          </p>

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
            {recordingState === "transcribing"
              ? "⏳ " + t.micTranscribing
              : transcript
                ? `"${transcript}"`
                : t.placeholder}
          </div>

          {/* Action Buttons */}
          <div style={{ display: "flex", justifyContent: "center", gap: "1rem", marginBottom: "1.5rem" }}>
            <button
              onClick={() => setTranscriptSync("")}
              disabled={!transcript || isSubmitting}
              style={{ padding: "0.75rem 1.5rem", borderRadius: "8px", border: "1.5px solid #e2e8f0", background: "white", cursor: transcript ? "pointer" : "not-allowed", color: "#475569", opacity: transcript ? 1 : 0.5, fontWeight: "500", fontSize: "1rem" }}
            >
              {t.retryBtn}
            </button>
            <button
              onClick={handleAnswerSubmit}
              disabled={!transcript || isSubmitting || recordingState !== "idle"}
              style={{ padding: "0.75rem 2rem", borderRadius: "8px", border: "none", background: transcript && !isSubmitting && recordingState === "idle" ? "#3b82f6" : "#93c5fd", color: "white", cursor: transcript && !isSubmitting && recordingState === "idle" ? "pointer" : "not-allowed", fontWeight: "700", fontSize: "1rem", display: "flex", alignItems: "center", gap: "8px" }}
            >
              {isSubmitting ? "⏳ " + t.micTranscribing : t.continueBtn + " ✓"}
            </button>
          </div>

          {/* Fallback Options */}
          <div style={{ display: "flex", justifyContent: "center", gap: "2rem", marginTop: "1rem" }}>
            <button
              onClick={() => setShowManual((v) => !v)}
              style={{ background: "none", border: "none", color: "#3b82f6", cursor: "pointer", fontSize: "0.95rem", fontWeight: "500", padding: "4px" }}
            >
              ⌨️ {t.manualBtn}
            </button>
            <label style={{ color: "#3b82f6", cursor: "pointer", fontSize: "0.95rem", fontWeight: "500" }}>
              <input type="file" accept="audio/*,.webm,.wav,.mp3,.m4a,.ogg" style={{ display: "none" }} onChange={handleAudioUpload} />
              📁 {t.uploadBtn}
            </label>
          </div>

          {showManual && (
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
