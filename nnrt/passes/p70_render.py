"""
Pass 70 — Constrained Rendering

Renders the IR into neutral narrative text.
This is where a constrained generator (LLM) may be used.

The generator can ONLY render what the IR contains.
It cannot add meaning, resolve ambiguity, or infer intent.
"""

from nnrt.core.context import TransformContext

PASS_NAME = "p70_render"


def render(ctx: TransformContext) -> TransformContext:
    """
    Render IR to neutral text.
    
    STUB IMPLEMENTATION.
    
    In production, this may use:
    - Template-based rendering (deterministic)
    - Constrained LLM rendering (from IR only)
    
    Per LLM policy:
    - Generator input is IR, not raw text
    - Generator proposes, does not decide
    - Output must be reviewable/rejectable
    """
    # Stub: concatenate segment texts as-is
    if ctx.segments:
        ctx.rendered_text = " ".join(seg.text for seg in ctx.segments)
    else:
        ctx.rendered_text = ""

    ctx.add_trace(
        pass_name=PASS_NAME,
        action="render_stub",
        after=f"{len(ctx.rendered_text or '')} chars rendered (passthrough - stub)",
    )
    ctx.add_diagnostic(
        level="warning",
        code="STUB_IMPLEMENTATION",
        message="Rendering using stub. Output is passthrough, not neutralized.",
        source=PASS_NAME,
    )

    return ctx
