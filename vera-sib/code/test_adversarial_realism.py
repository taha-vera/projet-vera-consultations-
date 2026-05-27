import numpy as np
from g1_g2_generators import generate_G1
from test_shift_robustness import compute_rsr_simple, compute_csc
from config import CONFIG, log_run

np.random.seed(CONFIG["seed"])

def add_gaussian_noise(sessions, sigma):
    """Add Gaussian noise."""
    return sessions + np.random.normal(0, sigma, sessions.shape)

def add_feature_dropout(sessions, dropout_prob):
    """Random feature dropout."""
    mask = np.random.binomial(1, 1-dropout_prob, sessions.shape)
    return sessions * mask

def add_temporal_shift(sessions, lag_drift=0.1):
    """Add temporal correlation shift."""
    shifted = sessions.copy()
    for i in range(1, len(shifted)):
        shifted[i] = shifted[i-1] * (1-lag_drift) + shifted[i] * lag_drift
    return shifted

def add_sensor_bias(sessions, offset_scale=0.2):
    """Simulate sensor offset + scaling anomalies."""
    offset = np.random.uniform(-offset_scale, offset_scale, sessions.shape[1])
    scale = np.random.uniform(0.8, 1.2, sessions.shape[1])
    return (sessions + offset) * scale

def test_gaussian_noise():
    """Stress: Gaussian noise σ=[0.1, 0.5, 1.0]."""
    g1_s, g1_m, _ = generate_G1(CONFIG["g1_users"], CONFIG["g1_dim"])
    
    results = {}
    for sigma in [0.1, 0.5, 1.0]:
        noisy = add_gaussian_noise(g1_s, sigma)
        rsr = compute_rsr_simple(noisy, g1_m)
        csc = compute_csc(noisy, g1_m)
        results[f"sigma_{sigma}"] = {"rsr": float(rsr), "csc": float(csc)}
    
    log_run("stress_gaussian_noise", results)
    print(f"✅ Gaussian noise: {results}")
    return results

def test_feature_dropout():
    """Stress: Feature dropout p=[0.05, 0.2, 0.4]."""
    g1_s, g1_m, _ = generate_G1(CONFIG["g1_users"], CONFIG["g1_dim"])
    
    results = {}
    for p in [0.05, 0.2, 0.4]:
        dropped = add_feature_dropout(g1_s, p)
        rsr = compute_rsr_simple(dropped, g1_m)
        csc = compute_csc(dropped, g1_m)
        results[f"dropout_{p}"] = {"rsr": float(rsr), "csc": float(csc)}
    
    log_run("stress_feature_dropout", results)
    print(f"✅ Feature dropout: {results}")
    return results

def test_temporal_shift():
    """Stress: Temporal lag drift."""
    g1_s, g1_m, _ = generate_G1(CONFIG["g1_users"], CONFIG["g1_dim"])
    
    results = {}
    for lag in [0.05, 0.15, 0.3]:
        shifted = add_temporal_shift(g1_s, lag)
        rsr = compute_rsr_simple(shifted, g1_m)
        csc = compute_csc(shifted, g1_m)
        results[f"lag_{lag}"] = {"rsr": float(rsr), "csc": float(csc)}
    
    log_run("stress_temporal_shift", results)
    print(f"✅ Temporal shift: {results}")
    return results

def test_sensor_bias():
    """Stress: Sensor offset + scaling."""
    g1_s, g1_m, _ = generate_G1(CONFIG["g1_users"], CONFIG["g1_dim"])
    
    results = {}
    for scale in [0.1, 0.2, 0.5]:
        biased = add_sensor_bias(g1_s, scale)
        rsr = compute_rsr_simple(biased, g1_m)
        csc = compute_csc(biased, g1_m)
        results[f"bias_{scale}"] = {"rsr": float(rsr), "csc": float(csc)}
    
    log_run("stress_sensor_bias", results)
    print(f"✅ Sensor bias: {results}")
    return results

if __name__ == "__main__":
    print("\n" + "="*60)
    print("PHASE 0.8 — ADVERSARIAL REALISM STRESS TESTS")
    print("="*60 + "\n")
    
    test_gaussian_noise()
    test_feature_dropout()
    test_temporal_shift()
    test_sensor_bias()
    
    print("\n✅ All stress tests complete.\n")
