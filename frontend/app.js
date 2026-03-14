/**
 * app.js — PIA Call Flow Controller
 *
 * State machine:
 *   idle → connecting → listening → processing → speaking → listening → …
 *                                                                      ↓
 *                                                                    ended
 *
 * STT: Web Speech API (Chrome) with MediaRecorder fallback to Whisper API.
 * TTS: ElevenLabs via /api/speak (backend).
 * LLM: Claude / GPT-4o via /api/chat (backend).
 */

// ── Config ────────────────────────────────────────────────────────────────────

const API_BASE = '';                // same origin as backend (FastAPI serves frontend)
const STT_MODE = 'webspeech';      // 'webspeech' | 'whisper'
const SILENCE_MS = 1500;          // ms of silence before sending to LLM (webspeech mode)

// ── State ─────────────────────────────────────────────────────────────────────

let state = 'idle';          // current call state
let sessionId = null;        // backend session ID
let turnCount = 0;
let callStartTime = null;
let timerInterval = null;
let muted = false;

// STT
let recognition = null;      // SpeechRecognition instance
let silenceTimer = null;      // debounce: send after silence
let lastTranscript = '';      // accumulated user speech this turn

// TTS playback
let audioEl = null;           // current <audio> element
const avatar = new AvatarAnimator();

// MediaRecorder fallback (Whisper mode)
let recorder = null;
let recordedChunks = [];


// ── State machine ─────────────────────────────────────────────────────────────

function setState(newState) {
  state = newState;
  const dot = document.getElementById('status-dot');
  const txt = document.getElementById('call-status-text');

  const labels = {
    connecting:  'Connecting…',
    listening:   '🎙 Listening…',
    processing:  'Thinking…',
    speaking:    'Speaking…',
    ended:       'Call ended',
  };

  const dotClass = {
    connecting:  '',
    listening:   'connected',
    processing:  'connected',
    speaking:    'speaking',
  };

  if (txt) txt.textContent = labels[newState] || newState;
  if (dot) { dot.className = 'call-status-dot'; if (dotClass[newState]) dot.classList.add(dotClass[newState]); }
}

function showScreen(id) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById(id).classList.add('active');
}


// ── Call lifecycle ─────────────────────────────────────────────────────────────

async function startCall() {
  showScreen('screen-call');
  setState('connecting');

  try {
    // 1. Start backend session
    const res  = await apiFetch('/api/call/start', 'POST');
    sessionId  = res.session_id;
    callStartTime = Date.now();

    // 2. Update UI with persona name
    const nameEl = document.getElementById('pia-name');
    if (nameEl) nameEl.textContent = res.persona_name || 'PIA';
    document.querySelectorAll('#idle-photo, #call-photo').forEach(img => {
      img.alt = res.persona_name || 'PIA';
    });

    // 3. Start call timer
    timerInterval = setInterval(updateTimer, 1000);

    // 4. Speak greeting
    await piaSpeaks(res.greeting);

    // 5. Start listening
    startListening();

  } catch (err) {
    console.error('[call] startCall failed:', err);
    showTranscript(`⚠ Could not connect: ${err.message}`, true);
    setTimeout(resetToIdle, 3000);
  }
}

async function endCall() {
  if (state === 'idle' || state === 'ended') return;
  setState('ended');

  // Stop everything
  stopListening();
  stopAudio();
  clearInterval(timerInterval);

  const duration = callStartTime ? formatTimer(Date.now() - callStartTime) : '00:00';

  // Notify backend
  try {
    if (sessionId) await apiFetch(`/api/call/end/${sessionId}`, 'POST');
  } catch (_) {}
  sessionId = null;

  // Show ended screen
  document.getElementById('ended-duration').textContent = `Duration: ${duration}`;
  document.getElementById('ended-turns').textContent    = `${turnCount} exchange${turnCount !== 1 ? 's' : ''}`;
  showScreen('screen-ended');
}

function resetToIdle() {
  state      = 'idle';
  sessionId  = null;
  turnCount  = 0;
  callStartTime = null;
  lastTranscript = '';
  clearInterval(timerInterval);
  updateTimer();   // reset to 00:00
  showScreen('screen-idle');
}

function toggleMute() {
  muted = !muted;
  document.getElementById('btn-mute').classList.toggle('muted', muted);
  document.getElementById('icon-mic').style.display     = muted ? 'none'  : 'block';
  document.getElementById('icon-mic-off').style.display = muted ? 'block' : 'none';

  if (recognition) {
    muted ? recognition.stop() : recognition.start();
  }
}

function toggleSpeaker() {
  if (audioEl) audioEl.muted = !audioEl.muted;
}


// ── STT: Web Speech API ───────────────────────────────────────────────────────

function startListening() {
  if (muted) return;
  setState('listening');
  showTranscript('');

  if (STT_MODE === 'webspeech' && ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window)) {
    startWebSpeech();
  } else {
    // Whisper mode fallback
    startMediaRecorder();
  }
}

function stopListening() {
  clearTimeout(silenceTimer);
  if (recognition) { try { recognition.stop(); } catch (_) {} recognition = null; }
  if (recorder && recorder.state !== 'inactive') { recorder.stop(); }
}

