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

// Camera
let camStream    = null;      // active MediaStream from getUserMedia
let camFacing    = 'user';    // 'user' (front) | 'environment' (back)
let cameraOn     = false;     // whether camera PIP is active
let lastFrameB64 = null;      // last captured JPEG frame (for vision context)
let frameInterval = null;     // frame-capture timer when back cam active
const FRAME_INTERVAL_MS = 4000;  // capture back-cam frame every 4 s

// Location & capabilities
let lastLocation = null;      // { lat, lon, accuracy, timestamp }
let locationWatchId = null;   // geolocation watch ID for continuous updates

// STT
let recognition = null;      // SpeechRecognition instance
let silenceTimer = null;      // debounce: send after silence
let lastTranscript = '';      // accumulated user speech this turn

// TTS playback
let audioEl = null;           // current <audio> element
const avatar = new RealisticAvatarAnimator();

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

  // Auto-hide topbar after 4 s (like a real video call)
  const topbar = document.getElementById('call-topbar');
  if (topbar) {
    clearTimeout(topbar._hideTimer);
    topbar._hideTimer = setTimeout(() => topbar.classList.add('hidden'), 4000);
  }

  // ── PRE-REQUEST MIC PERMISSION ───────────────────────────────────────────
  // Must happen inside a user gesture (button click). Ask now so the dialog
  // appears before call starts rather than silently failing mid-call.
  try {
    const micCheck = await navigator.mediaDevices.getUserMedia({ audio: true });
    micCheck.getTracks().forEach(t => t.stop());  // immediately release; we just needed the grant
    console.log('[call] mic permission granted');
  } catch (micErr) {
    console.warn('[call] mic permission denied:', micErr.message);
    showTranscript('⚠ Microphone access denied — check browser settings', true);
    setTimeout(resetToIdle, 3500);
    return;
  }

  // Request location permission (for weather, maps, location-aware responses)
  requestLocation();

  // Load avatar: localStorage (custom) → /avatar.jpg (default) → initials
  const loadAvatar = () => {
    const savedAvatar = localStorage.getItem('pia_avatar');
    const avatarImgs = document.querySelectorAll('#idle-photo, #call-photo');
    const bgImg = document.querySelector('.idle-bg img');
    const initials = document.getElementById('pia-initials');
    
    if (savedAvatar) {
      // Custom photo from onboarding
      avatarImgs.forEach(img => {
        img.src = savedAvatar;
        img.style.display = 'block';
      });
      if (bgImg) bgImg.src = savedAvatar;
      if (initials) initials.style.opacity = '0';
    } else {
      // Try default /avatar.jpg
      const defaultSrc = '/avatar.jpg';
      avatarImgs.forEach(img => {
        img.src = defaultSrc;
        img.onload = () => { img.style.display = 'block'; if (initials) initials.style.opacity = '0'; };
        img.onerror = () => { img.style.display = 'none'; if (initials) initials.style.opacity = '1'; };
      });
      if (bgImg) bgImg.src = defaultSrc;
    }
  };
  loadAvatar();

  // Start front camera automatically (non-blocking)
  initUserCamera('user').catch(() => {});

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
  stopCamera();
  stopLocation();
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
  stopCamera();
  stopLocation();
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


// ── Camera (user PIP) ─────────────────────────────────────────────────────────

async function initUserCamera(facing) {
  // Stop any existing stream
  if (camStream) {
    camStream.getTracks().forEach(t => t.stop());
    camStream = null;
  }

  const pipWrap    = document.getElementById('pip-wrap');
  const camEl      = document.getElementById('user-cam');
  const placeholder = document.getElementById('pip-placeholder');

  try {
    camStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: facing, width: { ideal: 360 }, height: { ideal: 480 } },
      audio: false,
    });
    camEl.srcObject = camStream;
    await camEl.play().catch(() => {}); // required on iOS/Safari — autoplay alone isn't enough
    if (placeholder) placeholder.classList.add('hidden');
    cameraOn  = true;
    camFacing = facing;

    // Mirror front, don't mirror back
    pipWrap?.classList.toggle('back-cam', facing === 'environment');

    // Camera-on icon
    document.getElementById('icon-cam-on')?.style?.setProperty('display','block');
    document.getElementById('icon-cam-off')?.style?.setProperty('display','none');
    document.getElementById('btn-cam')?.classList.remove('cam-off');

    // Start periodic frame capture when using back camera (twin sees what you see)
    clearInterval(frameInterval);
    if (facing === 'environment') {
      frameInterval = setInterval(() => { lastFrameB64 = captureFrame(); }, FRAME_INTERVAL_MS);
    } else {
      lastFrameB64 = null;
    }

    console.log(`[cam] Started ${facing} camera`);
  } catch (err) {
    console.warn('[cam] Could not start camera:', err.message);
    cameraOn = false;
    if (placeholder) placeholder.classList.remove('hidden');
  }
}

