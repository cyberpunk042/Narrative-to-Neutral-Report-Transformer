#!/usr/bin/env python3
"""
V5 Stress Test for NNRT

Comprehensive stress test that validates:
1. All V5 epistemic types are correctly classified
2. All rendered sections contain appropriate content
3. Critical invariants are enforced (STRICT)
4. V5 blocking issue fixes are validated
5. No known bugs regress

V5 UPDATES:
- Legal claims split into 4 sub-types
- Medical findings correctly attributed
- Actor resolution working
- Safety scrub applied
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


# =============================================================================
# TEST CONFIGURATION
# =============================================================================

@dataclass
class TestResult:
    name: str
    passed: bool
    message: str
    severity: str = "normal"  # "normal", "critical", "warning"


def run_stress_test():
    """Run comprehensive V5 stress test."""
    results: list[TestResult] = []
    
    # Load test narrative
    with open("tests/fixtures/stress_test_narrative.txt") as f:
        text = f.read()
    
    # Run pipeline
    engine = Engine()
    setup_default_pipeline(engine, profile="law_enforcement")
    result = engine.transform(TransformRequest(text=text), pipeline_id="default")
    
    # Pipeline already includes p90_render_structured which produces structured output
    # Just use result.rendered_text directly - DO NOT call renderer again
    report = result.rendered_text or ""
    
    # =========================================================================
    # TEST 1: Epistemic Type Coverage (V5 Updated)
    # =========================================================================
    epistemic_counts = Counter()
    for stmt in result.atomic_statements:
        epistemic = getattr(stmt, 'epistemic_type', 'unknown')
        epistemic_counts[epistemic] += 1
    
    total_statements = sum(epistemic_counts.values())
    unknown_count = epistemic_counts.get('unknown', 0)
    unknown_pct = (unknown_count / total_statements * 100) if total_statements > 0 else 0
    
    # V5: Stricter - should have < 20% unknown (was 50%)
    results.append(TestResult(
        name="Epistemic Coverage (< 20% unknown)",
        passed=unknown_pct < 20,
        message=f"{unknown_count}/{total_statements} ({unknown_pct:.1f}%)",
        severity="critical"
    ))
    
    # V5: Check for new legal sub-types (Issue #2 fix)
    expected_types = [
        # Original types
        ('direct_event', 'physical actions'),
        ('state_acute', 'emotional states'),
        ('characterization', 'name-calling/invective'),
        ('conspiracy_claim', 'conspiracy language'),
        # V5 NEW: Legal sub-types (Issue #2)
        ('legal_claim_direct', 'direct legal allegations'),
        ('legal_claim_admin', 'admin outcomes'),
        # V5 NEW: Medical finding (Issue #3)
        ('medical_finding', 'provider findings'),
    ]
    
    for etype, description in expected_types:
        count = epistemic_counts.get(etype, 0)
        results.append(TestResult(
            name=f"Has {etype}",
            passed=count > 0,
            message=f"count: {count} ({description})",
            severity="critical" if 'legal_claim' in etype or 'medical' in etype else "normal"
        ))
    
    # V5: Should NOT have old "legal_claim" (should be split)
    old_legal = epistemic_counts.get('legal_claim', 0)
    results.append(TestResult(
        name="No old 'legal_claim' (use sub-types)",
        passed=old_legal == 0,
        message=f"count: {old_legal}" if old_legal > 0 else "correctly using sub-types",
        severity="critical"
    ))
    
    # =========================================================================
    # TEST 2: Section Presence
    # =========================================================================
    # V5: More flexible section detection
    section_checks = [
        ("OBSERVED EVENTS", "incident scene"),
        ("SELF-REPORTED", "self-reported states"),
        ("CHARACTERIZATIONS", "characterizations"),
        ("INFERENCES", "inferences"),
        ("CONTESTED", "contested allegations"),
    ]
    
    for section_pattern, description in section_checks:
        found = section_pattern.upper() in report.upper()
        results.append(TestResult(
            name=f"Section: {description}",
            passed=found,
            message="present" if found else "MISSING",
            severity="normal"
        ))
    
    # =========================================================================
    # TEST 3: Critical Invariants (V5 STRICT)
    # =========================================================================
    
    # V5 CRITICAL: Rendered output should NOT contain raw dangerous language
    # These should all be attributed or removed by safety scrub
    dangerous_in_output = []
    output = result.rendered_text or ""
    output_lower = output.lower()
    
    # These should NEVER appear unattributed in output
    raw_dangerous = [
        'thugs with badges',
        'thug cop',
        'psychotic',
        'they always protect their own',
        'cover-up going on',  # unattributed
        'whitewash',
    ]
    
    for phrase in raw_dangerous:
        if phrase in output_lower and '-- reporter' not in output_lower:
            dangerous_in_output.append(phrase)
    
    results.append(TestResult(
        name="V5: No raw dangerous language",
        passed=len(dangerous_in_output) == 0,
        message=f"FOUND: {dangerous_in_output}" if dangerous_in_output else "clean",
        severity="critical"
    ))
    
    # V5 CRITICAL: Should have attribution markers in output
    has_attribution = '-- reporter' in output_lower or 'reporter alleges' in output_lower
    results.append(TestResult(
        name="V5: Has attribution markers",
        passed=has_attribution,
        message="has attribution" if has_attribution else "MISSING attribution markers",
        severity="critical"
    ))
    
    # INVARIANT: OBSERVED EVENTS should NOT contain interpretive words
    interpretive_words = [
        'horrifying', 'brutal', 'brutally', 'viciously', 'psychotic',
        'innocent', 'criminal', 'clearly', 'obviously', 'deliberately',
        'cover-up', 'whitewash', 'conspiracy'
    ]
    
    if "OBSERVED EVENTS" in report.upper():
        # Find the observed events section
        report_upper = report.upper()
        start_idx = report_upper.find("OBSERVED EVENTS")
        # Find the next section header (all caps header pattern)
        end_markers = ["SELF-REPORTED", "REPORTER", "LEGAL", "CONTESTED", "ADMINISTRATIVE"]
        end_idx = len(report)
        for marker in end_markers:
            idx = report_upper.find(marker, start_idx + 20)
            if idx > 0 and idx < end_idx:
                end_idx = idx
        
        incident_section = report[start_idx:end_idx].lower()
        
        found_interpretive = []
        for word in interpretive_words:
            if word in incident_section:
                found_interpretive.append(word)
        
        results.append(TestResult(
            name="OBSERVED: No interpretive language",
            passed=len(found_interpretive) == 0,
            message=f"found: {found_interpretive}" if found_interpretive else "clean",
            severity="critical"
        ))
    
    # =========================================================================
    # TEST 4: V5 Blocking Issues Validation
    # =========================================================================
    
    # ISSUE #2: Legal claims should be split into sub-types
    legal_subtypes = ['legal_claim_direct', 'legal_claim_admin', 
                      'legal_claim_causation', 'legal_claim_attorney']
    legal_subtype_count = sum(epistemic_counts.get(t, 0) for t in legal_subtypes)
    results.append(TestResult(
        name="V5 Issue #2: Legal taxonomy split",
        passed=legal_subtype_count > 5,  # Should have many
        message=f"legal sub-types: {legal_subtype_count}",
        severity="critical"
    ))
    
    # ISSUE #3: Medical findings should exist
    medical_count = epistemic_counts.get('medical_finding', 0)
    results.append(TestResult(
        name="V5 Issue #3: Medical findings exist",
        passed=medical_count > 0,
        message=f"count: {medical_count}",
        severity="critical"
    ))
    
    # ISSUE #5: Check for invective scrubbing in output
    # V7.2 FIX: Use word-bounded matching to allow 'brutality' (legitimate term)
    # while still catching standalone 'brutal' (invective)
    import re
    invective = ['thug', 'psychotic', 'maniac', 'brutal', 'vicious']
    found_invective = [w for w in invective if re.search(rf'\b{w}\b(?!ity)', output_lower)]
    results.append(TestResult(
        name="V5 Issue #5: Invective removed from output",
        passed=len(found_invective) == 0,
        message=f"found: {found_invective}" if found_invective else "clean",
        severity="critical"
    ))
    
    # =========================================================================
    # TEST 5: Bug Regression Checks
    # =========================================================================
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
            message="clean" if pattern not in output else f"FOUND: '{pattern}'",
            severity="normal"
        ))
    
    # =========================================================================
    # TEST 6: Entity Extraction
    # =========================================================================
    entity_roles = Counter()
    for e in result.entities:
        role = getattr(e, 'role', 'unknown')
        if hasattr(role, 'value'):
            role = role.value
        elif hasattr(role, 'name'):
            role = role.name
        entity_roles[str(role).upper()] += 1
    
    # Should have officers
    has_officers = entity_roles.get('SUBJECT_OFFICER', 0) > 0
    results.append(TestResult(
        name="Has officer entities",
        passed=has_officers,
        message=f"officers: {entity_roles.get('SUBJECT_OFFICER', 0)}",
        severity="normal"
    ))
    
    # Should have witnesses
    has_witnesses = entity_roles.get('WITNESS', 0) > 0
    results.append(TestResult(
        name="Has witness entities",
        passed=has_witnesses,
        message=f"witnesses: {entity_roles.get('WITNESS', 0)}",
        severity="normal"
    ))
    
    # =========================================================================
    # PRINT RESULTS
    # =========================================================================
    print("=" * 80)
    print("                    V5 STRESS TEST RESULTS")
    print("=" * 80)
    
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    critical_failed = sum(1 for r in results if not r.passed and r.severity == "critical")
    
    # Group by severity
    critical_results = [r for r in results if r.severity == "critical"]
    normal_results = [r for r in results if r.severity == "normal"]
    
    print("\n🔴 CRITICAL CHECKS:")
    print("-" * 80)
    for r in critical_results:
        status = "✅" if r.passed else "❌"
        print(f"  {status} {r.name.ljust(40)} {r.message}")
    
    print("\n📋 STANDARD CHECKS:")
    print("-" * 80)
    for r in normal_results:
        status = "✅" if r.passed else "❌"
        print(f"  {status} {r.name.ljust(40)} {r.message}")
    
    print("\n" + "=" * 80)
    print(f"  TOTAL: {passed} passed, {failed} failed ({critical_failed} critical)")
    print("=" * 80)
    
    # Epistemic type distribution
    print("\n📊 Epistemic Type Distribution:")
    print("-" * 40)
    for etype, count in epistemic_counts.most_common():
        bar = "█" * min(count, 30)
        print(f"  {etype.ljust(22)} {count:3d} {bar}")
    
    # V5 Summary
    print("\n" + "=" * 80)
    print("V5 BLOCKING ISSUES STATUS:")
    print("-" * 80)
    
    v5_checks = {
        "Issue #1 Actor Resolution": has_officers and has_witnesses,
        "Issue #2 Legal Taxonomy": legal_subtype_count > 5,
        "Issue #3 Medical Finding": medical_count > 0,
        "Issue #5 Attribution": has_attribution and len(found_invective) == 0,
    }
    
    for issue, passed in v5_checks.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {issue}")
    
    print("=" * 80)
    
    # V5: Fail if ANY critical check fails
    if critical_failed > 0:
        print(f"\n❌ STRESS TEST FAILED: {critical_failed} critical checks failed")
        return False
    else:
        print(f"\n✅ STRESS TEST PASSED: All critical checks passed")
        return True


if __name__ == "__main__":
    success = run_stress_test()
    sys.exit(0 if success else 1)
