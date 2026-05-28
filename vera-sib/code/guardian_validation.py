"""
Guardian Layer - Risk Scoring Validation
Phase 1 W1 - Test sur données synthétiques
"""
import json
import hashlib
import os

def load_metadata(path='vera-sib/data/fma_metadata_synthetic.json'):
    """Load synthetic metadata"""
    with open(path, 'r') as f:
        return json.load(f)

def risk_score(track, jurisdiction='FR'):
    """
    Calculate risk score for a track
    
    risk_score = (jurisdiction_risk × 0.4) 
               + (fingerprint_confidence × 0.3)
               + (source_trust × 0.3)
    """
    
    # Jurisdiction risk (normalized 0-1, lower is better)
    jurisdiction_risks = {
        'FR': 0.2,  # Low
        'US': 0.15, # Low
        'DE': 0.2,  # Low
        'UK': 0.35, # Medium
        'OTHER': 0.6  # High
    }
    j_risk = jurisdiction_risks.get(jurisdiction, 0.6)
    
    # Fingerprint confidence (hash-based, 0-1)
    title_hash = hashlib.sha256(track['title'].encode()).hexdigest()
    fp_confidence = len(set(title_hash[:8])) / 16  # Simplified
    
    # Source trust (CC0 > CC-BY > others)
    source_trust_map = {'CC0': 0.95, 'CC-BY': 0.80, 'CC-BY-SA': 0.75}
    s_trust = source_trust_map.get(track['license'], 0.5)
    
    # Calculate final score
    final_score = (j_risk * 0.4) + ((1 - fp_confidence) * 0.3) + ((1 - s_trust) * 0.3)
    
    return {
        'track_id': track['id'],
        'title': track['title'],
        'jurisdiction_risk': j_risk,
        'fingerprint_confidence': fp_confidence,
        'source_trust': s_trust,
        'risk_score': final_score,
        'accepted': final_score < 0.75  # Accept if score < 0.75
    }

def validate_all(jurisdiction='FR'):
    """Validate all tracks"""
    tracks = load_metadata()
    results = []
    
    print(f"Validating {len(tracks)} tracks for {jurisdiction}...")
    
    for track in tracks:
        result = risk_score(track, jurisdiction)
        results.append(result)
    
    # Statistics
    accepted = sum(1 for r in results if r['accepted'])
    rejected = len(results) - accepted
    
    print(f"\n✅ Results:")
    print(f"   Total: {len(results)}")
    print(f"   Accepted: {accepted} ({100*accepted/len(results):.1f}%)")
    print(f"   Rejected: {rejected} ({100*rejected/len(results):.1f}%)")
    
    # Save results
    os.makedirs('vera-sib/results', exist_ok=True)
    with open(f'vera-sib/results/guardian_validation_{jurisdiction}.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    return results

if __name__ == '__main__':
    validate_all('FR')
