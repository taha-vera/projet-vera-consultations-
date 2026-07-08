#!/usr/bin/env python3
import subprocess
import json
import os

def run_tests():
    """Master script to run all SIB tests."""
    print("\n" + "="*60)
    print("VERA SIB — Running All Tests")
    print("="*60 + "\n")
    
    # Run pytest
    result = subprocess.run(
        ["pytest", "tests/", "-v", "--tb=short"],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    # Create results directory
    os.makedirs("results", exist_ok=True)
    
    # Save raw output
    with open("results/pytest_output.txt", "w") as f:
        f.write(result.stdout)
    
    print("\n" + "="*60)
    if result.returncode == 0:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("="*60 + "\n")
    
    return result.returncode

if __name__ == "__main__":
    exit(run_tests())
