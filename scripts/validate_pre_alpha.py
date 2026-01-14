#!/usr/bin/env python3
"""
Run all Pre-Alpha Validation tests and generate a report.
"""

import subprocess
import sys
import time

TESTS = [
    ("No Hallucination", "tests/validation/test_no_hallucination.py"),
    ("Ambiguity Preservation", "tests/validation/test_ambiguity_preserved.py"),
    ("Neutralization", "tests/validation/test_neutralization.py"),
    ("LLM-Off Resilience", "tests/validation/test_llm_off.py"),
]

def main():
    print("=" * 60)
    print("🚀 STARTING PRE-ALPHA VALIDATION SUITE")
    print("=" * 60)
    
    results = []
    
    start_total = time.time()
    
    for name, path in TESTS:
        print(f"Running {name}...")
        start = time.time()
        
        # Run pytest
        result = subprocess.run(
            ["pytest", path, "-v", "--tb=short"],
            capture_output=True,
            text=True
        )
        
        duration = time.time() - start
        passed = result.returncode == 0
        
        results.append({
            "name": name,
            "passed": passed,
            "output": result.stdout + result.stderr,
            "duration": duration
        })
        
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  -> {status} ({duration:.2f}s)")
        
    print("\n" + "=" * 60)
    print("VALIDATION REPORT")
    print("=" * 60)
    
    all_passed = all(r["passed"] for r in results)
    
    for r in results:
        status_icon = "✅" if r["passed"] else "❌"
        print(f"{status_icon} {r['name']:<25} {r['duration']:>5.2f}s")
        if not r["passed"]:
            print("-" * 40)
            print(f"Failure Output for {r['name']}:")
            # Print last 10 lines of output for brevity
            lines = r["output"].splitlines()
            print("\n".join(lines[-15:]))
            print("-" * 40)
            
    print("=" * 60)
    if all_passed:
        print("🎉 PRE-ALPHA READY: All validation criteria met.")
        sys.exit(0)
    else:
        print("⚠️  NOT READY: Fix failing validation tests.")
        sys.exit(1)

if __name__ == "__main__":
    main()
