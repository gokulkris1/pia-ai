'use strict';

/* ── state ── */
let currentStep = 0, userName = '', greetTimer = null;
let selectedTone   = 'warm-but-direct';
let selectedHumor  = 'dry, understated';
let selectedLength = '2-4 sentences maximum';

/* ── voice ── */
let mediaRecorder = null, recordedChunks = [], recordedBlob = null, isRecording = false;
let recInt = null, recSecs = 0, micStream = null, analyser = null, waveInt = null;
const BARS = 36;

/* ── photo ── */
let photoBlob = null, camStream = null, camActive = false;

/* ─────────── init ─────────── */
document.addEventListener('DOMContentLoaded', () => {
  const wf = document.getElementById('waveform');
  for (let i = 0; i < BARS; i++) {
    const b = document.createElement('div');
    b.className = 'wbar';
    wf.appendChild(b);
  }
});

/* ─────────── navigation ─────────── */
function goTo(n) {
  document.querySelectorAll('.step').forEach(s => s.classList.remove('active'));
  document.getElementById('s' + n).classList.add('active');
  document.getElementById('prog-fill').style.width = (n / 5 * 100) + '%';
  currentStep = n;

  if (n === 1) {
    setTimeout(() => {
      const el = document.getElementById('inp-name');
      if (el) el.focus();
    }, 350);
  }
  if (n === 3) {
    const sn = document.getElementById('script-name');
    if (sn) sn.textContent = userName || 'you';
  }
  window.scrollTo(0, 0);
}

/* ─────────── step 1: name ─────────── */
function onNameType(value) {
  const trimmed = value.trim();
  const btn = document.getElementById('btn-1');
  if (btn) btn.disabled = !trimmed;

  clearTimeout(greetTimer);
  if (trimmed.length < 2) return;
  if (trimmed === userName) return;
  userName = trimmed.charAt(0).toUpperCase() + trimmed.slice(1);
  greetTimer = setTimeout(() => {
    const b = document.getElementById('bubble-name');
    if (!b) return;
    b.textContent = 'Hi ' + userName + '! Great to meet you.';
    b.classList.add('show');
  }, 750);
}

/* ─────────── step 2: chips ─────────── */
function pick(group, el, value) {
  el.closest('.chip-row').querySelectorAll('.chip').forEach(c => c.classList.remove('sel'));
  el.classList.add('sel');
  if (group === 'tone')   selectedTone   = value;
  if (group === 'humor')  selectedHumor  = value;
  if (group === 'length') selectedLength = value;
}

/* ─────────── step 3: voice ─────────── */
function bestMime() {
  const types = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/ogg;codecs=opus',
    'audio/mp4',
    ''
  ];
  for (const t of types) {
    try { if (!t || MediaRecorder.isTypeSupported(t)) return t; } catch(e) { /**/ }
  }
  return '';
}

function toggleRecord() {
  if (isRecording) stopRecording(true);
  else startRecording();
}

async function startRecording() {
  try {
    micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (err) {
    const st = document.getElementById('rec-status');
    if (st) st.textContent = 'Mic blocked \u2014 check browser settings';
    return;
  }

  recordedChunks = [];
  const mime = bestMime();
  const opts = mime ? { mimeType: mime } : {};
  try { mediaRecorder = new MediaRecorder(micStream, opts); } catch(e) { mediaRecorder = new MediaRecorder(micStream); }

  mediaRecorder.ondataavailable = e => { if (e.data && e.data.size > 0) recordedChunks.push(e.data); };
  mediaRecorder.onstop = () => {
    const mtype = mediaRecorder.mimeType || 'audio/webm';
    if (recordedChunks.length) recordedBlob = new Blob(recordedChunks, { type: mtype });
  };
  mediaRecorder.start(250);
  isRecording = true;

  const btn = document.getElementById('btn-rec');
  const st  = document.getElementById('rec-status');
  if (btn) { btn.classList.add('on'); btn.textContent = '\u23f9'; }
  if (st)  st.textContent = 'Recording\u2026';

  recSecs = 0;
  recInt = setInterval(() => {
    recSecs++;
    const t = document.getElementById('rec-timer');
    if (t) t.textContent = Math.floor(recSecs / 60) + ':' + String(recSecs % 60).padStart(2, '0');
    if (recSecs >= 90) stopRecording(true);
  }, 1000);

  /* waveform via WebAudio */
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const src = ctx.createMediaStreamSource(micStream);
    analyser  = ctx.createAnalyser();
    analyser.fftSize = 128;
    src.connect(analyser);
    const wf  = document.getElementById('waveform');
    if (wf) wf.classList.add('live');
    const data = new Uint8Array(analyser.frequencyBinCount);
    waveInt = setInterval(() => {
      analyser.getByteTimeDomainData(data);
      const bars = document.querySelectorAll('.wbar');
      bars.forEach((bar, i) => {
        const v = (data[Math.floor(i * data.length / BARS)] - 128) / 128;
        bar.style.height = Math.max(4, Math.abs(v) * 38) + 'px';
      });
    }, 70);
  } catch(e) { /* no waveform on unsupported browsers */ }
}

