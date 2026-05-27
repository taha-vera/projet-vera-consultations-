import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score
import pytest

def test_rsr(sample_aggregates, sample_membership_labels):
    """
    Test Reconstruction Success Rate (RSR).
    RSR = AUC of Membership Inference Attack (MIA).
    Threshold: AUC ≤ 0.53 (not better than random guessing).
    """
    X = sample_aggregates
    y = sample_membership_labels
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    # Train classifier
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X_train, y_train)
    
    # Predict
    y_pred_proba = clf.predict_proba(X_test)[:, 1]
    rsr = roc_auc_score(y_test, y_pred_proba)
    
    # Assert
    assert rsr <= 0.53, f"RSR FAIL: {rsr:.4f} > 0.53"
    
    return {"rsr": rsr, "status": "PASS"}

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
