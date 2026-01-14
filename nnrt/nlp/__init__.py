"""NLP — Semantic sensor layer."""

from nnrt.nlp.interfaces import EntityExtractor, EventExtractor, SpanTagger
from nnrt.nlp.spacy_loader import get_nlp, reset_nlp

__all__ = [
    # Interfaces
    "SpanTagger",
    "EntityExtractor",
    "EventExtractor",
    # Loader
    "get_nlp",
    "reset_nlp",
]

