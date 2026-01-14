"""
Integration tests for the full NNRT pipeline.

Tests transformation behavior with realistic synthetic narratives.
"""

import pytest

from nnrt.core.context import TransformRequest
from nnrt.core.engine import Engine, Pipeline
from nnrt.ir.enums import SpanLabel, TransformStatus
from nnrt.passes import (
    augment_ir,
    build_ir,
    evaluate_policy,
    extract_identifiers,
    normalize,
    package,
    render,
    segment,
    tag_spans,
)


@pytest.fixture
def engine():
    """Create an engine with the default pipeline."""
    eng = Engine()
    pipeline = Pipeline(
        id="default",
        name="Default NNRT Pipeline",
        passes=[
            normalize,
            segment,
            tag_spans,
            extract_identifiers,
            build_ir,
            evaluate_policy,
            augment_ir,
            render,
            package,
        ],
    )
    eng.register_pipeline(pipeline)
    return eng


class TestBasicTransformation:
    """Tests for basic text transformation."""

    def test_simple_narrative_preserved(self, engine):
        """Simple factual narrative should be largely preserved."""
        text = "I was walking home. A person approached me. They asked for directions."
        
        request = TransformRequest(text=text)
        result = engine.transform(request)
        
        assert result.status in (TransformStatus.SUCCESS, TransformStatus.PARTIAL)
        assert result.rendered_text is not None
        assert len(result.segments) == 3
        # Core content should be preserved
        assert "walking" in result.rendered_text
        assert "directions" in result.rendered_text

    def test_segments_created(self, engine):
        """Text should be segmented into sentences."""
        text = "First sentence. Second sentence. Third sentence."
        
        request = TransformRequest(text=text)
        result = engine.transform(request)
        
        assert len(result.segments) == 3
        assert result.segments[0].text == "First sentence."
        assert result.segments[1].text == "Second sentence."
        assert result.segments[2].text == "Third sentence."


class TestIntentAttributionRemoval:
    """Tests for removal/transformation of intent attribution."""

    def test_clearly_removed(self, engine):
        """'clearly' should be removed as an intensifier."""
        text = "He clearly wanted to harm me."
        
        request = TransformRequest(text=text)
        result = engine.transform(request)
        
        assert "clearly" not in result.rendered_text.lower()

    def test_intentionally_removed(self, engine):
        """'intentionally' should be removed."""
        text = "She intentionally ignored my request."
        
        request = TransformRequest(text=text)
        result = engine.transform(request)
        
        assert "intentionally" not in result.rendered_text.lower()
        # Core action should be preserved
        assert "ignored" in result.rendered_text.lower()

    def test_wanted_to_becomes_appeared_to(self, engine):
        """'wanted to' should become 'appeared to'."""
        text = "He wanted to intimidate me."
        
        request = TransformRequest(text=text)
        result = engine.transform(request)
        
        assert "wanted to" not in result.rendered_text.lower()
        assert "appeared to" in result.rendered_text.lower()

    def test_tried_to_becomes_appeared_to(self, engine):
        """'tried to' should become 'appeared to'."""
        text = "She tried to provoke a reaction."
        
        request = TransformRequest(text=text)
        result = engine.transform(request)
        
        assert "tried to" not in result.rendered_text.lower()
        assert "appeared to" in result.rendered_text.lower()


class TestInterpretationReframing:
    """Tests for reframing subjective interpretations."""

    def test_suspicious_reframed(self, engine):
        """'suspicious' should be reframed as 'described as suspicious'."""
        text = "He called me suspicious."
        
        request = TransformRequest(text=text)
        result = engine.transform(request)
        
        assert "described as suspicious" in result.rendered_text.lower()

    def test_aggressive_reframed(self, engine):
        """'aggressive' should be reframed."""
        text = "His behavior was aggressive."
        
        request = TransformRequest(text=text)
        result = engine.transform(request)
        
        assert "described as aggressive" in result.rendered_text.lower()


