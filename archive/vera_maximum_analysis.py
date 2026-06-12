
def reidentification_test(stations_dp):
    names = list(stations_dp.keys())
    correct = 0
    total = 0
    for i in range(len(names)):
        for j in range(i+1, len(names)):
            a, b = names[i], names[j]
            sa, sb = stations_dp[a], stations_dp[b]
            dist = math.sqrt(
                (sa["bass"]-sb["bass"])**2 +
                (sa["mid"]-sb["mid"])**2 +
                (sa["treble"]-sb["treble"])**2
            )
            if dist > 0.05:
                correct += 1
            total += 1
    return round(correct/total, 4) if total > 0 else 0.0

#!/usr/bin/env python3
"""
VERA — Maximum Analysis Radio France v2
FFT precalculee + ZCR + visualisation + DP optimisee
"""

import os, json, math
import numpy as np
from datetime import datetime

OUTPUT_DIR = "/tmp/vera_radio"
SAMPLE_RATE = 44100
CHUNK_SIZE = SAMPLE_RATE * 60

def read_raw_chunks(path, chunk_size=CHUNK_SIZE):
    chunks = []
    with open(path, 'rb') as f:
        while True:
            data = np.frombuffer(f.read(chunk_size * 4), dtype=np.float32)
            if len(data) < 1000:
                break
            data = data[np.isfinite(data)]
            if len(data) > 512:
                chunks.append(data)
    return chunks

def precompute_fft(chunk, sr=SAMPLE_RATE):
    """Precalcule FFT une seule fois par chunk"""
    win = np.hanning(len(chunk))
    fft_vals = np.abs(np.fft.rfft(chunk * win)) * 2
    freqs = np.fft.rfftfreq(len(chunk), 1/sr)
    return fft_vals, freqs

def band_energy(fft_vals, freqs, low_hz, high_hz):
    mask = (freqs >= low_hz) & (freqs < high_hz)
    return float(np.mean(fft_vals[mask])) if np.any(mask) else 0.0

def normalize(b, m, t):
    total = b + m + t
    if total == 0:
        return 0.0, 0.0, 0.0
    return b/total, m/total, t/total

def spectral_entropy(fft_vals):
    power = fft_vals ** 2
    power = power / (np.sum(power) + 1e-10)
    return round(float(-np.sum(power * np.log2(power + 1e-10))), 4)

def zero_crossing_rate(chunk):
    """ZCR — detectionparole vs musique"""
    return round(float(np.mean(np.abs(np.diff(np.sign(chunk)))) / 2), 4)

def spectral_fingerprint(fft_vals, freqs, n_bins=32):
    max_freq = 20000
    bins = np.linspace(0, max_freq, n_bins + 1)
    fp = []
    for i in range(n_bins):
        mask = (freqs >= bins[i]) & (freqs < bins[i+1])
        fp.append(float(np.mean(fft_vals[mask])) if np.any(mask) else 0.0)
    total = sum(fp) + 1e-10
    return [round(v/total, 6) for v in fp]

def apply_dp_noise(signature, epsilon=1.0, seed=42):
    np.random.seed(seed)
    scale = 1.0 / epsilon
    return {
        "bass": round(float(np.clip(signature["bass"] + np.random.laplace(0, scale/10), 0, 1)), 4),
        "mid": round(float(np.clip(signature["mid"] + np.random.laplace(0, scale/10), 0, 1)), 4),
        "treble": round(float(np.clip(signature["treble"] + np.random.laplace(0, scale/10), 0, 1)), 4)
    }

