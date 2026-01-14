#!/usr/bin/env python3
"""
NNRT Stress Test Runner

Runs stress tests from YAML files with strict pass/fail criteria.

Usage:
    python -m stress_tests.runner                    # Run all tests
    python -m stress_tests.runner tests/case1.yaml   # Run specific test
    python -m stress_tests.runner --verbose          # Detailed output
"""

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from nnrt.core.context import TransformRequest
from nnrt.core.engine import get_engine
from nnrt.cli.main import setup_default_pipeline
from nnrt.policy.loader import clear_cache


@dataclass
class CriterionResult:
    """Result of a single criterion check."""
    criterion_type: str
    pattern: str
    passed: bool
    message: str


@dataclass
class TestResult:
    """Result of a single test case."""
    name: str
    passed: bool
    input_text: str
    output_text: str
    criteria_results: list[CriterionResult] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class SuiteResult:
    """Result of an entire test suite."""
    suite_name: str
    test_results: list[TestResult] = field(default_factory=list)
    
    @property
    def passed_count(self) -> int:
        return sum(1 for t in self.test_results if t.passed)
    
    @property
    def failed_count(self) -> int:
        return sum(1 for t in self.test_results if not t.passed)
    
    @property
    def total_count(self) -> int:
        return len(self.test_results)


# Known bug patterns from schema
GRAMMAR_BUG_PATTERNS = [
    (r"against\s+(me|the|it)\s+against", "double against"),
    (r"forcerce", "word corruption"),
    (r"\scers\b", "truncation"),
    (r"criminalconduct", "missing space"),
    (r"dismissively me\b", "missing preposition"),
    (r"\ba\s+alleged\b", "article mismatch"),
    (r"to affecting\b", "infinitive form broken"),
    (r"was appeared", "double verb"),
]


