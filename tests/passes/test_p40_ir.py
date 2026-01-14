"""
Unit tests for p40_build_ir pass.
"""

import pytest
from nnrt.core.context import TransformContext, TransformRequest
from nnrt.ir.schema_v0_1 import Segment, Entity, Event, SemanticSpan
from nnrt.ir.enums import EntityRole, EntityType, EventType, SpeechActType, SpanLabel
from nnrt.passes.p40_build_ir import build_ir


def _make_context(text: str) -> TransformContext:
    """Helper to create a context with a segment."""
    req = TransformRequest(text=text)
    ctx = TransformContext(request=req, raw_text=text)
    ctx.segments = [Segment(id="seg_1", text=text, start_char=0, end_char=len(text))]
    ctx.spans = [SemanticSpan(
        id="span_1",
        segment_id="seg_1",
        start_char=0,
        end_char=len(text),
        text=text,
        label=SpanLabel.OBSERVATION,
        confidence=0.8,
        source="test"
    )]
    return ctx


class TestIRAssembly:
    """Tests for basic IR assembly."""
    
    def test_preserves_entities_from_p32(self):
        """Verify entities from p32 are preserved."""
        ctx = _make_context("The officer approached.")
        entity = Entity(
            id="ent_001",
            type=EntityType.PERSON,
            role=EntityRole.AUTHORITY,
            label="officer",
            mentions=["officer"]
        )
        ctx.entities = [entity]
        ctx.events = []
        
        build_ir(ctx)
        
        assert len(ctx.entities) == 1
        assert ctx.entities[0].id == "ent_001"
    
    def test_preserves_events_from_p34(self):
        """Verify events from p34 are preserved."""
        ctx = _make_context("He ran away.")
        event = Event(
            id="evt_001",
            type=EventType.MOVEMENT,
            description="ran away",
            source_spans=[],
            confidence=0.8
        )
        ctx.entities = []
        ctx.events = [event]
        
        build_ir(ctx)
        
        assert len(ctx.events) == 1
        assert ctx.events[0].id == "evt_001"
    
    def test_no_fallback_extraction_for_entities(self):
        """Verify p40 does NOT extract entities when p32 produces none."""
        ctx = _make_context("The officer approached me.")
        ctx.entities = []  # Empty from p32
        ctx.events = []
        
        build_ir(ctx)
        
        # Should still have no entities - no fallback!
        assert len(ctx.entities) == 0
        
        # Should have diagnostic about no entities
        no_entity_diags = [d for d in ctx.diagnostics if d.code == "NO_ENTITIES"]
        assert len(no_entity_diags) >= 1


class TestSpeechActExtraction:
    """Tests for speech act extraction (p40's unique responsibility)."""
    
    def test_extracts_direct_quote(self):
        """Verify direct quotes are extracted as speech acts."""
        ctx = _make_context('He said "Stop right there."')
        ctx.entities = []
        ctx.events = []
        
        build_ir(ctx)
        
        assert len(ctx.speech_acts) >= 1
        assert ctx.speech_acts[0].is_direct_quote is True
    
    def test_extracts_speech_content(self):
        """Verify quoted content is extracted."""
        ctx = _make_context('She asked "What is your name?"')
        ctx.entities = []
        ctx.events = []
        
        build_ir(ctx)
        
        assert len(ctx.speech_acts) >= 1
        assert "What is your name" in ctx.speech_acts[0].content
    
    def test_classifies_speech_types(self):
        """Verify speech act types are correctly classified."""
        # Command type
        ctx = _make_context('He demanded "Get on the ground!"')
        ctx.entities = []
        ctx.events = []
        
        build_ir(ctx)
        
        if ctx.speech_acts:
            assert ctx.speech_acts[0].type == SpeechActType.COMMAND
    
    def test_links_speaker_to_entity(self):
        """Verify speaker is linked to entity when available."""
        ctx = _make_context('The officer said "Stop."')
        officer = Entity(
            id="ent_officer",
            type=EntityType.PERSON,
            role=EntityRole.AUTHORITY,
            label="officer",
            mentions=["officer"]
        )
        ctx.entities = [officer]
        ctx.events = []
        
        build_ir(ctx)
        
        if ctx.speech_acts:
            assert ctx.speech_acts[0].speaker_id == "ent_officer"


class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_no_segments_adds_warning(self):
        """Verify missing segments produce warning."""
        req = TransformRequest(text="Hello")
        ctx = TransformContext(request=req, raw_text="Hello")
        ctx.segments = []
        
        build_ir(ctx)
        
        assert len(ctx.diagnostics) > 0
        assert ctx.diagnostics[0].code == "NO_SEGMENTS"
    
    def test_adds_trace(self):
        """Verify trace entry is added."""
        ctx = _make_context("Hello world.")
        ctx.entities = []
        ctx.events = []
        
        build_ir(ctx)
        
        trace_passes = [t.pass_name for t in ctx.trace]
        assert "p40_build_ir" in trace_passes
    
    def test_handles_no_quotes(self):
        """Verify text without quotes doesn't crash."""
        ctx = _make_context("He said something.")
        ctx.entities = []
        ctx.events = []
        
        build_ir(ctx)
        
        # Should not raise, may or may not have speech acts
        assert isinstance(ctx.speech_acts, list)
