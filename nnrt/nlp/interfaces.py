"""
NLP Interfaces — Abstract interfaces for NLP backends.

NLP components are semantic sensors, not authorities.
All outputs are treated as untrusted input.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from nnrt.ir.enums import EntityRole, EntityType, EventType, SpanLabel


@dataclass
class SpanTagResult:
    """Result from span tagging."""

    start_char: int
    end_char: int
    text: str
    label: SpanLabel
    confidence: float


@dataclass
class EntityExtractResult:
    """Result from entity extraction."""

    label: str
    type: EntityType
    role: EntityRole
    confidence: float
    mentions: list[tuple[int, int, str]] = field(default_factory=list)  # (start, end, text)
    is_new: bool = True  # Whether this is a new entity or links to existing


@dataclass
class EventExtractResult:
    """
    Result from event extraction.
    
    V5: Enhanced with Actor/Action/Target schema fields.
    """
    # Core event description (verbatim from source)
    description: str
    type: EventType
    confidence: float
    source_start: int
    source_end: int
    
    # V5: Proper Actor/Action/Target schema
    actor_mention: Optional[str] = None      # Raw text mention (may be pronoun)
    action_verb: Optional[str] = None        # The verb/action itself
    target_mention: Optional[str] = None     # Raw text mention
    
    # V5: Source sentence for context-aware pronoun resolution
    source_sentence: Optional[str] = None


class SpanTagger(ABC):
    """
    Abstract interface for span tagging.
    
    Implementations must:
    - Return spans with confidence scores
    - Output structured data only
    - Never infer intent or meaning
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Backend name for tracing."""
        ...

    @abstractmethod
    def tag(self, text: str) -> list[SpanTagResult]:
        """
        Tag spans in text with semantic labels.
        
        Args:
            text: Input text to tag
            
        Returns:
            List of tagged spans with confidence
        """
        ...


class EntityExtractor(ABC):
    """
    Abstract interface for entity extraction.
    
    Implementations must:
    - Return entities with confidence scores
    - Track mentions with positions
    - Detect ambiguity without resolving it
    - Never infer identity beyond evidence
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Backend name for tracing."""
        ...

    @abstractmethod
    def extract(self, text: str, existing_entities: list = None) -> list[EntityExtractResult]:
        """
        Extract entities from text.
        
        Args:
            text: Original text
            existing_entities: Previously extracted entities (for resolution)
            
        Returns:
            List of extracted entities with confidence
        """
        ...


class EventExtractor(ABC):
    """
    Abstract interface for event extraction.
    
    Implementations must:
    - Return events with evidence links
    - Include confidence scores
    - Never resolve ambiguity
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Backend name for tracing."""
        ...

    @abstractmethod
    def extract(self, text: str, spans: list[SpanTagResult]) -> list[EventExtractResult]:
        """
        Extract events from text and spans.
        
        Args:
            text: Original text
            spans: Previously tagged spans
            
        Returns:
            List of extracted events with confidence
        """
        ...