function startWebSpeech() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SR();
  recognition.lang        = 'en-US';
  recognition.interimResults = true;
  recognition.continuous  = false;    // single utterance — restart after each use
  recognition.maxAlternatives = 1;

  recognition.onresult = (event) => {
    let interim = '';
    let final   = '';
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const r = event.results[i];
      if (r.isFinal) final  += r[0].transcript;
      else           interim += r[0].transcript;
    }
    if (interim || final) showTranscript((interim || final).trim(), false);
    if (final.trim()) {
      lastTranscript = final.trim();
      clearTimeout(silenceTimer);
      silenceTimer = setTimeout(() => processUserSpeech(lastTranscript), 300);
    }
  };

  recognition.onerror = (event) => {
    if (event.error === 'no-speech') {
      // No speech detected — restart quietly
      if (state === 'listening') recognition.start();
    } else {
      console.warn('[stt] error:', event.error);
    }
  };

  recognition.onend = () => {
    // Restart if we're still in listening state (continuous feel)
    if (state === 'listening' && !muted) {
      try { recognition.start(); } catch (_) {}
    }
  };

  recognition.start();
}


// ── STT: Whisper fallback (MediaRecorder) ────────────────────────────────────

function startMediaRecorder() {
  if (!navigator.mediaDevices) {
    showTranscript('⚠ Microphone access not available', true);
    return;
  }

  navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
    recordedChunks = [];
    recorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });

    recorder.ondataavailable = e => { if (e.data.size > 0) recordedChunks.push(e.data); };

    recorder.onstop = async () => {
      const blob = new Blob(recordedChunks, { type: 'audio/webm' });
      stream.getTracks().forEach(t => t.stop());

      try {
        showTranscript('Transcribing…');
        const form = new FormData();
        form.append('file', blob, 'audio.webm');
        const res = await fetch(`${API_BASE}/api/transcribe`, { method: 'POST', body: form });
        const data = await res.json();
        if (data.transcript) await processUserSpeech(data.transcript);
      } catch (err) {
        console.error('[whisper] transcription failed:', err);
        startListening();  // retry
      }
    };

    recorder.start();

    // Auto-stop after 15 seconds (push-to-talk feel can be added later)
    setTimeout(() => {
      if (recorder.state !== 'inactive') recorder.stop();
    }, 15000);

  }).catch(err => {
    console.error('[mic] permission denied:', err);
    showTranscript('⚠ Microphone access denied', true);
  });
}


// ── LLM + TTS pipeline ────────────────────────────────────────────────────────

async function processUserSpeech(text) {
  if (!text || !text.trim()) return;
  if (state !== 'listening') return;

  stopListening();
  setState('processing');
  showTranscript(`You: ${text}`, false);

  try {
    // 1. Get LLM reply
    const chatRes = await apiFetch('/api/chat', 'POST', {
      session_id:   sessionId,
      user_message: text,
    });

    const reply = chatRes.reply;
    turnCount++;

    // 2. Speak reply
    await piaSpeaks(reply);

    // 3. Back to listening
    if (state !== 'ended') startListening();

  } catch (err) {
    console.error('[pipeline] error:', err);
    showTranscript('⚠ Something went wrong. Try again.', true);
    if (state !== 'ended') startListening();
  }
}

async function piaSpeaks(text) {
  setState('speaking');
  showTranscript(`PIA: ${text}`, false);

  try {
    // Fetch TTS audio from backend
    const res = await fetch(`${API_BASE}/api/speak`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ text }),
    });

    if (!res.ok) throw new Error(`TTS error ${res.status}`);

    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);

    // Create and play audio element
    stopAudio();   // stop any existing
    audioEl = new Audio(url);

    // Wire avatar animation to this audio element
    avatar.startSpeaking(audioEl);

    await new Promise((resolve, reject) => {
      audioEl.onended  = resolve;
      audioEl.onerror  = reject;
      audioEl.play().catch(reject);
    });

  } catch (err) {
    console.error('[tts] error:', err);
    // Still show text even if audio fails
  } finally {
    avatar.stopSpeaking();
    stopAudio();
  }
}

function stopAudio() {
  if (audioEl) {
    audioEl.pause();
    audioEl.src = '';
    audioEl = null;
  }
}


// ── UI helpers ─────────────────────────────────────────────────────────────────

function showTranscript(text, persist = false) {
  const bubble = document.getElementById('transcript-bubble');
  const span   = document.getElementById('transcript-text');
  if (!bubble || !span) return;

  span.textContent = text;
  bubble.classList.toggle('show', !!text);

  if (!persist && text) {
    clearTimeout(bubble._hideTimer);
    bubble._hideTimer = setTimeout(() => {
      bubble.classList.remove('show');
    }, 4000);
  }
}

function updateTimer() {
  const el = document.getElementById('call-timer');
  if (!el || !callStartTime) { if (el) el.textContent = '00:00'; return; }
  el.textContent = formatTimer(Date.now() - callStartTime);
}

function formatTimer(ms) {
  const total = Math.floor(ms / 1000);
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
}


// ── API helper ────────────────────────────────────────────────────────────────

async function apiFetch(path, method = 'GET', body = null) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body) opts.body = JSON.stringify(body);

  const res = await fetch(`${API_BASE}${path}`, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}


// ── Init ──────────────────────────────────────────────────────────────────────

// Check browser compatibility on load
window.addEventListener('DOMContentLoaded', async () => {
  const hasSpeech = 'SpeechRecognition' in window || 'webkitSpeechRecognition' in window;
  if (!hasSpeech && STT_MODE === 'webspeech') {
    console.warn('[stt] Web Speech API not available — will use Whisper via MediaRecorder');
  }

  // Init avatar animator (loads config from /api/avatar/config)
  await avatar.init();

  // Keyboard shortcut: Space = call/hang up, M = mute
  document.addEventListener('keydown', (e) => {
    if (e.code === 'Space' && e.target === document.body) {
      e.preventDefault();
      if (state === 'idle') startCall();
      else if (state !== 'ended') endCall();
    }
    if (e.code === 'KeyM') toggleMute();
  });
});
