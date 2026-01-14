"""
Pass 30 — Identifier Extraction (Side-channel)

Extracts identifiers (names, badge numbers, etc.) from text.
These are extracted to optional metadata, NOT asserted.
"""

from nnrt.core.context import TransformContext

PASS_NAME = "p30_extract_identifiers"


def extract_identifiers(ctx: TransformContext) -> TransformContext:
    """
    Extract identifiers from text.
    
    STUB IMPLEMENTATION.
    
    In production, this will use pattern matching and NLP
    to extract identifiers into side-channel metadata.
    
    Per design: identifiers are extracted but never asserted.
    Consumers may discard this metadata entirely.
    """
    # Stub: no extraction
    ctx.add_trace(
        pass_name=PASS_NAME,
        action="extract_identifiers_stub",
        after="0 identifiers (stub implementation)",
    )
    ctx.add_diagnostic(
        level="info",
        code="STUB_IMPLEMENTATION",
        message="Identifier extraction using stub. No extraction performed.",
        source=PASS_NAME,
    )

    return ctx
