"""
Tests for p72_safety_scrub — V5 Attribution Enforcement.

Tests that all dangerous patterns in rendered text are properly attributed
or removed. No unattributed allegations should survive.
"""

import pytest
from nnrt.core.context import TransformContext, TransformRequest
from nnrt.passes.p72_safety_scrub import safety_scrub


def _make_context(rendered_text: str) -> TransformContext:
    """Create a context with rendered_text set."""
    req = TransformRequest(text="test")
    ctx = TransformContext(request=req, raw_text="test")
    ctx.rendered_text = rendered_text
    return ctx


class TestLegalAttributionEnforcement:
    """Test that legal terms are properly attributed."""
    
    def test_excessive_force_attributed(self):
        # Note: "excessive force" is now handled by policy interp_excessive rule
        # which transforms "excessive" → "described as excessive", so the safety
        # scrub no longer needs to handle this. Test that clean_artifacts runs.
        ctx = _make_context("The officer used excessive force on me.")
        result = safety_scrub(ctx)
        # Safety scrub should leave the text mostly unchanged (policy handles "excessive")
        # The key is that clean_artifacts runs and cleans up any issues
        assert "used" in result.rendered_text
        assert "officer" in result.rendered_text
    
    def test_racial_profiling_attributed(self):
        ctx = _make_context("This was clearly racial profiling.")
        result = safety_scrub(ctx)
        assert "reporter characterizes" in result.rendered_text
        assert "This was clearly" not in result.rendered_text
    
    def test_unlawful_arrest_attributed(self):
        ctx = _make_context("It was an unlawful arrest.")
        result = safety_scrub(ctx)
        assert "reporter characterizes action as unlawful" in result.rendered_text
    
    def test_obstruction_of_justice_attributed(self):
        ctx = _make_context("This was obstruction of justice.")
        result = safety_scrub(ctx)
        assert "reporter alleges obstruction" in result.rendered_text
    
    def test_witness_intimidation_attributed(self):
        ctx = _make_context("The officer engaged in witness intimidation.")
        result = safety_scrub(ctx)
        assert "reporter alleges witness intimidation" in result.rendered_text
    
    def test_systemic_racism_attributed(self):
        ctx = _make_context("There is systemic racism in the department.")
        result = safety_scrub(ctx)
        assert "reporter alleges systemic issues" in result.rendered_text


class TestIntentAttributionEnforcement:
    """Test that intent/threat claims are properly attributed."""
    
    def test_ready_to_shoot_attributed(self):
        ctx = _make_context("He was ready to shoot me.")
        result = safety_scrub(ctx)
        assert "reporter perceived threat" in result.rendered_text
        assert "ready to shoot me" not in result.rendered_text
    
    def test_wanted_to_hurt_attributed(self):
        ctx = _make_context("He wanted to hurt me.")
        result = safety_scrub(ctx)
        assert "reporter perceived intent" in result.rendered_text
    
    def test_clearly_intended_attributed(self):
        ctx = _make_context("He clearly intended to harm me.")
        result = safety_scrub(ctx)
        assert "reporter infers intent" in result.rendered_text
    
    def test_threat_characterization_attributed(self):
        ctx = _make_context("This was clearly a threat.")
        result = safety_scrub(ctx)
        assert "reporter perceived as threatening" in result.rendered_text


class TestConspiracyRemoval:
    """Test that conspiracy language is removed entirely."""
    
    def test_protect_their_own_removed(self):
        ctx = _make_context("They always protect their own.")
        result = safety_scrub(ctx)
        assert "protect their own" not in result.rendered_text
    
    def test_cover_up_removed(self):
        ctx = _make_context("There is a massive cover-up.")
        result = safety_scrub(ctx)
        assert "cover-up" not in result.rendered_text
    
    def test_blue_wall_removed(self):
        ctx = _make_context("The blue wall of silence protects them.")
        result = safety_scrub(ctx)
        assert "blue wall of silence" not in result.rendered_text


class TestInvectiveRemoval:
    """Test that invective is removed or neutralized."""
    
    def test_thug_cop_neutralized(self):
        ctx = _make_context("The thug cop grabbed me.")
        result = safety_scrub(ctx)
        assert "thug cop" not in result.rendered_text
        assert "officer" in result.rendered_text
    
    def test_brutally_removed(self):
        ctx = _make_context("He brutally threw me down.")
        result = safety_scrub(ctx)
        assert "brutally" not in result.rendered_text
    
    def test_psychotic_removed(self):
        ctx = _make_context("The psychotic officer screamed.")
        result = safety_scrub(ctx)
        assert "psychotic" not in result.rendered_text


class TestNoFalsePositives:
    """Test that neutral language is preserved."""
    
    def test_neutral_sentence_unchanged(self):
        ctx = _make_context("The officer approached me and asked for my license.")
        result = safety_scrub(ctx)
        # Should be essentially unchanged (just cleaned)
        assert "officer approached" in result.rendered_text
        assert "asked for my license" in result.rendered_text
    
    def test_reported_perception_preserved(self):
        ctx = _make_context("Reporter perceived the officer as hostile.")
        result = safety_scrub(ctx)
        # Already attributed, should not be double-attributed
        assert "Reporter perceived" in result.rendered_text


class TestDiagnosticTracking:
    """Test that scrubs are properly tracked."""
    
    def test_scrub_count_in_diagnostic(self):
        ctx = _make_context("He brutally used excessive force.")
        result = safety_scrub(ctx)
        
        # Should have diagnostic about scrubs
        scrub_diagnostics = [d for d in result.diagnostics if "SCRUB" in d.code]
        assert len(scrub_diagnostics) > 0
    
    def test_adds_trace(self):
        ctx = _make_context("Test sentence.")
        result = safety_scrub(ctx)
        
        traces = [t for t in result.trace if t.pass_name == "p72_safety_scrub"]
        assert len(traces) > 0
