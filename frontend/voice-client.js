/*
 * Pia realtime voice client (Vapi / WebRTC).
 *
 * Active ONLY when the server config (GET /api/voice/config) reports
 * voiceMode === 'vapi' AND a public key is present — otherwise this stays
 * dormant and app.js runs the classic record → transcribe → chat → speak loop
 * (the runtime fallback, PIA_VOICE_MODE='classic').
 *
 * Decoupling: ears (STT) + mouth (TTS) are Vapi providers (Deepgram / ElevenLabs,
 * chosen via env in /api/voice/config). The BRAIN stays ours — Vapi's custom-LLM
 * points at /api/voice/llm → chooseModel() → Claude. This file only manages the
 * WebRTC session and maps Vapi events onto the orb states + transcript.
 */
(function () {
  let vapi = null;
  let enabled = false;
  let active = false;
  let cfg = null;
  let apiBase = '';
  let capTimer = null;
  const hooks = { onState: () => {}, onTranscript: () => {} };

  // Dev-only voice auditioning. Off unless ?voicedev=1 (or window.PIA_VOICE_DEV).
  // The chosen voice lives in sessionStorage only — transient, never persisted
  // server-side or per-user. The backend validates the id against a hardcoded
  // allow-list, so this can't point Pia at an arbitrary voice.
  function devEnabled() {
    try {
      const q = new URLSearchParams(window.location.search);
      return window.PIA_VOICE_DEV === true || q.get('voicedev') === '1';
    } catch (_) {
      return window.PIA_VOICE_DEV === true;
    }
  }

  function storedVoiceId() {
    try {
      return sessionStorage.getItem('piaVoiceId') || '';
    } catch (_) {
      return '';
    }
  }

  async function fetchConfig(voiceId) {
    const qs = voiceId ? `?voiceId=${encodeURIComponent(voiceId)}` : '';
    const res = await fetch(`${apiBase}/api/voice/config${qs}`);
    return res.json();
  }

  async function init(options = {}) {
    hooks.onState = options.onState || hooks.onState;
    hooks.onTranscript = options.onTranscript || hooks.onTranscript;
    apiBase = options.apiBase || '';

    try {
      cfg = await fetchConfig(devEnabled() ? storedVoiceId() : '');
    } catch (err) {
      console.warn('[vapi] config fetch failed — staying on classic mode', err);
      enabled = false;
      return false;
    }

    const mode = window.PIA_VOICE_MODE || cfg.voiceMode;
    if (mode !== 'vapi' || !cfg.publicKey) {
      enabled = false;
      return false;
    }

    try {
      const mod = await import('https://esm.sh/@vapi-ai/web@2');
      const Vapi = mod.default || mod.Vapi || window.Vapi;
      vapi = new Vapi(cfg.publicKey);
      wireEvents();
      enabled = true;
      if (devEnabled()) mountVoiceSwitcher();
      console.log('[vapi] realtime voice enabled');
      return true;
    } catch (err) {
      console.warn('[vapi] SDK load failed — staying on classic mode', err);
      enabled = false;
      return false;
    }
  }

  function wireEvents() {
    vapi.on('call-start', () => {
      active = true;
      armCap();
      hooks.onState('listening');
    });
    vapi.on('call-end', () => {
      active = false;
      clearCap();
      hooks.onState('idle');
    });
    // Vapi speech-start/end refer to the assistant talking.
    vapi.on('speech-start', () => hooks.onState('speaking'));
    vapi.on('speech-end', () => {
      if (active) hooks.onState('listening');
    });
    vapi.on('message', (msg) => {
      if (msg && msg.type === 'transcript' && msg.transcript) {
        const who = msg.role === 'assistant' ? 'Pia' : 'You';
        hooks.onTranscript(`${who}: ${msg.transcript}`);
      }
    });
    vapi.on('error', (err) => {
      console.error('[vapi] error', err);
      active = false;
      clearCap();
      hooks.onState('alert');
    });
  }

  // Client-side cost guardrail: auto-end if a session is left open. Vapi also
  // enforces maxDurationSeconds server-side via assistantOverrides.
  function armCap() {
    clearCap();
    const secs = Number(cfg && cfg.maxSessionSeconds) || 600;
    capTimer = setTimeout(() => {
      console.warn('[vapi] session length cap reached — ending call');
      stop();
    }, secs * 1000);
  }
  function clearCap() {
    if (capTimer) {
      clearTimeout(capTimer);
      capTimer = null;
    }
  }

  async function start() {
    if (!enabled || !vapi) return;
    hooks.onState('connecting');
    try {
      const overrides = cfg.assistantOverrides || {};
      if (cfg.assistantId) {
        await vapi.start(cfg.assistantId, { assistantOverrides: overrides });
      } else {
        // No assistant configured yet — overrides alone lack a model/brain.
        console.warn('[vapi] no assistantId configured; set VAPI_ASSISTANT_ID');
        await vapi.start(overrides);
      }
    } catch (err) {
      console.error('[vapi] start failed', err);
      active = false;
      hooks.onState('alert');
    }
  }

  async function stop() {
    clearCap();
    try {
      if (vapi) await vapi.stop();
    } catch (_) {
      /* ignore */
    }
    active = false;
    hooks.onState('idle');
  }

  function toggle() {
    return active ? stop() : start();
  }

  // Re-fetch config for the picked voice, then restart any live call so the new
  // voice is heard immediately (Vapi locks the voice in at call start).
  async function setVoice(voiceId) {
    try {
      sessionStorage.setItem('piaVoiceId', voiceId || '');
    } catch (_) {
      /* ignore */
    }
    try {
      cfg = await fetchConfig(voiceId);
    } catch (err) {
      console.warn('[vapi] voice switch config fetch failed', err);
      return;
    }
    if (active) {
      await stop();
      await start();
    }
  }

  function mountVoiceSwitcher() {
    if (document.getElementById('pia-voice-switcher')) return;
    const voices = (cfg && cfg.devVoices) || [];
    if (!voices.length) return;

    const wrap = document.createElement('div');
    wrap.id = 'pia-voice-switcher';
    wrap.style.cssText =
      'position:fixed;bottom:12px;left:12px;z-index:9999;display:flex;' +
      'align-items:center;gap:6px;padding:6px 10px;border-radius:10px;' +
      'background:rgba(20,20,28,.72);backdrop-filter:blur(8px);' +
      'font:12px system-ui,sans-serif;color:#cbd5e1;';

    const label = document.createElement('span');
    label.textContent = 'voice';
    label.style.opacity = '0.7';

    const select = document.createElement('select');
    select.style.cssText =
      'background:#0f0f16;color:#e2e8f0;border:1px solid #2a2a38;' +
      'border-radius:6px;padding:3px 6px;font:12px system-ui,sans-serif;';
    voices.forEach((v) => {
      const opt = document.createElement('option');
      opt.value = v.id;
      opt.textContent = v.label || v.id;
      if (cfg && cfg.voiceId === v.id) opt.selected = true;
      select.appendChild(opt);
    });
    select.addEventListener('change', () => setVoice(select.value));

    wrap.appendChild(label);
    wrap.appendChild(select);
    document.body.appendChild(wrap);
  }

  window.PiaVoice = {
    init,
    toggle,
    start,
    stop,
    setVoice,
    isEnabled: () => enabled,
    isActive: () => active,
  };
})();
