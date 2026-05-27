# VERA SIB — Surviving Information Budget

Empirical validation of VERA's privacy spine via 4 metrics:
- **RSR**: Reconstruction Success Rate (Membership Inference)
- **CSC**: Cross-Session Correlation (Linkage Attack)
- **SUR**: Signal Utility Retention (MAPE)
- **PHL**: Persistence Half-Life (Decay Rate)

## Threshold

| Metric | Threshold | Status |
|--------|-----------|--------|
| RSR    | ≤ 0.53    | - |
| CSC    | ≤ 1e-6    | - |
| SUR    | > 0.97    | - |
| PHL    | ≤ 1h      | - |

## Phase 1 Timeline

- W1: Collect real data (VERA Pulse on Android)
- W2: Implement tests (RSR, CSC, SUR, PHL)
- W3: Execute tests
- W4: Results + Whitepaper

## Running Tests

```bash
pytest tests/ -v
python run_all_tests.py
cat > tests/conftest.py << 'EOF'
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

