'use strict';

// ── State ─────────────────────────────────────────────────────────────────────
let currentStep     = 0;
let userName        = '';
let nameGreeted     = false;
let nameGreetTimer  = null;

let selectedTone    = 'warm-but-direct';
let selectedHumor   = 'dry, understated';
let selectedLength  = '2–4 sentences maximum';

// Voice
let mediaRecorder   = null;
let recordedChunks  = [];
let recordedBlob    = null;
let isRecording     = false;
let recTimerInt     = null;
let recSeconds      = 0;
let audioCtx        = null;
let analyserNode    = null;
let waveSource      = null;
let waveInterval    = null;
let micStream       = null;
const BAR_COUNT     = 44;

// Photo
let capturedPhotoBlob = null;
let cameraStream      = null;
let cameraActive      = false;

// ── Init ───────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Build waveform bars
  const wf = document.getElementById('waveform');
  for (let i = 0; i < BAR_COUNT; i++) {
    const b = document.createElement('div');
    b.className = 'wbar';
    wf.appendChild(b);
  }

  // Enable "Next" on step 1 when name is filled
  document.getElementById('inp-name').addEventListener('input', e => {
    document.getElementById('btn-1-next').disabled = !e.target.value.trim();
  });

  // PIA says welcome on load (subtle, non-blocking)
  setTimeout(() => piaSay('Hi there! Let\'s set up your personal AI twin. This takes just 2 minutes.'), 800);
});

// ── Navigation ─────────────────────────────────────────────────────────────────
function goTo(step) {
  currentStep = step;
  document.getElementById('steps-track').style.transform = `translateX(-${step * 100}vw)`;

  // Progress dots
  for (let i = 0; i < 5; i++) {
    const d = document.getElementById(`pdot-${i}`);
    d.className = 'pdot' + (i < step ? ' done' : i === step ? ' active' : '');
  }

  // Step side-effects
  if (step === 1) {
    setTimeout(() => document.getElementById('inp-name').focus(), 500);
  }
  if (step === 3) {
    document.getElementById('script-name').textContent = userName || 'you';
  }
  if (step === 4) {
    document.getElementById('cam-initials').textContent = userName ? userName[0].toUpperCase() : '?';
    // No auto-start — user taps "📷 Use camera" explicitly
  }
}

// ── PIA speaks ─────────────────────────────────────────────────────────────────
async function piaSay(text) {
  try {
    const res = await fetch('/api/speak', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) return;
    const blob = await res.blob();
    const audio = new Audio(URL.createObjectURL(blob));
    audio.play().catch(() => {});   // ignore autoplay block
  } catch (_) {}
}

// ── Step 1: Name ──────────────────────────────────────────────────────────────
function onNameInput(value) {
  userName = value.trim();
  document.getElementById('btn-1-next').disabled = !userName;
  clearTimeout(nameGreetTimer);

  if (userName.length >= 2 && !nameGreeted) {
    nameGreetTimer = setTimeout(async () => {
      nameGreeted = true;
      const el = document.getElementById('pia-name-says');
      el.textContent = `👋 Nice to meet you, ${userName}!`;
      el.classList.remove('hidden');
      await piaSay(`Nice to meet you, ${userName}!`);
    }, 900);
  } else if (userName.length < 2) {
    nameGreeted = false;
    document.getElementById('pia-name-says').classList.add('hidden');
  }
}

// ── Step 2: Style chips ────────────────────────────────────────────────────────
function pick(group, el, value) {
  el.closest('.chip-group').querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
  el.classList.add('active');
  if (group === 'tone')   selectedTone   = value;
  if (group === 'humor')  selectedHumor  = value;
  if (group === 'length') selectedLength = value;
}

// ── Step 3: Voice recording ────────────────────────────────────────────────────
async function toggleRecord() {
  if (isRecording) {
    stopRecording(true);  // stop & keep blob
  } else {
    await startRecording();
  }
}

function getSupportedAudioMime() {
  const types = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/ogg;codecs=opus',
    'audio/mp4',
  ];
  for (const t of types) {
    try { if (MediaRecorder.isTypeSupported(t)) return t; } catch (_) {}
  }
  return '';  // browser default
}

