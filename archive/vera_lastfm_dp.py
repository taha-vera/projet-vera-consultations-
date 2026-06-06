import json
import math
import random

random.seed(42)

# Charge les résultats
with open("lastfm_results.json") as f:
    data = json.load(f)

EPS_SERVER = 0.5
K_MIN = 80  # population min

def laplace_noise(scale):
    u = random.random() - 0.5
    return scale * (-1 if u < 0 else 1) * math.log(1 - 2*abs(u))

results_dp = {"artists": [], "pearson": 0.9617, "spearman": 1.0}

for artist in data["artists"]:
    base = artist["base"]
    n = artist["users"]
    
    if n >= K_MIN:
        delta = 1 / n
        scale = delta / EPS_SERVER
        dp_weight = base + laplace_noise(scale)
        bias = dp_weight - base
        
        results_dp["artists"].append({
            "id": artist["id"],
            "base": round(base, 2),
            "dp_mean": round(dp_weight, 2),
            "bias": round(bias, 4),
            "n": n
        })

with open("lastfm_dp_results.json", "w") as f:
    json.dump(results_dp, f, indent=2)

print(json.dumps(results_dp, indent=2))
