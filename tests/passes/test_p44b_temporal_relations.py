"""
Unit tests for p44b_temporal_relations pass.

V6 Timeline Reconstruction: Stage 2 Tests
"""

import pytest
from nnrt.core.context import TransformContext, TransformRequest
from nnrt.ir.schema_v0_1 import Segment, Event, TemporalExpression
from nnrt.ir.enums import EventType, AllenRelation, RelationEvidence, TemporalExpressionType


def _make_context_with_events(text: str, events: list) -> TransformContext:
    """Helper to create a context with segments and events."""
    req = TransformRequest(text=text)
    ctx = TransformContext(request=req, raw_text=text)
    ctx.normalized_text = text
    ctx.segments = [Segment(id="seg_1", text=text, start_char=0, end_char=len(text))]
    ctx.events = events
    ctx.temporal_expressions = []
    return ctx


class TestBasicRelations:
    """Tests for basic temporal relation extraction."""
    
    def test_creates_relations_between_adjacent_events(self):
        """Should create relations between adjacent event pairs."""
        from nnrt.passes.p44b_temporal_relations import extract_temporal_relations
        
        text = "He arrived. He spoke. He left."
        events = [
            Event(id="evt_001", type=EventType.ACTION, description="arrived", source_spans=[], confidence=0.9),
            Event(id="evt_002", type=EventType.VERBAL, description="spoke", source_spans=[], confidence=0.9),
            Event(id="evt_003", type=EventType.MOVEMENT, description="left", source_spans=[], confidence=0.9),
        ]
        
        ctx = _make_context_with_events(text, events)
        extract_temporal_relations(ctx)
        
        # Should have 2 relations: evt_001→evt_002, evt_002→evt_003
        assert len(ctx.temporal_relationships) == 2
    
    def test_default_relation_is_before(self):
        """Without markers, narrative order implies BEFORE."""
        from nnrt.passes.p44b_temporal_relations import extract_temporal_relations
        
        text = "He arrived. He left."
        events = [
            Event(id="evt_001", type=EventType.ACTION, description="arrived", source_spans=[], confidence=0.9),
            Event(id="evt_002", type=EventType.MOVEMENT, description="left", source_spans=[], confidence=0.9),
        ]
        
        ctx = _make_context_with_events(text, events)
        extract_temporal_relations(ctx)
        
        assert len(ctx.temporal_relationships) == 1
        rel = ctx.temporal_relationships[0]
        assert rel.relation == AllenRelation.BEFORE
        assert rel.evidence_type == RelationEvidence.NARRATIVE_ORDER


class TestMarkerBasedRelations:
    """Tests for relations inferred from temporal markers."""
    
    def test_then_marker_creates_before(self):
        """'then' marker creates BEFORE relation with explicit evidence."""
        from nnrt.passes.p44a_temporal_expressions import extract_temporal_expressions
        from nnrt.passes.p44b_temporal_relations import extract_temporal_relations
        
        text = "He arrived then left."
        events = [
            Event(id="evt_001", type=EventType.ACTION, description="arrived", source_spans=[], confidence=0.9),
            Event(id="evt_002", type=EventType.MOVEMENT, description="left", source_spans=[], confidence=0.9),
        ]
        
        ctx = _make_context_with_events(text, events)
        extract_temporal_expressions(ctx)
        extract_temporal_relations(ctx)
        
        assert len(ctx.temporal_relationships) >= 1
        rel = ctx.temporal_relationships[0]
        assert rel.relation == AllenRelation.BEFORE
        assert rel.evidence_type == RelationEvidence.EXPLICIT_MARKER
        assert "then" in rel.evidence_text.lower() if rel.evidence_text else False
    
    def test_while_marker_creates_during(self):
        """'while' marker creates DURING relation."""
        from nnrt.passes.p44a_temporal_expressions import extract_temporal_expressions
        from nnrt.passes.p44b_temporal_relations import extract_temporal_relations
        
        text = "While he was running, she was watching."
        events = [
            Event(id="evt_001", type=EventType.MOVEMENT, description="running", source_spans=[], confidence=0.9),
            Event(id="evt_002", type=EventType.ACTION, description="watching", source_spans=[], confidence=0.9),
        ]
        
        ctx = _make_context_with_events(text, events)
        extract_temporal_expressions(ctx)
        extract_temporal_relations(ctx)
        
        # Should have a DURING relation
        during_rels = [r for r in ctx.temporal_relationships if r.relation == AllenRelation.DURING]
        assert len(during_rels) >= 1
    
    def test_duration_marker_creates_before(self):
        """'20 minutes later' creates BEFORE relation with gap."""
        from nnrt.passes.p44a_temporal_expressions import extract_temporal_expressions
        from nnrt.passes.p44b_temporal_relations import extract_temporal_relations
        
        text = "He arrived. About 20 minutes later she left."
        events = [
            Event(id="evt_001", type=EventType.ACTION, description="arrived", source_spans=[], confidence=0.9),
            Event(id="evt_002", type=EventType.MOVEMENT, description="left", source_spans=[], confidence=0.9),
        ]
        
        ctx = _make_context_with_events(text, events)
        extract_temporal_expressions(ctx)
        extract_temporal_relations(ctx)
        
        assert len(ctx.temporal_relationships) >= 1
        rel = ctx.temporal_relationships[0]
        assert rel.relation == AllenRelation.BEFORE
        assert rel.evidence_type == RelationEvidence.EXPLICIT_MARKER


