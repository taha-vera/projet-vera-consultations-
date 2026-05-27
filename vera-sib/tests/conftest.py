import pytest
import numpy as np
import json

@pytest.fixture
def sample_aggregates():
    """Mock DP aggregates (ex: audio embeddings)."""
    return np.random.randn(1000, 128)

@pytest.fixture
def sample_membership_labels():
    """Mock membership labels (1=member, 0=non-member)."""
    return np.random.randint(0, 2, 1000)

@pytest.fixture
def sample_session_metadata():
    """Mock session metadata (timestamps, etc)."""
    return {
        "timestamps": np.arange(0, 100, 0.1),
        "session_ids": [f"sess_{i}" for i in range(1000)],
        "user_ids": np.random.randint(0, 50, 1000)
    }

@pytest.fixture
def sample_ground_truth():
    """Mock ground truth values (real data)."""
    return np.random.randn(1000, 128) * 10
