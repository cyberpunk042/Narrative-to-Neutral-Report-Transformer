#!/usr/bin/env python3
"""
V4 Stress Test for NNRT

Comprehensive stress test that validates:
1. All V4 epistemic types are correctly classified
2. All rendered sections contain appropriate content
3. Critical invariants are enforced
4. No known bugs regress
"""

import sys
import logging
from collections import Counter
from dataclasses import dataclass

# Suppress logging during test
logging.getLogger("nnrt").setLevel(logging.ERROR)

from nnrt.core.engine import Engine
from nnrt.cli.main import setup_default_pipeline, setup_structured_only_pipeline
from nnrt.core.context import TransformRequest
from nnrt.render.structured import format_structured_output


# =============================================================================
# TEST CONFIGURATION
# =============================================================================

@dataclass
class TestResult:
    name: str
    passed: bool
    message: str


def run_stress_test():
    """Run comprehensive V4 stress test."""
    results: list[TestResult] = []
    
    # Load test narrative
    with open("tests/fixtures/stress_test_narrative.txt") as f:
        text = f.read()
    
    # Run pipeline
    engine = Engine()
    setup_default_pipeline(engine, profile="law_enforcement")
    result = engine.transform(TransformRequest(text=text), pipeline_id="default")
    
    report = format_structured_output(
        rendered_text=result.rendered_text,
        atomic_statements=result.atomic_statements,
        entities=result.entities,
        events=result.events,
        identifiers=result.identifiers,
    )
    
    # =========================================================================
    # TEST 1: Epistemic Type Coverage
    # =========================================================================
    epistemic_counts = Counter()
    for stmt in result.atomic_statements:
        epistemic = getattr(stmt, 'epistemic_type', 'unknown')
        epistemic_counts[epistemic] += 1
    
    total_statements = sum(epistemic_counts.values())
    unknown_count = epistemic_counts.get('unknown', 0)
    unknown_pct = (unknown_count / total_statements * 100) if total_statements > 0 else 0
    
    # Should have < 50% unknown
    results.append(TestResult(
        name="Epistemic Coverage",
        passed=unknown_pct < 50,
        message=f"unknown: {unknown_count}/{total_statements} ({unknown_pct:.1f}%)"
    ))
    
    # Should have all key types present
    expected_types = ['direct_event', 'self_report', 'interpretation', 'legal_claim', 'conspiracy_claim']
    for etype in expected_types:
        results.append(TestResult(
            name=f"Has {etype}",
            passed=epistemic_counts.get(etype, 0) > 0,
            message=f"count: {epistemic_counts.get(etype, 0)}"
        ))
    
    # =========================================================================
    # TEST 2: Section Presence
    # =========================================================================
    expected_sections = [
        "OBSERVED EVENTS (INCIDENT SCENE)",
        "OBSERVED EVENTS (FOLLOW-UP ACTIONS)",
        "SELF-REPORTED STATE",
        "REPORTED CLAIMS",
        "REPORTER INTERPRETATIONS",
        "CONTESTED ALLEGATIONS",
        "MEDICAL FINDINGS",
        "ADMINISTRATIVE ACTIONS",
    ]
    
    for section in expected_sections:
        results.append(TestResult(
            name=f"Section: {section[:30]}...",
            passed=section in report,
            message="present" if section in report else "MISSING"
        ))
    
    # =========================================================================
    # TEST 3: Critical Invariants
    # =========================================================================
    
    # INVARIANT: OBSERVED EVENTS (INCIDENT SCENE) should NOT contain interpretive words
    interpretive_words = [
        'horrifying', 'brutal', 'brutally', 'viciously', 'psychotic',
        'innocent', 'criminal', 'clearly', 'obviously', 'deliberately',
        'cover-up', 'whitewash', 'conspiracy'
    ]
    
    if "OBSERVED EVENTS (INCIDENT SCENE)" in report:
        incident_section = report.split("OBSERVED EVENTS (INCIDENT SCENE)")[1]
        # Get just this section (up to next section)
        for end_marker in ["OBSERVED EVENTS (FOLLOW-UP", "REPORTER DESCRIPTIONS", "SELF-REPORTED", "REPORTED CLAIMS"]:
            if end_marker in incident_section:
                incident_section = incident_section.split(end_marker)[0]
                break
        
        found_interpretive = []
        for word in interpretive_words:
            if word.lower() in incident_section.lower():
                found_interpretive.append(word)
        
        results.append(TestResult(
            name="INCIDENT SCENE: No interpretive",
            passed=len(found_interpretive) == 0,
            message=f"found: {found_interpretive}" if found_interpretive else "clean"
        ))
    
    # INVARIANT: SELF-REPORTED STATE should have "Reporter reports:" prefix
    if "SELF-REPORTED STATE" in report:
        self_section = report.split("SELF-REPORTED STATE")[1].split("\n\n")[0]
        has_prefix = "Reporter reports:" in self_section
        results.append(TestResult(
            name="SELF-REPORTED: Has prefix",
            passed=has_prefix,
            message="has 'Reporter reports:'" if has_prefix else "MISSING prefix"
        ))
    
    # INVARIANT: REPORTED CLAIMS should have "Reporter characterizes:" prefix
    if "REPORTED CLAIMS" in report:
        claims_section = report.split("REPORTED CLAIMS")[1].split("\n\n")[0]
        has_prefix = "Reporter characterizes:" in claims_section
        results.append(TestResult(
            name="CLAIMS: Has attribution",
            passed=has_prefix,
            message="has attribution" if has_prefix else "MISSING attribution"
        ))
    
    # INVARIANT: CONTESTED ALLEGATIONS should have warning marker
    if "CONTESTED ALLEGATIONS" in report:
        contested_section = report.split("CONTESTED ALLEGATIONS")[1].split("\n\n")[0]
        has_warning = "⚠️" in contested_section or "Unverified" in contested_section
        results.append(TestResult(
            name="CONTESTED: Has warning",
            passed=has_warning,
            message="has warning" if has_warning else "MISSING warning"
        ))
    
    # =========================================================================
    # TEST 4: Bug Regression Checks
    # =========================================================================
    output = result.rendered_text or ""
    
    regression_checks = [
        ("speaking loudly in pain", "verb_tense_loss"),
        ("against me against", "double_against"),
        ("against against", "double_against"),
        ("forcerce", "word_corruption"),
        (" cers", "truncation"),
        ("criminalconduct", "no_space"),
        ("dismissively me", "missing_at"),
        ("causey", "boundary"),
        ("a alleged", "article"),
        ("to affecting", "infinitive"),
    ]
    
    for pattern, bug_name in regression_checks:
        results.append(TestResult(
            name=f"No regression: {bug_name}",
            passed=pattern not in output,
            message="clean" if pattern not in output else f"FOUND: '{pattern}'"
        ))
    
    # =========================================================================
    # TEST 5: Entity Extraction
    # =========================================================================
    entity_roles = Counter()
    for e in result.entities:
        role = getattr(e, 'role', 'unknown')
        # Handle enum values
        if hasattr(role, 'value'):
            role = role.value
        elif hasattr(role, 'name'):
            role = role.name
        entity_roles[str(role).upper()] += 1
    
    # Should have officers (SUBJECT_OFFICER)
    has_officers = entity_roles.get('SUBJECT_OFFICER', 0) > 0
    results.append(TestResult(
        name="Has officer entities",
        passed=has_officers,
        message=f"officers: {entity_roles.get('SUBJECT_OFFICER', 0)}"
    ))
    
    # Should have witnesses
    has_witnesses = entity_roles.get('WITNESS', 0) > 0
    results.append(TestResult(
        name="Has witness entities",
        passed=has_witnesses,
        message=f"witnesses: {entity_roles.get('WITNESS', 0)}"
    ))
    
    # =========================================================================
    # PRINT RESULTS
    # =========================================================================
    print("=" * 70)
    print("       V4 STRESS TEST RESULTS")
    print("=" * 70)
    
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    
    for r in results:
        status = "✅" if r.passed else "❌"
        print(f"  {status} {r.name.ljust(35)} {r.message}")
    
    print("=" * 70)
    print(f"  TOTAL: {passed} passed, {failed} failed")
    print("=" * 70)
    
    # Epistemic type distribution
    print("\nEpistemic Type Distribution:")
    for etype, count in epistemic_counts.most_common():
        print(f"  {etype.ljust(20)} {count}")
    
    return failed == 0


if __name__ == "__main__":
    success = run_stress_test()
    sys.exit(0 if success else 1)