def analyze_station_full(name, path):
    print(f"  Analyse {name}...")
    chunks = read_raw_chunks(path)
    if not chunks:
        return None

    signatures = []
    entropies = []
    zcr_vals = []
    fingerprints = []

    for chunk in chunks:
        try:
            fft_vals, freqs = precompute_fft(chunk)
            b = band_energy(fft_vals, freqs, 20, 250)
            m = band_energy(fft_vals, freqs, 250, 4000)
            t = band_energy(fft_vals, freqs, 4000, 20000)
            b, m, t = normalize(b, m, t)
            signatures.append({"bass": round(b,4), "mid": round(m,4), "treble": round(t,4)})
            entropies.append(spectral_entropy(fft_vals))
            zcr_vals.append(zero_crossing_rate(chunk))
            fingerprints.append(spectral_fingerprint(fft_vals, freqs))
        except Exception:
            continue

    if not signatures:
        return None

    bass_vals = [s["bass"] for s in signatures]
    mid_vals = [s["mid"] for s in signatures]
    treble_vals = [s["treble"] for s in signatures]
    mean_fp = [round(float(np.mean([fp[i] for fp in fingerprints])), 6) for i in range(32)]

    hourly = {}
    for h in range(0, len(signatures), 60):
        hour_sigs = signatures[h:h+60]
        if hour_sigs:
            label = f"hour_{h//60 + 1}"
            hourly[label] = {
                "bass": round(float(np.mean([s["bass"] for s in hour_sigs])), 4),
                "mid": round(float(np.mean([s["mid"] for s in hour_sigs])), 4),
                "treble": round(float(np.mean([s["treble"] for s in hour_sigs])), 4)
            }

    transitions = sum(1 for i in range(1, len(signatures))
                     if abs(signatures[i]["bass"] - signatures[i-1]["bass"]) > 0.05)

    return {
        "mean": {
            "bass": round(float(np.mean(bass_vals)), 4),
            "mid": round(float(np.mean(mid_vals)), 4),
            "treble": round(float(np.mean(treble_vals)), 4)
        },
        "variance": {
            "bass": round(float(np.var(bass_vals)), 6),
            "mid": round(float(np.var(mid_vals)), 6),
            "treble": round(float(np.var(treble_vals)), 6)
        },
        "spectral_entropy_mean": round(float(np.mean(entropies)), 4),
        "zcr_mean": round(float(np.mean(zcr_vals)), 4),
        "speech_music_ratio": round(float(np.mean([s["mid"] for s in signatures])) /
                                   (float(np.mean([s["bass"] for s in signatures])) + 1e-10), 4),
        "transitions_count": transitions,
        "spectral_fingerprint_32d": mean_fp,
        "hourly_evolution": hourly,
        "temporal_evolution": signatures[:10],
        "chunks_analyzed": len(signatures),
        "duration_minutes": len(signatures),
        "stability_score": round(1.0 - float(np.mean([
            np.var(bass_vals), np.var(mid_vals), np.var(treble_vals)
        ])) * 100, 4)
    }

def main():
    print("="*60)
    print("VERA — Maximum Analysis Radio France v2")
    print(f"Date : {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*60)
    files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.raw')]
    if not files:
        print("Aucun fichier .raw dans", OUTPUT_DIR)
        return
    stations = {}
    for f in sorted(files):
        name = f.replace('.raw', '')
        result = analyze_station_full(name, os.path.join(OUTPUT_DIR, f))
        if result:
            stations[name] = result
    distances = {}
    names = list(stations.keys())
    for i in range(len(names)):
        for j in range(i+1, len(names)):
            a, b = names[i], names[j]
            key = f"{a}vs{b}"
            sa, sb = stations[a]["mean"], stations[b]["mean"]
            distances[key] = round(math.sqrt(
                (sa["bass"]-sb["bass"])**2 +
                (sa["mid"]-sb["mid"])**2 +
                (sa["treble"]-sb["treble"])**2
            ), 4)
    dp_signatures = {name: apply_dp_noise(data["mean"]) for name, data in stations.items()}
    reid_score = reidentification_test(dp_signatures)
    print("\nRESULTATS :")
    for name, data in stations.items():
        m = data["mean"]
        print(f"  {name:20} bass={m['bass']:.3f} mid={m['mid']:.3f} treble={m['treble']:.3f} entropie={data['spectral_entropy_mean']:.3f} zcr={data['zcr_mean']:.4f} stabilite={data['stability_score']:.4f}")
    print("\nDISTANCES :")
    for pair, dist in sorted(distances.items(), key=lambda x: -x[1]):
        print(f"  {pair:45} {dist:.4f}")
    print(f"\nRE-IDENTIFICATION APRES DP : {reid_score}")
    out = os.path.join(OUTPUT_DIR, "vera_maximum_report.json")
    report = {"capture_date": datetime.now().strftime('%Y-%m-%d'),
              "protocol": "VERA v3.1.1", "stations": stations,
              "distance_matrix": distances, "dp_signatures": dp_signatures,
              "reidentification_score": reid_score}
    with open(out, 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nRapport : {out}")
    print("="*60)






if __name__ == '__main__':
    main()
