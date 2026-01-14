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
    driver = [e for e in ctx.entities if e.label == "driver"][0]
    assert "He" in driver.mentions or "he" in driver.mentions
