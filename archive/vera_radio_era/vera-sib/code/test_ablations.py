import numpy as np
from g1_g2_generators import generate_G1, generate_G2
from test_shift_robustness import compute_rsr_simple, compute_csc
from config import CONFIG, log_run

np.random.seed(CONFIG["seed"])

def test_rsr_only():
    """Ablation: RSR alone (no CSC)."""
    g1_s, g1_m, base = generate_G1(CONFIG["g1_users"], CONFIG["g1_dim"])
    g2_s, g2_m = generate_G2(base, CONFIG["g2_noise"])
    
    rsr_g1 = compute_rsr_simple(g1_s, g1_m)
    rsr_g2 = compute_rsr_simple(g2_s, g2_m)
    
    result = {"rsr_g1": float(rsr_g1), "rsr_g2": float(rsr_g2), "drift": float(abs(rsr_g1 - rsr_g2))}
    log_run("ablation_rsr_only", result)
    print(f"✅ RSR only: drift={result['drift']:.4f}")
    return result

def test_csc_only():
    """Ablation: CSC alone (no RSR)."""
    g1_s, g1_m, base = generate_G1(CONFIG["g1_users"], CONFIG["g1_dim"])
    g2_s, g2_m = generate_G2(base, CONFIG["g2_noise"])
    
    csc_g1 = compute_csc(g1_s, g1_m)
    csc_g2 = compute_csc(g2_s, g2_m)
    
    result = {"csc_g1": float(csc_g1), "csc_g2": float(csc_g2), "drift": float(abs(csc_g1 - csc_g2))}
    log_run("ablation_csc_only", result)
    print(f"✅ CSC only: drift={result['drift']:.4f}")
    return result

def test_without_normalization():
    """Ablation: Raw metrics, no normalization."""
    g1_s, g1_m, _ = generate_G1(CONFIG["g1_users"], CONFIG["g1_dim"])
    
    rsr_raw = compute_rsr_simple(g1_s, g1_m)
    
    result = {"rsr_raw": float(rsr_raw), "note": "unnormalized"}
    log_run("ablation_no_normalization", result)
    print(f"✅ No normalization: RSR={result['rsr_raw']:.4f}")
    return result

if __name__ == "__main__":
    print("\n" + "="*60)
    print("PHASE 0.8 — ABLATION TESTS")
    print("="*60 + "\n")
    
    test_rsr_only()
    test_csc_only()
    test_without_normalization()
    
    print("\n✅ Ablations complete. Log saved.\n")
