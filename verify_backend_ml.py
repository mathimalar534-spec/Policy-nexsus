# verify_backend_ml.py - Verify the ML model integrates successfully inside LLMClient.analyze_conflict

import os
import sys

# Resolve app path
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from app.llm.llm_client import LLMClient

def test_runs():
    print("Testing ML model predictions...")
    
    # 1. Test Conflict Case
    ob_a = "All enterprise passwords must undergo reset every 90 days."
    ob_b = "Password rotation is not required; rely on MFA validation instead."
    res_conflict = LLMClient.analyze_conflict(ob_a, ob_b, topic="password")
    print(f"\nConflict Test Result:\n{res_conflict}")
    
    # 2. Test Redundancy Case
    ob_c = "All public API endpoints must be audited and scanned weekly."
    ob_d = "Weekly vulnerability scans are mandatory for all public interfaces."
    res_redundancy = LLMClient.analyze_conflict(ob_c, ob_d, topic="vulnerability scanning")
    print(f"\nRedundancy Test Result:\n{res_redundancy}")
    
    # 3. Test Unrelated Case
    ob_e = "Visitors must wear security badges visible at all times."
    ob_f = "Production databases must reside in encrypted SSD volumes."
    res_unrelated = LLMClient.analyze_conflict(ob_e, ob_f, topic="general")
    print(f"\nUnrelated Test Result:\n{res_unrelated}")

if __name__ == "__main__":
    test_runs()
