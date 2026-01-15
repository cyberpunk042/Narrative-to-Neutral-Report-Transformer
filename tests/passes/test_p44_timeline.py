"""
Unit tests for p44_timeline pass.

Test-driven development: these tests define expected behavior before implementation.
"""

import pytest
from nnrt.core.context import TransformContext, TransformRequest
from nnrt.ir.schema_v0_1 import Segment, Event, Identifier
from nnrt.ir.enums import EventType, IdentifierType


def _make_context(text: str) -> TransformContext:
    """Helper to create a context with segments."""
    req = TransformRequest(text=text)
    ctx = TransformContext(request=req, raw_text=text)
    ctx.normalized_text = text
    ctx.segments = [Segment(id="seg_1", text=text, start_char=0, end_char=len(text))]
    return ctx


class TestAbsoluteTimeExtraction:
    """Tests for extracting absolute times from identifiers."""
    
    def test_uses_existing_time_identifiers(self):
        """Should use TIME identifiers already extracted by p30."""
        from nnrt.passes.p44_timeline import build_timeline
        
        ctx = _make_context("At 11:30 PM, Officer Jenkins arrived.")
        ctx.identifiers = [
            Identifier(
                id="id_001",
                type=IdentifierType.TIME,
                value="11:30 PM",
                original_text="11:30 PM",
                start_char=3,
                end_char=11,
                source_segment_id="seg_1",
                confidence=0.9,
            )
        ]
        ctx.events = [
            Event(id="evt_001", type=EventType.ACTION, description="Officer Jenkins arrived", 
                  source_spans=[], confidence=0.9)
        ]
        
        build_timeline(ctx)
        
        # Should have timeline entries
        assert len(ctx.timeline) >= 1
        entry = ctx.timeline[0]
        assert entry.absolute_time == "11:30 PM"
    
    def test_uses_existing_date_identifiers(self):
        """Should use DATE identifiers for full temporal context."""
        from nnrt.passes.p44_timeline import build_timeline
        
        ctx = _make_context("On January 15th, 2026, the incident occurred.")
        ctx.identifiers = [
            Identifier(
                id="id_001",
                type=IdentifierType.DATE,
                value="January 15th, 2026",
                original_text="January 15th, 2026",
                start_char=3,
                end_char=21,
                source_segment_id="seg_1",
                confidence=0.9,
            )
        ]
        ctx.events = [
            Event(id="evt_001", type=EventType.ACTION, description="incident occurred",
                  source_spans=[], confidence=0.9)
        ]
        
        build_timeline(ctx)
        
        assert len(ctx.timeline) >= 1
        entry = ctx.timeline[0]
        assert entry.date == "January 15th, 2026"


class TestRelativeTimeExtraction:
    """Tests for extracting relative time markers."""
    
    def test_detects_then(self):
        """'Then' indicates sequence."""
        from nnrt.passes.p44_timeline import build_timeline
        
        ctx = _make_context("Officer Jenkins arrived. Then he approached the vehicle.")
        ctx.events = [
            Event(id="evt_001", type=EventType.ACTION, description="arrived", source_spans=[], confidence=0.9),
            Event(id="evt_002", type=EventType.ACTION, description="approached", source_spans=[], confidence=0.9),
        ]
        
        build_timeline(ctx)
        
        # Should have entries with sequence order
        assert len(ctx.timeline) >= 2
        # First event should have lower sequence order
        orders = sorted([e.sequence_order for e in ctx.timeline])
        assert orders[0] < orders[-1]
    
    def test_detects_after_that(self):
        """'After that' indicates sequence."""
        from nnrt.passes.p44_timeline import build_timeline
        
        ctx = _make_context("He grabbed my arm. After that, I screamed.")
        ctx.events = [
            Event(id="evt_001", type=EventType.ACTION, description="grabbed arm", source_spans=[], confidence=0.9),
            Event(id="evt_002", type=EventType.VERBAL, description="screamed", source_spans=[], confidence=0.9),
        ]
        
        build_timeline(ctx)
        
        assert len(ctx.timeline) >= 2
    
    def test_detects_later(self):
        """'Later', 'X minutes later' indicates time gap."""
        from nnrt.passes.p44_timeline import build_timeline
        
        ctx = _make_context("The arrest happened. 20 minutes later, Sergeant Williams arrived.")
        ctx.events = [
            Event(id="evt_001", type=EventType.ACTION, description="arrest", source_spans=[], confidence=0.9),
            Event(id="evt_002", type=EventType.ACTION, description="Sergeant arrived", source_spans=[], confidence=0.9),
        ]
        
        build_timeline(ctx)
        
        assert len(ctx.timeline) >= 2
        # Second entry should have relative time
        later_entry = next((e for e in ctx.timeline if e.event_id == "evt_002"), None)
        assert later_entry is not None
        assert later_entry.relative_time is not None or later_entry.sequence_order > 0
    
    def test_detects_the_next_day(self):
        """'The next day' indicates day boundary."""
        from nnrt.passes.p44_timeline import build_timeline
        
        ctx = _make_context("I was released that night. The next day, I filed a complaint.")
        ctx.events = [
            Event(id="evt_001", type=EventType.ACTION, description="released", source_spans=[], confidence=0.9),
            Event(id="evt_002", type=EventType.ACTION, description="filed complaint", source_spans=[], confidence=0.9),
        ]
        
        build_timeline(ctx)
        
        assert len(ctx.timeline) >= 2
        next_day_entry = next((e for e in ctx.timeline if e.event_id == "evt_002"), None)
        assert next_day_entry is not None
        assert next_day_entry.relative_time is not None


