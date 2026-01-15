"""
Unit tests for p25_annotate_context pass.
"""

import pytest
from nnrt.core.context import TransformContext, TransformRequest
from nnrt.ir.schema_v0_1 import Segment
from nnrt.ir.enums import SegmentContext
from nnrt.passes.p25_annotate_context import annotate_context


def _make_context(text: str) -> TransformContext:
    """Helper to create a context with a segment."""
    req = TransformRequest(text=text)
    ctx = TransformContext(request=req, raw_text=text)
    ctx.segments = [Segment(id="seg_1", text=text, start_char=0, end_char=len(text))]
    return ctx


class TestDirectQuoteDetection:
    """Tests for direct quote detection."""
    
    def test_detects_double_quotes(self):
        """Verify text in double quotes is marked as direct quote."""
        ctx = _make_context('He said "Stop right there."')
        
        annotate_context(ctx)
        
        assert SegmentContext.DIRECT_QUOTE.value in ctx.segments[0].contexts
    
    def test_detects_single_quotes(self):
        """Verify text in single quotes is marked as direct quote."""
        ctx = _make_context("He said 'Stop right there.'")
        
        annotate_context(ctx)
        
        assert SegmentContext.DIRECT_QUOTE.value in ctx.segments[0].contexts


class TestPhysicalContactDetection:
    """Tests for physical contact detection."""
    
    def test_detects_grabbed(self):
        """Verify 'grabbed' triggers physical contact."""
        ctx = _make_context("He grabbed my arm.")
        
        annotate_context(ctx)
        
        assert SegmentContext.PHYSICAL_FORCE.value in ctx.segments[0].contexts
    
    def test_detects_pushed(self):
        """Verify 'pushed' triggers physical contact."""
        ctx = _make_context("He pushed me against the wall.")
        
        annotate_context(ctx)
        
        assert SegmentContext.PHYSICAL_FORCE.value in ctx.segments[0].contexts
    
    def test_detects_punched(self):
        """Verify 'punched' triggers physical contact."""
        ctx = _make_context("He punched me in the face.")
        
        annotate_context(ctx)
        
        assert SegmentContext.PHYSICAL_FORCE.value in ctx.segments[0].contexts


class TestChargeDescriptionDetection:
    """Tests for charge description detection."""
    
    def test_detects_charged_with(self):
        """Verify 'charged with' triggers charge description."""
        ctx = _make_context("He was charged with assault.")
        
        annotate_context(ctx)
        
        assert SegmentContext.CHARGE_DESCRIPTION.value in ctx.segments[0].contexts


class TestOpinionOnlyDetection:
    """Tests for opinion_only detection."""
    
    def test_detects_i_think(self):
        """Verify 'I think' triggers opinion_only context."""
        ctx = _make_context("I think he was angry.")
        
        annotate_context(ctx)
        
        assert SegmentContext.OPINION_ONLY.value in ctx.segments[0].contexts


class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_no_segments(self):
        """Verify empty segments list doesn't crash."""
        req = TransformRequest(text="Hello")
        ctx = TransformContext(request=req, raw_text="Hello")
        ctx.segments = []
        
        annotate_context(ctx)
        
        # Should not raise
        assert ctx.segments == []
    
    def test_plain_text_minimal_contexts(self):
        """Verify plain text has minimal context annotations."""
        ctx = _make_context("The sky is blue.")
        
        annotate_context(ctx)
        
        # Should have few or no context annotations
        assert len(ctx.segments[0].contexts) <= 2
    
    def test_adds_trace(self):
        """Verify trace entry is added."""
        ctx = _make_context("Hello world.")
        
        annotate_context(ctx)
        
        trace_passes = [t.pass_name for t in ctx.trace]
        assert "p25_annotate_context" in trace_passes


class TestMultipleContexts:
    """Tests for segments with multiple contexts."""
    
    def test_can_have_multiple_contexts(self):
        """Verify a segment can have multiple contexts."""
        ctx = _make_context('He grabbed me and said "Stop!"')
        
        annotate_context(ctx)
        
        contexts = ctx.segments[0].contexts
        # Should have both physical force and direct quote
        assert SegmentContext.PHYSICAL_FORCE.value in contexts
        assert SegmentContext.DIRECT_QUOTE.value in contexts
