#!/usr/bin/env python3
import numpy as np
from g1_g2_generators import generate_G1, generate_G2
from test_shift_robustness import test_metric_shift_robustness, compute_rsr_simple, compute_csc
from vif_identifiability import test_vif
import json

def run_full_evaluation():
    """Master: Run G1/G2, shift robustness, VIF, save results."""
    print("\n" + "="*70)
    print("VERA SIB v0.7.6 — Full Evaluation")
    print("="*70 + "\n")
    
    # Generate
    g1_s, g1_m, base = generate_G1(20, 16)
    g2_s, g2_m = generate_G2(base)
    
    # Test shift robustness
    drift_result = test_metric_shift_robustness()
    
    # Compute metrics
    metrics = {
        "rsr_g1": np.array([compute_rsr_simple(g1_s[i:i+10], g1_m[i:i+10]) for i in range(0, len(g1_s), 10)]),
        "csc_g1": np.array([compute_csc(g1_s[i:i+10], g1_m[i:i+10]) for i in range(0, len(g1_s), 10)]),
        "rsr_g2": np.array([compute_rsr_simple(g2_s[i:i+10], g2_m[i:i+10]) for i in range(0, len(g2_s), 10)]),
        "csc_g2": np.array([compute_csc(g2_s[i:i+10], g2_m[i:i+10]) for i in range(0, len(g2_s), 10)]),
    }
    
    # Test VIF
    test_vif({k: v.flatten() for k, v in metrics.items()})
    
    # Save
    results = {
        "shift_robustness": drift_result,
        "metrics": {k: v.mean().item() for k, v in metrics.items()}
    }
    
    with open("../results/evaluation_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "="*70)
    print("✅ Full evaluation complete. Results saved to results/evaluation_results.json")
    print("="*70 + "\n")
    
    return results

if __name__ == "__main__":
    run_full_evaluation()
