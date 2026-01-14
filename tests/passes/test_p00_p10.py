"""
Unit tests for early pipeline passes (p00, p10, p20, p22).
"""

import pytest
from nnrt.core.context import TransformContext, TransformRequest
from nnrt.passes.p00_normalize import normalize
from nnrt.passes.p10_segment import segment


class TestP00Normalize:
    """Tests for p00_normalize pass."""
    
    def test_strips_whitespace(self):
        """Verify leading/trailing whitespace is stripped."""
        text = "   Hello world.   "
        req = TransformRequest(text=text)
        ctx = TransformContext(request=req, raw_text=text)
        
        normalize(ctx)
        
        assert ctx.normalized_text == "Hello world."
    
    def test_collapses_internal_whitespace(self):
        """Verify multiple spaces collapse to single space."""
        text = "Hello    world.    How are   you?"
        req = TransformRequest(text=text)
        ctx = TransformContext(request=req, raw_text=text)
        
        normalize(ctx)
        
        assert ctx.normalized_text == "Hello world. How are you?"
    
    def test_preserves_paragraph_breaks(self):
        """Verify double newlines (paragraphs) are preserved."""
        text = "First paragraph.\n\nSecond paragraph."
        req = TransformRequest(text=text)
        ctx = TransformContext(request=req, raw_text=text)
        
        normalize(ctx)
        
        assert "\n\n" in ctx.normalized_text
        assert "First paragraph." in ctx.normalized_text
        assert "Second paragraph." in ctx.normalized_text
    
    def test_unicode_normalization(self):
        """Verify Unicode is normalized to NFC form."""
        # Combining character: é = e + combining acute
        text = "cafe\u0301"  # e + combining acute
        req = TransformRequest(text=text)
        ctx = TransformContext(request=req, raw_text=text)
        
        normalize(ctx)
        
        # Should be normalized to single codepoint é
        assert ctx.normalized_text == "café"
    
    def test_adds_trace(self):
        """Verify trace entry is added."""
        text = "Hello world."
        req = TransformRequest(text=text)
        ctx = TransformContext(request=req, raw_text=text)
        
        normalize(ctx)
        
        assert len(ctx.trace) > 0
        assert ctx.trace[0].pass_name == "p00_normalize"
    
    def test_empty_input(self):
        """Verify empty input produces empty output."""
        text = ""
        req = TransformRequest(text=text)
        ctx = TransformContext(request=req, raw_text=text)
        
        normalize(ctx)
        
        assert ctx.normalized_text == ""


class TestP10Segment:
    """Tests for p10_segment pass."""
    
    def test_single_sentence(self):
        """Verify single sentence creates one segment."""
        text = "The officer approached the vehicle."
        req = TransformRequest(text=text)
        ctx = TransformContext(request=req, raw_text=text)
        ctx.normalized_text = text
        
        segment(ctx)
        
        assert len(ctx.segments) == 1
        assert ctx.segments[0].text == text
    
    def test_multiple_sentences(self):
        """Verify multiple sentences create multiple segments."""
        text = "The officer approached. I stayed calm. He asked for ID."
        req = TransformRequest(text=text)
        ctx = TransformContext(request=req, raw_text=text)
        ctx.normalized_text = text
        
        segment(ctx)
        
        assert len(ctx.segments) == 3
    
    def test_segment_ids_are_sequential(self):
        """Verify segment IDs are sequential (seg_000, seg_001, ...)."""
        text = "First sentence. Second sentence. Third sentence."
        req = TransformRequest(text=text)
        ctx = TransformContext(request=req, raw_text=text)
        ctx.normalized_text = text
        
        segment(ctx)
        
        ids = [s.id for s in ctx.segments]
        assert ids == ["seg_000", "seg_001", "seg_002"]
    
    def test_segment_offsets_are_correct(self):
        """Verify segment character offsets are correct."""
        text = "Hello. World."
        req = TransformRequest(text=text)
        ctx = TransformContext(request=req, raw_text=text)
        ctx.normalized_text = text
        
        segment(ctx)
        
        # First segment should start at 0
        assert ctx.segments[0].start_char == 0
        # Offsets should allow reconstruction
        for seg in ctx.segments:
            reconstructed = text[seg.start_char:seg.end_char].strip()
            assert seg.text == reconstructed
    
    def test_empty_input_creates_warning(self):
        """Verify empty input adds a warning diagnostic."""
        text = ""
        req = TransformRequest(text=text)
        ctx = TransformContext(request=req, raw_text=text)
        ctx.normalized_text = text
        
        segment(ctx)
        
        assert len(ctx.segments) == 0
        # Should have a warning diagnostic
        assert len(ctx.diagnostics) > 0
        assert ctx.diagnostics[0].code == "EMPTY_INPUT"
    
    def test_adds_trace(self):
        """Verify trace entry is added."""
        text = "Hello world."
        req = TransformRequest(text=text)
        ctx = TransformContext(request=req, raw_text=text)
        ctx.normalized_text = text
        
        segment(ctx)
        
        assert len(ctx.trace) > 0
        trace_pass_names = [t.pass_name for t in ctx.trace]
        assert "p10_segment" in trace_pass_names


class TestP00P10Integration:
    """Tests for p00 -> p10 integration."""
    
    def test_normalize_then_segment(self):
        """Verify normalize output feeds correctly into segment."""
        text = "   The officer    approached.   I stayed calm.  "
        req = TransformRequest(text=text)
        ctx = TransformContext(request=req, raw_text=text)
        
        normalize(ctx)
        segment(ctx)
        
        # Should have 2 segments
        assert len(ctx.segments) == 2
        # Text should be clean
        assert "officer" in ctx.segments[0].text
        assert "  " not in ctx.segments[0].text  # No double spaces
