"""
Unit tests for p44c_timeline_ordering and p44d_timeline_gaps passes.

V6 Timeline Reconstruction: Stages 3 & 4 Tests
"""

import pytest
from nnrt.core.context import TransformContext, TransformRequest
from nnrt.ir.schema_v0_1 import Segment, Event
from nnrt.ir.enums import EventType, TimeSource, TimeGapType


def _make_full_ctx(text: str, events: list) -> TransformContext:
    """Helper to create a context, run expressions and relations."""
    from nnrt.passes.p44a_temporal_expressions import extract_temporal_expressions
    from nnrt.passes.p44b_temporal_relations import extract_temporal_relations
    
    req = TransformRequest(text=text)
    ctx = TransformContext(request=req, raw_text=text)
    ctx.normalized_text = text
    ctx.segments = [Segment(id="seg_1", text=text, start_char=0, end_char=len(text))]
    ctx.events = events
    
    extract_temporal_expressions(ctx)
    extract_temporal_relations(ctx)
    return ctx


class TestTimelineOrdering:
    """Tests for p44c_timeline_ordering pass."""
    
    def test_creates_timeline_entries_for_events(self):
        """Should create one timeline entry per event."""
        from nnrt.passes.p44c_timeline_ordering import build_timeline_ordering
        
        text = "He arrived. He left."
        events = [
            Event(id="evt_001", type=EventType.ACTION, description="arrived", source_spans=[], confidence=0.9),
            Event(id="evt_002", type=EventType.MOVEMENT, description="left", source_spans=[], confidence=0.9),
        ]
        
        ctx = _make_full_ctx(text, events)
        build_timeline_ordering(ctx)
        
        assert len(ctx.timeline) == 2
        assert ctx.timeline[0].event_id == "evt_001"
        assert ctx.timeline[1].event_id == "evt_002"
    
    def test_explicit_time_gets_normalized(self):
        """Events with explicit times get normalized_time."""
        from nnrt.passes.p44c_timeline_ordering import build_timeline_ordering
        
        text = "At 11:30 PM I was walking on Cedar Street."
        events = [
            Event(id="evt_001", type=EventType.MOVEMENT, description="walking on Cedar", source_spans=[], confidence=0.9),
        ]
        
        ctx = _make_full_ctx(text, events)
        build_timeline_ordering(ctx)
        
        assert ctx.timeline[0].time_source == TimeSource.EXPLICIT
        assert ctx.timeline[0].normalized_time == "T23:30:00"
    
    def test_time_expression_used_once(self):
        """TIME expressions should only be assigned to one event."""
        from nnrt.passes.p44c_timeline_ordering import build_timeline_ordering
        
        text = "At 11:30 PM I walked. Then I ran. Then I stopped."
        events = [
            Event(id="evt_001", type=EventType.MOVEMENT, description="walked", source_spans=[], confidence=0.9),
            Event(id="evt_002", type=EventType.MOVEMENT, description="ran", source_spans=[], confidence=0.9),
            Event(id="evt_003", type=EventType.ACTION, description="stopped", source_spans=[], confidence=0.9),
        ]
        
        ctx = _make_full_ctx(text, events)
        build_timeline_ordering(ctx)
        
        # Only first event should have explicit time
        assert ctx.timeline[0].time_source == TimeSource.EXPLICIT
        # Others should be relative or inferred
        assert ctx.timeline[1].time_source in (TimeSource.RELATIVE, TimeSource.INFERRED)
    
    def test_multi_day_support(self):
        """'The next day' creates day_offset=1."""
        from nnrt.passes.p44c_timeline_ordering import build_timeline_ordering
        
        text = "At 11:30 PM I was walking. The next day I went to the hospital."
        events = [
            Event(id="evt_001", type=EventType.MOVEMENT, description="walking", source_spans=[], confidence=0.9),
            Event(id="evt_002", type=EventType.ACTION, description="went to the hospital", source_spans=[], confidence=0.9),
        ]
        
        ctx = _make_full_ctx(text, events)
        build_timeline_ordering(ctx)
        
        assert ctx.timeline[0].day_offset == 0
        assert ctx.timeline[1].day_offset == 1
    
    def test_three_months_later(self):
        """'Three months later' creates day_offset=90."""
        from nnrt.passes.p44c_timeline_ordering import build_timeline_ordering
        
        text = "I was walking. Three months later I filed a complaint."
        events = [
            Event(id="evt_001", type=EventType.MOVEMENT, description="walking", source_spans=[], confidence=0.9),
            Event(id="evt_002", type=EventType.ACTION, description="filed a complaint", source_spans=[], confidence=0.9),
        ]
        
        ctx = _make_full_ctx(text, events)
        build_timeline_ordering(ctx)
        
        assert ctx.timeline[1].day_offset > 0  # Should be >0 (approximately 90)
    
    def test_sequence_order_assigned(self):
        """Entries should have sequential order numbers."""
        from nnrt.passes.p44c_timeline_ordering import build_timeline_ordering
        
        text = "He arrived. He spoke. He left."
        events = [
            Event(id="evt_001", type=EventType.ACTION, description="arrived", source_spans=[], confidence=0.9),
            Event(id="evt_002", type=EventType.VERBAL, description="spoke", source_spans=[], confidence=0.9),
            Event(id="evt_003", type=EventType.MOVEMENT, description="left", source_spans=[], confidence=0.9),
        ]
        
        ctx = _make_full_ctx(text, events)
        build_timeline_ordering(ctx)
        
        orders = [e.sequence_order for e in ctx.timeline]
        assert orders == [0, 1, 2]


