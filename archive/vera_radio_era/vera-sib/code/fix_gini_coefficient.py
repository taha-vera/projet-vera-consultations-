"""
Fix: Gini Coefficient Formula
Issue: Gini was negative (mathematically incorrect)
Solution: Standard formula (always [0,1])
"""
import numpy as np

def gini_coefficient_corrected(distribution):
    """
    Calculate Gini coefficient correctly
    Range: [0, 1] where 0 = perfect equality, 1 = total inequality
    
    Formula: Gini = 1 - (2 * sum(cumsum)) / (n * sum(dist)) + 1/n
    """
    sorted_dist = np.sort(distribution)
    n = len(sorted_dist)
    
    if np.sum(sorted_dist) == 0:
        return 0.0
    
    cumsum = np.cumsum(sorted_dist)
    total = np.sum(sorted_dist)
    
    # Standard Gini formula (always positive)
    gini = 1 - (2 * np.sum(cumsum)) / (n * total) + 1/n
    
    # Clamp to [0, 1] for safety
    gini = np.clip(gini, 0, 1)
    
    return float(gini)

def test_gini_fix():
    """Test corrected Gini"""
    
    print("\n" + "=" * 60)
    print("GINI COEFFICIENT FIX — Validation")
    print("=" * 60)
    
    # Test 1: Perfect equality (Gini should be 0)
    equal_dist = np.ones(100)
    gini_equal = gini_coefficient_corrected(equal_dist)
    print(f"\n✅ Perfect equality: Gini = {gini_equal:.4f} (should be ~0)")
    assert gini_equal < 0.1, "FAIL: Perfect equality should have Gini ≈ 0"
    
    # Test 2: Perfect inequality (Gini should be ~1)
    unequal_dist = np.zeros(100)
    unequal_dist[0] = 100
    gini_unequal = gini_coefficient_corrected(unequal_dist)
    print(f"✅ Perfect inequality: Gini = {gini_unequal:.4f} (should be ~1)")
    assert gini_unequal > 0.95, "FAIL: Perfect inequality should have Gini ≈ 1"
    
    # Test 3: Pareto distribution
    pareto_dist = np.random.pareto(1.16, 1000) + 1
    gini_pareto = gini_coefficient_corrected(pareto_dist)
    print(f"✅ Pareto distribution: Gini = {gini_pareto:.4f} (expected ~0.5)")
    assert 0.3 < gini_pareto < 0.7, "FAIL: Pareto Gini out of bounds"
    
    print(f"\n✅ All Gini tests PASSED")
    print("=" * 60)

if __name__ == '__main__':
    test_gini_fix()
