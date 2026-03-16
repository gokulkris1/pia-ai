/**
 * Avatar Animator — Realistic Talking Head with Lip Sync
 *
 * Creates an animated talking head that reacts to audio input with:
 * - Real-time lip syncing based on audio frequencies
 * - Natural head movements (subtle bobbing, slight turns)
 * - Eye movements and blinking
 * - Scalp/jaw animations for natural speech
 *
 * Usage:
 *   const animator = new AvatarAnimator();
 *   animator.init(containerId);
 *   animator.startSpeaking(audioElement);
 *   animator.stopSpeaking();
 */

class AvatarAnimator {
  constructor() {
    this.canvas = null;
    this.ctx = null;
    this.audioContext = null;
    this.analyser = null;
    this.source = null;
    this.dataArray = null;
    this.animationId = null;
    
    // Avatar state
    this.mouthOpen = 0;        // 0-1 scale
    this.headRotation = 0;     // -0.1 to 0.1 radians
    this.eyeOpen = 1;          // 0-1 scale
    this.blinkTimer = 0;
    this.isSpeaking = false;
    this.time = 0;
    
    // Dimensions
    this.width = 400;
    this.height = 500;
    this.centerX = this.width / 2;
    this.centerY = this.height / 2;
  }

  /**
   * Initialize the animator and attach to DOM
   */
  init(containerId = 'pia-main') {
    return Promise.resolve().then(() => {
      const container = document.getElementById(containerId) || document.querySelector('.pia-main');
      if (!container) {
        console.warn('[avatar] Container not found');
        return;
      }

      // Create canvas
      this.canvas = document.createElement('canvas');
      this.canvas.width = this.width;
      this.canvas.height = this.height;
      this.canvas.style.position = 'absolute';
      this.canvas.style.top = '0';
      this.canvas.style.left = '0';
      this.canvas.style.width = '100%';
      this.canvas.style.height = '100%';
      this.canvas.style.zIndex = '10';
      this.canvas.style.pointerEvents = 'none';
      this.ctx = this.canvas.getContext('2d');

      // Insert before the avatar image so it overlays
      container.insertBefore(this.canvas, container.firstChild);
      console.log('[avatar] Initialized canvas animator');
      return this;
    });
  }

