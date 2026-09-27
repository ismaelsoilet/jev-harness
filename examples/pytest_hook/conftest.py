"""
Jev Harness - Transparent Pytest Failure Interceptor Hook.

Drop this conftest.py into your repository root or test directory.
Whenever a test fails, Jev intercepts the failure in < 500µs:
- If it is a deterministic failure (ModuleNotFoundError, timeout, port in use):
  it advises the exact shell fix, preventing AI coding agents from burning 50k tokens.
- If it is a genuine logic defect, it confirms escalation to System 2.
"""

import os
import pytest
from jev_harness import triage_test_failure

def pytest_runtest_makereport(item, call):
    if call.excinfo is not None and call.when == "call":
        error_text = str(call.excinfo.getrepr(style="short"))
        
        # Run local deterministic triage (< 500µs)
        try:
            result = triage_test_failure(error_text)
            if result.skip_llm:
                print("\n" + "=" * 70)
                print("⚡ [JEV HARNESS - SYSTEM 1.5 DETERMINISTIC TRIAGE]")
                print(f"Category:       {result.category.upper()}")
                print(f"Skip LLM Call:  YES (0 tokens required)")
                print(f"Action:         {result.action_recommendation}")
                if result.recovery and result.recovery.get("commands"):
                    print(f"Suggested Fix:  {' && '.join(result.recovery['commands'])}")
                print("=" * 70 + "\n")
        except Exception:
            pass
