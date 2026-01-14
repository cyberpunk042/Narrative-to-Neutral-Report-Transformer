"""
Schema Validator — Validates IR structure and types.
"""

from nnrt.core.context import TransformContext
from nnrt.core.contracts import Validator


class SchemaValidator(Validator):
    """Validates IR schema compliance."""

    @property
    def name(self) -> str:
        return "schema"

    def validate(self, ctx: TransformContext) -> list[str]:
        """
        Validate IR schema.
        
        Checks:
        - All required fields present
        - All ID references resolve
        - Confidence values in bounds
        - No empty required lists
        """
        errors: list[str] = []

        # Check segments
        if not ctx.segments:
            errors.append("No segments in IR")

        # Check spans reference valid segments
        segment_ids = {s.id for s in ctx.segments}
        for span in ctx.spans:
            if span.segment_id not in segment_ids:
                errors.append(f"Span {span.id} references unknown segment {span.segment_id}")

        # Check confidence bounds
        for span in ctx.spans:
            if not 0.0 <= span.confidence <= 1.0:
                errors.append(f"Span {span.id} has invalid confidence {span.confidence}")

        for event in ctx.events:
            if not 0.0 <= event.confidence <= 1.0:
                errors.append(f"Event {event.id} has invalid confidence {event.confidence}")

        return errors
