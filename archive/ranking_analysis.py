import json
with open("results_stability.json") as f: data=json.load(f)
ranked=sorted(data["stations"].items(),key=lambda x:x[1]["dp_mean"],reverse=True)
print("Classement par dp_mean:")
for i,(s,v) in enumerate(ranked,1): print(f"{i}. {s}: {v["dp_mean"]:.4f}")
print(f"Pearson={data["pearson"]} Spearman={data["spearman"]}")
