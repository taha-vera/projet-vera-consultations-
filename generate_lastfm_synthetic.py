import json
import random

random.seed(42)

# 10 artistes avec écouteurs et poids (reproduit pattern Radio France)
artists = {
    "1": {"name": "The Beatles", "base_weight": 1200},
    "2": {"name": "Pink Floyd", "base_weight": 950},
    "3": {"name": "Led Zeppelin", "base_weight": 850},
    "4": {"name": "David Bowie", "base_weight": 780},
    "5": {"name": "Queen", "base_weight": 720},
    "6": {"name": "The Rolling Stones", "base_weight": 680},
    "7": {"name": "Metallica", "base_weight": 620},
    "8": {"name": "Nirvana", "base_weight": 540},
    "9": {"name": "The Who", "base_weight": 480},
    "10": {"name": "AC/DC", "base_weight": 420}
}

# Écris user_artists.dat
with open("user_artists.dat", "w") as f:
    f.write("userID\tartistID\tweight\n")
    for artist_id, data in artists.items():
        n_users = random.randint(80, 150)
        for _ in range(n_users):
            weight = max(1, int(random.gauss(data["base_weight"]/n_users, 5)))
            f.write(f"{random.randint(1000,9999)}\t{artist_id}\t{weight}\n")

print("Synthétique user_artists.dat créé")
