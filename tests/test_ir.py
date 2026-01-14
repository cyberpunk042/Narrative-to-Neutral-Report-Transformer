"""
Tests for IR models and serialization.
"""

from datetime import datetime

from nnrt.ir import Segment, SemanticSpan, SpanLabel, TransformResult, TransformStatus
from nnrt.ir.serialization import from_json, to_json


def test_segment_creation():
    """Segment should be created with required fields."""
    seg = Segment(
        id="seg_001",
        text="Test text",
        start_char=0,
        end_char=9,
    )
    assert seg.id == "seg_001"
    assert seg.text == "Test text"


def test_span_confidence_bounds():
    """Span confidence should be validated."""
    span = SemanticSpan(
        id="span_001",
        segment_id="seg_001",
        start_char=0,
        end_char=4,
        text="Test",
        label=SpanLabel.OBSERVATION,
        confidence=0.95,
        source="test",
    )
    assert span.confidence == 0.95


def test_transform_result_serialization():
    """TransformResult should serialize to/from JSON."""
    result = TransformResult(
        request_id="test-123",
        timestamp=datetime.now(),
        segments=[
            Segment(id="seg_001", text="Test", start_char=0, end_char=4),
        ],
        status=TransformStatus.SUCCESS,
    )

    json_str = to_json(result)
    assert "test-123" in json_str

    loaded = from_json(json_str)
    assert loaded.request_id == "test-123"
    assert len(loaded.segments) == 1
