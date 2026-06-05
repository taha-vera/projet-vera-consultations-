import json

with open("results_stability.json") as f:
    radio = json.load(f)
with open("lastfm_dp_results.json") as f:
    lastfm = json.load(f)

print("=== PATTERN COMPARISON ===\n")
print(f"Radio France | Pearson: {radio['pearson']}, Spearman: {radio['spearman']}")
print(f"Last.fm      | Pearson: {lastfm['pearson']}, Spearman: {lastfm['spearman']}\n")

print("Biais statistics:")
radio_biases = [abs(s['bias']) for s in radio['stations'].values()]
lastfm_biases = [abs(a['bias']) for a in lastfm['artists']]

print(f"Radio France | mean={sum(radio_biases)/len(radio_biases):.5f}, max={max(radio_biases):.5f}")
print(f"Last.fm      | mean={sum(lastfm_biases)/len(lastfm_biases):.5f}, max={max(lastfm_biases):.5f}")