async function startRecording() {
  try {
    micStream      = await navigator.mediaDevices.getUserMedia({ audio: true });
    recordedChunks = [];
    isRecording    = true;

    const mime    = getSupportedAudioMime();
    const mrOpts  = mime ? { mimeType: mime } : {};
    mediaRecorder = new MediaRecorder(micStream, mrOpts);
    mediaRecorder.ondataavailable = e => { if (e.data.size > 0) recordedChunks.push(e.data); };
    mediaRecorder.onstop = () => {
      recordedBlob = new Blob(recordedChunks, { type: 'audio/webm' });
      micStream.getTracks().forEach(t => t.stop());
      micStream = null;
      document.getElementById('rec-status').textContent = `✅ Recorded ${formatTime(recSeconds)}`;
      document.getElementById('btn-3-next').disabled    = false;
    };
    mediaRecorder.start(100);

    // UI
    document.getElementById('btn-record').classList.add('recording');
    document.getElementById('btn-record').textContent = '⏹';
    document.getElementById('rec-status').textContent = 'Recording…';
    document.getElementById('waveform').classList.add('active');

    // Timer — auto-stop at 90 s
    recSeconds = 0;
    recTimerInt = setInterval(() => {
      recSeconds++;
      document.getElementById('rec-timer').textContent = formatTime(recSeconds);
      if (recSeconds >= 90) stopRecording(true);
    }, 1000);

    // Web Audio analyser for real-time waveform
    try {
      audioCtx     = new AudioContext();
      analyserNode = audioCtx.createAnalyser();
      analyserNode.fftSize = 128;
      waveSource   = audioCtx.createMediaStreamSource(micStream);
      waveSource.connect(analyserNode);
      waveInterval = setInterval(() => animateWave(true), 80);
    } catch (_) {
      waveInterval = setInterval(() => animateWave(false), 120);
    }
  } catch (err) {
    console.warn('[voice] mic access denied:', err);
    const msg = err.name === 'NotAllowedError'
      ? '⚠ Mic blocked — allow access or skip'
      : `⚠ Mic error: ${err.message}`;
    document.getElementById('rec-status').textContent = msg;
    // Auto-enable Next so user isn't stuck
    document.getElementById('btn-3-next').disabled = false;
  }
}

function stopRecording(keepBlob = false) {
  if (!isRecording) return;
  isRecording = false;
  clearInterval(recTimerInt);
  clearInterval(waveInterval);
  if (micStream) { micStream.getTracks().forEach(t => t.stop()); micStream = null; }
  if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();
  document.getElementById('btn-record').classList.remove('recording');
  document.getElementById('btn-record').textContent = '🎙';
  document.getElementById('waveform').classList.remove('active');
  document.querySelectorAll('.wbar').forEach(b => b.style.height = '6px');
  if (!keepBlob) recordedBlob = null;
}

function stopAndNext() {
  stopRecording(true);
  goTo(4);
}

function skipAndNext(n) {
  stopRecording(false);
  goTo(n);
}

function animateWave(useAnalyser) {
  const bars = document.querySelectorAll('.wbar');
  if (useAnalyser && analyserNode) {
    const data = new Uint8Array(analyserNode.frequencyBinCount);
    analyserNode.getByteFrequencyData(data);
    const step = Math.max(1, Math.floor(data.length / BAR_COUNT));
    bars.forEach((bar, i) => {
      const raw = data[i * step] || 0;
      bar.style.height = Math.max(6, raw * 0.42) + 'px';
    });
  } else {
    bars.forEach(bar => {
      bar.style.height = (6 + Math.random() * 44) + 'px';
    });
  }
}

function formatTime(s) {
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}

// ── Step 4: Camera / Photo ─────────────────────────────────────────────────────
async function startCamera() {
  if (cameraActive) return;
  const hint = document.getElementById('cam-hint');
  hint.textContent = 'Starting camera…';
  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 640 } },
      audio: false,
    });
    const video = document.getElementById('cam-video');
    video.srcObject = cameraStream;
    video.style.display = 'block';
    document.getElementById('cam-initials').style.display = 'none';
    hint.textContent = 'Tap the circle to take your photo';
    cameraActive = true;
  } catch (err) {
    console.warn('[camera] not available:', err);
    const msg = err.name === 'NotAllowedError'
      ? '⚠ Camera blocked — allow access in browser settings, or upload a photo'
      : '⚠ No camera found — upload a photo below';
    hint.textContent = msg;
    document.getElementById('cam-initials').style.display = '';
  }
}

