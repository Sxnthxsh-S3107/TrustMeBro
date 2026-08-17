/**
 * Voice Intake & NLP Frontend Logic
 * Real-time Speech-to-Text via Web Speech API (English & Tamil)
 * + Backend Whisper ASR fallback & Audio File Upload.
 */

// UI Localization Dictionaries
const UI_TEXT = {
  en: {
    appTitle: "Voice Intake & NLP",
    appSubtitle: "Person 2 Independent Subsystem • English & தமிழ்",
    appBadge: "Live Voice Intake Mode",
    session: "Session",
    language: "Language",
    langName: "English",
    questionStep: "Question",
    followUpStep: "Clinical Follow-up",
    micReady: "Click microphone to speak",
    micRecording: "Listening to your voice... (Speak now)",
    micTranscribing: "Processing speech...",
    micError: "Microphone error or permission denied",
    micPermissionRequired: "Microphone permission is required. Please ensure you access the site via http://localhost:5000 and allow microphone access in browser settings.",
    micNoSpeech: "No speech detected. Please speak into the microphone and try again.",
    micTranscribeFail: "Speech recognition failed. Please try again or type your answer.",
    transcriptPlaceholder: "Your spoken answer will appear here in real-time...",
    extractedTitle: "Extracted Clinical Data",
    lblComplaint: "Complaint",
    lblDuration: "Duration",
    lblMeds: "Meds",
    lblHistory: "History",
    btnContinue: "Continue",
    btnRetry: "Retry",
    manualToggle: "⌨️ Type answer manually",
    uploadToggle: "📁 Upload audio file",
    manualPlaceholder: "Type answer in English / Tamil / Tanglish...",
    manualApply: "Apply",
    resultTitle: "Intake Completed",
    resultSubtitle: "Standardized patient encounter JSON conforming to contracts/intake_schema.json.",
    btnCopy: "📋 Copy JSON",
    btnNewSession: "🔄 New Session",
    copied: "Copied to clipboard!",
  },
  ta: {
    appTitle: "குரல் பதிவு மற்றும் மருத்துவ மதிப்பீடு",
    appSubtitle: "பகுதி 2 தனித்த அமைப்பு • ஆங்கிலம் & தமிழ்",
    appBadge: "நேரடி குரல் பதிவு தளம்",
    session: "அமர்வு",
    language: "மொழி",
    langName: "தமிழ் (Tamil)",
    questionStep: "கேள்வி",
    followUpStep: "கூடுதல் மருத்துவக் கேள்வி",
    micReady: "பேச மைக் பொத்தானை அழுத்தவும்",
    micRecording: "உங்கள் குரலைக் கேட்கிறது... (இப்போது பேசவும்)",
    micTranscribing: "குரல் உரையாக மாற்றப்படுகிறது...",
    micError: "மைக் அனுமதி கிடைக்கவில்லை",
    micPermissionRequired: "மைக்ரோஃபோன் அனுமதி தேவை. http://localhost:5000 இல் திறந்து அனுமதி வழங்கவும்.",
    micNoSpeech: "குரல் கண்டறியப்படவில்லை. மைக் அருகே பேசி மீண்டும் முயற்சிக்கவும்.",
    micTranscribeFail: "குரலை அடையாளம் காண முடியவில்லை. மீண்டும் முயற்சிக்கவும் அல்லது கீழே தட்டச்சு செய்யவும்.",
    transcriptPlaceholder: "நீங்கள் பேசும் வார்த்தைகள் நேரடியாக இங்கு தோன்றும்...",
    extractedTitle: "கண்டறியப்பட்ட மருத்துவத் தகவல்கள்",
    lblComplaint: "பிரச்சனை",
    lblDuration: "கால அளவு",
    lblMeds: "மருந்துகள்",
    lblHistory: "வரலாறு",
    btnContinue: "அடுத்து செல்லவும்",
    btnRetry: "மீண்டும் முயற்சிக்கவும்",
    manualToggle: "⌨️ நேரடியாக தட்டச்சு செய்யவும்",
    uploadToggle: "📁 ஆடியோ கோப்பை பதிவேற்றவும்",
    manualPlaceholder: "ஆங்கிலம் / தமிழ் / Tanglish இல் தட்டச்சு செய்யவும்...",
    manualApply: "சேர்க்கவும்",
    resultTitle: "மதிப்பீடு வெற்றிகரமாக முடிந்தது",
    resultSubtitle: "ஒப்பந்தத்தின்படி இறுதி மருத்துவத் தரவு (contracts/intake_schema.json).",
    btnCopy: "📋 JSON நகலெடுக்க",
    btnNewSession: "🔄 புதிய பதிவு தொடங்க",
    copied: "நகலெடுக்கப்பட்டது!",
  },
};

