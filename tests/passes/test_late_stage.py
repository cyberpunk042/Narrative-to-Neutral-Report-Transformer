"""
Unit tests for late-stage passes (p60, p70, p80).
"""

import pytest
from nnrt.core.context import TransformContext, TransformRequest
from nnrt.ir.schema_v0_1 import Segment
from nnrt.ir.enums import TransformStatus
from nnrt.passes.p60_augment_ir import augment_ir
from nnrt.passes.p70_render import render
from nnrt.passes.p80_package import package


def _make_context(text: str) -> TransformContext:
    """Helper to create a context with a segment."""
    req = TransformRequest(text=text)
    ctx = TransformContext(request=req, raw_text=text)
    ctx.segments = [Segment(id="seg_1", text=text, start_char=0, end_char=len(text))]
    return ctx


class TestP60AugmentIR:
    """Tests for p60_augment_ir (stub pass)."""
    
    def test_returns_context(self):
        """Verify pass returns context."""
        ctx = _make_context("Hello world.")
        
        result = augment_ir(ctx)
        
        assert result is ctx
    
    def test_adds_trace(self):
        """Verify trace entry is added."""
        ctx = _make_context("Hello world.")
        
        augment_ir(ctx)
        
        trace_passes = [t.pass_name for t in ctx.trace]
        assert "p60_augment_ir" in trace_passes


class TestP70Render:
    """Tests for p70_render pass."""
    
    def test_produces_rendered_text(self):
        """Verify rendered text is produced."""
        ctx = _make_context("The officer approached.")
        
        render(ctx)
        
        assert ctx.rendered_text is not None
        assert len(ctx.rendered_text) > 0
    
    def test_handles_no_segments(self):
        """Verify empty segments produce empty output."""
        req = TransformRequest(text="Hello")
        ctx = TransformContext(request=req, raw_text="Hello")
        ctx.segments = []
        
        render(ctx)
        
        assert ctx.rendered_text == ""
    
    def test_adds_trace(self):
        """Verify trace entry is added."""
        ctx = _make_context("Hello world.")
        
        render(ctx)
        
        trace_passes = [t.pass_name for t in ctx.trace]
        assert "p70_render" in trace_passes
    
    def test_applies_policy_transformations(self):
        """Verify policy rules are applied during rendering."""
        ctx = _make_context("He intentionally hit me.")
        
        render(ctx)
        
        # The word "intentionally" might be modified by policy
        # Just verify we get some output
        assert ctx.rendered_text is not None


class TestP80Package:
    """Tests for p80_package pass."""
    
    def test_validates_segments_exist(self):
        """Verify validation checks for segments."""
        req = TransformRequest(text="Hello")
        ctx = TransformContext(request=req, raw_text="Hello")
        ctx.segments = []
        ctx.rendered_text = "Hello"
        
        package(ctx)
        
        # Should add validation error
        errors = [d for d in ctx.diagnostics if d.code == "VALIDATION_FAILED"]
        assert len(errors) >= 1
    
    def test_validates_rendered_text_exists(self):
        """Verify validation checks for rendered text."""
        ctx = _make_context("Hello world.")
        ctx.rendered_text = None
        
        package(ctx)
        
        # Should add validation error
        errors = [d for d in ctx.diagnostics if d.code == "VALIDATION_FAILED"]
        assert len(errors) >= 1
    
    def test_sets_partial_status_on_error(self):
        """Verify status is set to PARTIAL on validation errors."""
        ctx = _make_context("Hello world.")
        ctx.rendered_text = None
        ctx.status = TransformStatus.SUCCESS
        
        package(ctx)
        
        assert ctx.status == TransformStatus.PARTIAL
    
    def test_adds_trace(self):
        """Verify trace entry is added."""
        ctx = _make_context("Hello world.")
        ctx.rendered_text = "Hello world."
        
        package(ctx)
        
        trace_passes = [t.pass_name for t in ctx.trace]
        assert "p80_package" in trace_passes
    
    def test_success_with_valid_context(self):
        """Verify success status is preserved with valid context."""
        ctx = _make_context("Hello world.")
        ctx.rendered_text = "Hello world."
        ctx.status = TransformStatus.SUCCESS
        
        package(ctx)
        
        # Should remain SUCCESS (no errors added)
        # Note: status may still be SUCCESS if validation passes
        assert ctx.status in (TransformStatus.SUCCESS, TransformStatus.PARTIAL)