class TestAllenRelationMethods:
    """Tests for AllenRelation enum methods."""
    
    def test_display_label_simplified(self):
        """Should return simplified labels."""
        assert AllenRelation.BEFORE.display_label(simplified=True) == "then"
        assert AllenRelation.DURING.display_label(simplified=True) == "during"
        assert AllenRelation.EQUALS.display_label(simplified=True) == "at the same time as"
    
    def test_display_label_full(self):
        """Should return full relation names."""
        assert AllenRelation.BEFORE.display_label(simplified=False) == "before"
        assert AllenRelation.MET_BY.display_label(simplified=False) == "met by"
    
    def test_inverse_relations(self):
        """Should return correct inverse relations."""
        assert AllenRelation.BEFORE.inverse() == AllenRelation.AFTER
        assert AllenRelation.AFTER.inverse() == AllenRelation.BEFORE
        assert AllenRelation.DURING.inverse() == AllenRelation.CONTAINS
        assert AllenRelation.CONTAINS.inverse() == AllenRelation.DURING
        assert AllenRelation.MEETS.inverse() == AllenRelation.MET_BY
        assert AllenRelation.EQUALS.inverse() == AllenRelation.EQUALS


class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_no_events_no_crash(self):
        """Handles empty event list gracefully."""
        from nnrt.passes.p44b_temporal_relations import extract_temporal_relations
        
        text = "Some text without events."
        ctx = _make_context_with_events(text, [])
        extract_temporal_relations(ctx)
        
        assert ctx.temporal_relationships == []
    
    def test_single_event_no_relations(self):
        """Single event has no relations."""
        from nnrt.passes.p44b_temporal_relations import extract_temporal_relations
        
        text = "He arrived."
        events = [
            Event(id="evt_001", type=EventType.ACTION, description="arrived", source_spans=[], confidence=0.9),
        ]
        
        ctx = _make_context_with_events(text, events)
        extract_temporal_relations(ctx)
        
        assert ctx.temporal_relationships == []
    
    def test_adds_trace(self):
        """Should add trace entry."""
        from nnrt.passes.p44b_temporal_relations import extract_temporal_relations
        
        text = "He arrived. He left."
        events = [
            Event(id="evt_001", type=EventType.ACTION, description="arrived", source_spans=[], confidence=0.9),
            Event(id="evt_002", type=EventType.MOVEMENT, description="left", source_spans=[], confidence=0.9),
        ]
        
        ctx = _make_context_with_events(text, events)
        extract_temporal_relations(ctx)
        
        trace_passes = [t.pass_name for t in ctx.trace]
        assert "p44b_temporal_relations" in trace_passes


class TestComplexScenarios:
    """Tests for more complex temporal scenarios."""
    
    def test_full_narrative(self):
        """Full narrative with multiple relation types."""
        from nnrt.passes.p44a_temporal_expressions import extract_temporal_expressions
        from nnrt.passes.p44b_temporal_relations import extract_temporal_relations
        
        text = """At 11:30 PM I was walking. Officer Jenkins approached me then grabbed my arm.
        About 20 minutes later, Sergeant Williams arrived. The next day, I filed a complaint."""
        
        events = [
            Event(id="evt_001", type=EventType.MOVEMENT, description="walking", source_spans=[], confidence=0.9),
            Event(id="evt_002", type=EventType.ACTION, description="approached me", source_spans=[], confidence=0.9),
            Event(id="evt_003", type=EventType.ACTION, description="grabbed my arm", source_spans=[], confidence=0.9),
            Event(id="evt_004", type=EventType.ACTION, description="Williams arrived", source_spans=[], confidence=0.9),
            Event(id="evt_005", type=EventType.ACTION, description="filed a complaint", source_spans=[], confidence=0.9),
        ]
        
        ctx = _make_context_with_events(text, events)
        extract_temporal_expressions(ctx)
        extract_temporal_relations(ctx)
        
        # Should have 4 relations (n-1 for n events)
        assert len(ctx.temporal_relationships) == 4
        
        # All should be BEFORE type for this narrative
        for rel in ctx.temporal_relationships:
            assert rel.relation == AllenRelation.BEFORE