// State Variables
let currentSessionId = null;
let currentLanguage = "en";
let currentQuestionId = null;
let currentTranscript = "";
let speechRecognizer = null;
let mediaStream = null;
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let recordedMimeType = "audio/webm";

/**
 * Select intake language and initialize session
 */
async function selectLanguage(lang) {
  currentLanguage = lang;
  applyLocalization(lang);

  try {
    const response = await fetch("/intake/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ language: lang }),
    });

    const data = await response.json();
    if (!response.ok) {
      alert("Error starting intake session: " + (data.error || "Unknown"));
      return;
    }

    currentSessionId = data.session_id;

    // Transition Screen
    document.getElementById("language-screen").classList.add("hidden");
    document.getElementById("intake-screen").classList.remove("hidden");
    document.getElementById("result-screen").classList.add("hidden");

    // Display session details
    document.getElementById("lbl-session-id").innerText = currentSessionId.substring(0, 8) + "...";
    document.getElementById("lbl-lang").innerText = UI_TEXT[lang].langName;

    // Load first question
    if (data.first_question) {
      renderQuestion(data.first_question);
    }
  } catch (err) {
    console.error("Failed to start session:", err);
    alert("Connection error connecting to voice intake backend.");
  }
}

/**
 * Apply localized UI strings
 */
function applyLocalization(lang) {
  const t = UI_TEXT[lang] || UI_TEXT.en;

  document.getElementById("app-title").innerText = t.appTitle;
  document.getElementById("app-subtitle").innerText = t.appSubtitle;
  document.getElementById("app-badge").innerText = t.appBadge;

  document.getElementById("lbl-mic-status").innerText = t.micReady;
  document.getElementById("transcript-box").innerText = t.transcriptPlaceholder;
  document.getElementById("lbl-extracted-title").innerText = t.extractedTitle;

  document.getElementById("btn-submit").innerText = t.btnContinue;
  document.getElementById("btn-retry").innerText = t.btnRetry;

  document.getElementById("btn-toggle-text").innerText = t.manualToggle;
  const uploadBtn = document.getElementById("btn-upload-audio");
  if (uploadBtn) uploadBtn.innerText = t.uploadToggle;
  document.getElementById("manual-text-input").placeholder = t.manualPlaceholder;
  document.getElementById("btn-manual-submit").innerText = t.manualApply;

  document.getElementById("lbl-result-title").innerText = t.resultTitle;
  document.getElementById("lbl-result-subtitle").innerText = t.resultSubtitle;
  document.getElementById("btn-copy-json").innerText = t.btnCopy;
  document.getElementById("btn-new-session").innerText = t.btnNewSession;
}

/**
 * Render Question onto the screen
 */
function renderQuestion(q) {
  currentQuestionId = q.question_id;
  const t = UI_TEXT[currentLanguage];

  const stepTag = q.is_adaptive ? t.followUpStep : t.questionStep;
  document.getElementById("lbl-step-tag").innerText = stepTag;
  document.getElementById("lbl-question-text").innerText = q.question_text;

  // Reset answer controls for the new question
  resetCurrentAnswer();
}

/**
 * Reset answer text and controls for current question
 */
function resetCurrentAnswer() {
  currentTranscript = "";
  const t = UI_TEXT[currentLanguage];
  const box = document.getElementById("transcript-box");
  box.innerText = t.transcriptPlaceholder;
  box.classList.add("placeholder");
  box.style.color = "";

  document.getElementById("btn-submit").disabled = true;
  document.getElementById("manual-text-input").value = "";
  document.getElementById("lbl-mic-status").innerText = t.micReady;
}

/**
 * Toggle Audio Recording / Real-Time Speech Recognition
 */
async function toggleRecording() {
  if (isRecording) {
    stopRecording();
  } else {
    await startRecording();
  }
}

/**
 * Start Live Speech Recognition & Microphone Capture
 */
