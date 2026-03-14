/**
 * avatar.js — Audio-reactive avatar animation
 *
 * Config is loaded from /api/avatar/config (sourced from users/default/avatar.json).
 * All animation parameters are driven by that config — nothing is hardcoded here.
 *
 * Training hooks are present throughout for Phase 2 (facial expressions, head
 * movement, lip sync). Search for "TRAINING HOOK" to find them.
 *
 * Usage:
 *   const avatar = new AvatarAnimator();
 *   await avatar.init();                    // loads config from backend
 *   avatar.startSpeaking(audioElement);
 *   avatar.stopSpeaking();
 */

class AvatarAnimator {
  constructor() {
    this._cfg        = null;     // loaded from /api/avatar/config
    this._ctx        = null;
    this._analyser   = null;
    this._source     = null;
    this._rafId      = null;
    this._data       = null;
    this._lastHeight = 2;

    // DOM refs
    this._mouth     = document.getElementById('mouth');
    this._mouthWrap = document.getElementById('mouth-wrap');
    this._avatarEl  = document.querySelector('.call-avatar');

    // ── TRAINING HOOK: callback registry ─────────────────────────────────
    // Future training signals will fire these. Nothing calls them in MVP.
    this._trainingCallbacks = {
      onAmplitudeSample:    null,   // (amplitude: number, timestamp: ms) => void
      onExpressionTrigger:  null,   // (expression: string) => void
      onHeadMovement:       null,   // (pattern: string) => void
      onSpeakingMismatch:   null,   // (expected, actual) => void
    };
  }

  /**
   * Load avatar config from backend and apply CSS variables.
   * Call once before using the animator.
   */
  async init() {
    try {
      const res  = await fetch('/api/avatar/config');
      this._cfg  = await res.json();
      this._applyConfig(this._cfg);
      console.log('[avatar] Config loaded:', this._cfg);
    } catch (err) {
      console.warn('[avatar] Could not load config — using defaults:', err);
      this._cfg = this._defaultConfig();
    }
    return this;
  }

  /**
   * Start animating the avatar mouth for a given <audio> element.
   * @param {HTMLAudioElement} audioEl
   */
  startSpeaking(audioEl) {
    const cfg = this._cfg || this._defaultConfig();
    this._setSpeakingState(true);

    try {
      if (!this._ctx || this._ctx.state === 'closed') {
        this._ctx = new (window.AudioContext || window.webkitAudioContext)();
      }
      if (this._ctx.state === 'suspended') this._ctx.resume();

      if (this._source) { try { this._source.disconnect(); } catch (_) {} }

      this._analyser                      = this._ctx.createAnalyser();
      this._analyser.fftSize              = 256;
      this._analyser.smoothingTimeConstant = cfg.smoothing ?? 0.75;
      this._data                          = new Uint8Array(this._analyser.frequencyBinCount);

      this._source = this._ctx.createMediaElementSource(audioEl);
      this._source.connect(this._analyser);
      this._analyser.connect(this._ctx.destination);

      this._mouthMin = cfg.mouth_min_height ?? 2;
      this._mouthMax = cfg.mouth_max_height ?? 28;
      this._threshold = cfg.amplitude_threshold ?? 8;

      this._animate();

    } catch (err) {
      console.warn('[avatar] AudioContext failed — using fallback:', err);
      this._animateFallback();
    }
  }

  /** Stop speaking animation and reset mouth to closed. */
  stopSpeaking() {
    this._setSpeakingState(false);
    cancelAnimationFrame(this._rafId);
    this._rafId = null;
    this._setMouth(this._mouthMin ?? 2, 'closed');

    if (this._source) {
      try { this._source.disconnect(); } catch (_) {}
      this._source = null;
    }
  }

  /**
   * Register a training signal callback.
   * Called by future training UI — no-op in MVP.
   *
   * @param {'onAmplitudeSample'|'onExpressionTrigger'|'onHeadMovement'|'onSpeakingMismatch'} event
   * @param {Function} callback
   */
  onTrainingSignal(event, callback) {
    if (event in this._trainingCallbacks) {
      this._trainingCallbacks[event] = callback;
    }
  }

