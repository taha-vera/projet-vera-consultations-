import json,statistics
with open("results_stability.json") as f: data=json.load(f)
vals=[v["dp_mean"] for v in data["stations"].values()]
avg=statistics.mean(vals); std=statistics.stdev(vals)
for s,v in data["stations"].items():
    flag="ANOMALIE" if abs(v["dp_mean"]-avg)>2*std else "OK"
    print(f"{s}: {flag} dp_mean={v["dp_mean"]:.4f}")
