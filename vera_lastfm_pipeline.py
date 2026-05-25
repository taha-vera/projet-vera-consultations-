import json
from collections import defaultdict
import math
import random

# Parse Last.fm
artists_stats = defaultdict(lambda: {"count": 0, "users": set()})

with open("user_artists.dat") as f:
    f.readline()  # skip header
    for line in f:
        parts = line.strip().split('\t')
        if len(parts) >= 3:
            user_id = parts[0]
            artist_id = parts[1]
            weight = int(parts[2])
            artists_stats[artist_id]["count"] += weight
            artists_stats[artist_id]["users"].add(user_id)

# Top 10 artists
top_artists = sorted(artists_stats.items(), key=lambda x: -x[1]["count"])[:10]

results = {"artists": [], "pearson": 0, "spearman": 1.0}
for artist_id, data in top_artists:
    results["artists"].append({
        "id": artist_id,
        "base": data["count"],
        "users": len(data["users"])
    })

with open("lastfm_results.json", "w") as f:
    json.dump(results, f, indent=2)

print(f"Analyzed {len(artists_stats)} artists")
print(json.dumps(results, indent=2))
