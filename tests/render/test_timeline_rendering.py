"""
Unit tests for V6 timeline rendering in structured output.
"""

import pytest


class TestTimelineRendering:
    """Tests for timeline section in structured output."""
    
    def _setup_ctx_with_timeline(self, text: str, events: list):
        """Helper to create context and run timeline pipeline."""
        from nnrt.core.context import TransformContext, TransformRequest
        from nnrt.ir.schema_v0_1 import Segment
        from nnrt.passes.p44a_temporal_expressions import extract_temporal_expressions
        from nnrt.passes.p44b_temporal_relations import extract_temporal_relations
        from nnrt.passes.p44c_timeline_ordering import build_timeline_ordering
        from nnrt.passes.p44d_timeline_gaps import detect_timeline_gaps
        
        req = TransformRequest(text=text)
        ctx = TransformContext(request=req, raw_text=text)
        ctx.normalized_text = text
        ctx.segments = [Segment(id="seg_1", text=text, start_char=0, end_char=len(text))]
        ctx.events = events
        
        extract_temporal_expressions(ctx)
        extract_temporal_relations(ctx)
        build_timeline_ordering(ctx)
        detect_timeline_gaps(ctx)
        
        return ctx
    
    def test_timeline_section_rendered(self):
        """Timeline section should appear in output when timeline data exists."""
        from nnrt.render.structured import format_structured_output
        from nnrt.ir.schema_v0_1 import Event
        from nnrt.ir.enums import EventType
        
        text = "At 11:30 PM I walked. Then I ran."
        events = [
            Event(id="evt_001", type=EventType.MOVEMENT, description="walked", source_spans=[], confidence=0.9),
            Event(id="evt_002", type=EventType.MOVEMENT, description="ran", source_spans=[], confidence=0.9),
        ]
        
        ctx = self._setup_ctx_with_timeline(text, events)
        
        output = format_structured_output(
            rendered_text="",
            atomic_statements=[],
            entities=[],
            events=events,
            identifiers=[],
            timeline=ctx.timeline,
            time_gaps=ctx.time_gaps,
        )
        
        assert "RECONSTRUCTED TIMELINE" in output
    
    def test_timeline_shows_day_grouping(self):
        """Events should be grouped by day."""
        from nnrt.render.structured import format_structured_output
        from nnrt.ir.schema_v0_1 import Event
        from nnrt.ir.enums import EventType
        
        # Use a more complete narrative with clear day boundary
        text = "At 11:30 PM I was walking on the street. The next day I went to the hospital."
        events = [
            Event(id="evt_001", type=EventType.MOVEMENT, description="walking on the street", source_spans=[], confidence=0.9),
            Event(id="evt_002", type=EventType.ACTION, description="went to the hospital", source_spans=[], confidence=0.9),
        ]
        
        ctx = self._setup_ctx_with_timeline(text, events)
        
        output = format_structured_output(
            rendered_text="",
            atomic_statements=[],
            entities=[],
            events=events,
            identifiers=[],
            timeline=ctx.timeline,
            time_gaps=ctx.time_gaps,
        )
        
        assert "INCIDENT DAY" in output
        assert "NEXT DAY" in output or "Day 1" in output
    
    def test_investigation_questions_shown(self):
        """Unexplained gaps should show investigation questions."""
        from nnrt.render.structured import format_structured_output
        from nnrt.ir.schema_v0_1 import Event
        from nnrt.ir.enums import EventType
        
        text = "At 11:30 PM I walked. I woke up in a car."
        events = [
            Event(id="evt_001", type=EventType.MOVEMENT, description="walked", source_spans=[], confidence=0.9),
            Event(id="evt_002", type=EventType.ACTION, description="woke up in a car", source_spans=[], confidence=0.9),
        ]
        
        ctx = self._setup_ctx_with_timeline(text, events)
        
        output = format_structured_output(
            rendered_text="",
            atomic_statements=[],
            entities=[],
            events=events,
            identifiers=[],
            timeline=ctx.timeline,
            time_gaps=ctx.time_gaps,
        )
        
        # Should have investigation section
        assert "GAPS REQUIRING INVESTIGATION" in output
        assert "What happened" in output
    
    def test_legend_displayed(self):
        """Legend should explain the symbols."""
        from nnrt.render.structured import format_structured_output
        from nnrt.ir.schema_v0_1 import Event
        from nnrt.ir.enums import EventType
        
        text = "At 11:30 PM I walked."
        events = [
            Event(id="evt_001", type=EventType.MOVEMENT, description="walked", source_spans=[], confidence=0.9),
        ]
        
        ctx = self._setup_ctx_with_timeline(text, events)
        
        output = format_structured_output(
            rendered_text="",
            atomic_statements=[],
            entities=[],
            events=events,
            identifiers=[],
            timeline=ctx.timeline,
            time_gaps=ctx.time_gaps,
        )
        
        assert "Legend" in output
    
    def test_statistics_shown(self):
        """Summary statistics should be displayed."""
        from nnrt.render.structured import format_structured_output
        from nnrt.ir.schema_v0_1 import Event
        from nnrt.ir.enums import EventType
        
        text = "At 11:30 PM I walked. Then I ran."
        events = [
            Event(id="evt_001", type=EventType.MOVEMENT, description="walked", source_spans=[], confidence=0.9),
            Event(id="evt_002", type=EventType.MOVEMENT, description="ran", source_spans=[], confidence=0.9),
        ]
        
        ctx = self._setup_ctx_with_timeline(text, events)
        
        output = format_structured_output(
            rendered_text="",
            atomic_statements=[],
            entities=[],
            events=events,
            identifiers=[],
            timeline=ctx.timeline,
            time_gaps=ctx.time_gaps,
        )
        
        assert "Timeline:" in output
        assert "events" in output
    
    def test_backward_compatible_without_timeline(self):
        """Should work without timeline parameters (backward compatibility)."""
        from nnrt.render.structured import format_structured_output
        
        output = format_structured_output(
            rendered_text="Test narrative",
            atomic_statements=[],
            entities=[],
            events=[],
            identifiers=[],
            # No timeline or time_gaps
        )
        
        # Should not error and should not have timeline section
        assert "NEUTRALIZED REPORT" in output
        assert "RECONSTRUCTED TIMELINE" not in output


