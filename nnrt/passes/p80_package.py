"""
Pass 80 — Packaging

Final packaging of IR, text, trace, and diagnostics.
Performs validation before output.
"""

from nnrt.core.context import TransformContext
from nnrt.ir.enums import TransformStatus

PASS_NAME = "p80_package"


def package(ctx: TransformContext) -> TransformContext:
    """
    Package the final output.
    
    This pass:
    - Validates the IR
    - Sets final status
    - Prepares output for return
    """
    # Basic validation
    errors: list[str] = []

    if not ctx.segments:
        errors.append("No segments produced")

    if ctx.rendered_text is None:
        errors.append("No rendered text produced")

    # Set status based on validation
    if errors:
        for error in errors:
            ctx.add_diagnostic(
                level="error",
                code="VALIDATION_FAILED",
                message=error,
                source=PASS_NAME,
            )
        if ctx.status == TransformStatus.SUCCESS:
            ctx.status = TransformStatus.PARTIAL

    ctx.add_trace(
        pass_name=PASS_NAME,
        action="packaged",
        after=f"status={ctx.status.value}, errors={len(errors)}",
    )

    return ctx