function handleCircleTap() {
  if (cameraActive) capturePhoto();
}

function capturePhoto() {
  const video  = document.getElementById('cam-video');
  const canvas = document.getElementById('cam-canvas');
  const snap   = document.getElementById('cam-snap');

  canvas.width  = 400;
  canvas.height = 400;
  const ctx = canvas.getContext('2d');
  // Mirror the selfie camera
  ctx.translate(400, 0);
  ctx.scale(-1, 1);
  ctx.drawImage(video, 0, 0, 400, 400);

  canvas.toBlob(blob => {
    capturedPhotoBlob = blob;
    snap.src = URL.createObjectURL(blob);
    snap.style.display  = 'block';
    video.style.display = 'none';
    document.getElementById('cam-initials').style.display = 'none';
    document.getElementById('cam-hint').textContent = '✅ Photo saved — tap again to retake';
    // Stop camera
    if (cameraStream) { cameraStream.getTracks().forEach(t => t.stop()); }
    cameraStream = null;
    cameraActive = false;
  }, 'image/jpeg', 0.9);
}

function handleUpload(event) {
  const file = event.target.files[0];
  if (!file) return;
  capturedPhotoBlob = file;
  const snap = document.getElementById('cam-snap');
  snap.src = URL.createObjectURL(file);
  snap.style.display = 'block';
  document.getElementById('cam-video').style.display    = 'none';
  document.getElementById('cam-initials').style.display = 'none';
  document.getElementById('cam-hint').textContent = '✅ Photo ready';
  if (cameraStream) { cameraStream.getTracks().forEach(t => t.stop()); cameraStream = null; }
  cameraActive = false;
}

// ── Finish onboarding — save then show ready ────────────────────────────────────
async function finishOnboarding() {
  // Stop any ongoing recording
  stopRecording(true);
  // Stop camera
  if (cameraStream) { cameraStream.getTracks().forEach(t => t.stop()); cameraStream = null; }

  // Go straight to step 5 (spinner) — do NOT call goTo(4) which re-starts camera
  goTo(5);

  try {
    // 1. Save profile
    await fetch('/api/onboard/profile', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name:            userName,
        tagline:         document.getElementById('inp-tagline').value.trim(),
        tone:            selectedTone,
        humor:           selectedHumor,
        response_length: selectedLength,
      }),
    });

    // 2. Upload voice sample
    if (recordedBlob) {
      const fd = new FormData();
      fd.append('file', recordedBlob, 'voice_sample.webm');
      await fetch('/api/onboard/voice-sample', { method: 'POST', body: fd });
    }

    // 3. Upload photo
    if (capturedPhotoBlob) {
      const fd = new FormData();
      fd.append('file', capturedPhotoBlob, 'avatar.jpg');
      await fetch('/api/onboard/photo', { method: 'POST', body: fd });
    }
  } catch (err) {
    console.error('[onboard] save error:', err);
    // Continue anyway — don't block the user
  }

  // Mark onboarded in localStorage
  localStorage.setItem('pia_onboarded', '1');
  localStorage.setItem('pia_user_name', userName);

  // Build ready screen
  buildReadyScreen();
}

function buildReadyScreen() {
  // Swap spinner → ready block
  document.getElementById('saving-block').style.display = 'none';
  const readyBlock = document.getElementById('ready-block');
  readyBlock.style.display = 'flex';

  // Show photo or initials
  document.getElementById('ready-initials').textContent = (userName || '?')[0].toUpperCase();
  document.getElementById('ready-title').textContent = `${userName || 'You'}, your twin is ready.`;

  if (capturedPhotoBlob) {
    const img = document.getElementById('ready-photo');
    img.src = URL.createObjectURL(capturedPhotoBlob);
    img.style.display = 'block';
    document.getElementById('ready-initials').style.display = 'none';
  }

  // PIA speaks the welcome — this is the "amazed" moment
  setTimeout(() => {
    piaSay(
      `Hi ${userName || 'there'}! I'm PIA — your personal AI twin. ` +
      `I'm ready to take calls on your behalf and respond exactly how you would. ` +
      `Let's do this.`
    );
  }, 700);
}

function startFirstCall() {
  window.location.href = '/';
}
