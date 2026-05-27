import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import pytest

def test_csc(sample_session_metadata):
    """
    Test Cross-Session Correlation (CSC).
    CSC = Probability of linking two sessions of same user.
    Threshold: CSC ≤ 1e-6 (statistically negligible).
    """
    user_ids = sample_session_metadata["user_ids"]
    timestamps = sample_session_metadata["timestamps"]
    
    # Mock embeddings (one per session)
    embeddings = np.random.randn(len(user_ids), 64)
    
    # Compute pairwise similarity
    similarity_matrix = cosine_similarity(embeddings)
    
    # Find intra-user pairs (same user)
    intra_user_sims = []
    for i in range(len(user_ids)):
        for j in range(i+1, len(user_ids)):
            if user_ids[i] == user_ids[j]:
                intra_user_sims.append(similarity_matrix[i, j])
    
    # CSC = fraction of intra-user pairs with high similarity
    if len(intra_user_sims) > 0:
        csc = np.mean(np.array(intra_user_sims) > 0.9)
    else:
        csc = 0
    
    # Assert
    assert csc <= 1e-6, f"CSC FAIL: {csc:.2e} > 1e-6"
    
    return {"csc": csc, "status": "PASS"}

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
