import numpy as np

def cluster_bootstrap(sessions, metadata, metric_fn, B=100):
    """Bootstrap at user level (cluster resampling)."""
    unique_users = list(set(m["user_id"] for m in metadata))
    results = []
    
    for _ in range(B):
        sampled_users = np.random.choice(unique_users, len(unique_users), replace=True)
        sample_idx = [i for i in range(len(metadata)) if metadata[i]["user_id"] in sampled_users]
        
        sample_sessions = sessions[sample_idx]
        sample_meta = [metadata[i] for i in sample_idx]
        
        results.append(metric_fn(sample_sessions, sample_meta))
    
    return {
        "mean": np.mean(results),
        "ci_lower": np.percentile(results, 2.5),
        "ci_upper": np.percentile(results, 97.5)
    }

def block_bootstrap(sessions, metadata, metric_fn, block_size=5, B=100):
    """Bootstrap with time blocks (temporal dependency)."""
    sorted_idx = np.argsort([m["t"] for m in metadata])
    results = []
    
    for _ in range(B):
        blocks = []
        for i in range(0, len(sorted_idx), block_size):
            blocks.append(sorted_idx[i:i+block_size])
        
        sampled_blocks = np.random.choice(len(blocks), len(blocks), replace=True)
        sample_idx = np.concatenate([blocks[b] for b in sampled_blocks])
        
        sample_sessions = sessions[sample_idx]
        sample_meta = [metadata[i] for i in sample_idx]
        
        results.append(metric_fn(sample_sessions, sample_meta))
    
    return {
        "mean": np.mean(results),
        "ci_lower": np.percentile(results, 2.5),
        "ci_upper": np.percentile(results, 97.5)
    }

if __name__ == "__main__":
    print("Bootstrap inference module ready.")