class StressTestRunner:
    """Runs NNRT stress tests with validation."""
    
    def __init__(self, profile: str = "law_enforcement", verbose: bool = False):
        self.profile = profile
        self.verbose = verbose
        self._engine = None
    
    def _get_engine(self):
        """Get or create the transformation engine."""
        if self._engine is None:
            clear_cache()
            self._engine = get_engine()
            setup_default_pipeline(self._engine, profile=self.profile)
        return self._engine
    
    def transform(self, text: str) -> str:
        """Transform text through the pipeline."""
        engine = self._get_engine()
        req = TransformRequest(text=text)
        result = engine.transform(req)
        return result.rendered_text or ""
    
    def run_suite(self, suite_path: Path) -> SuiteResult:
        """Run all tests in a suite file."""
        with open(suite_path) as f:
            suite_data = yaml.safe_load(f)
        
        suite_name = suite_data.get("name", suite_path.stem)
        result = SuiteResult(suite_name=suite_name)
        
        for test_data in suite_data.get("tests", []):
            test_result = self.run_test(test_data)
            result.test_results.append(test_result)
        
        return result
    
    def run_test(self, test_data: dict) -> TestResult:
        """Run a single test case."""
        name = test_data.get("name", "unnamed")
        input_text = test_data.get("input", "")
        criteria = test_data.get("criteria", {})
        
        try:
            output_text = self.transform(input_text)
        except Exception as e:
            return TestResult(
                name=name,
                passed=False,
                input_text=input_text,
                output_text="",
                error=str(e),
            )
        
        # Run all criteria checks
        criteria_results = []
        
        # Check must_contain
        for pattern in criteria.get("must_contain", []):
            passed = pattern.lower() in output_text.lower()
            criteria_results.append(CriterionResult(
                criterion_type="must_contain",
                pattern=pattern,
                passed=passed,
                message=f"Required text {'found' if passed else 'NOT found'}: '{pattern}'"
            ))
        
        # Check must_not_contain
        for pattern in criteria.get("must_not_contain", []):
            passed = pattern.lower() not in output_text.lower()
            criteria_results.append(CriterionResult(
                criterion_type="must_not_contain",
                pattern=pattern,
                passed=passed,
                message=f"Forbidden text {'not found' if passed else 'FOUND'}: '{pattern}'"
            ))
        
        # Check preserved content
        for pattern in criteria.get("preserved", []):
            passed = pattern in output_text
            criteria_results.append(CriterionResult(
                criterion_type="preserved",
                pattern=pattern,
                passed=passed,
                message=f"Protected content {'preserved' if passed else 'MODIFIED'}: '{pattern}'"
            ))
        
        # Check patterns_absent (regex)
        for pattern_data in criteria.get("patterns_absent", []):
            if isinstance(pattern_data, str):
                pattern = pattern_data
                desc = pattern
            else:
                pattern = pattern_data.get("pattern", "")
                desc = pattern_data.get("description", pattern)
            
            regex = re.compile(pattern, re.IGNORECASE)
            found = regex.search(output_text)
            passed = found is None
            criteria_results.append(CriterionResult(
                criterion_type="patterns_absent",
                pattern=pattern,
                passed=passed,
                message=f"Pattern '{desc}' {'not found' if passed else 'FOUND: ' + (found.group() if found else '')}"
            ))
        
        # Check transformed pairs
        for pair in criteria.get("transformed", []):
            original = pair.get("from", "")
            expected = pair.get("to", "")
            # Check that original is NOT in output and expected IS in output
            orig_gone = original.lower() not in output_text.lower()
            expected_present = expected.lower() in output_text.lower()
            passed = orig_gone and expected_present
            criteria_results.append(CriterionResult(
                criterion_type="transformed",
                pattern=f"{original} → {expected}",
                passed=passed,
                message=f"Transform {'successful' if passed else 'FAILED'}: '{original}' → '{expected}'"
            ))
        
        # Always check for known grammar bugs
        if criteria.get("check_grammar_bugs", True):
            for pattern, desc in GRAMMAR_BUG_PATTERNS:
                regex = re.compile(pattern, re.IGNORECASE)
                found = regex.search(output_text)
                if found:
                    criteria_results.append(CriterionResult(
                        criterion_type="grammar_bug",
                        pattern=pattern,
                        passed=False,
                        message=f"Grammar bug detected ({desc}): '{found.group()}'"
                    ))
        
        # Overall pass/fail
        all_passed = all(r.passed for r in criteria_results)
        
        return TestResult(
            name=name,
            passed=all_passed,
            input_text=input_text,
            output_text=output_text,
            criteria_results=criteria_results,
        )
    
    def print_result(self, result: TestResult):
        """Print a test result."""
        status = "✅ PASS" if result.passed else "❌ FAIL"
        print(f"\n{status}: {result.name}")
        
        if result.error:
            print(f"  ERROR: {result.error}")
            return
        
        if self.verbose or not result.passed:
            # Show failed criteria
            for cr in result.criteria_results:
                if not cr.passed:
                    print(f"  ❌ {cr.message}")
                elif self.verbose:
                    print(f"  ✓ {cr.message}")
        
        if self.verbose:
            print(f"\n  INPUT ({len(result.input_text)} chars):")
            print(f"  {result.input_text[:200]}...")
            print(f"\n  OUTPUT ({len(result.output_text)} chars):")
            print(f"  {result.output_text[:200]}...")


def main():
    parser = argparse.ArgumentParser(description="NNRT Stress Test Runner")
    parser.add_argument("files", nargs="*", help="Test suite YAML files to run")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--profile", default="law_enforcement", help="Policy profile")
    args = parser.parse_args()
    
    runner = StressTestRunner(profile=args.profile, verbose=args.verbose)
    
    # Find test files
    if args.files:
        test_files = [Path(f) for f in args.files]
    else:
        test_dir = Path(__file__).parent
        test_files = list(test_dir.glob("cases/*.yaml"))
    
    if not test_files:
        print("No test files found!")
        return 1
    
    # Run all suites
    total_passed = 0
    total_failed = 0
    
    for test_file in test_files:
        if not test_file.exists():
            print(f"File not found: {test_file}")
            continue
        
        print(f"\n{'=' * 60}")
        print(f"Running: {test_file}")
        print("=" * 60)
        
        suite_result = runner.run_suite(test_file)
        
        for test_result in suite_result.test_results:
            runner.print_result(test_result)
        
        total_passed += suite_result.passed_count
        total_failed += suite_result.failed_count
        
        print(f"\n{suite_result.suite_name}: {suite_result.passed_count}/{suite_result.total_count} passed")
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total: {total_passed + total_failed} tests")
    print(f"Passed: {total_passed}")
    print(f"Failed: {total_failed}")
    
    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
