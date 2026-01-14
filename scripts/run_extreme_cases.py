#!/usr/bin/env python3
"""
Run all extreme cases through NNRT and analyze results.
"""

import yaml
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from nnrt.core.context import TransformRequest
from nnrt.core.engine import get_engine
from nnrt.cli.main import setup_default_pipeline


def load_extreme_cases():
    """Load extreme cases from YAML."""
    path = Path(__file__).parent.parent / "data" / "synthetic" / "extreme_cases.yaml"
    with open(path) as f:
        return yaml.safe_load(f)


def run_case(engine, case):
    """Run a single case and return results."""
    request = TransformRequest(text=case["input"])
    result = engine.transform(request)
    
    return {
        "id": case["id"],
        "category": case["category"],
        "input": case["input"],
        "output": result.rendered_text,
        "diagnostics": [(d.code, d.message) for d in result.diagnostics],
        "preserved": case.get("expected_preserved", []),
        "status": result.status.value,
    }


def analyze_case(result):
    """Analyze if the case was handled correctly."""
    issues = []
    
    # Check if expected content was preserved
    for expected in result["preserved"]:
        if expected.lower() not in result["output"].lower():
            issues.append(f"MISSING: '{expected}' not in output")
    
    # Check for critical diagnostics
    critical_codes = ["SARCASM_DETECTED", "AMBIGUOUS_PRONOUN", "PHYSICAL_CONTRADICTION", 
                      "SELF_CONTRADICTION", "VAGUE_REFERENCE"]
    found_issues = [code for code, _ in result["diagnostics"] if code in critical_codes]
    
    return {
        "passed": len(issues) == 0,
        "issues": issues,
        "detected": found_issues,
    }


def main():
    # Setup
    engine = get_engine()
    setup_default_pipeline(engine)
    
    # Load cases
    data = load_extreme_cases()
    cases = data["cases"]  # Changed from extreme_cases
    
    print(f"=" * 80)
    print(f"NNRT Extreme Case Analysis")
    print(f"=" * 80)
    print(f"Running {len(cases)} extreme cases...\n")
    
    results = []
    passed = 0
    failed = 0
    
    for case in cases:
        result = run_case(engine, case)
        analysis = analyze_case(result)
        
        status = "✅ PASS" if analysis["passed"] else "❌ FAIL"
        if analysis["passed"]:
            passed += 1
        else:
            failed += 1
        
        print(f"\n{'-' * 60}")
        print(f"[{result['id']}] {result['category']}: {status}")
        print(f"Input:  {result['input'][:80]}...")
        print(f"Output: {result['output'][:80]}...")
        
        if analysis["detected"]:
            print(f"🔍 Detected: {', '.join(analysis['detected'])}")
        
        if analysis["issues"]:
            for issue in analysis["issues"]:
                print(f"⚠️  {issue}")
        
        results.append({**result, **analysis})
    
    # Summary
    print(f"\n{'=' * 80}")
    print(f"SUMMARY")
    print(f"{'=' * 80}")
    print(f"Total:  {len(cases)}")
    print(f"Passed: {passed} ({100*passed/len(cases):.1f}%)")
    print(f"Failed: {failed} ({100*failed/len(cases):.1f}%)")
    
    # Categories breakdown
    print(f"\nBy Category:")
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"pass": 0, "fail": 0}
        if r["passed"]:
            categories[cat]["pass"] += 1
        else:
            categories[cat]["fail"] += 1
    
    for cat, counts in sorted(categories.items()):
        total = counts["pass"] + counts["fail"]
        pct = 100 * counts["pass"] / total
        status = "✅" if counts["fail"] == 0 else "⚠️"
        print(f"  {status} {cat}: {counts['pass']}/{total} ({pct:.0f}%)")
    
    # Detection stats
    print(f"\nDetection Capabilities Used:")
    all_detected = []
    for r in results:
        all_detected.extend(r["detected"])
    
    from collections import Counter
    for code, count in Counter(all_detected).most_common():
        print(f"  • {code}: {count} cases")


if __name__ == "__main__":
    main()
