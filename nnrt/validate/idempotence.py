"""
Idempotence Validator — Checks transformation is stable.
"""

from nnrt.core.context import TransformContext
from nnrt.core.contracts import Validator


class IdempotenceValidator(Validator):
    """
    Validates that transformation is idempotent.
    
    Running the same input twice should produce equivalent output.
    This validator checks structural equivalence, not exact match.
    """

    @property
    def name(self) -> str:
        return "idempotence"

    def validate(self, ctx: TransformContext) -> list[str]:
        """
        Check idempotence (placeholder).
        
        Full implementation would run transformation twice
        and compare IR structures.
        """
        # Stub: cannot validate without re-running
        return []