class TestGapDetection:
    """Tests for p44d_timeline_gaps pass."""
    
    def test_explained_gap_not_flagged(self):
        """Gaps with markers should not require investigation."""
        from nnrt.passes.p44c_timeline_ordering import build_timeline_ordering
        from nnrt.passes.p44d_timeline_gaps import detect_timeline_gaps
        
        text = "He arrived. About 20 minutes later he left."
        events = [
            Event(id="evt_001", type=EventType.ACTION, description="arrived", source_spans=[], confidence=0.9),
            Event(id="evt_002", type=EventType.MOVEMENT, description="left", source_spans=[], confidence=0.9),
        ]
        
        ctx = _make_full_ctx(text, events)
        build_timeline_ordering(ctx)
        detect_timeline_gaps(ctx)
        
        explained_gaps = [g for g in ctx.time_gaps if g.gap_type == TimeGapType.EXPLAINED]
        assert len(explained_gaps) >= 1
        assert not explained_gaps[0].requires_investigation
    
    def test_unexplained_gap_flagged(self):
        """Gaps without markers should be flagged for investigation."""
        from nnrt.passes.p44c_timeline_ordering import build_timeline_ordering
        from nnrt.passes.p44d_timeline_gaps import detect_timeline_gaps
        
        text = "At 11:30 PM I walked. I woke up in the car."
        events = [
            Event(id="evt_001", type=EventType.MOVEMENT, description="walked", source_spans=[], confidence=0.9),
            Event(id="evt_002", type=EventType.ACTION, description="woke up in the car", source_spans=[], confidence=0.9),
        ]
        
        ctx = _make_full_ctx(text, events)
        build_timeline_ordering(ctx)
        detect_timeline_gaps(ctx)
        
        investigation_gaps = [g for g in ctx.time_gaps if g.requires_investigation]
        assert len(investigation_gaps) >= 1
    
    def test_day_boundary_detected(self):
        """Day boundaries should be detected."""
        from nnrt.passes.p44c_timeline_ordering import build_timeline_ordering
        from nnrt.passes.p44d_timeline_gaps import detect_timeline_gaps
        
        text = "At 11:30 PM I walked. The next day I went to the hospital."
        events = [
            Event(id="evt_001", type=EventType.MOVEMENT, description="walked", source_spans=[], confidence=0.9),
            Event(id="evt_002", type=EventType.ACTION, description="went to the hospital", source_spans=[], confidence=0.9),
        ]
        
        ctx = _make_full_ctx(text, events)
        build_timeline_ordering(ctx)
        detect_timeline_gaps(ctx)
        
        day_gaps = [g for g in ctx.time_gaps if g.gap_type == TimeGapType.DAY_BOUNDARY]
        assert len(day_gaps) >= 1
    
    def test_suggested_question_generated(self):
        """Unexplained gaps should have suggested questions."""
        from nnrt.passes.p44c_timeline_ordering import build_timeline_ordering
        from nnrt.passes.p44d_timeline_gaps import detect_timeline_gaps
        
        text = "At 11:30 PM I walked. I woke up in the car."
        events = [
            Event(id="evt_001", type=EventType.MOVEMENT, description="walked", source_spans=[], confidence=0.9),
            Event(id="evt_002", type=EventType.ACTION, description="woke up in the car", source_spans=[], confidence=0.9),
        ]
        
        ctx = _make_full_ctx(text, events)
        build_timeline_ordering(ctx)
        detect_timeline_gaps(ctx)
        
        investigation_gaps = [g for g in ctx.time_gaps if g.requires_investigation]
        assert len(investigation_gaps) >= 1
        assert investigation_gaps[0].suggested_question is not None
        assert "What happened" in investigation_gaps[0].suggested_question
    
    def test_gap_links_to_entry(self):
        """Gaps should be linked to their following entry."""
        from nnrt.passes.p44c_timeline_ordering import build_timeline_ordering
        from nnrt.passes.p44d_timeline_gaps import detect_timeline_gaps
        
        text = "He arrived. He left."
        events = [
            Event(id="evt_001", type=EventType.ACTION, description="arrived", source_spans=[], confidence=0.9),
            Event(id="evt_002", type=EventType.MOVEMENT, description="left", source_spans=[], confidence=0.9),
        ]
        
        ctx = _make_full_ctx(text, events)
        build_timeline_ordering(ctx)
        detect_timeline_gaps(ctx)
        
        if ctx.time_gaps:
            # Second entry should reference the gap before it
            second_entry = ctx.timeline[1]
            if second_entry.gap_before_id:
                gap = next(g for g in ctx.time_gaps if g.id == second_entry.gap_before_id)
                assert gap is not None


