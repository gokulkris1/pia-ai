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
  let capTimer = null;
  const hooks = { onState: () => {}, onTranscript: () => {} };

  async function init(options = {}) {
    hooks.onState = options.onState || hooks.onState;
    hooks.onTranscript = options.onTranscript || hooks.onTranscript;
    const apiBase = options.apiBase || '';

    try {
      const res = await fetch(`${apiBase}/api/voice/config`);
      cfg = await res.json();
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

  window.PiaVoice = {
    init,
    toggle,
    start,
    stop,
    isEnabled: () => enabled,
    isActive: () => active,
  };
})();
