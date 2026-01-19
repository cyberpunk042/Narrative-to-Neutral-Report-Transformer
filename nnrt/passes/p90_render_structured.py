"""
p90_render_structured — Render structured report using SelectionResult

Stage 3: This pass renders the structured output using ctx.selection_result,
making use of the new simplified rendering path via structured_v2.

This pass should run LAST in the pipeline, after all analysis is complete.
"""

from typing import Any

from nnrt.core.context import TransformContext
from nnrt.core.logging import get_pass_logger

PASS_NAME = "p90_render_structured"
log = get_pass_logger(PASS_NAME)


def render_structured(ctx: TransformContext) -> TransformContext:
    """
    Render structured output using the appropriate path.
    
    If ctx.selection_result is populated (new path from p55_select):
        Uses structured_v2.format_structured_output_v2 which reads
        pre-computed fields from atoms (is_camera_friendly, etc.)
        
    Otherwise (legacy path):
        Falls back to structured.format_structured_output which
        computes classifications inline.
    
    Args:
        ctx: Transform context with selection_result populated by p55_select
        
    Returns:
        Context with rendered_text populated
    """
    if ctx.selection_result is not None:
        # NEW PATH: Use V2 renderer that reads pre-computed fields
        from nnrt.render.structured_v2 import format_structured_output_v2
        
        log.info("rendering_v2", message="Using structured_v2 with SelectionResult")
        
        rendered = format_structured_output_v2(
            selection_result=ctx.selection_result,
            entities=ctx.entities,
            events=ctx.events,
            identifiers=ctx.identifiers,
            timeline=ctx.timeline,
            time_gaps=ctx.time_gaps,
            atomic_statements=ctx.atomic_statements,
            segments=ctx.segments,  # V7 FIX: Pass segments for event_generator
            metadata=ctx,  # Pass context as metadata for speech_acts access
            rendered_text=ctx.rendered_text or '',
        )
        
        ctx.rendered_text = rendered
        
        log.info("rendered_v2", 
                 lines=len(rendered.split('\n')),
                 chars=len(rendered))
    else:
        # LEGACY PATH: Use V1 renderer (computes inline)
        from nnrt.render.structured import format_structured_output
        
        log.warning("rendering_v1_fallback", 
                    message="No SelectionResult - falling back to V1 renderer")
        
        metadata = ctx.request.metadata if ctx.request else {}
        
        rendered = format_structured_output(
            rendered_text=ctx.rendered_text or '',
            atomic_statements=ctx.atomic_statements,
            entities=ctx.entities,
            events=ctx.events,
            identifiers=ctx.identifiers,
            metadata=metadata,
            timeline=ctx.timeline,
            time_gaps=ctx.time_gaps,
            segments=ctx.segments,
        )
        
        ctx.rendered_text = rendered
        
        log.info("rendered_v1", 
                 lines=len(rendered.split('\n')),
                 chars=len(rendered))
    
    return ctx

