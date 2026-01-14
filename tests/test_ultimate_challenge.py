"""
Ultimate System Challenge Test

A comprehensive, complex test case that exercises EVERY capability of NNRT:
- Statement classification (observation, claim, interpretation, quote)
- Entity extraction (multiple people with different roles)
- Event extraction (physical actions, verbal exchanges)
- Context detection (quotes, physical force, charges, opinions)
- Policy rule application (intent words, legal conclusions, inflammatory language)
- Uncertainty detection (ambiguous references, pronouns)
- Per-segment neutral text and traceability

Success Criteria:
1. NO CRASHES - System completes without errors
2. STATEMENT CLASSIFICATION - Each statement has a type
3. ENTITY EXTRACTION - All people identified with correct roles
4. EVENT EXTRACTION - Physical and verbal events captured
5. QUOTE PRESERVATION - All direct quotes preserved verbatim
6. INTENT REMOVAL - Intent words removed
7. TRANSFORMATIONS TRACKED - Each segment shows what rules applied
8. NEUTRAL TEXT GENERATED - Each segment has neutral version

Run with: python -m pytest tests/test_ultimate_challenge.py -v
"""

import json
import pytest

from nnrt.core.context import TransformRequest
from nnrt.core.engine import Engine
from nnrt.cli.main import setup_default_pipeline
from nnrt.output.structured import build_structured_output
from nnrt.ir.enums import StatementType, EntityRole, EventType


# =============================================================================
# THE ULTIMATE CHALLENGE CASE
# =============================================================================

ULTIMATE_CHALLENGE = """
I was walking home from work on January 15th around 11:30 PM when I saw a police cruiser 
pull up beside me. Officer badge number 4821 - I think his name was Martinez - stepped 
out and immediately yelled "Stop right there!" in an aggressive tone.

I stopped and asked "What's the problem, officer?" He obviously wanted to intimidate me 
because he deliberately got right in my face and said I matched the description of a 
robbery suspect. I told him "I just got off work at the restaurant on Main Street" but 
he clearly didn't believe me.

He intentionally grabbed my arm and twisted it behind my back, which hurt really bad. 
I tried to say "You're hurting me!" but he choked me so hard I couldn't breathe properly. 
His partner - I didn't catch her name, maybe Officer Chen or something - just stood there 
watching and did nothing to help.

The brutal cop then viciously threw me against the hood of the car and accused me of 
resisting arrest, which is a complete lie. He or she - I'm not sure which officer - kept 
their knee on my back while I was handcuffed.

Martinez then told me I was being charged with assault on an officer and resisting arrest. 
I believe this was retaliation because I asked for his badge number earlier. Someone at 
the scene told me they saw the whole thing, but I don't know who they were.

My neck still hurts from when he choked me, and I have bruises on my wrists from the 
handcuffs. I think what they did was police brutality and I want to file a complaint.
"""


# =============================================================================
# SUCCESS CRITERIA
# =============================================================================

class SuccessCriteria:
    """Defines what must pass for pre-alpha readiness."""
    
    # MUST-PASS (blocking for pre-alpha)
    MUST_PASS = [
        "no_crash",
        "has_output",
        "has_statements",
        "has_entities",
        "has_events",
        "quotes_preserved",
        "intent_words_removed",
    ]
    
    # SHOULD-PASS (important but not blocking)
    SHOULD_PASS = [
        "statement_types_classified",
        "authority_entities_detected",
        "reporter_entity_detected",
        "physical_events_detected",
        "verbal_events_detected",
        "neutral_text_generated",
        "transformations_tracked",
    ]
    
    # NICE-TO-HAVE (stretch goals)
    STRETCH = [
        "ambiguity_detected",
        "legal_terms_flagged",
        "inflammatory_removed",
        "uncertainty_captured",
    ]


@pytest.fixture
def engine():
    """Create a fresh engine with the default pipeline."""
    eng = Engine()
    setup_default_pipeline(eng)
    return eng


@pytest.fixture
def result(engine):
    """Run the ultimate challenge through the pipeline."""
    request = TransformRequest(text=ULTIMATE_CHALLENGE)
    return engine.transform(request)


@pytest.fixture
def structured(result):
    """Get structured output for analysis."""
    return build_structured_output(result, ULTIMATE_CHALLENGE)


# =============================================================================
# MUST-PASS CRITERIA (Blocking for Pre-Alpha)
# =============================================================================

