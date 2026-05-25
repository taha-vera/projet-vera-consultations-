import json
import sys
from collections import defaultdict

# Parse ListenBrainz JSON, compte par artiste/user
artist_counts = defaultdict(int)
user_counts = defaultdict(int)

for line in sys.stdin:
    try:
        listen = json.loads(line)
        artist = listen.get('track_metadata', {}).get('artist_name', 'unknown')
        user = listen.get('user_name', 'unknown')
        artist_counts[artist] += 1
        user_counts[user] += 1
    except:
        pass

# Top 10 artists
for artist, count in sorted(artist_counts.items(), key=lambda x: -x[1])[:10]:
    print(f"{artist}: {count}")
