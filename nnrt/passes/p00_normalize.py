"""
Pass 00 — Input Normalization

Normalizes raw input text:
- Whitespace normalization
- Unicode normalization
- Basic cleanup
"""

import unicodedata

from nnrt.core.context import TransformContext

PASS_NAME = "p00_normalize"


def normalize(ctx: TransformContext) -> TransformContext:
    """
    Normalize raw input text.
    
    This pass:
    - Strips leading/trailing whitespace
    - Normalizes Unicode (NFC)
    - Collapses multiple whitespace to single space
    - Preserves paragraph breaks
    """
    raw = ctx.raw_text

    # Unicode normalization (NFC)
    text = unicodedata.normalize("NFC", raw)

    # Strip and collapse whitespace (preserve double newlines as paragraph breaks)
    lines = text.split("\n\n")
    normalized_lines = []
    for line in lines:
        # Collapse whitespace within paragraph
        words = line.split()
        normalized_lines.append(" ".join(words))

    text = "\n\n".join(normalized_lines)

    ctx.normalized_text = text
    ctx.add_trace(
        pass_name=PASS_NAME,
        action="normalized_input",
        before=f"{len(raw)} chars",
        after=f"{len(text)} chars",
    )

    return ctx
