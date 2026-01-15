"""
Unit tests for p22_classify_statements pass.
"""

import pytest
from nnrt.core.context import TransformContext, TransformRequest
from nnrt.ir.schema_v0_1 import Segment
from nnrt.ir.enums import StatementType, SegmentContext
from nnrt.passes.p22_classify_statements import classify_statements


def _make_context(text: str) -> TransformContext:
    """Helper to create a context with a segment."""
    req = TransformRequest(text=text)
    ctx = TransformContext(request=req, raw_text=text)
    ctx.segments = [Segment(id="seg_1", text=text, start_char=0, end_char=len(text))]
    return ctx


class TestObservationClassification:
    """Tests for OBSERVATION classification."""
    
    def test_i_saw_is_observation(self):
        """Verify 'I saw' triggers OBSERVATION."""
        ctx = _make_context("I saw him grab my arm.")
        
        classify_statements(ctx)
        
        assert ctx.segments[0].statement_type == StatementType.OBSERVATION
    
    def test_i_heard_is_observation(self):
        """Verify 'I heard' triggers OBSERVATION."""
        ctx = _make_context("I heard him yelling.")
        
        classify_statements(ctx)
        
        assert ctx.segments[0].statement_type == StatementType.OBSERVATION
    
    def test_i_felt_is_observation(self):
        """Verify 'I felt' triggers OBSERVATION."""
        ctx = _make_context("I felt pain in my arm.")
        
        classify_statements(ctx)
        
        assert ctx.segments[0].statement_type == StatementType.OBSERVATION
    
    def test_i_watched_is_observation(self):
        """Verify 'I watched' triggers OBSERVATION."""
        ctx = _make_context("I watched him walk away.")
        
        classify_statements(ctx)
        
        assert ctx.segments[0].statement_type == StatementType.OBSERVATION


class TestInterpretationClassification:
    """Tests for INTERPRETATION classification."""
    
    def test_wanted_to_is_interpretation(self):
        """Verify 'wanted to' triggers INTERPRETATION."""
        ctx = _make_context("He wanted to hurt me.")
        
        classify_statements(ctx)
        
        assert ctx.segments[0].statement_type == StatementType.INTERPRETATION
    
    def test_tried_to_is_interpretation(self):
        """Verify 'tried to' triggers INTERPRETATION."""
        ctx = _make_context("He tried to escape.")
        
        classify_statements(ctx)
        
        assert ctx.segments[0].statement_type == StatementType.INTERPRETATION
    
    def test_intentionally_is_interpretation(self):
        """Verify 'intentionally' triggers INTERPRETATION."""
        ctx = _make_context("He intentionally pushed me.")
        
        classify_statements(ctx)
        
        assert ctx.segments[0].statement_type == StatementType.INTERPRETATION
    
    def test_i_think_is_interpretation(self):
        """Verify 'I think' triggers INTERPRETATION."""
        ctx = _make_context("I think he was angry.")
        
        classify_statements(ctx)
        
        assert ctx.segments[0].statement_type == StatementType.INTERPRETATION


class TestClaimClassification:
    """Tests for CLAIM (default) classification."""
    
    def test_simple_assertion_is_claim(self):
        """Verify simple assertions become CLAIM."""
        ctx = _make_context("He grabbed my arm.")
        
        classify_statements(ctx)
        
        assert ctx.segments[0].statement_type == StatementType.CLAIM
    
    def test_action_without_witness_is_claim(self):
        """Verify actions without witness language are CLAIM."""
        ctx = _make_context("The officer approached the vehicle.")
        
        classify_statements(ctx)
        
        assert ctx.segments[0].statement_type == StatementType.CLAIM


class TestQuoteClassification:
    """Tests for QUOTE classification."""
    
    def test_direct_quote_context_is_quote(self):
        """Verify segments with DIRECT_QUOTE context become QUOTE."""
        ctx = _make_context('"Stop right there!"')
        ctx.segments[0].contexts = [SegmentContext.DIRECT_QUOTE.value]
        
        classify_statements(ctx)
        
        assert ctx.segments[0].statement_type == StatementType.QUOTE


class TestConfidenceScores:
    """Tests for confidence score assignment."""
    
    def test_observation_has_high_confidence(self):
        """Verify OBSERVATION has high confidence."""
        ctx = _make_context("I saw him do it.")
        
        classify_statements(ctx)
        
        assert ctx.segments[0].statement_confidence >= 0.8
    
    def test_claim_has_lower_confidence(self):
        """Verify CLAIM has lower confidence than OBSERVATION."""
        ctx = _make_context("He did it.")
        
        classify_statements(ctx)
        
        assert ctx.segments[0].statement_confidence < 0.8


class TestMultipleSegments:
    """Tests for multiple segments."""
    
    def test_classifies_all_segments(self):
        """Verify all segments get classified."""
        req = TransformRequest(text="Multiple sentences.")
        ctx = TransformContext(request=req, raw_text="Multiple sentences.")
        ctx.segments = [
            Segment(id="seg_1", text="I saw him.", start_char=0, end_char=10),
            Segment(id="seg_2", text="He ran.", start_char=11, end_char=18),
            Segment(id="seg_3", text="He wanted to escape.", start_char=19, end_char=39),
        ]
        
        classify_statements(ctx)
        
        assert ctx.segments[0].statement_type == StatementType.OBSERVATION
        assert ctx.segments[1].statement_type == StatementType.CLAIM
        assert ctx.segments[2].statement_type == StatementType.INTERPRETATION


class TestTracing:
    """Tests for trace entries."""
    
    def test_adds_trace(self):
        """Verify trace entries are added."""
        ctx = _make_context("Hello world.")
        
        classify_statements(ctx)
        
        trace_passes = [t.pass_name for t in ctx.trace]
        assert "p22_classify_statements" in trace_passes

