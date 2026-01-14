"""
Stub Backend — No-op implementation for testing.

Used to validate pipeline architecture without real NLP models.
"""

from nnrt.ir.enums import EntityRole, EntityType, EventType, SpanLabel
from nnrt.nlp.interfaces import (
    EntityExtractResult,
    EntityExtractor,
    EventExtractResult,
    EventExtractor,
    SpanTagResult,
    SpanTagger,
)


class StubSpanTagger(SpanTagger):
    """Stub span tagger that returns UNKNOWN for everything."""

    @property
    def name(self) -> str:
        return "stub"

    def tag(self, text: str) -> list[SpanTagResult]:
        """Return single UNKNOWN span covering entire text."""
        return [
            SpanTagResult(
                start_char=0,
                end_char=len(text),
                text=text,
                label=SpanLabel.UNKNOWN,
                confidence=0.0,
            )
        ]


class StubEntityExtractor(EntityExtractor):
    """Stub entity extractor that returns nothing."""

    @property
    def name(self) -> str:
        return "stub"

    def extract(self, text: str, existing_entities: list = None) -> list[EntityExtractResult]:
        """Return no entities."""
        return []


class StubEventExtractor(EventExtractor):
    """Stub event extractor that returns nothing."""

    @property
    def name(self) -> str:
        return "stub"

    def extract(self, text: str, spans: list[SpanTagResult] = None) -> list[EventExtractResult]:
        """Return no events."""
        return []