  // ── Private ─────────────────────────────────────────────────────────────────

  _animate() {
    this._rafId = requestAnimationFrame(() => this._animate());
    this._analyser.getByteFrequencyData(this._data);

    // Voice frequency range (~85Hz–3400Hz maps to 20%–80% of FFT bins)
    const start = Math.floor(this._data.length * 0.2);
    const end   = Math.floor(this._data.length * 0.8);
    let sum = 0;
    for (let i = start; i < end; i++) sum += this._data[i];
    const avg = sum / (end - start);

    // ── TRAINING HOOK: amplitude sample ────────────────────────────────────
    if (this._trainingCallbacks.onAmplitudeSample) {
      this._trainingCallbacks.onAmplitudeSample(avg, Date.now());
    }

    if (avg < this._threshold) {
      this._lastHeight = this._lerp(this._lastHeight, this._mouthMin, 0.2);
      this._setMouth(this._lastHeight, 'closed');
    } else {
      const t      = Math.min((avg - this._threshold) / (255 - this._threshold), 1);
      const target = this._mouthMin + t * (this._mouthMax - this._mouthMin);
      this._lastHeight = this._lerp(this._lastHeight, target, 0.35);
      this._setMouth(this._lastHeight, 'open');
    }

    // ── TRAINING HOOK: expression trigger (future: sentiment → expression) ──
    // if (this._trainingCallbacks.onExpressionTrigger) { ... }

    // ── TRAINING HOOK: head movement (future: speech phase → head tilt) ────
    // if (this._trainingCallbacks.onHeadMovement) { ... }
  }

  _animateFallback() {
    if (!this._mouth) return;
    this._mouth.style.animation = 'mouth-pulse .4s ease-in-out infinite alternate';
  }

  _setMouth(height, state) {
    if (!this._mouth) return;
    const h  = Math.round(height);
    const br = state === 'open' ? `${Math.round(h / 2)}px` : '99px';
    this._mouth.style.height       = `${h}px`;
    this._mouth.style.borderRadius = br;
  }

  _setSpeakingState(speaking) {
    // Drive the fullscreen pia-main speaking state (glow, mouth, brightness)
    document.querySelector('.pia-main')?.classList.toggle('speaking', speaking);

    // ── TRAINING HOOK: future lip-sync provider would be called here ─────────
    // if (speaking && this._cfg?.future?.lip_sync) { this._startLipSync(); }
  }

  /**
   * Apply avatar.json config as CSS custom properties and inline styles
   * so the frontend exactly matches what avatar.json specifies.
   */
  _applyConfig(cfg) {
    const root   = document.documentElement;
    const avatar = document.querySelector('.call-avatar');

    // Photo position
    const photos = document.querySelectorAll('#idle-photo, #call-photo');
    photos.forEach(img => {
      img.style.objectPosition = cfg.object_position || 'center top';
    });

    // ── TRAINING HOOK: future facial/body capability flags ─────────────────
    // if (cfg.future?.facial_expressions) { this._initExpressionEngine(); }
    // if (cfg.future?.head_movement)      { this._initHeadMovementEngine(); }
    // if (cfg.future?.lip_sync)           { this._initLipSyncEngine(); }

    window.__AVATAR_CONFIG__ = cfg;   // expose for debugging / future use
  }

  _defaultConfig() {
    return {
      smoothing: 0.75, mouth_min_height: 2, mouth_max_height: 28,
      amplitude_threshold: 8, idle_mode: 'breathe', idle_scale_min: 1.0,
      idle_scale_max: 1.012, idle_duration: 4, ring_color: 'rgba(52,199,89,0.35)',
      future: { facial_expressions: false, head_movement: false, lip_sync: false, body_language: false },
    };
  }

  _lerp(a, b, t) { return a + (b - a) * t; }
}

// Fallback CSS for when AudioContext is unavailable
(function() {
  const s = document.createElement('style');
  s.textContent = `
    @keyframes mouth-pulse {
      from { height: 3px;  border-radius: 99px; }
      to   { height: 18px; border-radius: 6px;  }
    }
  `;
  document.head.appendChild(s);
})();

window.AvatarAnimator = AvatarAnimator;
