"""
Unit tests for p44a_temporal_expressions pass.

V6 Timeline Reconstruction: Stage 1 Tests
"""

import pytest
from nnrt.core.context import TransformContext, TransformRequest
from nnrt.ir.schema_v0_1 import Segment
from nnrt.ir.enums import TemporalExpressionType


def _make_context(text: str) -> TransformContext:
    """Helper to create a context with segments."""
    req = TransformRequest(text=text)
    ctx = TransformContext(request=req, raw_text=text)
    ctx.normalized_text = text
    ctx.segments = [Segment(id="seg_1", text=text, start_char=0, end_char=len(text))]
    return ctx


class TestTimeNormalization:
    """Tests for time normalization to ISO format."""
    
    def test_normalizes_pm_time(self):
        """'11:30 PM' -> 'T23:30:00'"""
        from nnrt.passes.p44a_temporal_expressions import extract_temporal_expressions
        
        ctx = _make_context("At 11:30 PM the incident occurred.")
        extract_temporal_expressions(ctx)
        
        assert len(ctx.temporal_expressions) >= 1
        time_expr = ctx.temporal_expressions[0]
        assert time_expr.type == TemporalExpressionType.TIME
        assert time_expr.normalized_value == "T23:30:00"
    
    def test_normalizes_am_time(self):
        """'3:00 AM' -> 'T03:00:00'"""
        from nnrt.passes.p44a_temporal_expressions import extract_temporal_expressions
        
        ctx = _make_context("At 3:00 AM I was released.")
        extract_temporal_expressions(ctx)
        
        time_exprs = [e for e in ctx.temporal_expressions if e.type == TemporalExpressionType.TIME]
        assert len(time_exprs) >= 1
        assert time_exprs[0].normalized_value == "T03:00:00"
    
    def test_normalizes_noon(self):
        """'12:00 PM' -> 'T12:00:00'"""
        from nnrt.passes.p44a_temporal_expressions import extract_temporal_expressions
        
        ctx = _make_context("At 12:00 PM we had lunch.")
        extract_temporal_expressions(ctx)
        
        time_exprs = [e for e in ctx.temporal_expressions if e.type == TemporalExpressionType.TIME]
        assert len(time_exprs) >= 1
        assert time_exprs[0].normalized_value == "T12:00:00"
    
    def test_normalizes_midnight(self):
        """'12:00 AM' -> 'T00:00:00'"""
        from nnrt.passes.p44a_temporal_expressions import extract_temporal_expressions
        
        ctx = _make_context("At 12:00 AM the call came.")
        extract_temporal_expressions(ctx)
        
        time_exprs = [e for e in ctx.temporal_expressions if e.type == TemporalExpressionType.TIME]
        assert len(time_exprs) >= 1
        assert time_exprs[0].normalized_value == "T00:00:00"


class TestDateNormalization:
    """Tests for date normalization to ISO format."""
    
    def test_normalizes_full_date(self):
        """'January 10, 2026' -> '2026-01-10'"""
        from nnrt.passes.p44a_temporal_expressions import extract_temporal_expressions
        
        ctx = _make_context("On January 10, 2026 the incident occurred.")
        extract_temporal_expressions(ctx)
        
        date_exprs = [e for e in ctx.temporal_expressions if e.type == TemporalExpressionType.DATE]
        assert len(date_exprs) >= 1
        assert date_exprs[0].normalized_value == "2026-01-10"
    
    def test_normalizes_date_with_ordinal(self):
        """'January 10th, 2026' -> '2026-01-10'"""
        from nnrt.passes.p44a_temporal_expressions import extract_temporal_expressions
        
        ctx = _make_context("On January 10th, 2026 I filed my complaint.")
        extract_temporal_expressions(ctx)
        
        date_exprs = [e for e in ctx.temporal_expressions if e.type == TemporalExpressionType.DATE]
        assert len(date_exprs) >= 1
        assert date_exprs[0].normalized_value == "2026-01-10"


