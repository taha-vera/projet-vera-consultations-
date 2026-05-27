import numpy as np
import pytest

def test_sur(sample_aggregates, sample_ground_truth):
    """
    Test Signal Utility Retention (SUR).
    SUR = 1 - MAPE (Mean Absolute Percentage Error).
    Threshold: MAPE < 3% (SUR > 0.97).
    """
    y_true = sample_ground_truth
    y_pred = sample_aggregates
    
    # Compute MAPE
    mape = np.mean(np.abs((y_true - y_pred) / (np.abs(y_true) + 1e-8))) * 100
    sur = 1 - (mape / 100)
    
    # Assert
    assert mape < 3, f"SUR FAIL: MAPE={mape:.2f}% > 3%"
    
    return {"sur": sur, "mape": mape, "status": "PASS"}

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
