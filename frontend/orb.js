(function () {
  const canvas = document.getElementById('orb-canvas');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  const points = [];
  const totalPoints = 720;
  const goldenAngle = Math.PI * (3 - Math.sqrt(5));
  let state = 'idle';
  let inputAnalyser = null;
  let outputAnalyser = null;
  let inputData = null;
  let outputData = null;
  let rotation = 0;

  for (let index = 0; index < totalPoints; index += 1) {
    const y = 1 - (index / (totalPoints - 1)) * 2;
    const radius = Math.sqrt(1 - y * y);
    const theta = goldenAngle * index;
    points.push({ x: Math.cos(theta) * radius, y, z: Math.sin(theta) * radius, seed: Math.random() });
  }

  const palettes = {
    idle: { core: [82, 212, 255], glow: [65, 160, 205], speed: 0.0022, pulse: 0.9 },
    listening: { core: [104, 230, 255], glow: [72, 190, 210], speed: 0.0035, pulse: 1.15 },
    thinking: { core: [190, 150, 255], glow: [120, 90, 220], speed: 0.0065, pulse: 1.05 },
    speaking: { core: [235, 252, 255], glow: [104, 230, 255], speed: 0.005, pulse: 1.35 },
    alert: { core: [255, 202, 111], glow: [235, 145, 55], speed: 0.0048, pulse: 1.2 },
  };

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
    const palette = palettes[state] || palettes.idle;
    const audio = getAudioLevel();
    const breathe = 0.5 + Math.sin(time * 0.0015) * 0.5;
    const sphereRadius = width * (0.295 + audio * 0.045 + breathe * 0.01);

    rotation += palette.speed + audio * 0.008;
    ctx.clearRect(0, 0, width, height);
    ctx.globalCompositeOperation = 'lighter';

    const bloom = ctx.createRadialGradient(center, center, 0, center, center, width * 0.36);
    bloom.addColorStop(0, `rgba(${palette.glow.join(',')},${0.13 + audio * 0.12})`);
    bloom.addColorStop(0.45, `rgba(${palette.glow.join(',')},${0.045 + breathe * 0.035})`);
    bloom.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = bloom;
    ctx.beginPath();
    ctx.arc(center, center, width * 0.37, 0, Math.PI * 2);
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
      const size = 0.62 + depth * 1.55 + audio * 1.25;
      const alpha = (0.08 + depth * 0.66) * palette.pulse * (0.82 + point.seed * 0.25);
      const px = center + x1 * sphereRadius;
      const py = center + y1 * sphereRadius;

      ctx.fillStyle = `rgba(${palette.core.join(',')},${Math.min(1, alpha)})`;
      ctx.beginPath();
      ctx.arc(px, py, size, 0, Math.PI * 2);
      ctx.fill();
    }

    ctx.globalCompositeOperation = 'source-over';
    if (state === 'idle') {
      ctx.fillStyle = `rgba(255,255,255,${0.02 + breathe * 0.02})`;
      for (let y = 0; y < height; y += 5) ctx.fillRect(0, y, width, 1);
    }

    requestAnimationFrame(draw);
  }

  window.PiaOrb = {
    setState(nextState) { state = nextState || 'idle'; },
    connectInputStream(stream) { connectAnalyserFromStream(stream); },
    connectOutputElement(audioEl) { connectAnalyserFromElement(audioEl); },
  };

  requestAnimationFrame(draw);
})();