class TestRelativeExpressions:
    """Tests for relative temporal expressions."""
    
    def test_detects_then(self):
        """'then' is detected as sequence marker."""
        from nnrt.passes.p44a_temporal_expressions import extract_temporal_expressions
        
        ctx = _make_context("He arrived. He then grabbed my arm.")
        extract_temporal_expressions(ctx)
        
        then_exprs = [e for e in ctx.temporal_expressions if 'then' in e.original_text.lower()]
        assert len(then_exprs) >= 1
        assert then_exprs[0].type == TemporalExpressionType.RELATIVE
        assert then_exprs[0].anchor_type == 'sequence'
    
    def test_detects_next_day(self):
        """'the next day' is detected with next_day anchor."""
        from nnrt.passes.p44a_temporal_expressions import extract_temporal_expressions
        
        ctx = _make_context("The next day I went to the hospital.")
        extract_temporal_expressions(ctx)
        
        next_day_exprs = [e for e in ctx.temporal_expressions if 'next day' in e.original_text.lower()]
        assert len(next_day_exprs) >= 1
        assert next_day_exprs[0].anchor_type == 'next_day'
    
    def test_detects_while(self):
        """'while' is detected as during marker."""
        from nnrt.passes.p44a_temporal_expressions import extract_temporal_expressions
        
        ctx = _make_context("While he was restraining me, I screamed.")
        extract_temporal_expressions(ctx)
        
        while_exprs = [e for e in ctx.temporal_expressions if 'while' in e.original_text.lower()]
        assert len(while_exprs) >= 1
        assert while_exprs[0].anchor_type == 'during'


class TestDurationExpressions:
    """Tests for duration expressions."""
    
    def test_detects_minutes_later(self):
        """'20 minutes later' is detected as duration."""
        from nnrt.passes.p44a_temporal_expressions import extract_temporal_expressions
        
        ctx = _make_context("About 20 minutes later the sergeant arrived.")
        extract_temporal_expressions(ctx)
        
        dur_exprs = [e for e in ctx.temporal_expressions if e.type == TemporalExpressionType.DURATION]
        assert len(dur_exprs) >= 1
        assert dur_exprs[0].anchor_type == 'gap'
    
    def test_detects_months_later(self):
        """'Three months later' is detected as duration."""
        from nnrt.passes.p44a_temporal_expressions import extract_temporal_expressions
        
        ctx = _make_context("Three months later I filed a complaint.")
        extract_temporal_expressions(ctx)
        
        dur_exprs = [e for e in ctx.temporal_expressions if e.type == TemporalExpressionType.DURATION]
        assert len(dur_exprs) >= 1


class TestMultipleExpressions:
    """Tests for narratives with multiple temporal expressions."""
    
    def test_complex_narrative(self):
        """Full narrative with multiple time types."""
        from nnrt.passes.p44a_temporal_expressions import extract_temporal_expressions
        
        text = """At 11:30 PM on January 10, 2026, I was walking on Cedar Street.
        Officer Jenkins approached me then grabbed my arm.
        About 20 minutes later, Sergeant Williams arrived.
        The next day, I went to the emergency room."""
        
        ctx = _make_context(text)
        extract_temporal_expressions(ctx)
        
        # Should have at least: 11:30 PM, January 10 2026, then, 20 minutes later, next day
        assert len(ctx.temporal_expressions) >= 5
        
        # Check types are diverse
        types = {e.type for e in ctx.temporal_expressions}
        assert TemporalExpressionType.TIME in types
        assert TemporalExpressionType.DATE in types
        assert TemporalExpressionType.RELATIVE in types
    
    def test_expressions_sorted_by_position(self):
        """Expressions should be sorted by start position."""
        from nnrt.passes.p44a_temporal_expressions import extract_temporal_expressions
        
        ctx = _make_context("At 11:30 PM. Then at 3:00 AM. The next day.")
        extract_temporal_expressions(ctx)
        
        positions = [e.start_char for e in ctx.temporal_expressions]
        assert positions == sorted(positions)


class TestEdgeCases:
    """Tests for edge cases and robustness."""
    
    def test_no_temporal_expressions(self):
        """Handles text without temporal expressions."""
        from nnrt.passes.p44a_temporal_expressions import extract_temporal_expressions
        
        ctx = _make_context("The officer approached me on the street.")
        extract_temporal_expressions(ctx)
        
        # May have some false positives from spaCy, but shouldn't crash
        assert ctx.temporal_expressions is not None
    
    def test_adds_trace(self):
        """Adds trace entry for debugging."""
        from nnrt.passes.p44a_temporal_expressions import extract_temporal_expressions
        
        ctx = _make_context("At 11:30 PM the incident occurred.")
        extract_temporal_expressions(ctx)
        
        trace_passes = [t.pass_name for t in ctx.trace]
        assert "p44a_temporal_expressions" in trace_passes
    
    def test_preserves_original_text(self):
        """Original text is preserved for display."""
        from nnrt.passes.p44a_temporal_expressions import extract_temporal_expressions
        
        ctx = _make_context("At 11:30 PM the incident occurred.")
        extract_temporal_expressions(ctx)
        
        expr = ctx.temporal_expressions[0]
        assert expr.original_text in ctx.normalized_text
