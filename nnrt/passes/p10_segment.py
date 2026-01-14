"""
Pass 10 — Lexical & Syntactic Segmentation

Segments normalized text into sentences using spaCy.
Includes quote-aware merging to keep quoted content together.
"""

import re
from uuid import uuid4

from nnrt.core.context import TransformContext
from nnrt.ir.schema_v0_1 import Segment
from nnrt.nlp.spacy_loader import get_nlp

PASS_NAME = "p10_segment"

# Regex to find quote boundaries
QUOTE_PATTERN = re.compile(r'"[^"]*"')


def segment(ctx: TransformContext) -> TransformContext:
    """
    Segment normalized text into sentences using spaCy.
    
    This pass:
    - Uses spaCy's sentence segmentation
    - Merges segments that are inside quotes (quote-aware)
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

    # Find all quoted regions first
    quote_ranges: list[tuple[int, int]] = []
    for match in QUOTE_PATTERN.finditer(text):
        quote_ranges.append((match.start(), match.end()))

    # Process with spaCy (centralized loader)
    nlp = get_nlp()
    doc = nlp(text)

    # Build initial segments from sentences
    raw_segments: list[tuple[str, int, int]] = []
    for sent in doc.sents:
        raw_segments.append((sent.text.strip(), sent.start_char, sent.end_char))

    # Merge segments that are inside the same quote
    merged_segments = _merge_quoted_segments(text, raw_segments, quote_ranges)

    # Build final Segment objects
    segments: list[Segment] = []
    for i, (seg_text, start, end) in enumerate(merged_segments):
        segments.append(
            Segment(
                id=f"seg_{i:03d}",
                text=seg_text,
                start_char=start,
                end_char=end,
                source_line=None,
            )
        )

    ctx.segments = segments
    ctx.add_trace(
        pass_name=PASS_NAME,
        action="segmented_text",
        after=f"{len(segments)} segments (quote-aware)",
    )

    return ctx


def _merge_quoted_segments(
    full_text: str,
    segments: list[tuple[str, int, int]],
    quote_ranges: list[tuple[int, int]],
) -> list[tuple[str, int, int]]:
    """
    Merge adjacent segments that overlap with the same quote.
    
    This ensures quoted content like:
        He said "First sentence. Second sentence."
    becomes a single segment, not split at the period.
    
    A segment overlaps a quote if any part of it is inside the quote.
    """
    if not segments or not quote_ranges:
        return segments

    result: list[tuple[str, int, int]] = []
    i = 0
    
    while i < len(segments):
        seg_text, seg_start, seg_end = segments[i]
        
        # Check if this segment OVERLAPS with any quote
        # (not just starts inside - a segment can start before quote but end inside it)
        overlapping_quote = None
        for q_start, q_end in quote_ranges:
            # Segment overlaps quote if:
            # - Segment ends after quote starts AND
            # - Segment starts before quote ends
            if seg_end > q_start and seg_start < q_end:
                overlapping_quote = (q_start, q_end)
                break
        
        if overlapping_quote is None:
            # No overlap with any quote - keep as-is
            result.append((seg_text, seg_start, seg_end))
            i += 1
            continue
        
        # This segment overlaps a quote - we need to merge with all segments
        # that are part of this quote until we fully exit
        q_start, q_end = overlapping_quote
        merged_start = seg_start
        merged_end = seg_end
        
        # Keep merging while next segment is also within or overlapping this quote
        while i + 1 < len(segments):
            next_text, next_start, next_end = segments[i + 1]
            
            # Check if next segment overlaps or is inside the same quote
            # Next segment is part of quote if it starts before quote ends
            if next_start < q_end:
                # Merge
                merged_end = next_end
                i += 1
            else:
                break
        
        # Extract the merged text from the original (to preserve spacing)
        merged_text = full_text[merged_start:merged_end].strip()
        result.append((merged_text, merged_start, merged_end))
        i += 1
    
    return result


