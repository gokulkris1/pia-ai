/**
 * avatar-realistic.js — Photorealistic Avatar
 *
 * Uses the user's actual photo from onboarding as the base face.
 * Overlays animated eyes, mouth, and expressions on top.
 * 
 * This creates a "talking version" of the user that actually looks like them.
 */

class RealisticAvatarAnimator {
  constructor() {
    this.photoCanvas = null;      // the user's photo as base
    this.overlayCanvas = null;    // overlay for animations
    this.photoCtx = null;
    this.overlayCtx = null;
    this.audioContext = null;
    this.analyser = null;
    this.source = null;
    this.dataArray = null;
    this.animationId = null;
    
    // Animation state
    this.mouthOpen = 0;           // 0-1
    this.eyeOpen = 1;             // 0-1
    this.blinkTimer = 0;
    this.isSpeaking = false;
    this.time = 0;
    
    // Face detection results (if available)
    this.faceData = null;         // { eyes: [...], mouth: {...}, bounds: {...} }
  }

  /**
   * Initialize with user's photo
   */
  async init(containerId = 'pia-main') {
    const container = document.getElementById(containerId) || document.querySelector('.pia-main');
    if (!container) {
      console.warn('[avatar-realistic] Container not found');
      return;
    }

    // Get user's photo
    const photoUrl = this._getPhotoUrl();
    if (!photoUrl) {
      console.warn('[avatar-realistic] No photo found, falling back to initials');
      return;
    }

    // Load photo and create canvas
    await this._loadPhotoAndSetupCanvas(container, photoUrl);
    console.log('[avatar-realistic] Initialized with user photo');
    return this;
  }

  /**
   * Get the user's photo URL (from localStorage or /avatar.jpg)
   */
  _getPhotoUrl() {
    const saved = localStorage.getItem('pia_avatar');
    if (saved) return saved;
    // Try default
    return '/avatar.jpg';
  }