class TestDiagnostics:
    """Tests for diagnostic generation."""

    def test_intent_attribution_flagged(self, engine):
        """Intent attribution should generate a diagnostic."""
        text = "He intentionally blocked my exit."
        
        request = TransformRequest(text=text)
        result = engine.transform(request)
        
        intent_diags = [d for d in result.diagnostics 
                        if d.code == "INTENT_ATTRIBUTION_DETECTED"]
        assert len(intent_diags) >= 1

    def test_trace_entries_created(self, engine):
        """Pipeline should create trace entries."""
        text = "A simple test sentence."
        
        request = TransformRequest(text=text)
        result = engine.transform(request)
        
        # Should have trace entries for each pass
        pass_names = {t.pass_name for t in result.trace}
        assert "p00_normalize" in pass_names
        assert "p10_segment" in pass_names
        assert "p20_tag_spans" in pass_names


class TestRealWorldScenarios:
    """Tests with realistic narrative scenarios."""

    def test_police_encounter_narrative(self, engine):
        """Test transformation of a police encounter narrative."""
        text = (
            "I was walking home around 11 PM when a police officer stopped me. "
            "He said I looked suspicious. "
            "He clearly wanted to intimidate me, standing way too close and staring at me. "
            "He intentionally blocked my path. "
            "After 20 minutes he let me go without any explanation."
        )
        
        request = TransformRequest(text=text)
        result = engine.transform(request)
        
        assert result.status in (TransformStatus.SUCCESS, TransformStatus.PARTIAL)
        
        # Intent language should be transformed
        assert "clearly wanted to" not in result.rendered_text
        assert "intentionally" not in result.rendered_text
        
        # Core facts should be preserved
        assert "11 PM" in result.rendered_text
        assert "police officer" in result.rendered_text
        assert "20 minutes" in result.rendered_text
        
        # Should have diagnostics for problematic content
        assert len(result.diagnostics) > 0

    def test_witness_narrative(self, engine):
        """Test transformation of a witness narrative."""
        text = (
            "I saw two officers approach a man on the corner. "
            "One officer grabbed him aggressively. "
            "The man fell to the ground. "
            "I believe the officer used excessive force."
        )
        
        request = TransformRequest(text=text)
        result = engine.transform(request)
        
        # Factual observations should be preserved
        assert "two officers" in result.rendered_text.lower()
        assert "fell to the ground" in result.rendered_text.lower()
        
        # Interpretive language should be transformed
        assert "aggressively" not in result.rendered_text.lower() or \
               "described as" in result.rendered_text.lower()

    def test_preserves_direct_quotes(self, engine):
        """Direct quotes should be preserved."""
        text = 'He said "Show me your ID" in a loud voice.'
        
        request = TransformRequest(text=text)
        result = engine.transform(request)
        
        # Quote content should be preserved
        assert "Show me your ID" in result.rendered_text

    def test_temporal_markers_preserved(self, engine):
        """Temporal markers should be preserved."""
        text = "At approximately 3:45 PM on January 5th, the incident occurred."
        
        request = TransformRequest(text=text)
        result = engine.transform(request)
        
        assert "3:45 PM" in result.rendered_text
        assert "January 5th" in result.rendered_text


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_input(self, engine):
        """Empty input should be handled gracefully."""
        text = ""
        
        request = TransformRequest(text=text)
        result = engine.transform(request)
        
        assert result.status in (TransformStatus.SUCCESS, TransformStatus.PARTIAL)

    def test_whitespace_only(self, engine):
        """Whitespace-only input should be handled gracefully."""
        text = "   \n\t  "
        
        request = TransformRequest(text=text)
        result = engine.transform(request)
        
        # Should not crash
        assert result is not None

    def test_very_long_sentence(self, engine):
        """Very long sentences should be handled."""
        text = "I " + "walked and " * 50 + "stopped."
        
        request = TransformRequest(text=text)
        result = engine.transform(request)
        
        assert result.status in (TransformStatus.SUCCESS, TransformStatus.PARTIAL)

    def test_unicode_content(self, engine):
        """Unicode content should be preserved."""
        text = 'He said "Hello" — with an accent: café résumé.'
        
        request = TransformRequest(text=text)
        result = engine.transform(request)
        
        assert "café" in result.rendered_text
        assert "résumé" in result.rendered_text
