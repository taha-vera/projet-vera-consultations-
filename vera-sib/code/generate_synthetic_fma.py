"""Generate synthetic FMA-like metadata for Phase 1 testing"""
import json
import os
import random
from datetime import datetime

def generate_synthetic_tracks(n=1000):
    """Generate n synthetic tracks similar to FMA structure"""
    
    genres = ['Electronic', 'Rock', 'Hip-Hop', 'Classical', 'Jazz', 'Pop', 'Ambient']
    licenses = ['CC0', 'CC-BY', 'CC-BY-SA']
    
    tracks = []
    for i in range(n):
        tracks.append({
            'id': i + 1,
            'title': f'Synthetic Track {i+1}',
            'artist': f'Artist {random.randint(1, 100)}',
            'license': random.choice(licenses),
            'duration': random.randint(120, 600),
            'genres': random.sample(genres, k=random.randint(1, 3)),
            'date_created': datetime.now().isoformat()
        })
    
    return tracks

def save_metadata(tracks, output_path='vera-sib/data/fma_metadata_synthetic.json'):
    """Save tracks to JSON"""
    os.makedirs('vera-sib/data', exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(tracks, f, indent=2)
    
    print(f"✅ Generated and saved {len(tracks)} synthetic tracks")
    print(f"   Location: {output_path}")
    
    return output_path

if __name__ == '__main__':
    tracks = generate_synthetic_tracks(1000)
    save_metadata(tracks)
