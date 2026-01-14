"""
Tests for the pipeline engine and passes.
"""

from nnrt.core.context import TransformContext, TransformRequest
from nnrt.core.engine import Engine, Pipeline
from nnrt.ir.enums import TransformStatus
from nnrt.passes import normalize, package, render, segment, tag_spans


def test_transform_request_generates_id():
    """TransformRequest should auto-generate an ID if not provided."""
    request = TransformRequest(text="Hello world")
    assert request.request_id is not None
    assert len(request.request_id) > 0


def test_context_from_request():
    """TransformContext should be created from request."""
    request = TransformRequest(text="Test input")
    ctx = TransformContext.from_request(request)
    assert ctx.raw_text == "Test input"
    assert ctx.request == request


def test_normalize_pass():
    """Normalize pass should clean up whitespace."""
    request = TransformRequest(text="  Hello   world  ")
    ctx = TransformContext.from_request(request)
    ctx = normalize(ctx)
    assert ctx.normalized_text == "Hello world"
    assert len(ctx.trace) == 1


def test_segment_pass():
    """Segment pass should split text into segments."""
    request = TransformRequest(text="First sentence. Second sentence.")
    ctx = TransformContext.from_request(request)
    ctx = normalize(ctx)
    ctx = segment(ctx)
    assert len(ctx.segments) >= 1


def test_full_pipeline():
    """Full pipeline should run without errors."""
    engine = Engine()
    pipeline = Pipeline(
        id="test",
        name="Test Pipeline",
        passes=[normalize, segment, tag_spans, render, package],
    )
    engine.register_pipeline(pipeline)

    request = TransformRequest(text="This is a test narrative.")
    result = engine.transform(request, "test")

    assert result.status in (TransformStatus.SUCCESS, TransformStatus.PARTIAL)
    assert result.rendered_text is not None
    assert len(result.trace) > 0


def test_pipeline_not_found():
    """Engine should handle missing pipeline gracefully."""
    engine = Engine()
    request = TransformRequest(text="Test")
    result = engine.transform(request, "nonexistent")

    assert result.status == TransformStatus.ERROR
    assert any(d.code == "PIPELINE_NOT_FOUND" for d in result.diagnostics)
