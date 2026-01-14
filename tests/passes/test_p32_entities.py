"""
Unit tests for p32_extract_entities.pass.
"""

import pytest
from nnrt.core.context import TransformContext, Segment, TransformRequest
from nnrt.passes.p32_extract_entities import extract_entities
from nnrt.ir.enums import EntityRole
from nnrt.ir.schema_v0_1 import Identifier

def test_extract_generic_subjects():
    """Verify generic subjects are extracted as distinct entities."""
    text = "The manager told the employee."
    req = TransformRequest(text=text)
    ctx = TransformContext(request=req, raw_text=text)
    ctx.segments = [Segment(id="seg_1", text=text, start_char=0, end_char=len(text))]
    
    extract_entities(ctx)
    
    # Expect 3 entities: Reporter, manager, employee
    assert len(ctx.entities) == 3
    labels = {e.label for e in ctx.entities}
    assert "manager" in labels
    assert "employee" in labels
    
    # Verify roles
    # Verify roles
    for ent in ctx.entities:
        if ent.label != "Reporter":
            assert ent.role == EntityRole.SUBJECT

def test_ambiguity_detection():
    """Verify ambiguity is detected when multiple candidates exist."""
    text = "The driver hit the passenger. He fled."
    req = TransformRequest(text=text)
    ctx = TransformContext(request=req, raw_text=text)
    ctx.segments = [Segment(id="seg_1", text=text, start_char=0, end_char=len(text))]
    
    extract_entities(ctx)
    
    # driver, passenger extracted.
    # "He" sees both.
    
    assert len(ctx.uncertainty) > 0
    u = ctx.uncertainty[0]
    assert "Ambiguous pronoun" in u.description
    assert "driver" in u.description
    assert "passenger" in u.description

def test_no_ambiguity_single_candidate():
    """Verify resolution works when only one candidate exists."""
    text = "The driver fled. He was fast."
    req = TransformRequest(text=text)
    ctx = TransformContext(request=req, raw_text=text)
    ctx.segments = [Segment(id="seg_1", text=text, start_char=0, end_char=len(text))]
    
    extract_entities(ctx)
    
    # driver extracted.
    # He -> driver.
    # No ambiguity.
    
    assert len(ctx.uncertainty) == 0
    # "He" mentions should be linked to driver
    # Mentions are now span IDs or "text:He" fallbacks
    driver = [e for e in ctx.entities if e.label == "driver"][0]
    # Check that driver has a mention containing "He" (either as span ID or text fallback)
    has_he_mention = any("He" in m or "he" in m for m in driver.mentions)
    assert has_he_mention, f"Expected 'He' mention in driver, got: {driver.mentions}"


class TestInterfaceSwapping:
    """Tests demonstrating interface-based backend swapping."""
    
    def test_can_use_stub_extractor(self):
        """Verify stub extractor can be injected for testing."""
        from nnrt.nlp.backends.stub import StubEntityExtractor
        from nnrt.passes.p32_extract_entities import set_extractor, reset_extractor
        
        try:
            # Inject stub extractor
            set_extractor(StubEntityExtractor())
            
            text = "The officer grabbed my arm."
            req = TransformRequest(text=text)
            ctx = TransformContext(request=req, raw_text=text)
            ctx.segments = [Segment(id="seg_1", text=text, start_char=0, end_char=len(text))]
            
            extract_entities(ctx)
            
            # Stub returns no extraction results, so only Reporter exists
            assert len(ctx.entities) == 1
            assert ctx.entities[0].label == "Reporter"
        finally:
            # Reset to default
            reset_extractor()
    
    def test_default_extractor_works_after_reset(self):
        """Verify reset_extractor restores default behavior."""
        from nnrt.passes.p32_extract_entities import reset_extractor
        
        reset_extractor()
        
        text = "The manager told the employee."
        req = TransformRequest(text=text)
        ctx = TransformContext(request=req, raw_text=text)
        ctx.segments = [Segment(id="seg_1", text=text, start_char=0, end_char=len(text))]
        
        extract_entities(ctx)
        
        # Default spaCy extractor should find entities
        assert len(ctx.entities) >= 2  # At least Reporter + one other

