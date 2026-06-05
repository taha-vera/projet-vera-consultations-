#!/usr/bin/env python3
import json, math, numpy as np
from datetime import datetime

def add_laplace_noise(value, epsilon, seed=42):
    np.random.seed(seed)
    noise = np.random.laplace(0, 1.0/epsilon)
    return float(np.clip(value + noise, 0.0, 1.0))

def generate_dp_signatures(stations, epsilon, seed=42):
    dp = {}
    for name, sig in stations.items():
        np.random.seed(seed + hash(name) % 1000)
        dp[name] = {
            "bass": add_laplace_noise(sig["bass"], epsilon, seed),
            "mid": add_laplace_noise(sig["mid"], epsilon, seed+1),
            "treble": add_laplace_noise(sig["treble"], epsilon, seed+2)
        }
    return dp

def separability_score(dp_stations, threshold=0.05):
    names = list(dp_stations.keys())
    correct = 0
    total = 0
    for i in range(len(names)):
        for j in range(i+1, len(names)):
            sa, sb = dp_stations[names[i]], dp_stations[names[j]]
            dist = math.sqrt(
                (sa["bass"]-sb["bass"])**2 +
                (sa["mid"]-sb["mid"])**2 +
                (sa["treble"]-sb["treble"])**2
            )
            if dist > threshold:
                correct += 1
            total += 1
    return round(correct/total, 4) if total > 0 else 0.0

stations_mean = {
    "fip":            {"bass": 0.837, "mid": 0.143, "treble": 0.021},
    "france-culture": {"bass": 0.688, "mid": 0.274, "treble": 0.038},
    "france-info":    {"bass": 0.735, "mid": 0.245, "treble": 0.019},
    "france-inter":   {"bass": 0.802, "mid": 0.174, "treble": 0.024},
    "france-musique": {"bass": 0.783, "mid": 0.198, "treble": 0.018},
    "mouv":           {"bass": 0.817, "mid": 0.149, "treble": 0.035}
}

print("="*50)
print("VERA — Privacy-Utility Tradeoff")
print(f"Date : {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print("="*50)

results = {}
for eps in [2.0, 1.0, 0.5, 0.1]:
    scores = [separability_score(generate_dp_signatures(stations_mean, eps, seed=42+r)) for r in range(20)]
    mean_s = round(float(np.mean(scores)), 4)
    std_s = round(float(np.std(scores)), 4)
    results[str(eps)] = {"separability_score": mean_s, "std": std_s}
    print(f"  epsilon={eps:.1f} : {mean_s:.4f} (±{std_s:.4f})")

output = {
    "date": datetime.now().strftime('%Y-%m-%d'),
    "protocol": "VERA v3.1.1",
    "metric": "separability_score",
    "definition": "proportion of station pairs with euclidean distance > 0.05 after DP noise",
    "threshold": 0.05,
    "epsilons": results
}

with open("results/separability_scores.json", 'w') as f:
    json.dump(output, f, indent=2)

print("\nRapport : results/separability_scores.json")
print("="*50)
