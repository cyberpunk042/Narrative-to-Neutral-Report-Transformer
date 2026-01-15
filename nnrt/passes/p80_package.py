"""
Pass 80 — Packaging

Final packaging of IR, text, trace, and diagnostics.
Performs validation before output.
"""

from nnrt.core.context import TransformContext
from nnrt.core.logging import get_pass_logger
from nnrt.ir.enums import TransformStatus

PASS_NAME = "p80_package"
log = get_pass_logger(PASS_NAME)


def package(ctx: TransformContext) -> TransformContext:
    """
    Package the final output.
    
    This pass:
    - Validates the IR
    - Sets final status
    - Prepares output for return
    """
    log.verbose("starting_packaging")
    
    # Basic validation
    errors: list[str] = []

    if not ctx.segments:
        errors.append("No segments produced")

    if ctx.rendered_text is None:
        errors.append("No rendered text produced")

    # Set status based on validation
    if errors:
        for error in errors:
            log.warning("validation_error", error=error)
            ctx.add_diagnostic(
                level="error",
                code="VALIDATION_FAILED",
                message=error,
                source=PASS_NAME,
            )
        if ctx.status == TransformStatus.SUCCESS:
            ctx.status = TransformStatus.PARTIAL

    log.info("packaged",
        status=ctx.status.value,
        segments=len(ctx.segments),
        spans=len(ctx.spans),
        entities=len(ctx.entities),
        events=len(ctx.events),
        identifiers=len(ctx.identifiers),
        diagnostics=len(ctx.diagnostics),
        validation_errors=len(errors),
    )

    ctx.add_trace(
        pass_name=PASS_NAME,
        action="packaged",
        after=f"status={ctx.status.value}, errors={len(errors)}",
    )

    return ctx