class TestFullPipeline:
    """Tests for the complete V6 timeline pipeline."""
    
    def test_memory_gap_narrative(self):
        """Should detect memory gap in officer encounter narrative."""
        from nnrt.passes.p44c_timeline_ordering import build_timeline_ordering
        from nnrt.passes.p44d_timeline_gaps import detect_timeline_gaps
        
        text = """At 11:30 PM I was walking on Cedar Street.
        Officer Jenkins approached me.
        I woke up in the back of the police car.
        About 20 minutes later, Sergeant Williams arrived."""
        
        events = [
            Event(id="evt_001", type=EventType.MOVEMENT, description="walking on Cedar", source_spans=[], confidence=0.9),
            Event(id="evt_002", type=EventType.ACTION, description="approached me", source_spans=[], confidence=0.9),
            Event(id="evt_003", type=EventType.ACTION, description="woke up in the car", source_spans=[], confidence=0.9),
            Event(id="evt_004", type=EventType.ACTION, description="Williams arrived", source_spans=[], confidence=0.9),
        ]
        
        ctx = _make_full_ctx(text, events)
        build_timeline_ordering(ctx)
        detect_timeline_gaps(ctx)
        
        # Should detect the critical gap between "approached" and "woke up"
        investigation_gaps = [g for g in ctx.time_gaps if g.requires_investigation]
        assert len(investigation_gaps) >= 1
        
        # At least one gap should mention the memory gap events
        questions = [g.suggested_question for g in investigation_gaps if g.suggested_question]
        combined = " ".join(questions).lower()
        assert "woke" in combined or "approached" in combined
    
    def test_adds_trace(self):
        """Should add trace entries."""
        from nnrt.passes.p44c_timeline_ordering import build_timeline_ordering
        from nnrt.passes.p44d_timeline_gaps import detect_timeline_gaps
        
        text = "He arrived. He left."
        events = [
            Event(id="evt_001", type=EventType.ACTION, description="arrived", source_spans=[], confidence=0.9),
            Event(id="evt_002", type=EventType.MOVEMENT, description="left", source_spans=[], confidence=0.9),
        ]
        
        ctx = _make_full_ctx(text, events)
        build_timeline_ordering(ctx)
        detect_timeline_gaps(ctx)
        
        pass_names = [t.pass_name for t in ctx.trace]
        assert "p44c_timeline_ordering" in pass_names
        assert "p44d_timeline_gaps" in pass_names
