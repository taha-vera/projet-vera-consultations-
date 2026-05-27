import numpy as np
from g1_g2_generators import generate_G1, generate_G2

def compute_rsr_simple(sessions, metadata):
    """RSR via simple cosine distance (no sklearn needed)."""
    # Average per user
    users = set(m["user_id"] for m in metadata)
    user_avgs = {}
    for u in users:
        user_avgs[u] = np.mean([sessions[i] for i in range(len(metadata)) if metadata[i]["user_id"] == u], axis=0)
    
    # Compute distance to closest user avg
    correct = 0
    for i in range(len(sessions)):
        true_user = metadata[i]["user_id"]
        dists = {u: np.linalg.norm(sessions[i] - user_avgs[u]) for u in users}
        pred_user = min(dists, key=dists.get)
        if pred_user == true_user:
            correct += 1
    
    return correct / len(sessions)

def compute_csc(sessions, metadata):
    """CSC via cosine similarity."""
    sim = np.dot(sessions, sessions.T) / (np.linalg.norm(sessions, axis=1, keepdims=True) * np.linalg.norm(sessions, axis=1, keepdims=True).T + 1e-8)
    
    intra_user = []
    for i in range(len(metadata)):
        for j in range(i+1, len(metadata)):
            if metadata[i]["user_id"] == metadata[j]["user_id"]:
                intra_user.append(sim[i, j])
    
    return np.mean(np.array(intra_user) > 0.9) if len(intra_user) > 0 else 0

def test_metric_shift_robustness():
    """Test: metrics robust under distribution shift (G1 vs G2)."""
    print("\n" + "="*60)
    print("TEST: Metric Shift Robustness (G1 vs G2)")
    print("="*60)
    
    g1_s, g1_m, base = generate_G1(10, 16)
    g2_s, g2_m = generate_G2(base)
    
    rsr_g1 = compute_rsr_simple(g1_s, g1_m)
    rsr_g2 = compute_rsr_simple(g2_s, g2_m)
    csc_g1 = compute_csc(g1_s, g1_m)
    csc_g2 = compute_csc(g2_s, g2_m)
    
    rsr_drift = abs(rsr_g1 - rsr_g2)
    csc_drift = abs(csc_g1 - csc_g2)
    total_drift = np.mean([rsr_drift, csc_drift])
    
    print(f"\nRSR: G1={rsr_g1:.4f}, G2={rsr_g2:.4f}, drift={rsr_drift:.4f}")
    print(f"CSC: G1={csc_g1:.2e}, G2={csc_g2:.2e}, drift={csc_drift:.2e}")
    print(f"\nTotal drift: {total_drift:.4f}")
    
    assert total_drift < 0.3, f"Drift too high: {total_drift:.4f}"
    print("✅ PASS: Metrics stable\n")

if __name__ == "__main__":
    test_metric_shift_robustness()
