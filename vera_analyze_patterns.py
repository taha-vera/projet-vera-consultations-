#!/usr/bin/env python3
import os, json, math, struct
import numpy as np
from datetime import datetime

OUTPUT_DIR = "/tmp/vera_radio"
SAMPLE_RATE = 44100
MAX_SAMPLES = SAMPLE_RATE * 60

def read_raw(path):
    with open(path, 'rb') as f:
        data = np.frombuffer(f.read(MAX_SAMPLES * 4), dtype=np.float32)
    return data[np.isfinite(data)]

def band_energy_fft(samples, low_hz, high_hz, sr=SAMPLE_RATE):
    if len(samples) < 512:
        return 0.0
    win = np.hanning(len(samples))
    fft_vals = np.abs(np.fft.rfft(samples * win)) * 2
    freqs = np.fft.rfftfreq(len(samples), 1/sr)
    mask = (freqs >= low_hz) & (freqs < high_hz)
    return float(np.mean(fft_vals[mask])) if np.any(mask) else 0.0

def normalize(b, m, t):
    total = b + m + t
    if total == 0:
        return 0.0, 0.0, 0.0
    return b/total, m/total, t/total

def analyze_station(name, path):
    print(f"  Analyse {name}...")
    try:
        samples = read_raw(path)
        if len(samples) < 1000:
            return None
        b = band_energy_fft(samples, 20, 250)
        m = band_energy_fft(samples, 250, 4000)
        t = band_energy_fft(samples, 4000, 20000)
        b, m, t = normalize(b, m, t)
        return {"bass": round(b,4), "mid": round(m,4), "treble": round(t,4),
                "samples": len(samples), "duration_s": round(len(samples)/SAMPLE_RATE,1),
                "signature": [round(b,4), round(m,4), round(t,4)]}
    except Exception as e:
        return {"error": str(e)}

def spectral_distance(a, b):
    return round(math.sqrt(sum((a["signature"][i]-b["signature"][i])**2 for i in range(3))), 4)

def main():
    print("="*60)
    print("VERA — Analyse Radio France (FFT + Hann)")
    print(f"Date : {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*60)
    files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.raw')]
    stations = {}
    for f in sorted(files):
        name = f.replace('.raw','')
        result = analyze_station(name, os.path.join(OUTPUT_DIR, f))
        if result and "error" not in result:
            stations[name] = result
    distances = {}
    names = list(stations.keys())
    for i in range(len(names)):
        for j in range(i+1, len(names)):
            a, b = names[i], names[j]
            distances[f"{a}vs{b}"] = spectral_distance(stations[a], stations[b])
    summary = {}
    if stations:
        summary = {
            "stations_analyzed": len(stations),
            "most_bass_heavy": max(stations, key=lambda k: stations[k]["bass"]),
            "most_speech_like": max(stations, key=lambda k: stations[k]["mid"]),
            "most_treble": max(stations, key=lambda k: stations[k]["treble"]),
        }
    report = {"capture_date": datetime.now().strftime('%Y-%m-%d'),
              "protocol": "VERA v3.1.1", "method": "FFT + Hann window",
              "stations": stations, "distance_matrix": distances, "summary": summary}
    out = os.path.join(OUTPUT_DIR, "vera_report.json")
    with open(out, 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print("\nRESULTATS :")
    for name, data in stations.items():
        print(f"  {name:20} bass={data['bass']:.3f} mid={data['mid']:.3f} treble={data['treble']:.3f}")
    if distances:
        max_pair = max(distances, key=distances.get)
        print(f"\nDistance max : {max_pair} = {distances[max_pair]}")
    print(f"\nRapport : {out}")
    print("="*60)

if __name__ == "__main__":
    main()