async function startRecording() {
  const t = UI_TEXT[currentLanguage];
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  isRecording = true;
  const micBtn = document.getElementById("btn-mic");
  micBtn.classList.add("recording");
  document.getElementById("lbl-mic-status").innerText = t.micRecording;

  const box = document.getElementById("transcript-box");
  box.innerText = "Listening...";
  box.classList.remove("placeholder");
  box.style.color = "#93c5fd";

  let capturedSpeechViaWebSpeech = false;

  // 1. Try Browser Web Speech API for instant, real-time live transcription
  if (SpeechRecognition) {
    try {
      speechRecognizer = new SpeechRecognition();
      // Set language: 'ta-IN' for Tamil, 'en-US' for English
      speechRecognizer.lang = (currentLanguage === "ta") ? "ta-IN" : "en-US";
      speechRecognizer.interimResults = true;
      speechRecognizer.continuous = false;
      speechRecognizer.maxAlternatives = 1;

      speechRecognizer.onresult = (event) => {
        let interimTranscript = "";
        let finalTranscript = "";

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript;
          } else {
            interimTranscript += event.results[i][0].transcript;
          }
        }

        const liveText = finalTranscript || interimTranscript;
        if (liveText.trim()) {
          capturedSpeechViaWebSpeech = true;
          box.innerText = `"${liveText.trim()}"`;
          box.style.color = "#f1f5f9";
          currentTranscript = liveText.trim();
          document.getElementById("btn-submit").disabled = false;
        }
      };

      speechRecognizer.onerror = (event) => {
        console.warn("Web Speech API event:", event.error);
      };

      speechRecognizer.onend = () => {
        if (isRecording) {
          stopRecording();
        }
      };

      speechRecognizer.start();
    } catch (e) {
      console.warn("SpeechRecognition init error:", e);
    }
  }

  // 2. Also start MediaRecorder for audio capture (used for backend / audio blob)
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true },
    });

    audioChunks = [];
    recordedMimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus") ? "audio/webm;codecs=opus" : "audio/webm";

    mediaRecorder = new MediaRecorder(mediaStream);
    mediaRecorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) audioChunks.push(e.data);
    };

    mediaRecorder.onstop = async () => {
      // If Web Speech API already transcribed the speech live, we are done
      if (currentTranscript && currentTranscript.trim().length > 0) {
        document.getElementById("lbl-mic-status").innerText = t.micReady;
        return;
      }

      // Otherwise, send recorded audio blob to backend Whisper /transcribe
      const audioBlob = new Blob(audioChunks, { type: recordedMimeType });
      if (audioBlob.size >= 500) {
        await processAudioTranscription(audioBlob);
      } else {
        document.getElementById("lbl-mic-status").innerText = t.micNoSpeech;
        box.innerText = t.micNoSpeech;
        box.style.color = "#f87171";
      }
    };

    mediaRecorder.start();
  } catch (err) {
    console.error("Microphone hardware error:", err);
    // If Web Speech API didn't start either, alert user
    if (!SpeechRecognition) {
      document.getElementById("lbl-mic-status").innerText = t.micError;
      alert(t.micPermissionRequired);
      isRecording = false;
      micBtn.classList.remove("recording");
    }
  }
}

function stopRecording() {
  if (!isRecording) return;
  isRecording = false;

  const t = UI_TEXT[currentLanguage];
  const micBtn = document.getElementById("btn-mic");
  micBtn.classList.remove("recording");
  document.getElementById("lbl-mic-status").innerText = t.micReady;

  if (speechRecognizer) {
    try { speechRecognizer.stop(); } catch (e) {}
  }

  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    try { mediaRecorder.stop(); } catch (e) {}
  }

  if (mediaStream) {
    mediaStream.getTracks().forEach((track) => track.stop());
  }
}

/**
 * Send Audio to Backend /transcribe (Whisper STT)
 */