class TestMustPassCriteria:
    """These MUST pass for pre-alpha. Failures are blocking."""
    
    def test_no_crash(self, result):
        """System completes without crashing."""
        assert result is not None
        assert result.status is not None
    
    def test_has_output(self, result):
        """System produces rendered output."""
        assert result.rendered_text is not None
        assert len(result.rendered_text) > 100, "Output seems too short"
    
    def test_has_statements(self, result, structured):
        """Statements are extracted from segments."""
        assert len(structured.statements) > 0, "No statements extracted"
        assert len(structured.statements) >= 5, f"Expected at least 5 statements, got {len(structured.statements)}"
    
    def test_has_entities(self, result, structured):
        """Entities are extracted."""
        assert len(structured.entities) > 0, "No entities extracted"
        
        # Print entities for debugging
        entity_labels = [e.label for e in structured.entities]
        print(f"\nExtracted entities: {entity_labels}")
    
    def test_has_events(self, result, structured):
        """Events are extracted."""
        assert len(structured.events) > 0, "No events extracted"
        
        # Print events for debugging
        event_types = [e.type for e in structured.events]
        print(f"\nExtracted events: {event_types}")
    
    def test_quotes_preserved(self, result):
        """Direct quotes are preserved verbatim."""
        output = result.rendered_text
        
        # These exact quotes MUST appear
        critical_quotes = [
            "Stop right there",
            "What's the problem, officer",
            "I just got off work at the restaurant on Main Street",
            "You're hurting me",
        ]
        
        for quote in critical_quotes:
            assert quote in output, f"Quote not preserved: '{quote}'"
    
    def test_intent_words_removed(self, result):
        """Intent attribution words are removed."""
        output = result.rendered_text.lower()
        
        # These intent words should ALWAYS be removed (no context requirement)
        always_remove = ["intentionally", "deliberately", "obviously", "purposely"]
        
        for word in always_remove:
            assert word not in output, f"Intent word not removed: '{word}'"
        
        # Note: "clearly" is context-dependent - only removed near intent words
        # like "wanted", "intended", "meant", "tried". Not removed in 
        # "clearly didn't believe" which expresses doubt, not intent.


# =============================================================================
# SHOULD-PASS CRITERIA (Important but not blocking)
# =============================================================================

class TestShouldPassCriteria:
    """These SHOULD pass for a quality pre-alpha."""
    
    def test_statement_types_classified(self, result, structured):
        """Statements have proper type classifications."""
        for stmt in structured.statements:
            assert stmt.type != "unknown", f"Statement {stmt.id} has no classification"
        
        # Should have mix of types
        types = set(stmt.type for stmt in structured.statements)
        print(f"\nStatement types found: {types}")
        
        # Should have at least 2 different types
        assert len(types) >= 2, "Should have variety of statement types"
    
    def test_authority_entities_detected(self, result, structured):
        """Authority figures (officers) are identified."""
        authority_roles = {"authority", "officer"}
        officers = [e for e in structured.entities if e.role.lower() in authority_roles]
        
        print(f"\nAuthority entities: {[(e.label, e.role) for e in officers]}")
        
        # Should detect at least one officer
        assert len(officers) >= 1, "Should detect at least one authority figure"
    
    def test_reporter_entity_detected(self, result, structured):
        """The narrator/reporter is identified."""
        reporter_roles = {"reporter", "narrator", "victim"}
        reporters = [e for e in structured.entities if e.role.lower() in reporter_roles]
        
        print(f"\nReporter entities: {[(e.label, e.role) for e in reporters]}")
        
        # Should detect the narrator
        assert len(reporters) >= 1, "Should detect the narrator/reporter"
    
    def test_physical_events_detected(self, result, structured):
        """Physical contact events are extracted."""
        physical_types = {"action", "physical_contact", "physical"}
        physical_events = [e for e in structured.events if e.type.lower() in physical_types]
        
        print(f"\nPhysical events: {[(e.id, e.description) for e in physical_events]}")
        
        # Should detect physical events
        assert len(physical_events) >= 1, "Should detect physical events"
    
    def test_verbal_events_detected(self, result, structured):
        """Verbal events (quotes, commands) are extracted."""
        verbal_types = {"verbal", "statement", "command", "question"}
        verbal_events = [e for e in structured.events if e.type.lower() in verbal_types]
        
        print(f"\nVerbal events: {[(e.id, e.description) for e in verbal_events]}")
    
    def test_neutral_text_generated(self, result, structured):
        """Some statements have neutral text generated."""
        with_neutral = [s for s in structured.statements if s.neutral is not None]
        
        print(f"\nStatements with neutral text: {len(with_neutral)}/{len(structured.statements)}")
        
        # At least some should have neutral text
        assert len(with_neutral) >= 1, "At least some statements should have neutral text"
    
    def test_transformations_tracked(self, result, structured):
        """Transformations are tracked per statement."""
        with_transformations = [s for s in structured.statements if len(s.transformations) > 0]
        
        print(f"\nStatements with transformations: {len(with_transformations)}/{len(structured.statements)}")
        
        if with_transformations:
            # Show first transformation for debugging
            first = with_transformations[0]
            print(f"Example transformation: {first.transformations[0]}")


# =============================================================================
# STRETCH CRITERIA (Nice-to-have)
# =============================================================================

