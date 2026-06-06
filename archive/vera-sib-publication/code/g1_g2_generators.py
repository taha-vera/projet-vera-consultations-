import numpy as np

def generate_G1(num_users=10, dim=16, sessions_per_user=10):
    """G1: Structure correlée (baseline)."""
    user_bases = np.random.randn(num_users, dim)
    sessions = []
    metadata = []
    
    for u in range(num_users):
        for t in range(np.random.randint(5, sessions_per_user+1)):
            vec = user_bases[u] + np.random.normal(0, 0.1, dim)
            sessions.append(vec)
            metadata.append({"user_id": u, "t": t})
    
    return np.array(sessions), metadata, user_bases

def generate_G2(user_bases, noise_level=0.25):
    """G2: Structure perturbée (light adversarial, not destruction)."""
    # Light rotation + noise (not tanh destruction)
    transformed = user_bases * 0.7 + np.random.randn(*user_bases.shape) * 0.3
    
    sessions = []
    metadata = []
    
    for u in range(len(user_bases)):
        for t in range(np.random.randint(5, 15)):
            vec = transformed[u] + np.random.normal(0, noise_level, len(user_bases[0]))
            sessions.append(vec)
            metadata.append({"user_id": u, "t": t})
    
    return np.array(sessions), metadata

if __name__ == "__main__":
    g1_s, g1_m, base = generate_G1(10, 16)
    g2_s, g2_m = generate_G2(base)
    print(f"G1: {g1_s.shape}, G2: {g2_s.shape}")