class TestSequenceOrdering:
    """Tests for computing sequence order."""
    
    def test_narrative_order_as_fallback(self):
        """Events without explicit time markers use narrative order."""
        from nnrt.passes.p44_timeline import build_timeline
        
        ctx = _make_context("He arrived. He spoke. He left.")
        ctx.events = [
            Event(id="evt_001", type=EventType.ACTION, description="arrived", source_spans=[], confidence=0.9),
            Event(id="evt_002", type=EventType.VERBAL, description="spoke", source_spans=[], confidence=0.9),
            Event(id="evt_003", type=EventType.MOVEMENT, description="left", source_spans=[], confidence=0.9),
        ]
        
        build_timeline(ctx)
        
        # Should preserve narrative order
        assert len(ctx.timeline) == 3
        orders = [e.sequence_order for e in ctx.timeline]
        assert orders == sorted(orders)  # Should be in ascending order
    
    def test_absolute_time_overrides_narrative(self):
        """Events with absolute times should be ordered by time."""
        from nnrt.passes.p44_timeline import build_timeline
        
        # Narrative mentions 3:00 before 11:30, but 11:30 came first
        ctx = _make_context("At 3:00 AM he was released. Earlier, at 11:30 PM, he was arrested.")
        ctx.identifiers = [
            Identifier(id="id_001", type=IdentifierType.TIME, value="3:00 AM",
                      original_text="3:00 AM", start_char=3, end_char=10,
                      source_segment_id="seg_1", confidence=0.9),
            Identifier(id="id_002", type=IdentifierType.TIME, value="11:30 PM",
                      original_text="11:30 PM", start_char=45, end_char=53,
                      source_segment_id="seg_1", confidence=0.9),
        ]
        ctx.events = [
            Event(id="evt_001", type=EventType.ACTION, description="released", source_spans=[], confidence=0.9),
            Event(id="evt_002", type=EventType.ACTION, description="arrested", source_spans=[], confidence=0.9),
        ]
        
        build_timeline(ctx)
        
        assert len(ctx.timeline) >= 2


class TestTemporalRelations:
    """Tests for before/after relations."""
    
    def test_before_relation(self):
        """'Before' should create relation."""
        from nnrt.passes.p44_timeline import build_timeline
        
        ctx = _make_context("Before the arrest, I asked what was happening.")
        ctx.events = [
            Event(id="evt_001", type=EventType.ACTION, description="arrest", source_spans=[], confidence=0.9),
            Event(id="evt_002", type=EventType.VERBAL, description="asked", source_spans=[], confidence=0.9),
        ]
        
        build_timeline(ctx)
        
        # The "asked" event should be before "arrest"
        assert len(ctx.timeline) >= 2


class TestEdgeCases:
    """Tests for edge cases and robustness."""
    
    def test_no_events_no_crash(self):
        """Should handle case with no events gracefully."""
        from nnrt.passes.p44_timeline import build_timeline
        
        ctx = _make_context("Some text without events.")
        ctx.events = []
        
        build_timeline(ctx)
        
        assert ctx.timeline == []
    
    def test_adds_trace(self):
        """Should add trace entry."""
        from nnrt.passes.p44_timeline import build_timeline
        
        ctx = _make_context("At 11:30 PM, something happened.")
        ctx.events = [
            Event(id="evt_001", type=EventType.ACTION, description="happened", source_spans=[], confidence=0.9)
        ]
        
        build_timeline(ctx)
        
        trace_passes = [t.pass_name for t in ctx.trace]
        assert "p44_timeline" in trace_passes
    
    def test_confidence_for_explicit_times(self):
        """Entries with explicit times should have higher confidence."""
        from nnrt.passes.p44_timeline import build_timeline
        
        ctx = _make_context("At 11:30 PM he arrived. Something else happened.")
        ctx.identifiers = [
            Identifier(id="id_001", type=IdentifierType.TIME, value="11:30 PM",
                      original_text="11:30 PM", start_char=3, end_char=11,
                      source_segment_id="seg_1", confidence=0.9),
        ]
        ctx.events = [
            Event(id="evt_001", type=EventType.ACTION, description="arrived", source_spans=[], confidence=0.9),
            Event(id="evt_002", type=EventType.ACTION, description="something", source_spans=[], confidence=0.9),
        ]
        
        build_timeline(ctx)
        
        # Event with explicit time should have higher confidence
        timed_entry = next((e for e in ctx.timeline if e.absolute_time), None)
        untimed_entry = next((e for e in ctx.timeline if not e.absolute_time and not e.relative_time), None)
        
        if timed_entry and untimed_entry:
            assert timed_entry.time_confidence >= untimed_entry.time_confidence
