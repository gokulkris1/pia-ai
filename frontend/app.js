const API_BASE = window.PIA_API_BASE || '';
const STT_MODE = 'webspeech';

let state = 'idle';
let sessionId = null;
let recognition = null;
let recorder = null;
let recordedChunks = [];
let audioEl = null;
let activeMicStream = null;
let lastTranscript = '';

const els = {};

function setState(nextState) {
  state = nextState;
  const copy = {
    idle: ['tap to speak', 'pia is listening for you'],
    connecting: ['connecting', 'starting the voice loop'],
    listening: ['listening', 'say what you need'],
    thinking: ['thinking', 'routing through claude'],
    speaking: ['speaking', 'pia is talking back'],
    alert: ['needs attention', 'check permissions or try again'],
  }[nextState] || [nextState, ''];

  if (els.statusLine) els.statusLine.textContent = copy[0];
  if (els.statusSubline) els.statusSubline.textContent = copy[1];
  if (els.micButton) {
    els.micButton.className = `mic-action ${nextState}`;
    els.micButton.setAttribute('aria-label', nextState === 'idle' ? 'Start speaking' : 'Listening');
  }
  if (els.endButton) els.endButton.disabled = !sessionId;
  window.PiaOrb?.setState(nextState === 'thinking' ? 'thinking' : nextState);
}

async function toggleConversation() {
  if (!sessionId) {
    await startConversation();
    return;
  }

  if (state === 'idle') {
    startListening();
    return;
  }

  if (state === 'listening') {
    stopListening();
    setState('idle');
    return;
  }

  if (state === 'speaking') stopAudio();
}

async function startConversation() {
  setState('connecting');
  setTranscript('');

  try {
    await primeMicrophone();
    const res = await apiFetch('/api/call/start', 'POST');
    sessionId = res.session_id;
    setState('speaking');
    await piaSpeaks(res.greeting);
    if (state !== 'idle') startListening();
  } catch (err) {
    console.error('[start]', err);
    setTranscript(err.message || 'Could not start Pia.');
    setState('alert');
  }
}

async function endConversation() {
  stopListening();
  stopAudio();

  try {
    if (sessionId) await apiFetch(`/api/call/end/${sessionId}`, 'POST');
  } catch (err) {
    console.warn('[end]', err);
  }

  sessionId = null;
  lastTranscript = '';
  if (activeMicStream) {
    activeMicStream.getTracks().forEach((track) => track.stop());
    activeMicStream = null;
  }
  setTranscript('');
  setState('idle');
}

async function primeMicrophone() {
  if (!navigator.mediaDevices?.getUserMedia) throw new Error('Microphone is not available in this browser.');
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  window.PiaOrb?.connectInputStream(stream);
  activeMicStream = stream;
}

function startListening() {
  if (!sessionId) return;
  setState('listening');
  setTranscript('');

  const hasWebSpeech = 'SpeechRecognition' in window || 'webkitSpeechRecognition' in window;
  if (STT_MODE === 'webspeech' && hasWebSpeech) startWebSpeech();
  else startWhisperTurn();
}

function stopListening() {
  if (recognition) {
    recognition.onend = null;
    try { recognition.stop(); } catch (_) {}
    recognition = null;
  }
  if (recorder && recorder.state !== 'inactive') recorder.stop();
}

function startWebSpeech() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRecognition();
  recognition.lang = 'en-US';
  recognition.interimResults = true;
  recognition.continuous = false;
  recognition.maxAlternatives = 1;

  recognition.onresult = (event) => {
    let interim = '';
    let final = '';
    for (let index = event.resultIndex; index < event.results.length; index += 1) {
      const result = event.results[index];
      if (result.isFinal) final += result[0].transcript;
      else interim += result[0].transcript;
    }

    const text = (final || interim).trim();
    if (text) setTranscript(text);
    if (final.trim()) {
      lastTranscript = final.trim();
      processUserSpeech(lastTranscript);
    }
  };

  recognition.onerror = (event) => {
    if (event.error === 'no-speech' && state === 'listening') return;
    console.warn('[stt]', event.error);
    setTranscript('I missed that. Tap and try again.');
    setState('alert');
  };

  recognition.onend = () => {
    if (state === 'listening') {
      try { recognition.start(); } catch (_) {}
    }
  };

  recognition.start();
}

async function startWhisperTurn() {
  try {
    const stream = activeMicStream || await navigator.mediaDevices.getUserMedia({ audio: true });
    recordedChunks = [];
    recorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) recordedChunks.push(event.data);
    };
    recorder.onstop = async () => {
      const blob = new Blob(recordedChunks, { type: 'audio/webm' });
      const form = new FormData();
      form.append('file', blob, 'audio.webm');
      setState('thinking');
      setTranscript('transcribing');
      const response = await fetch(`${API_BASE}/api/transcribe`, { method: 'POST', body: form });
      const data = await response.json();
      if (data.transcript) await processUserSpeech(data.transcript);
      else startListening();
    };
    recorder.start();
    setTimeout(() => {
      if (recorder?.state !== 'inactive') recorder.stop();
    }, 9000);
  } catch (err) {
    console.error('[whisper]', err);
    setTranscript('Microphone access failed.');
    setState('alert');
  }
}

async function processUserSpeech(text) {
  if (!text?.trim() || !sessionId) return;
  stopListening();
  setState('thinking');
  setTranscript(`You: ${text}`);

  try {
    const chatRes = await apiFetch('/api/chat', 'POST', {
      session_id: sessionId,
      user_message: text.trim(),
    });
    await piaSpeaks(chatRes.reply);
    if (sessionId && state !== 'idle') startListening();
  } catch (err) {
    console.error('[chat]', err);
    setTranscript('Something went wrong. Tap to try again.');
    setState('alert');
  }
}

async function piaSpeaks(text) {
  setState('speaking');
  setTranscript(`Pia: ${text}`);

  try {
    const response = await fetch(`${API_BASE}/api/speak`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    if (!response.ok) throw new Error(`TTS failed (${response.status})`);

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    stopAudio();
    audioEl = new Audio(url);
    window.PiaOrb?.connectOutputElement(audioEl);

    await new Promise((resolve, reject) => {
      audioEl.onended = resolve;
      audioEl.onerror = reject;
      audioEl.play().catch(reject);
    });
  } catch (err) {
    console.error('[tts]', err);
  } finally {
    stopAudio();
  }
}

function stopAudio() {
  if (!audioEl) return;
  audioEl.pause();
  audioEl.removeAttribute('src');
  audioEl.load();
  audioEl = null;
}

function setTranscript(text) {
  if (els.transcript) els.transcript.textContent = text || '';
}

async function apiFetch(path, method = 'GET', body = null) {
  const options = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) options.body = JSON.stringify(body);
  const response = await fetch(`${API_BASE}${path}`, options);
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
  return response.json();
}

window.addEventListener('DOMContentLoaded', async () => {
  els.statusLine = document.getElementById('status-line');
  els.statusSubline = document.getElementById('status-subline');
  els.transcript = document.getElementById('transcript');
  els.micButton = document.getElementById('mic-button');
  els.endButton = document.getElementById('end-button');

  els.micButton?.addEventListener('click', toggleConversation);
  els.endButton?.addEventListener('click', endConversation);

  try {
    const health = await apiFetch('/api/health');
    if (els.statusSubline && health.user) els.statusSubline.textContent = `ready for ${health.user}`;
  } catch (_) {
    if (els.statusSubline) els.statusSubline.textContent = 'backend not connected yet';
  }

  setState('idle');
});
