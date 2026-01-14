"""
Pass 10 — Lexical & Syntactic Segmentation

Segments normalized text into chunks (typically sentences).
"""

import re
from uuid import uuid4

from nnrt.core.context import TransformContext
from nnrt.ir.schema_v0_1 import Segment

PASS_NAME = "p10_segment"

# Simple sentence boundary pattern (will be replaced by NLP in production)
SENTENCE_PATTERN = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')


def segment(ctx: TransformContext) -> TransformContext:
    """
    Segment normalized text into sentences.
    
    This is a stub implementation using regex.
    Production will use NLP-based segmentation.
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

    # Split into sentences (naive implementation)
    sentence_texts = SENTENCE_PATTERN.split(text)
    if not sentence_texts:
        sentence_texts = [text]

    # Build segments with character offsets
    segments: list[Segment] = []
    current_pos = 0

    for i, sentence_text in enumerate(sentence_texts):
        sentence_text = sentence_text.strip()
        if not sentence_text:
            continue

        # Find actual position in text
        start = text.find(sentence_text, current_pos)
        if start == -1:
            start = current_pos
        end = start + len(sentence_text)

        segments.append(
            Segment(
                id=f"seg_{i:03d}",
                text=sentence_text,
                start_char=start,
                end_char=end,
                source_line=None,  # Not tracking line numbers yet
            )
        )
        current_pos = end

    ctx.segments = segments
    ctx.add_trace(
        pass_name=PASS_NAME,
        action="segmented_text",
        after=f"{len(segments)} segments",
    )

    return ctx
