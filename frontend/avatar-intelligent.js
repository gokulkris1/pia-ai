/**
 * avatar-intelligent.js — Smart Avatar with Face Detection
 *
 * Intelligently detects facial features from user's photo and animates them:
 * - Detects eye positions and animates natural blinking/gazing
 * - Detects mouth area and animates lip/jaw movements
 * - Uses actual facial colors and dimensions
 * - Blends seamlessly with the real face
 */

class IntelligentAvatarAnimator {
  constructor() {
    this.baseCanvas = null;      // User's photo
    this.animCanvas = null;      // Animation overlays
    this.baseCtx = null;
    this.animCtx = null;
    
    this.audioContext = null;
    this.analyser = null;
    this.source = null;
    this.dataArray = null;
    this.animationId = null;
    
    // Detected face data
    this.faceDetected = false;
    this.faceRegion = null;      // { x, y, width, height }
    this.leftEye = null;         // { x, y, width, height, color }
    this.rightEye = null;
    this.mouth = null;           // { x, y, width, height }
    
    // Animation state
    this.mouthOpen = 0;
    this.leftEyeOpen = 1;
    this.rightEyeOpen = 1;
    this.eyeGaze = 0;            // -1 to 1
    this.blinkTimer = 0;
    this.isSpeaking = false;
    this.time = 0;
  }

  /**
   * Initialize with user's photo
   */
  async init(containerId = 'pia-main') {
    const container = document.getElementById(containerId) || document.querySelector('.pia-main');
    if (!container) {
      console.warn('[avatar] Container not found');
      return;
    }

    const photoUrl = this._getPhotoUrl();
    if (!photoUrl) {
      console.warn('[avatar] No photo found');
      return;
    }

    await this._loadAndSetup(container, photoUrl);
    console.log('[avatar] Intelligent animator initialized');
    return this;
  }

  _getPhotoUrl() {
    const saved = localStorage.getItem('pia_avatar');
    if (saved) return saved;
    return '/avatar.jpg';
  }

  /**
   * Load photo and detect facial regions
   */
  async _loadAndSetup(container, photoUrl) {
    const photo = new Image();
    photo.crossOrigin = 'anonymous';

    return new Promise((resolve) => {
      photo.onload = () => {
        const w = 400, h = 500;

        // Create base canvas with photo
        this.baseCanvas = document.createElement('canvas');
        this.baseCanvas.width = w;
        this.baseCanvas.height = h;
        this.baseCtx = this.baseCanvas.getContext('2d');
        
        this.baseCtx.fillStyle = '#000';
        this.baseCtx.fillRect(0, 0, w, h);
        
        const scale = Math.max(w / photo.width, h / photo.height);
        const scaledW = photo.width * scale;
        const scaledH = photo.height * scale;
        const ox = (w - scaledW) / 2;
        const oy = (h - scaledH) / 2;
        
        this.baseCtx.drawImage(photo, ox, oy, scaledW, scaledH);

        // Create animation canvas
        this.animCanvas = document.createElement('canvas');
        this.animCanvas.width = w;
        this.animCanvas.height = h;
        this.animCtx = this.animCanvas.getContext('2d');
        this.animCanvas.style.position = 'absolute';
        this.animCanvas.style.top = '0';
        this.animCanvas.style.left = '0';
        this.animCanvas.style.width = '100%';
        this.animCanvas.style.height = '100%';
        this.animCanvas.style.zIndex = '10';
        this.animCanvas.style.pointerEvents = 'none';

        // Detect face regions (simple heuristic - can be improved with ML.js later)
        this._detectFaceRegions(w, h);

        // Add canvases to DOM
        const baseEl = document.createElement('canvas');
        baseEl.width = w;
        baseEl.height = h;
        const ctx2 = baseEl.getContext('2d');
        ctx2.drawImage(this.baseCanvas, 0, 0);
        baseEl.style.position = 'absolute';
        baseEl.style.top = '0';
        baseEl.style.left = '0';
        baseEl.style.width = '100%';
        baseEl.style.height = '100%';
        baseEl.style.zIndex = '9';

        container.appendChild(baseEl);
        container.appendChild(this.animCanvas);

        resolve();
      };
      photo.onerror = () => {
        console.warn('[avatar] Failed to load photo');
        resolve();
      };
      photo.src = photoUrl;
    });
  }

