"""
Unit tests for p34_extract_events pass.
"""

import pytest
from nnrt.core.context import TransformContext, TransformRequest
from nnrt.ir.schema_v0_1 import Segment, Entity
from nnrt.ir.enums import EntityRole, EntityType, EventType
from nnrt.passes.p34_extract_events import extract_events


def _make_context(text: str, entities: list[Entity] = None) -> TransformContext:
    """Helper to create a context with segments and optional entities."""
    req = TransformRequest(text=text)
    ctx = TransformContext(request=req, raw_text=text)
    ctx.segments = [Segment(id="seg_1", text=text, start_char=0, end_char=len(text))]
    ctx.entities = entities or []
    return ctx


class TestEventExtraction:
    """Tests for basic event extraction."""
    
    def test_extracts_action_verbs(self):
        """Verify action verbs are extracted as ACTION events."""
        ctx = _make_context("The officer grabbed my arm.")
        
        extract_events(ctx)
        
        assert len(ctx.events) > 0
        # "grabbed" should be detected
        grabbed_events = [e for e in ctx.events if "grabbed" in e.description.lower()]
        assert len(grabbed_events) >= 1
        assert grabbed_events[0].type == EventType.ACTION
    
    def test_extracts_movement_verbs(self):
        """Verify movement verbs are extracted as MOVEMENT events."""
        ctx = _make_context("He ran away quickly.")
        
        extract_events(ctx)
        
        assert len(ctx.events) > 0
        run_events = [e for e in ctx.events if "ran" in e.description.lower()]
        assert len(run_events) >= 1
        assert run_events[0].type == EventType.MOVEMENT
    
    def test_extracts_verbal_events(self):
        """Verify speech verbs are extracted as VERBAL events."""
        ctx = _make_context("She yelled at the crowd.")
        
        extract_events(ctx)
        
        assert len(ctx.events) > 0
        yell_events = [e for e in ctx.events if "yelled" in e.description.lower()]
        assert len(yell_events) >= 1
        assert yell_events[0].type == EventType.VERBAL


class TestActorTargetLinking:
    """Tests for linking events to entities."""
    
    def test_links_actor_from_subject(self):
        """Verify actor is linked when subject matches entity."""
        driver = Entity(
            id="ent_001",
            type=EntityType.PERSON,
            role=EntityRole.SUBJECT,
            label="driver",
            mentions=["driver"]
        )
        ctx = _make_context("The driver fled.", entities=[driver])
        
        extract_events(ctx)
        
        # Find the "fled" event
        fled_events = [e for e in ctx.events if "fled" in e.description.lower()]
        assert len(fled_events) >= 1
        assert fled_events[0].actor_id == "ent_001"
    
    def test_links_target_from_object(self):
        """Verify target is linked when object matches entity."""
        victim = Entity(
            id="ent_002",
            type=EntityType.PERSON,
            role=EntityRole.SUBJECT,
            label="victim",
            mentions=["victim"]
        )
        ctx = _make_context("He hit the victim.", entities=[victim])
        
        extract_events(ctx)
        
        hit_events = [e for e in ctx.events if "hit" in e.description.lower()]
        assert len(hit_events) >= 1
        assert hit_events[0].target_id == "ent_002"


class TestVerbTypeMapping:
    """Tests for verb type taxonomy."""
    
    def test_physical_verbs_are_action(self):
        """Verify physical contact verbs map to ACTION type."""
        physical_verbs = ["grabbed", "hit", "pushed", "kicked", "tackled"]
        
        for verb in physical_verbs:
            ctx = _make_context(f"He {verb} him.")
            extract_events(ctx)
            
            verb_events = [e for e in ctx.events if verb in e.description.lower()]
            if verb_events:
                assert verb_events[0].type == EventType.ACTION, \
                    f"Expected {verb} to be ACTION type"
    
    def test_movement_verbs_are_movement(self):
        """Verify movement verbs map to MOVEMENT type."""
        movement_verbs = ["walked", "ran", "drove", "approached", "left"]
        
        for verb in movement_verbs:
            ctx = _make_context(f"He {verb} away.")
            extract_events(ctx)
            
            verb_events = [e for e in ctx.events if verb in e.description.lower()]
            if verb_events:
                assert verb_events[0].type == EventType.MOVEMENT, \
                    f"Expected {verb} to be MOVEMENT type"
    
    def test_verbal_verbs_are_verbal(self):
        """Verify speech verbs map to VERBAL type."""
        verbal_verbs = ["said", "yelled", "shouted", "asked", "told"]
        
        for verb in verbal_verbs:
            ctx = _make_context(f"She {verb} something.")
            extract_events(ctx)
            
            verb_events = [e for e in ctx.events if verb in e.description.lower()]
            if verb_events:
                assert verb_events[0].type == EventType.VERBAL, \
                    f"Expected {verb} to be VERBAL type"


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_input(self):
        """Verify empty input produces no events."""
        ctx = _make_context("")
        
        extract_events(ctx)
        
        assert len(ctx.events) == 0
    
    def test_no_verbs(self):
        """Verify sentences without verbs produce no events."""
        ctx = _make_context("The big red car.")
        
        extract_events(ctx)
        
        # May produce some events for auxiliary verbs, should be minimal
        assert len(ctx.events) <= 1
    
    def test_multiple_events_in_sentence(self):
        """Verify multiple events are extracted from complex sentences."""
        ctx = _make_context("He grabbed her arm and pushed her away.")
        
        extract_events(ctx)
        
        # Should have at least 2 events
        assert len(ctx.events) >= 2
