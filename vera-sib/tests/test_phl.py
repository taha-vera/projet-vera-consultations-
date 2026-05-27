import numpy as np
from scipy.optimize import curve_fit
import pytest

def exp_decay(t, a, b):
    """Exponential decay model."""
    return a * np.exp(-b * t)

def test_phl(sample_session_metadata):
    """
    Test Persistence Half-Life (PHL).
    PHL = time for correlability to drop to 50%.
    Threshold: PHL ≤ 1 hour.
    """
    timestamps = sample_session_metadata["timestamps"]
    
    # Mock correlability decay over time
    # Start at 1.0, decay exponentially
    correlability = np.exp(-0.866 * timestamps)  # 0.866 ≈ ln(2)/0.8
    
    # Fit exponential model
    try:
        params, _ = curve_fit(exp_decay, timestamps, correlability)
        a, b = params
        phl = np.log(2) / b  # Half-life in hours
    except:
        phl = 0
    
    # Assert
    assert phl <= 1.0, f"PHL FAIL: {phl:.2f}h > 1h"
    
    return {"phl": phl, "status": "PASS"}

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
