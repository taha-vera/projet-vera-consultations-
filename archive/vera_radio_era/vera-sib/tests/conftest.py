import pytest
import numpy as np

@pytest.fixture
def sample_aggregates():
    np.random.seed(42)
    return np.random.randn(1000, 128)

@pytest.fixture
def sample_ground_truth(sample_aggregates):
    """Ground truth = aggregates + small noise (simulates DP distortion)"""
    np.random.seed(99)
    noise = np.random.randn(*sample_aggregates.shape) * 0.001
    return sample_aggregates + noise

@pytest.fixture
def sample_membership_labels():
    np.random.seed(42)
    return np.random.randint(0, 2, 1000)

@pytest.fixture
def sample_session_metadata():
    np.random.seed(42)
    return {
        "timestamps": np.arange(0, 100, 0.1),
        "session_ids": [f"sess_{i}" for i in range(1000)],
        "user_ids": np.random.randint(0, 50, 1000)
    }
