"""NLP Backends — Concrete implementations of NLP interfaces."""

from nnrt.nlp.backends.spacy_backend import (
    SpacyEntityExtractor,
    SpacyEventExtractor,
    get_entity_extractor,
    get_event_extractor,
)
from nnrt.nlp.backends.stub import (
    StubEntityExtractor,
    StubEventExtractor,
    StubSpanTagger,
)

__all__ = [
    # SpaCy backends
    "SpacyEntityExtractor",
    "SpacyEventExtractor",
    "get_entity_extractor",
    "get_event_extractor",
    # Stub backends
    "StubSpanTagger",
    "StubEntityExtractor",
    "StubEventExtractor",
]

