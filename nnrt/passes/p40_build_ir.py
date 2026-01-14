"""
Pass 40 — IR Construction

Builds the core IR structures (entities, events, speech acts)
from segments and tagged spans.
"""

from nnrt.core.context import TransformContext

PASS_NAME = "p40_build_ir"


def build_ir(ctx: TransformContext) -> TransformContext:
    """
    Build IR structures from segments and spans.
    
    STUB IMPLEMENTATION.
    
    In production, this will:
    - Identify entities and their roles
    - Extract events with evidence links
    - Detect speech acts
    - Create uncertainty markers
    """
    # Stub: entities, events, speech_acts remain empty
    ctx.add_trace(
        pass_name=PASS_NAME,
        action="build_ir_stub",
        after="IR structures empty (stub implementation)",
    )
    ctx.add_diagnostic(
        level="warning",
        code="STUB_IMPLEMENTATION",
        message="IR construction using stub. No structures built.",
        source=PASS_NAME,
    )

    return ctx
