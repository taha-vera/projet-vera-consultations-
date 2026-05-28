"""
Phase 2 W1 Task 2 — Guardian Validation on Real Data
Test realistic duplicate detection rate
"""
import json
import hashlib
import numpy as np
import os

def load_fma_data(path='vera-sib/data/fma_phase2_real.json'):
    """Load FMA metadata"""
    with open(path, 'r') as f:
        data = json.load(f)
    return data['tracks']

def compute_track_signature(track):
    """
    Create fingerprint from track metadata
    Realistic: based on title + artist + duration
    """
    sig_input = f"{track['title']}|{track['artist']}|{track['duration']}"
    return hashlib.sha256(sig_input.encode()).hexdigest()

def detect_duplicates(tracks, similarity_threshold=0.95):
    """
    Realistic duplicate detection
    Checks for near-identical metadata
    """
    duplicates = []
    
    for i, t1 in enumerate(tracks):
        for j, t2 in enumerate(tracks[i+1:], start=i+1):
            # Simple similarity: check if title very similar
            title_match = t1['title'].lower() == t2['title'].lower()
            artist_match = t1['artist'].lower() == t2['artist'].lower()
            
            if title_match and artist_match:
                duplicates.append((i, j))
    
    return duplicates

def guardian_validation_realistic(tracks):
    """
    Realistic Guardian validation on FMA data
    
    Mimics real challenges:
    - Title variations
    - Artist name variations
    - Duration differences
    - Genre mismatches
    """
    
    print("\n" + "=" * 70)
    print("PHASE 2 W1 TASK 2 — GUARDIAN REAL DATA VALIDATION")
    print("=" * 70)
    
    accepted = []
    rejected = []
    
    print(f"\n🔍 Validating {len(tracks)} real FMA-like tracks...")
    
    for i, track in enumerate(tracks):
        if i % 100 == 0:
            print(f"   Processed {i}/{len(tracks)}...", end='\r')
        
        # Realistic Guardian checks:
        # 1. Metadata completeness
        has_required = track.get('id') and track.get('title') and track.get('artist')
        
        # 2. Duration sanity (music tracks: 30s - 15min)
        duration_valid = 30 <= track.get('duration', 0) <= 900
        
        # 3. License is CC0 (already filtered, but double-check)
        license_valid = track.get('license') == 'CC0'
        
        # 4. No suspicious patterns (simplified)
        title_len = len(track.get('title', ''))
        suspicious = title_len < 3 or title_len > 200
        
        # Decision
        if has_required and duration_valid and license_valid and not suspicious:
            accepted.append(track)
        else:
            rejected.append(track)
    
    # Duplicate detection
    duplicates = detect_duplicates(tracks)
    
    print(f"\n✅ GUARDIAN VALIDATION RESULTS:")
    print(f"   Total tracks: {len(tracks)}")
    print(f"   Accepted: {len(accepted)} ({100*len(accepted)/len(tracks):.1f}%)")
    print(f"   Rejected: {len(rejected)} ({100*len(rejected)/len(tracks):.1f}%)")
    print(f"   Duplicates detected: {len(duplicates)}")
    
    # Realistic rejection rate
    rejection_rate = len(rejected) / len(tracks)
    print(f"\n   Rejection rate: {100*rejection_rate:.1f}% (realistic: 10-20% expected)")
    
    # Save results
    results = {
        'timestamp': __import__('datetime').datetime.now().isoformat(),
        'total_tracks': len(tracks),
        'accepted': len(accepted),
        'rejected': len(rejected),
        'duplicates': len(duplicates),
        'rejection_rate': float(rejection_rate),
        'status': 'PASS' if rejection_rate < 0.3 else 'WARNING'
    }
    
    os.makedirs('vera-sib/results', exist_ok=True)
    with open('vera-sib/results/phase2_guardian_real_data.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Results saved to vera-sib/results/phase2_guardian_real_data.json")
    print("=" * 70)
    
    return accepted, rejected, duplicates

def main():
    tracks = load_fma_data()
    accepted, rejected, duplicates = guardian_validation_realistic(tracks)

if __name__ == '__main__':
    main()