class TestTimelineRenderingMultiDay:
    """Tests for multi-day timeline rendering."""
    
    def _setup_ctx_with_timeline(self, text: str, events: list):
        from nnrt.core.context import TransformContext, TransformRequest
        from nnrt.ir.schema_v0_1 import Segment
        from nnrt.passes.p44a_temporal_expressions import extract_temporal_expressions
        from nnrt.passes.p44b_temporal_relations import extract_temporal_relations
        from nnrt.passes.p44c_timeline_ordering import build_timeline_ordering
        from nnrt.passes.p44d_timeline_gaps import detect_timeline_gaps
        
        req = TransformRequest(text=text)
        ctx = TransformContext(request=req, raw_text=text)
        ctx.normalized_text = text
        ctx.segments = [Segment(id="seg_1", text=text, start_char=0, end_char=len(text))]
        ctx.events = events
        
        extract_temporal_expressions(ctx)
        extract_temporal_relations(ctx)
        build_timeline_ordering(ctx)
        detect_timeline_gaps(ctx)
        
        return ctx
    
    def test_three_months_later_label(self):
        """Three months later should show months label."""
        from nnrt.render.structured import format_structured_output
        from nnrt.ir.schema_v0_1 import Event
        from nnrt.ir.enums import EventType
        
        text = "I walked. Three months later I filed."
        events = [
            Event(id="evt_001", type=EventType.MOVEMENT, description="walked", source_spans=[], confidence=0.9),
            Event(id="evt_002", type=EventType.ACTION, description="filed", source_spans=[], confidence=0.9),
        ]
        
        ctx = self._setup_ctx_with_timeline(text, events)
        
        output = format_structured_output(
            rendered_text="",
            atomic_statements=[],
            entities=[],
            events=events,
            identifiers=[],
            timeline=ctx.timeline,
            time_gaps=ctx.time_gaps,
        )
        
        # Should show "3 MONTHS LATER" or similar
        assert "MONTH" in output.upper()
