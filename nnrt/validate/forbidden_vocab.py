"""
Forbidden Vocabulary Validator — Checks for prohibited terms.
"""

from nnrt.core.context import TransformContext
from nnrt.core.contracts import Validator

# Terms that should not appear in neutral output
FORBIDDEN_TERMS = [
    # Legal conclusions
    "guilty",
    "innocent",
    "illegal",
    "unlawful",
    "criminal",
    # Intent attribution
    "intentionally",
    "deliberately",
    "maliciously",
    "on purpose",
    # Inflammatory
    "brutality",
    "abuse",
    "assault",
    "attack",
]


class ForbiddenVocabValidator(Validator):
    """Validates that output doesn't contain forbidden vocabulary."""

    @property
    def name(self) -> str:
        return "forbidden_vocab"

    def validate(self, ctx: TransformContext) -> list[str]:
        """Check rendered text for forbidden terms."""
        errors: list[str] = []

        if not ctx.rendered_text:
            return errors

        text_lower = ctx.rendered_text.lower()

        for term in FORBIDDEN_TERMS:
            if term in text_lower:
                errors.append(f"Forbidden term found: '{term}'")

        return errors
