"""
No New Facts Validator — Ensures transformation doesn't add facts.
"""

from nnrt.core.context import TransformContext
from nnrt.core.contracts import Validator


class NoNewFactsValidator(Validator):
    """
    Validates that output doesn't contain facts not in input.
    
    This is a heuristic check - not perfect but catches obvious violations.
    """

    @property
    def name(self) -> str:
        return "no_new_facts"

    def validate(self, ctx: TransformContext) -> list[str]:
        """
        Check that output doesn't introduce new content.
        
        Heuristic: output words should be derivable from input words.
        """
        errors: list[str] = []

        if not ctx.rendered_text or not ctx.raw_text:
            return errors

        # Simple word-based check (will need improvement)
        input_words = set(ctx.raw_text.lower().split())
        output_words = set(ctx.rendered_text.lower().split())

        # Common words that are OK to add (articles, prepositions)
        allowed_additions = {
            "the",
            "a",
            "an",
            "is",
            "was",
            "were",
            "are",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "shall",
            "can",
            "to",
            "of",
            "in",
            "for",
            "on",
            "with",
            "at",
            "by",
            "from",
            "as",
            "into",
            "through",
            "during",
            "before",
            "after",
            "above",
            "below",
            "between",
            "under",
            "and",
            "but",
            "or",
            "nor",
            "so",
            "yet",
            "that",
            "this",
            "these",
            "those",
            "it",
            "its",
        }

        new_words = output_words - input_words - allowed_additions

        if new_words:
            # Only error on significant additions
            significant_new = [w for w in new_words if len(w) > 3]
            if len(significant_new) > 5:
                errors.append(
                    f"Output may contain new content: {', '.join(list(significant_new)[:5])}..."
                )

        return errors
