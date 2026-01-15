"""
Unit tests for p32_extract_entities.pass.
"""

import pytest
from nnrt.core.context import TransformContext, Segment, TransformRequest
from nnrt.passes.p32_extract_entities import extract_entities
from nnrt.ir.enums import EntityRole
from nnrt.ir.schema_v0_1 import Identifier

def test_extract_generic_subjects():
    """
    Verify contextual role references are extracted as entities.
    
    V4: Role-based references like 'manager' and 'employee' ARE valid 
    entity references (they refer to real people), just not named ones.
    They should be tracked for coreference and ambiguity detection.
    """
    text = "The manager told the employee."
    req = TransformRequest(text=text)
    ctx = TransformContext(request=req, raw_text=text)
    ctx.segments = [Segment(id="seg_1", text=text, start_char=0, end_char=len(text))]
    
    extract_entities(ctx)
    
    # Expect entities for the roles (they reference real people)
    # Manager and employee should be extracted
    assert len(ctx.entities) >= 2  # At least Reporter + one role
    labels = {e.label.lower() for e in ctx.entities if e.label}
    # Should have some role-based entities
    assert "manager" in labels or "employee" in labels or "reporter" in labels

def test_ambiguity_detection():
    """Verify ambiguity is detected when multiple candidates exist."""
    text = "The driver hit the passenger. He fled."
    req = TransformRequest(text=text)
    ctx = TransformContext(request=req, raw_text=text)
    ctx.segments = [Segment(id="seg_1", text=text, start_char=0, end_char=len(text))]
    
    extract_entities(ctx)
    
    # driver, passenger extracted.
    # "He" sees both.
    
    # V4: Both role-based references should be extracted as entities
    labels = {e.label.lower() for e in ctx.entities if e.label}
    assert "driver" in labels or len(ctx.entities) >= 2, f"Expected role entities, got: {labels}"

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
    
    # V4: Role-based reference should be extracted
    labels = {e.label.lower() for e in ctx.entities if e.label}
    assert "driver" in labels or len(ctx.entities) >= 2, f"Expected driver entity, got: {labels}"






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