function captureFrame() {
  const video = document.getElementById('user-cam');
  if (!video || !video.srcObject || video.videoWidth === 0) return null;
  try {
    const canvas = document.createElement('canvas');
    // Downscale for API efficiency — 480px wide max
    const scale = Math.min(1, 480 / video.videoWidth);
    canvas.width  = Math.round(video.videoWidth  * scale);
    canvas.height = Math.round(video.videoHeight * scale);
    const ctx = canvas.getContext('2d');
    // Don't mirror capture — send raw image to LLM
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL('image/jpeg', 0.65).split(',')[1];  // base64 only
  } catch (_) {
    return null;
  }
}

async function flipCamera() {
  const next = camFacing === 'user' ? 'environment' : 'user';
  await initUserCamera(next);
  // Capture one frame immediately after flip
  if (next === 'environment') {
    lastFrameB64 = captureFrame();
  } else {
    lastFrameB64 = null;
  }
}

async function toggleCamera() {
  const camOn  = document.getElementById('icon-cam-on');
  const camOff = document.getElementById('icon-cam-off');
  const btn    = document.getElementById('btn-cam');
  if (cameraOn) {
    // Turn off
    if (camStream) camStream.getTracks().forEach(t => t.stop());
    camStream = null; cameraOn = false; lastFrameB64 = null;
    clearInterval(frameInterval);
    const placeholder = document.getElementById('pip-placeholder');
    if (placeholder) placeholder.classList.remove('hidden');
    if (camOn)  camOn.style.display  = 'none';
    if (camOff) camOff.style.display = 'block';
    btn?.classList.add('cam-off');
  } else {
    await initUserCamera(camFacing);
  }
}

function stopCamera() {
  clearInterval(frameInterval);
  if (camStream) { camStream.getTracks().forEach(t => t.stop()); camStream = null; }
  cameraOn = false; lastFrameB64 = null;
}


// ── Location & Capabilities ───────────────────────────────────────────────────

function requestLocation() {
  if (!navigator.geolocation) {
    console.warn('[geo] Geolocation API not available');
    return;
  }
  
  // Request permission and start watching location
  navigator.geolocation.watchPosition(
    (pos) => {
      lastLocation = {
        lat: pos.coords.latitude,
        lon: pos.coords.longitude,
        accuracy: Math.round(pos.coords.accuracy),
        timestamp: Date.now(),
      };
      console.log('[geo] Location:', lastLocation);
    },
    (err) => {
      console.warn('[geo] Permission denied:', err.message);
    },
    {
      enableHighAccuracy: false,
      maximumAge: 30000,  // re-use cached location if < 30s old
      timeout: 10000,
    }
  );
}

function stopLocation() {
  if (locationWatchId !== null) {
    navigator.geolocation.clearWatch(locationWatchId);
    locationWatchId = null;
  }
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

  // Capture a fresh frame if using back camera (twin sees what you see)
  const frameForApi = camFacing === 'environment' ? (captureFrame() || lastFrameB64) : null;

  try {
    // 1. Get LLM reply (optionally with visual frame + location for context)
    const chatReq = {
      session_id:   sessionId,
      user_message: text,
    };
    if (frameForApi) chatReq.image_base64 = frameForApi;
    if (lastLocation) chatReq.location = lastLocation;
    
    const chatRes = await apiFetch('/api/chat', 'POST', chatReq);

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
  // New design: caption bar floating above controls
  const captionEl = document.getElementById('caption-text');
  // Also re-show topbar briefly when there's activity
  const topbar = document.getElementById('call-topbar');
  if (!captionEl) return;

  captionEl.textContent = text;
  captionEl.classList.toggle('show', !!text);

  if (topbar && text) {
    topbar.classList.remove('hidden');
    clearTimeout(topbar._hideTimer);
    topbar._hideTimer = setTimeout(() => topbar.classList.add('hidden'), 3500);
  }

  if (!persist && text) {
    clearTimeout(captionEl._hideTimer);
    captionEl._hideTimer = setTimeout(() => {
      captionEl.classList.remove('show');
    }, 5000);
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

  // Init avatar animator (creates canvas-based talking head with lip sync)
  await avatar.init('pia-main');

  // Restore saved avatar photo immediately (works even offline)
  const savedAvatar = localStorage.getItem('pia_avatar');
  if (savedAvatar) {
    document.querySelectorAll('#idle-photo, #call-photo').forEach(img => {
      img.src = savedAvatar;
    });
    const bgImg = document.querySelector('.idle-bg img');
    if (bgImg) bgImg.src = savedAvatar;
  }

  // Load persona name / subtitle onto idle screen
  try {
    const health = await apiFetch('/api/health');
    const twinName = health.twin || 'PIA';
    const userName = health.user || '';
    const idleName = document.getElementById('idle-name');
    if (idleName) idleName.textContent = twinName;
    // Update subtitle to reflect whose twin this is
    const sub = document.querySelector('.idle-subtitle');
    if (sub && userName) sub.textContent = `${userName}'s personal AI twin • always on`;
  } catch (_) {}

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
