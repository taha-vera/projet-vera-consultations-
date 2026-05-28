"""
Fairness Metrics — Phase 1 W2
Gini coefficient + Capture detection
"""
import json
import numpy as np
import os

def gini_coefficient(distribution):
    """Calculate Gini coefficient (0 = perfect equality, 1 = total concentration)"""
    sorted_dist = np.sort(distribution)
    n = len(sorted_dist)
    cumsum = np.cumsum(sorted_dist)
    
    gini = (2 * np.sum((n + 1 - np.arange(1, n + 1)) * sorted_dist)) / (n * np.sum(sorted_dist)) - (n + 1) / n
    
    return float(gini)

def capture_detection(distribution, threshold=0.4):
    """Detect if top 10% captures > 40% of value"""
    sorted_dist = np.sort(distribution)[::-1]
    top_10_pct = int(len(sorted_dist) * 0.1)
    
    if top_10_pct == 0:
        top_10_pct = 1
    
    top_10_value = np.sum(sorted_dist[:top_10_pct])
    total_value = np.sum(sorted_dist)
    
    capture_ratio = top_10_value / total_value
    
    return {
        'capture_ratio': float(capture_ratio),
        'threshold': threshold,
        'captured': bool(capture_ratio > threshold),
        'top_10_pct_value': float(top_10_value),
        'total_value': float(total_value)
    }

def simulate_contribution_distribution(n_creators=1000, scenario='fair'):
    """Simulate different contribution scenarios"""
    if scenario == 'fair':
        return np.random.uniform(1, 10, n_creators)
    elif scenario == 'pareto':
        contributions = np.random.pareto(1.16, n_creators) + 1
        return contributions
    elif scenario == 'captured':
        contributions = np.random.exponential(0.1, n_creators)
        top_1_pct = int(n_creators * 0.01)
        contributions[:top_1_pct] *= 100
        return contributions

def test_fairness_scenarios():
    """Test all scenarios"""
    scenarios = ['fair', 'pareto', 'captured']
    
    print("=" * 60)
    print("FAIRNESS TESTING - Phase 1 W2")
    print("=" * 60)
    
    results = []
    
    for scenario in scenarios:
        print(f"\n📊 Scenario: {scenario.upper()}")
        
        dist = simulate_contribution_distribution(1000, scenario)
        gini = gini_coefficient(dist)
        capture = capture_detection(dist)
        
        gini_pass = gini < 0.3
        capture_pass = not capture['captured']
        
        result = {
            'scenario': scenario,
            'gini': gini,
            'gini_target': 0.3,
            'gini_pass': bool(gini_pass),
            'capture_ratio': capture['capture_ratio'],
            'capture_threshold': 0.4,
            'capture_pass': bool(capture_pass),
            'overall_pass': bool(gini_pass and capture_pass)
        }
        
        results.append(result)
        
        print(f"   Gini: {gini:.4f} (target < 0.3) {'✅' if gini_pass else '❌'}")
        print(f"   Top 10%: {capture['capture_ratio']:.1%} (threshold 40%) {'✅' if capture_pass else '❌'}")
        print(f"   Overall: {'✅ PASS' if result['overall_pass'] else '❌ FAIL'}")
    
    os.makedirs('vera-sib/results', exist_ok=True)
    with open('vera-sib/results/fairness_scenarios_w2.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Results saved to vera-sib/results/fairness_scenarios_w2.json")
    
    return results

if __name__ == '__main__':
    test_fairness_scenarios()