  /**
   * Load photo and setup canvas overlays
   */
  async _loadPhotoAndSetupCanvas(container, photoUrl) {
    const photo = new Image();
    photo.crossOrigin = 'anonymous';
    
    return new Promise((resolve) => {
      photo.onload = () => {
        // Create base photo canvas
        this.photoCanvas = document.createElement('canvas');
        const width = 400;
        const height = 500;
        this.photoCanvas.width = width;
        this.photoCanvas.height = height;
        this.photoCtx = this.photoCanvas.getContext('2d');

        // Draw photo onto canvas (centered, cropped to face)
        this.photoCtx.fillStyle = '#000';
        this.photoCtx.fillRect(0, 0, width, height);
        
        const imgWidth = photo.width;
        const imgHeight = photo.height;
        const scale = Math.max(width / imgWidth, height / imgHeight);
        const scaledWidth = imgWidth * scale;
        const scaledHeight = imgHeight * scale;
        const offsetX = (width - scaledWidth) / 2;
        const offsetY = (height - scaledHeight) / 2;
        
        this.photoCtx.drawImage(photo, offsetX, offsetY, scaledWidth, scaledHeight);

        // Create overlay canvas for animations
        this.overlayCanvas = document.createElement('canvas');
        this.overlayCanvas.width = width;
        this.overlayCanvas.height = height;
        this.overlayCtx = this.overlayCanvas.getContext('2d');
        this.overlayCanvas.style.position = 'absolute';
        this.overlayCanvas.style.top = '0';
        this.overlayCanvas.style.left = '0';
        this.overlayCanvas.style.width = '100%';
        this.overlayCanvas.style.height = '100%';
        this.overlayCanvas.style.zIndex = '10';
        this.overlayCanvas.style.pointerEvents = 'none';

        // Also add photo canvas as base
        const photoCanvasElement = document.createElement('canvas');
        photoCanvasElement.width = width;
        photoCanvasElement.height = height;
        const photoCtx2 = photoCanvasElement.getContext('2d');
        photoCtx2.drawImage(this.photoCanvas, 0, 0);
        photoCanvasElement.style.position = 'absolute';
        photoCanvasElement.style.top = '0';
        photoCanvasElement.style.left = '0';
        photoCanvasElement.style.width = '100%';
        photoCanvasElement.style.height = '100%';
        photoCanvasElement.style.zIndex = '9';

        container.appendChild(photoCanvasElement);
        container.appendChild(this.overlayCanvas);

        resolve();
      };
      photo.onerror = () => {
        console.warn('[avatar-realistic] Failed to load photo');
        resolve();
      };
      photo.src = photoUrl;
    });
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
      console.warn('[avatar-realistic] Setup failed:', err);
    }
  }

  /**
   * Stop speaking
   */
  stopSpeaking() {
    this.isSpeaking = false;
    this.mouthOpen = 0;
    this.eyeOpen = 1;
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
      
      // Mouth from low-mid frequencies
      const mouthFreqs = this.dataArray.slice(0, 15);
      const mouthAvg = mouthFreqs.reduce((a, b) => a + b, 0) / mouthFreqs.length;
      this.mouthOpen = Math.min(1, mouthAvg / 180);
    }

    // Blink
    this.blinkTimer += 0.016;
    if (this.blinkTimer > 3 + Math.random() * 2) {
      const blinkPhase = (this.blinkTimer - (3 + Math.random() * 2)) / 0.15;
      if (blinkPhase < 1) {
        this.eyeOpen = Math.cos(blinkPhase * Math.PI) * 0.5 + 0.5;
      } else {
        this.blinkTimer = 0;
        this.eyeOpen = 1;
      }
    }

    this._draw();
    this.animationId = requestAnimationFrame(this._animate);
  };

  /**
   * Draw animated eyes and mouth on overlay
   */
  _draw() {
    if (!this.overlayCtx) return;

    const ctx = this.overlayCtx;
    const w = this.overlayCanvas.width;
    const h = this.overlayCanvas.height;

    // Clear overlay
    ctx.clearRect(0, 0, w, h);

    // Estimate face region (top-center area)
    const faceTop = h * 0.15;
    const faceBottom = h * 0.75;
    const faceHeight = faceBottom - faceTop;
    const centerX = w / 2;

    // Eye positions
    const eyeY = faceTop + faceHeight * 0.35;
    const eyeSpacing = 60;
    const eyeSize = 16;

    // Draw animated eyes
    ctx.save();
    
    // Left eye
    ctx.globalAlpha = 1;
    ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
    ctx.beginPath();
    ctx.ellipse(centerX - eyeSpacing, eyeY, eyeSize, eyeSize * this.eyeOpen, 0, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = 'rgba(0, 0, 0, 0.8)';
    ctx.beginPath();
    ctx.arc(centerX - eyeSpacing, eyeY + 1, eyeSize * 0.6, 0, Math.PI * 2);
    ctx.fill();

    // Right eye
    ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
    ctx.beginPath();
    ctx.ellipse(centerX + eyeSpacing, eyeY, eyeSize, eyeSize * this.eyeOpen, 0, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = 'rgba(0, 0, 0, 0.8)';
    ctx.beginPath();
    ctx.arc(centerX + eyeSpacing, eyeY + 1, eyeSize * 0.6, 0, Math.PI * 2);
    ctx.fill();

    // Mouth animation
    const mouthY = faceTop + faceHeight * 0.75;
    const mouthWidth = 50;
    const mouthHeight = 15 + this.mouthOpen * 30;

    ctx.strokeStyle = 'rgba(0, 0, 0, 0.5)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.ellipse(centerX, mouthY, mouthWidth, mouthHeight * 0.5, 0, 0, Math.PI * 2);
    ctx.stroke();

    // Mouth fill (inner)
    if (this.mouthOpen > 0.1) {
      ctx.fillStyle = 'rgba(150, 50, 50, 0.3)';
      ctx.beginPath();
      ctx.ellipse(centerX, mouthY + 2, mouthWidth * 0.8, mouthHeight * 0.3 * this.mouthOpen, 0, 0, Math.PI * 2);
      ctx.fill();
    }

    ctx.restore();
  }
}
