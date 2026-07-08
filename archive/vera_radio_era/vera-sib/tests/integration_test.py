import pytest
from test_rsr import test_rsr
from test_csc import test_csc
from test_sur import test_sur
from test_phl import test_phl

def test_all_metrics(sample_aggregates, sample_membership_labels, 
                      sample_session_metadata, sample_ground_truth):
    """Run all 4 SIB metrics together."""
    results = {}
    
    results["rsr"] = test_rsr(sample_aggregates, sample_membership_labels)
    results["csc"] = test_csc(sample_session_metadata)
    results["sur"] = test_sur(sample_aggregates, sample_ground_truth)
    results["phl"] = test_phl(sample_session_metadata)
    
    # Summary
    all_pass = all(r["status"] == "PASS" for r in results.values())
    
    print("\n" + "="*50)
    print("SIB VALIDATION SUMMARY")
    print("="*50)
    for metric, result in results.items():
        status = "✅ PASS" if result["status"] == "PASS" else "❌ FAIL"
        print(f"{metric.upper()}: {status}")
    print("="*50)
    print(f"Overall: {'✅ SPINE VALID' if all_pass else '❌ SPINE INVALID'}")
    print("="*50 + "\n")
    
    assert all_pass, "SIB validation FAILED"
    return results

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
