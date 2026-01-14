"""
Pass 10 — Lexical & Syntactic Segmentation

Segments normalized text into sentences using spaCy.
"""

from typing import Optional
from uuid import uuid4

from nnrt.core.context import TransformContext
from nnrt.ir.schema_v0_1 import Segment

PASS_NAME = "p10_segment"

# Lazy-loaded spaCy model
_nlp: Optional["spacy.language.Language"] = None


def _get_nlp() -> "spacy.language.Language":
    """Get or load the spaCy model."""
    global _nlp
    if _nlp is None:
        try:
            import spacy
            _nlp = spacy.load("en_core_web_sm", disable=["ner", "lemmatizer"])
        except OSError:
            raise RuntimeError(
                "spaCy model 'en_core_web_sm' not found. "
                "Install with: python -m spacy download en_core_web_sm"
            )
    return _nlp


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

    # Process with spaCy
    nlp = _get_nlp()
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
