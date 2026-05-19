var STREAMS = {
  fip: 'https://icecast.radiofrance.fr/fip-midfi.mp3',
  franceinter: 'https://icecast.radiofrance.fr/franceinter-midfi.mp3',
  franceculture: 'https://icecast.radiofrance.fr/franceculture-midfi.mp3',
  francemusique: 'https://icecast.radiofrance.fr/francemusique-midfi.mp3',
  mouv: 'https://icecast.radiofrance.fr/mouv-midfi.mp3',
  franceinfo: 'https://icecast.radiofrance.fr/franceinfo-midfi.mp3'
};

const audio = document.getElementById('audio');
const signal = document.getElementById('signal');
const status = document.getElementById('status');

let analyser = null;
let ctx = null;
let simulation = null;

function updateSignal(v) {
  signal.textContent = v.toFixed(3);
}

function startSimulation() {
  status.textContent = 'SIMULATION MODE';

  if (simulation) return;

  simulation = setInterval(() => {
    const t = Date.now() / 1000;

    const s =
      0.45 +
      0.15 * Math.sin(t / 4) +
      0.05 * Math.random();

    updateSignal(Math.max(0, Math.min(1, s)));
  }, 120);
}

function stopSimulation() {
  if (simulation) {
    clearInterval(simulation);
    simulation = null;
  }
}

async function startAudio(name) {
  stopSimulation();

  audio.src = STREAMS[name];

  try {
    if (!ctx) {
      ctx = new AudioContext();

      const src = ctx.createMediaElementSource(audio);

      analyser = ctx.createAnalyser();
      analyser.fftSize = 256;

      src.connect(analyser);
      analyser.connect(ctx.destination);
    }

    await audio.play();

    status.textContent = 'LIVE AUDIO';

    const data = new Uint8Array(analyser.frequencyBinCount);

    function tick() {
      if (audio.paused) return;

      analyser.getByteFrequencyData(data);

      let sum = 0;

      for (let i = 0; i < data.length; i++) {
        sum += data[i];
      }

      updateSignal((sum / data.length) / 255);

      requestAnimationFrame(tick);
    }

    tick();

  } catch (e) {
    console.log(e);
    startSimulation();
  }
}

audio.addEventListener('error', startSimulation);

window.startAudio = startAudio;
