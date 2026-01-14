"""
Pass 20 — Semantic Span Tagging

Tags spans within segments with semantic labels.
This is where the NLP encoder model will be used.
"""

from nnrt.core.context import TransformContext
from nnrt.ir.enums import SpanLabel
from nnrt.ir.schema_v0_1 import SemanticSpan

PASS_NAME = "p20_tag_spans"


def tag_spans(ctx: TransformContext) -> TransformContext:
    """
    Tag semantic spans within segments.
    
    STUB IMPLEMENTATION.
    
    In production, this will use an encoder model (BERT-class)
    to classify spans with semantic labels.
    
    Current stub: marks entire segment as UNKNOWN with low confidence.
    """
    spans: list[SemanticSpan] = []

    for segment in ctx.segments:
        # Stub: create one span per segment, labeled UNKNOWN
        spans.append(
            SemanticSpan(
                id=f"span_{segment.id}",
                segment_id=segment.id,
                start_char=0,
                end_char=len(segment.text),
                text=segment.text,
                label=SpanLabel.UNKNOWN,
                confidence=0.0,  # No confidence - stub
                source=f"{PASS_NAME}:stub",
            )
        )

    ctx.spans = spans
    ctx.add_trace(
        pass_name=PASS_NAME,
        action="tagged_spans_stub",
        after=f"{len(spans)} spans (all UNKNOWN - stub implementation)",
    )
    ctx.add_diagnostic(
        level="warning",
        code="STUB_IMPLEMENTATION",
        message="Span tagging using stub. No NLP model loaded.",
        source=PASS_NAME,
    )

    return ctx
