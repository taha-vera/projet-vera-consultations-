function updateSignal(v) {
  document.getElementById('signal').textContent =
    v.toFixed(3);
}

function startSimulation() {
  document.getElementById('status').textContent =
    'SIMULATION MODE';

  setInterval(() => {
    const t = Date.now() / 1000;

    const s =
      0.45 +
      0.15 * Math.sin(t / 4) +
      0.05 * Math.random();

    updateSignal(
      Math.max(0, Math.min(1, s))
    );
  }, 120);
}

function openRadio() {
  window.open(
    'https://www.radiofrance.fr/fip',
    '_blank'
  );
}

window.openRadio = openRadio;

startSimulation();