async function processAudioTranscription(blob) {
  const t = UI_TEXT[currentLanguage];
  const formData = new FormData();

  let extension = "webm";
  if (recordedMimeType.includes("mp4")) extension = "mp4";
  else if (recordedMimeType.includes("wav")) extension = "wav";

  formData.append("audio", blob, `recording.${extension}`);
  formData.append("session_id", currentSessionId);
  formData.append("language", currentLanguage);

  document.getElementById("lbl-mic-status").innerText = t.micTranscribing;

  try {
    const response = await fetch("/transcribe", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();
    document.getElementById("lbl-mic-status").innerText = t.micReady;

    if (response.ok && data.transcript) {
      applyTranscriptText(data.transcript);
    } else {
      const errorMsg = data.error || t.micTranscribeFail;
      const box = document.getElementById("transcript-box");
      box.innerText = `⚠️ ${errorMsg}`;
      box.style.color = "#f87171";
      box.classList.remove("placeholder");
      document.getElementById("btn-submit").disabled = true;
    }
  } catch (err) {
    console.error("Transcription request failed:", err);
    document.getElementById("lbl-mic-status").innerText = t.micReady;
    alert("Failed to communicate with transcription service.");
  }
}

/**
 * Set active transcript from speech, upload, or manual text
 */
function applyTranscriptText(text) {
  currentTranscript = text.trim();
  const box = document.getElementById("transcript-box");
  box.innerText = `"${currentTranscript}"`;
  box.classList.remove("placeholder");
  box.style.color = "#f1f5f9";
  document.getElementById("btn-submit").disabled = false;
}

/**
 * Manual text fallback handlers
 */
function toggleManualInput(event) {
  if (event) event.preventDefault();
  const box = document.getElementById("manual-input-box");
  box.classList.toggle("hidden");
  if (!box.classList.contains("hidden")) {
    document.getElementById("manual-text-input").focus();
  }
}

function submitManualText() {
  const input = document.getElementById("manual-text-input");
  if (input.value.trim()) {
    applyTranscriptText(input.value.trim());
  }
}

/**
 * Audio file upload handlers
 */
function triggerAudioUpload(event) {
  if (event) event.preventDefault();
  const fileInput = document.getElementById("audio-file-input");
  fileInput.click();
}

async function handleAudioFileUpload(event) {
  const file = event.target.files && event.target.files[0];
  if (!file) return;

  const t = UI_TEXT[currentLanguage];
  document.getElementById("lbl-mic-status").innerText = t.micTranscribing;

  recordedMimeType = file.type || "audio/webm";
  await processAudioTranscription(file);

  event.target.value = "";
}

/**
 * Submit current answer to /intake/answer
 */
async function submitCurrentAnswer() {
  if (!currentTranscript || !currentTranscript.trim() || !currentSessionId) {
    const warningMsg = currentLanguage === "ta" 
      ? "முதலில் உங்கள் பதிலைப் பேசவும் அல்லது தட்டச்சு செய்யவும்." 
      : "Please speak or type your answer before continuing.";
    alert(warningMsg);
    document.getElementById("btn-submit").disabled = true;
    return;
  }

  document.getElementById("btn-submit").disabled = true;

  try {
    const response = await fetch("/intake/answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: currentSessionId,
        text: currentTranscript.trim(),
      }),
    });

    const data = await response.json();
    if (!response.ok) {
      alert("Error submitting answer: " + (data.error || "Unknown"));
      document.getElementById("btn-submit").disabled = false;
      return;
    }

    // Update entity badges
    updateEntityBadges(data.extracted);

    // Check if session completed
    if (data.status === "completed" || !data.next_question) {
      await showFinalResults();
    } else {
      renderQuestion(data.next_question);
    }
  } catch (err) {
    console.error("Error submitting answer:", err);
    alert("Connection error submitting answer.");
    document.getElementById("btn-submit").disabled = false;
  }
}

/**
 * Update clinical entity badges in UI
 */
function updateEntityBadges(extracted) {
  if (!extracted) return;

  if (extracted.chief_complaint) {
    document.getElementById("val-complaint").innerText = extracted.chief_complaint;
  }
  if (extracted.duration) {
    document.getElementById("val-duration").innerText = extracted.duration;
  }
  if (extracted.medications) {
    document.getElementById("val-meds").innerText = Array.isArray(extracted.medications)
      ? extracted.medications.join(", ")
      : extracted.medications;
  }
  if (extracted.history) {
    document.getElementById("val-history").innerText = extracted.history;
  }
}

/**
 * Fetch and show final structured JSON
 */
async function showFinalResults() {
  try {
    const response = await fetch(`/intake/result?session_id=${currentSessionId}`);
    const data = await response.json();

    document.getElementById("intake-screen").classList.add("hidden");
    document.getElementById("result-screen").classList.remove("hidden");

    document.getElementById("final-json-view").innerText = JSON.stringify(data, null, 2);
  } catch (err) {
    console.error("Error fetching final result:", err);
    alert("Failed to load final intake JSON.");
  }
}

/**
 * Copy JSON to clipboard
 */
function copyJsonToClipboard() {
  const jsonText = document.getElementById("final-json-view").innerText;
  navigator.clipboard.writeText(jsonText).then(() => {
    const t = UI_TEXT[currentLanguage];
    alert(t.copied);
  });
}

/**
 * Start a brand new session
 */
function startFreshSession() {
  currentSessionId = null;
  currentQuestionId = null;
  currentTranscript = "";

  document.getElementById("val-complaint").innerText = "-";
  document.getElementById("val-duration").innerText = "-";
  document.getElementById("val-meds").innerText = "-";
  document.getElementById("val-history").innerText = "-";

  document.getElementById("result-screen").classList.add("hidden");
  document.getElementById("intake-screen").classList.add("hidden");
  document.getElementById("language-screen").classList.remove("hidden");
}