function stopRecording(keep) {
  clearInterval(recInt);
  clearInterval(waveInt);
  waveInt = null;
  if (mediaRecorder && isRecording) {
    try { mediaRecorder.stop(); } catch(e) { /**/ }
  }
  if (micStream) { micStream.getTracks().forEach(t => t.stop()); micStream = null; }
  isRecording = false;
  if (!keep) recordedBlob = null;

  const btn = document.getElementById('btn-rec');
  const st  = document.getElementById('rec-status');
  const wf  = document.getElementById('waveform');
  if (btn) { btn.classList.remove('on'); btn.textContent = '\uD83C\uDF9D'; }
  if (st)  st.textContent = keep && recordedBlob ? 'Voice saved \u2713' : 'Tap to record';
  if (wf)  { wf.classList.remove('live'); wf.querySelectorAll('.wbar').forEach(b => b.style.height = '4px'); }
}

function finishVoice() { stopRecording(true); goTo(4); }
function skipVoice()   { stopRecording(false); goTo(4); }

/* ─────────── step 4: photo ─────────── */
async function openCamera() {
  if (camActive) return;
  const hint = document.getElementById('cam-hint');
  try {
    camStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 640 } }
    });
  } catch(err) {
    if (hint) hint.textContent = 'Camera blocked \u2014 use Upload instead.';
    return;
  }
  camActive = true;
  const vid = document.getElementById('cam-video');
  const ico = document.getElementById('cam-icon');
  if (vid) { vid.srcObject = camStream; vid.style.display = 'block'; }
  if (ico) ico.style.display = 'none';
  if (hint) hint.textContent = 'Tap the circle to take a photo';
}

function camTap() {
  if (!camActive) { openCamera(); return; }
  const vid    = document.getElementById('cam-video');
  const canvas = document.getElementById('cam-canvas');
  const snap   = document.getElementById('cam-snap');
  const hint   = document.getElementById('cam-hint');
  if (!vid || !canvas || !snap) return;

  const size = 480;
  canvas.width = size; canvas.height = size;
  const ctx = canvas.getContext('2d');
  ctx.save();
  ctx.translate(size, 0); ctx.scale(-1, 1);
  ctx.drawImage(vid, 0, 0, size, size);
  ctx.restore();

  canvas.toBlob(blob => {
    if (!blob) return;
    photoBlob = blob;
    const url = URL.createObjectURL(blob);
    snap.src = url;
    snap.style.display = 'block';
    if (vid) vid.style.display = 'none';
    if (hint) hint.textContent = 'Looking good! Tap Upload to change it.';
    if (camStream) { camStream.getTracks().forEach(t => t.stop()); camStream = null; camActive = false; }
  }, 'image/jpeg', 0.88);
}

function fileChosen(e) {
  const file = e.target.files && e.target.files[0];
  if (!file) return;
  photoBlob = file;
  const url = URL.createObjectURL(file);
  const snap = document.getElementById('cam-snap');
  const ico  = document.getElementById('cam-icon');
  const hint = document.getElementById('cam-hint');
  if (snap) { snap.src = url; snap.style.display = 'block'; }
  if (ico)  ico.style.display = 'none';
  if (hint) hint.textContent = 'Photo selected \u2713';
}

/* ─────────── step 5: finish ─────────── */
async function finishSetup() {
  stopRecording(true);
  if (camStream) { camStream.getTracks().forEach(t => t.stop()); camStream = null; }
  goTo(5);

  const tagEl  = document.getElementById('inp-tagline');
  const tagline = tagEl ? tagEl.value.trim() : '';

  try {
    await fetch('/api/onboard/profile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: userName, tagline,
        tone: selectedTone, humor: selectedHumor, length: selectedLength
      })
    });
  } catch(e) { /* offline \u2014 continue */ }

  if (recordedBlob) {
    try {
      const ext  = recordedBlob.type.includes('ogg') ? 'ogg' : recordedBlob.type.includes('mp4') ? 'm4a' : 'webm';
      const form = new FormData();
      form.append('file', recordedBlob, 'voice.' + ext);
      await fetch('/api/onboard/voice-sample', { method: 'POST', body: form });
    } catch(e) { /* ignore */ }
  }

  if (photoBlob) {
    try {
      const ext  = photoBlob.type === 'image/png' ? 'png' : 'jpg';
      const form = new FormData();
      form.append('file', photoBlob, 'photo.' + ext);
      await fetch('/api/onboard/photo', { method: 'POST', body: form });
    } catch(e) { /* ignore */ }
  }

  localStorage.setItem('pia_onboarded', '1');
  showReady();
}

function showReady() {
  const savEl   = document.getElementById('saving-view');
  const readyEl = document.getElementById('ready-view');
  const av      = document.getElementById('ready-av');
  const img     = document.getElementById('ready-img');
  const init    = document.getElementById('ready-init');
  const h1      = document.getElementById('ready-h1');

  if (savEl) savEl.style.display = 'none';
  if (readyEl) { readyEl.style.display = 'flex'; }

  const name = userName || 'there';
  if (h1)   h1.textContent = name + ', your twin is ready.';
  if (init) init.textContent = name.charAt(0).toUpperCase();

  if (photoBlob && img) {
    img.src = URL.createObjectURL(photoBlob);
    img.style.display = 'block';
    if (init) init.style.display = 'none';
  }
}

function startFirstCall() {
  window.location.href = '/';
}