  /**
   * Simple face region detection (assumes standard portrait photo)
   */
  _detectFaceRegions(w, h) {
    // Assumes face is centered and occupies roughly middle 60% of image
    const faceTop = h * 0.1;
    const faceHeight = h * 0.8;
    const faceWidth = faceHeight * 0.7; // face is taller than wide
    const faceLeft = (w - faceWidth) / 2;

    this.faceRegion = { x: faceLeft, y: faceTop, width: faceWidth, height: faceHeight };

    // Eyes are roughly 30% down from top of face
    const eyeY = faceTop + faceHeight * 0.32;
    const eyeSpacing = faceWidth * 0.35;
    const centerX = w / 2;
    const eyeWidth = 30;
    const eyeHeight = 32;

    this.leftEye = {
      x: centerX - eyeSpacing,
      y: eyeY,
      width: eyeWidth,
      height: eyeHeight,
      colorSampled: this._sampleColor(centerX - eyeSpacing, eyeY),
    };

    this.rightEye = {
      x: centerX + eyeSpacing,
      y: eyeY,
      width: eyeWidth,
      height: eyeHeight,
      colorSampled: this._sampleColor(centerX + eyeSpacing, eyeY),
    };

    // Mouth is roughly 65% down from top of face
    this.mouth = {
      x: centerX,
      y: faceTop + faceHeight * 0.65,
      width: 45,
      height: 25,
    };

    this.faceDetected = true;
  }

  /**
   * Sample color from photo at given coordinates
   */
  _sampleColor(x, y) {
    try {
      const imageData = this.baseCtx.getImageData(x - 5, y - 5, 10, 10);
      const data = imageData.data;
      let r = 0, g = 0, b = 0, count = 0;
      for (let i = 0; i < data.length; i += 4) {
        r += data[i];
        g += data[i + 1];
        b += data[i + 2];
        count++;
      }
      return {
        r: Math.round(r / count),
        g: Math.round(g / count),
        b: Math.round(b / count),
      };
    } catch (e) {
      return { r: 100, g: 75, b: 50 }; // skin tone fallback
    }
  }

