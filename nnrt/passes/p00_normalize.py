"""
Pass 00 — Input Normalization

Normalizes raw input text:
- Whitespace normalization
- Unicode normalization
- Basic cleanup
"""

import unicodedata

from nnrt.core.context import TransformContext
from nnrt.core.logging import get_pass_logger

PASS_NAME = "p00_normalize"
log = get_pass_logger(PASS_NAME)


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
    raw_len = len(raw)
    
    log.verbose("starting_normalization", input_chars=raw_len)

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
    output_len = len(text)
    
    # Log results
    log.info(
        "normalized", 
        input_chars=raw_len, 
        output_chars=output_len,
        paragraphs=len(normalized_lines),
        chars_removed=raw_len - output_len,
    )

    ctx.normalized_text = text
    ctx.add_trace(
        pass_name=PASS_NAME,
        action="normalized_input",
        before=f"{raw_len} chars",
        after=f"{output_len} chars",
    )

    return ctx

