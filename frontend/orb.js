(function () {
  const canvas = document.getElementById('orb-canvas');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  const points = [];
  const totalPoints = 980;
  const goldenAngle = Math.PI * (3 - Math.sqrt(5));
  let state = 'idle';
  let inputAnalyser = null;
  let outputAnalyser = null;
  let inputData = null;
  let outputData = null;
  let rotation = 0;
  let visualState = 'idle';
  let stateMix = 1;

  for (let index = 0; index < totalPoints; index += 1) {
    const y = 1 - (index / (totalPoints - 1)) * 2;
    const radius = Math.sqrt(1 - y * y);
    const theta = goldenAngle * index;
    points.push({ x: Math.cos(theta) * radius, y, z: Math.sin(theta) * radius, seed: Math.random() });
  }

  const palettes = {
    idle: { core: [120, 218, 232], glow: [58, 150, 178], speed: 0.0018, pulse: 0.9, spread: 0.292 },
    listening: { core: [134, 238, 232], glow: [72, 190, 186], speed: 0.0031, pulse: 1.12, spread: 0.304 },
    thinking: { core: [190, 156, 245], glow: [119, 92, 216], speed: 0.0056, pulse: 1.06, spread: 0.286 },
    speaking: { core: [245, 253, 252], glow: [119, 230, 229], speed: 0.0044, pulse: 1.32, spread: 0.318 },
    alert: { core: [255, 206, 118], glow: [232, 148, 65], speed: 0.004, pulse: 1.16, spread: 0.298 },
  };

  function mixPalette() {
    if (visualState === state) return palettes[state] || palettes.idle;
    stateMix = Math.min(1, stateMix + 0.055);
    const from = palettes[visualState] || palettes.idle;
    const to = palettes[state] || palettes.idle;
    if (stateMix >= 1) visualState = state;
    return {
      core: from.core.map((value, index) => value + (to.core[index] - value) * stateMix),
      glow: from.glow.map((value, index) => value + (to.glow[index] - value) * stateMix),
      speed: from.speed + (to.speed - from.speed) * stateMix,
      pulse: from.pulse + (to.pulse - from.pulse) * stateMix,
      spread: from.spread + (to.spread - from.spread) * stateMix,
    };
  }

  function connectAnalyserFromStream(stream) {
    try {
      const audioContext = new AudioContext();
      const source = audioContext.createMediaStreamSource(stream);
      inputAnalyser = audioContext.createAnalyser();
      inputAnalyser.fftSize = 256;
      source.connect(inputAnalyser);
      inputData = new Uint8Array(inputAnalyser.frequencyBinCount);
    } catch (err) {
      console.warn('[orb] input analyser failed', err);
    }
  }

  function connectAnalyserFromElement(audioEl) {
    try {
      const audioContext = new AudioContext();
      const source = audioContext.createMediaElementSource(audioEl);
      outputAnalyser = audioContext.createAnalyser();
      outputAnalyser.fftSize = 256;
      source.connect(outputAnalyser);
      outputAnalyser.connect(audioContext.destination);
      outputData = new Uint8Array(outputAnalyser.frequencyBinCount);
    } catch (_) {
      outputAnalyser = null;
      outputData = null;
    }
  }

  function getAudioLevel() {
    const analyser = state === 'speaking' ? outputAnalyser : inputAnalyser;
    const data = state === 'speaking' ? outputData : inputData;
    if (!analyser || !data) return 0;
    analyser.getByteFrequencyData(data);
    const sum = data.reduce((total, value) => total + value, 0);
    return Math.min(1, (sum / data.length) / 130);
  }

  function draw(time) {
    const width = canvas.width;
    const height = canvas.height;
    const center = width / 2;
    const palette = mixPalette();
    const audio = getAudioLevel();
    const breathe = 0.5 + Math.sin(time * 0.00125) * 0.5;
    const sphereRadius = width * (palette.spread + audio * 0.038 + breathe * 0.008);

    rotation += palette.speed + audio * 0.008;
    ctx.clearRect(0, 0, width, height);
    ctx.globalCompositeOperation = 'lighter';

    const bloom = ctx.createRadialGradient(center, center, width * 0.03, center, center, width * 0.38);
    bloom.addColorStop(0, `rgba(${palette.glow.map(Math.round).join(',')},${0.16 + audio * 0.12})`);
    bloom.addColorStop(0.42, `rgba(${palette.glow.map(Math.round).join(',')},${0.052 + breathe * 0.032})`);
    bloom.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = bloom;
    ctx.beginPath();
    ctx.arc(center, center, width * 0.39, 0, Math.PI * 2);
    ctx.fill();

    const lens = ctx.createRadialGradient(center, center, width * 0.1, center, center, width * 0.32);
    lens.addColorStop(0, 'rgba(255,255,255,0.035)');
    lens.addColorStop(0.58, 'rgba(255,255,255,0.012)');
    lens.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = lens;
    ctx.beginPath();
    ctx.arc(center, center, width * 0.31, 0, Math.PI * 2);
    ctx.fill();

    const sinY = Math.sin(rotation);
    const cosY = Math.cos(rotation);
    const sinX = Math.sin(rotation * 0.52);
    const cosX = Math.cos(rotation * 0.52);

    for (const point of points) {
      const x1 = point.x * cosY - point.z * sinY;
      const z1 = point.x * sinY + point.z * cosY;
      const y1 = point.y * cosX - z1 * sinX;
      const z2 = point.y * sinX + z1 * cosX;
      const depth = (z2 + 1) / 2;
      const size = 0.48 + depth * 1.32 + audio * 1.05;
      const alpha = (0.045 + depth * 0.72) * palette.pulse * (0.84 + point.seed * 0.24);
      const px = center + x1 * sphereRadius;
      const py = center + y1 * sphereRadius;

      ctx.fillStyle = `rgba(${palette.core.map(Math.round).join(',')},${Math.min(1, alpha)})`;
      ctx.beginPath();
      ctx.arc(px, py, size, 0, Math.PI * 2);
      ctx.fill();
    }

    ctx.globalCompositeOperation = 'source-over';

    requestAnimationFrame(draw);
  }

  window.PiaOrb = {
    setState(nextState) {
      const next = nextState || 'idle';
      if (next !== state) {
        visualState = state;
        stateMix = 0;
      }
      state = next;
    },
    connectInputStream(stream) { connectAnalyserFromStream(stream); },
    connectOutputElement(audioEl) { connectAnalyserFromElement(audioEl); },
  };

  requestAnimationFrame(draw);
})();