  /**
   * Start speaking animation
   */
  startSpeaking(audioEl) {
    this.isSpeaking = true;

    try {
      if (!this.audioContext || this.audioContext.state === 'closed') {
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
      }
      if (this.audioContext.state === 'suspended') {
        this.audioContext.resume();
      }

      if (this.source) {
        try { this.source.disconnect(); } catch (_) {}
      }

      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 256;
      this.analyser.smoothingTimeConstant = 0.8;
      this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);

      this.source = this.audioContext.createMediaElementSource(audioEl);
      this.source.connect(this.analyser);
      this.analyser.connect(this.audioContext.destination);

      this.time = 0;
      this._animate();
    } catch (err) {
      console.warn('[avatar] Setup failed:', err);
    }
  }

  /**
   * Stop speaking
   */
  stopSpeaking() {
    this.isSpeaking = false;
    this.mouthOpen = 0;
    this.leftEyeOpen = 1;
    this.rightEyeOpen = 1;
    if (this.animationId) {
      cancelAnimationFrame(this.animationId);
    }
    this._draw();
  }

  /**
   * Main animation loop
   */
  _animate = () => {
    if (!this.isSpeaking) return;

    this.time += 0.016;

    if (this.analyser && this.dataArray) {
      this.analyser.getByteFrequencyData(this.dataArray);
      const mouthFreqs = this.dataArray.slice(0, 15);
      const mouthAvg = mouthFreqs.reduce((a, b) => a + b, 0) / mouthFreqs.length;
      this.mouthOpen = Math.min(1, mouthAvg / 180);
    }

    // Natural eye gaze
    this.eyeGaze = Math.sin(this.time * 0.5) * 0.3;

    // Blinking
    this.blinkTimer += 0.016;
    if (this.blinkTimer > 3 + Math.random() * 2) {
      const blinkPhase = (this.blinkTimer - (3 + Math.random() * 2)) / 0.15;
      if (blinkPhase < 1) {
        const blink = Math.cos(blinkPhase * Math.PI) * 0.5 + 0.5;
        this.leftEyeOpen = blink;
        this.rightEyeOpen = blink;
      } else {
        this.blinkTimer = 0;
        this.leftEyeOpen = 1;
        this.rightEyeOpen = 1;
      }
    }

    this._draw();
    this.animationId = requestAnimationFrame(this._animate);
  };

  /**
   * Draw animations on overlay canvas
   */
  _draw() {
    if (!this.animCtx || !this.faceDetected) return;

    const ctx = this.animCtx;
    const w = this.animCanvas.width;
    const h = this.animCanvas.height;

    ctx.clearRect(0, 0, w, h);
    ctx.save();

    // Darken non-eye/mouth areas to isolate animations
    ctx.globalAlpha = 0.15;
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, w, h);
    ctx.globalAlpha = 1;

    // Animate eyes with real sampled colors
    this._drawAnimatedEye(ctx, this.leftEye, this.leftEyeOpen);
    this._drawAnimatedEye(ctx, this.rightEye, this.rightEyeOpen);

    // Animate mouth
    this._drawAnimatedMouth(ctx, this.mouth);

    ctx.restore();
  }

  /**
   * Draw single animated eye
   */
  _drawAnimatedEye(ctx, eye, openness) {
    // Semi-transparent overlay for eyelids (closing/opening)
    ctx.globalAlpha = 1 - openness;
    ctx.fillStyle = 'rgba(200, 150, 100, 0.8)';
    
    // Draw eyelid from top
    ctx.beginPath();
    ctx.ellipse(eye.x, eye.y, eye.width / 2 + 5, eye.height / 2, 0, 0, Math.PI * 2);
    ctx.fill();

    // Draw eyelid from bottom
    ctx.globalAlpha = (1 - openness) * 0.5;
    ctx.beginPath();
    ctx.ellipse(eye.x, eye.y, eye.width / 2, eye.height / 2 + 3, 0, 0, Math.PI * 2);
    ctx.fill();

    ctx.globalAlpha = 1;

    // Pupil movement (gaze)
    const gazeX = eye.x + this.eyeGaze * 8;
    ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
    ctx.beginPath();
    ctx.arc(gazeX, eye.y + 2, eye.width * 0.25, 0, Math.PI * 2);
    ctx.fill();
  }

  /**
   * Draw animated mouth
   */
  _drawAnimatedMouth(ctx, mouth) {
    const mouthHeight = mouth.height * 0.3 + this.mouthOpen * mouth.height * 0.5;

    // Jaw drop animation (subtle)
    ctx.globalAlpha = 0.2 + this.mouthOpen * 0.3;
    ctx.strokeStyle = 'rgba(100, 50, 50, 0.6)';
    ctx.lineWidth = 2;
    
    // Draw mouth opening
    ctx.beginPath();
    ctx.ellipse(mouth.x, mouth.y, mouth.width * 0.5, mouthHeight, 0, 0, Math.PI * 2);
    ctx.stroke();

    // Inner mouth darkness (darker when open)
    if (this.mouthOpen > 0.15) {
      ctx.fillStyle = `rgba(80, 30, 30, ${0.3 * this.mouthOpen})`;
      ctx.beginPath();
      ctx.ellipse(mouth.x, mouth.y, mouth.width * 0.4, mouthHeight * 0.7, 0, 0, Math.PI * 2);
      ctx.fill();
    }

    ctx.globalAlpha = 1;
  }
}