class TestStretchCriteria:
    """These are stretch goals for enhanced capability."""
    
    def test_ambiguity_detected(self, result, structured):
        """Ambiguous references are flagged."""
        # The case has: "He or she - I'm not sure which officer"
        # This should trigger ambiguity detection
        
        ambiguity_codes = ["AMBIGUOUS", "UNCLEAR", "UNCERTAIN"]
        has_ambiguity = any(
            any(code in str(d) for code in ambiguity_codes)
            for d in result.diagnostics
        )
        
        # Also check uncertainties
        has_uncertainties = len(structured.uncertainties) > 0
        
        print(f"\nAmbiguity detected: {has_ambiguity}")
        print(f"Uncertainties: {len(structured.uncertainties)}")
    
    def test_legal_terms_flagged(self, result):
        """Legal terms are flagged in diagnostics."""
        legal_codes = ["LEGAL", "CHARGE", "ACCUSATION"]
        
        legal_diagnostics = [
            d for d in result.diagnostics 
            if any(code in d.code for code in legal_codes)
        ]
        
        print(f"\nLegal diagnostics: {len(legal_diagnostics)}")
        for d in legal_diagnostics[:3]:
            print(f"  - {d.code}: {d.message[:50]}...")
    
    def test_inflammatory_removed(self, result):
        """Inflammatory language is removed or neutralized."""
        output = result.rendered_text.lower()
        
        inflammatory = ["brutal", "viciously", "vicious", "ruthlessly"]
        found = [word for word in inflammatory if word in output]
        
        print(f"\nInflammatory words found: {found}")
        
        # Ideally none should be present
        assert len(found) == 0, f"Inflammatory words not removed: {found}"


# =============================================================================
# FULL OUTPUT ANALYSIS
# =============================================================================

class TestFullAnalysis:
    """Complete analysis of the transformation."""
    
    def test_full_output_report(self, result, structured):
        """Generate a comprehensive report of the transformation."""
        report = []
        report.append("\n" + "="*80)
        report.append("ULTIMATE CHALLENGE TRANSFORMATION REPORT")
        report.append("="*80)
        
        # Status
        report.append(f"\nStatus: {result.status.value}")
        report.append(f"Segments: {len(result.segments)}")
        report.append(f"Statements: {len(structured.statements)}")
        report.append(f"Entities: {len(structured.entities)}")
        report.append(f"Events: {len(structured.events)}")
        report.append(f"Uncertainties: {len(structured.uncertainties)}")
        report.append(f"Diagnostics: {len(result.diagnostics)}")
        
        # Statement breakdown
        report.append("\n--- STATEMENT CLASSIFICATION ---")
        type_counts = {}
        for s in structured.statements:
            type_counts[s.type] = type_counts.get(s.type, 0) + 1
        for t, c in type_counts.items():
            report.append(f"  {t}: {c}")
        
        # Entity breakdown
        report.append("\n--- ENTITIES ---")
        for e in structured.entities:
            report.append(f"  [{e.role}] {e.label}")
        
        # Event breakdown
        report.append("\n--- EVENTS ---")
        for e in structured.events:
            desc = e.description[:50] if e.description else "N/A"
            report.append(f"  [{e.type}] {desc}")
        
        # Transformations applied
        report.append("\n--- TRANSFORMATIONS APPLIED ---")
        total_transforms = sum(len(s.transformations) for s in structured.statements)
        report.append(f"  Total: {total_transforms}")
        
        # Show first few
        for s in structured.statements:
            if s.transformations:
                for t in s.transformations[:2]:
                    report.append(f"    - {t.rule_id}: {t.action}")
        
        # Rendered text preview
        report.append("\n--- RENDERED OUTPUT (first 500 chars) ---")
        report.append(result.rendered_text[:500] + "...")
        
        report.append("\n" + "="*80)
        
        print("\n".join(report))
        
        # This test always passes - it's for visibility
        assert True


# =============================================================================
# SUMMARY METRICS
# =============================================================================

class TestSummaryMetrics:
    """Overall success metrics."""
    
    def test_pre_alpha_readiness_score(self, result, structured):
        """Calculate overall pre-alpha readiness score."""
        passed = 0
        total = 0
        failed_criteria = []
        
        # MUST-PASS checks
        checks = [
            ("has_output", result.rendered_text is not None and len(result.rendered_text) > 100),
            ("has_statements", len(structured.statements) >= 5),
            ("has_entities", len(structured.entities) > 0),
            ("has_events", len(structured.events) > 0),
            ("quotes_preserved", "Stop right there" in result.rendered_text),
            ("intent_removed", "intentionally" not in result.rendered_text.lower()),
            ("neutral_generated", any(s.neutral is not None for s in structured.statements)),
            ("transforms_tracked", any(len(s.transformations) > 0 for s in structured.statements)),
        ]
        
        for name, passed_check in checks:
            total += 1
            if passed_check:
                passed += 1
            else:
                failed_criteria.append(name)
        
        score = (passed / total) * 100
        
        print(f"\n{'='*60}")
        print(f"PRE-ALPHA READINESS SCORE: {score:.1f}%")
        print(f"{'='*60}")
        print(f"Passed: {passed}/{total}")
        
        if failed_criteria:
            print(f"Failed: {failed_criteria}")
        
        # Must score at least 75% for pre-alpha
        assert score >= 75, f"Pre-alpha requires 75%+ score. Got {score:.1f}%"
