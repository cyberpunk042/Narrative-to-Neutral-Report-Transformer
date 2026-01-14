"""
Pass 10 — Lexical & Syntactic Segmentation

Segments normalized text into sentences using spaCy.
"""

from uuid import uuid4

from nnrt.core.context import TransformContext
from nnrt.ir.schema_v0_1 import Segment
from nnrt.nlp.spacy_loader import get_nlp

PASS_NAME = "p10_segment"


def segment(ctx: TransformContext) -> TransformContext:
    """
    Segment normalized text into sentences using spaCy.
    
    This pass:
    - Uses spaCy's sentence segmentation
    - Creates Segment objects with character offsets
    - Preserves source positions for traceability
    """
    text = ctx.normalized_text
    if not text:
        ctx.add_diagnostic(
            level="warning",
            code="EMPTY_INPUT",
            message="Normalized text is empty",
            source=PASS_NAME,
        )
        return ctx

    # Process with spaCy (centralized loader)
    nlp = get_nlp()
    doc = nlp(text)

    # Build segments from sentences
    segments: list[Segment] = []
    for i, sent in enumerate(doc.sents):
        segments.append(
            Segment(
                id=f"seg_{i:03d}",
                text=sent.text.strip(),
                start_char=sent.start_char,
                end_char=sent.end_char,
                source_line=None,  # Could compute from newlines if needed
            )
        )

    ctx.segments = segments
    ctx.add_trace(
        pass_name=PASS_NAME,
        action="segmented_text",
        after=f"{len(segments)} segments",
    )

    return ctx