  /**
   * Start speaking animation with audio element
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

      // Clean up old connections
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
      console.warn('[avatar] AudioContext setup failed:', err);
    }
  }

  /**
   * Stop speaking animation
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

    this.time += 0.016; // ~60fps

    if (this.analyser && this.dataArray) {
      this.analyser.getByteFrequencyData(this.dataArray);
      
      // Compute mouth opening from low-mid frequencies (speech formants)
      const mouthFreqs = this.dataArray.slice(0, 15);  // Hz 0-600 range
      const mouthAvg = mouthFreqs.reduce((a, b) => a + b, 0) / mouthFreqs.length;
      this.mouthOpen = Math.min(1, mouthAvg / 180);

      // Head movement from overall energy
      const allFreqs = Array.from(this.dataArray);
      const totalEnergy = allFreqs.reduce((a, b) => a + b, 0) / allFreqs.length;
      this.headRotation = Math.sin(this.time * 1.5) * (totalEnergy / 255) * 0.08;
    }

    // Blink animation
    this.blinkTimer += 0.016;
    if (this.blinkTimer > 3 + Math.random() * 2) {
      // Blink for 0.15 seconds
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
   * Draw the avatar on canvas
   */
  _draw() {
    const ctx = this.ctx;
    const cx = this.centerX;
    const cy = this.centerY;

    // Clear canvas with transparency
    ctx.clearRect(0, 0, this.width, this.height);

    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(this.headRotation);
    ctx.translate(-cx, -cy);

    // Skin tone
    ctx.fillStyle = '#fdbcb4';

    // Head (oval)
    ctx.beginPath();
    ctx.ellipse(cx, cy - 20, 80, 110, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = '#d4a574';
    ctx.lineWidth = 1;
    ctx.stroke();

    // Eyes
    const eyeY = cy - 40;
    const eyeSpacing = 50;

    // Left eye
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.ellipse(cx - eyeSpacing, eyeY, 18, 22 * this.eyeOpen, 0, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = '#333333';
    ctx.beginPath();
    const leftIrisOffset = Math.sin(this.time * 0.8) * 5;
    ctx.arc(cx - eyeSpacing + leftIrisOffset, eyeY + 2, 10, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.arc(cx - eyeSpacing + leftIrisOffset + 3, eyeY - 1, 4, 0, Math.PI * 2);
    ctx.fill();

    // Right eye
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.ellipse(cx + eyeSpacing, eyeY, 18, 22 * this.eyeOpen, 0, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = '#333333';
    ctx.beginPath();
    const rightIrisOffset = Math.sin(this.time * 0.8) * 5;
    ctx.arc(cx + eyeSpacing + rightIrisOffset, eyeY + 2, 10, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.arc(cx + eyeSpacing + rightIrisOffset + 3, eyeY - 1, 4, 0, Math.PI * 2);
    ctx.fill();

    // Eyebrows
    ctx.strokeStyle = '#8b6f47';
    ctx.lineWidth = 3;
    ctx.lineCap = 'round';

    // Left eyebrow
    ctx.beginPath();
    ctx.moveTo(cx - eyeSpacing - 20, eyeY - 35);
    ctx.quadraticCurveTo(cx - eyeSpacing, eyeY - 42, cx - eyeSpacing + 20, eyeY - 35);
    ctx.stroke();

    // Right eyebrow
    ctx.beginPath();
    ctx.moveTo(cx + eyeSpacing - 20, eyeY - 35);
    ctx.quadraticCurveTo(cx + eyeSpacing, eyeY - 42, cx + eyeSpacing + 20, eyeY - 35);
    ctx.stroke();

    // Nose
    ctx.strokeStyle = '#d4a574';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(cx, eyeY + 15);
    ctx.lineTo(cx, cy + 10);
    ctx.stroke();

    ctx.beginPath();
    ctx.arc(cx - 6, cy + 10, 4, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.arc(cx + 6, cy + 10, 4, 0, Math.PI * 2);
    ctx.fill();

    // Mouth
    const mouthY = cy + 45;
    const mouthWidth = 45;
    const mouthHeight = 20 + this.mouthOpen * 35;

    // Outer mouth
    ctx.fillStyle = '#c85a65';
    ctx.beginPath();
    ctx.ellipse(cx, mouthY, mouthWidth, mouthHeight * 0.6, 0, 0, Math.PI * 2);
    ctx.fill();

    // Inner mouth (tongue/oral cavity)
    if (this.mouthOpen > 0.2) {
      ctx.fillStyle = '#8b3a3f';
      ctx.beginPath();
      ctx.ellipse(cx, mouthY + 5, mouthWidth * 0.7, mouthHeight * 0.4 * this.mouthOpen, 0, 0, Math.PI * 2);
      ctx.fill();
    }

    // Mouth outline
    ctx.strokeStyle = '#a84652';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.ellipse(cx, mouthY, mouthWidth, mouthHeight * 0.5, 0, 0, Math.PI * 2);
    ctx.stroke();

    // Cheeks (blush)
    ctx.fillStyle = 'rgba(255, 150, 150, 0.3)';
    ctx.beginPath();
    ctx.ellipse(cx - 50, cy + 10, 20, 15, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.ellipse(cx + 50, cy + 10, 20, 15, 0, 0, Math.PI * 2);
    ctx.fill();

    // Subtle emotion based on mouth openness
    if (this.mouthOpen > 0.7) {
      ctx.fillStyle = 'rgba(200, 200, 200, 0.1)';
      ctx.beginPath();
      ctx.ellipse(cx, cy - 20, 85, 115, 0, 0, Math.PI * 2);
      ctx.fill();
    }

    ctx.restore();
  }
}
