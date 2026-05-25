import requests
import json
from collections import defaultdict

artist_counts = defaultdict(int)

# Fetch recent listens (limité à 1000 requêtes = ~100k listens)
for offset in range(0, 10000, 100):
    url = f"https://api.listenbrainz.org/1/stats/sitewide/artists?range=month&count=100&offset={offset}"
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            data = r.json()
            for artist in data.get('payload', []):
                artist_counts[artist['artist_name']] += artist['listen_count']
            print(f"Offset {offset}: OK")
        else:
            break
    except:
        break

# Top 20 artists
for artist, count in sorted(artist_counts.items(), key=lambda x: -x[1])[:20]:
    print(f"{artist}: {count}")
