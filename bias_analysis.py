import json
with open("results_stability.json") as f: data=json.load(f)
for s,v in data["stations"].items():
    print(f"{s}: biais={v["bias"]:.4f} dp_mean={v["dp_mean"]:.4f} base={v["base"]:.4f}")
