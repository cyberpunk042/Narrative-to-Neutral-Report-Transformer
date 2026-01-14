"""
Pass 34 — Event Extraction

Extracts events (actions, interactions) by using the EventExtractor interface
and linking results to the high-fidelity entities extracted in Pass 32.

This pass:
- Delegates NLP extraction to EventExtractor interface
- Links extracted events to entities from p32
- Assembles Event IR objects
- Does NOT directly access spaCy (that's the backend's job)
"""

from typing import Optional, List, Dict
from uuid import uuid4

from nnrt.core.context import TransformContext
from nnrt.ir.enums import EventType, EntityRole
from nnrt.ir.schema_v0_1 import Event, Entity
from nnrt.nlp.interfaces import EventExtractor, EventExtractResult
from nnrt.nlp.backends.spacy_backend import get_event_extractor

PASS_NAME = "p34_extract_events"

# Default extractor (can be swapped for testing)
_extractor: Optional[EventExtractor] = None


def get_extractor() -> EventExtractor:
    """Get the event extractor instance."""
    global _extractor
    if _extractor is None:
        _extractor = get_event_extractor()
    return _extractor


def set_extractor(extractor: EventExtractor) -> None:
    """Set a custom extractor (for testing)."""
    global _extractor
    _extractor = extractor


def reset_extractor() -> None:
    """Reset to default extractor."""
    global _extractor
    _extractor = None


# -----------------------------------------------------------------------------
# Pass Implementation
# -----------------------------------------------------------------------------

def extract_events(ctx: TransformContext) -> TransformContext:
    """
    Extract events using the EventExtractor interface.
    
    This pass:
    1. Uses EventExtractor to get raw extraction results
    2. Links actor/target mentions to entities from p32
    3. Creates Event IR objects
    """
    events: List[Event] = []
    extractor = get_extractor()
    
    # Build Entity Lookup for linking
    text_to_entity = _build_entity_lookup(ctx.entities)

    # Process each segment using the interface
    for segment in ctx.segments:
        # Use the interface - not direct spaCy
        extraction_results = extractor.extract(segment.text)
        
        # Convert extraction results to Event IR objects
        for result in extraction_results:
            event = _result_to_event(result, text_to_entity, segment.id)
            if event:
                events.append(event)

    ctx.events = events
    
    ctx.add_trace(
        pass_name=PASS_NAME,
        action="extracted_events",
        after=f"{len(events)} events extracted (via {extractor.name})",
    )
    
    return ctx


def _build_entity_lookup(entities: List[Entity]) -> Dict[str, Entity]:
    """Build a text -> entity lookup from existing entities."""
    lookup: Dict[str, Entity] = {}
    
    for ent in entities:
        # Map mentions to entity
        for mention in ent.mentions:
            # Handle both span IDs (span_XXX) and text fallbacks (text:XXX)
            if isinstance(mention, str):
                if mention.startswith("text:"):
                    text = mention[5:]  # Strip "text:" prefix
                    lookup[text.lower()] = ent
                elif not mention.startswith("span_"):
                    # Legacy plain text mentions
                    lookup[mention.lower()] = ent
        
        # Also map label parts for flexible matching
        if ent.label:
            lookup[ent.label.lower()] = ent
            for part in ent.label.split():
                if len(part) > 2:  # Skip initials
                    lookup[part.lower()] = ent
    
    return lookup


def _result_to_event(
    result: EventExtractResult,
    entity_lookup: Dict[str, Entity],
    segment_id: str
) -> Optional[Event]:
    """Convert an EventExtractResult to an Event IR object."""
    # Link actor mention to entity
    actor_id = None
    if result.actor_mention:
        actor_ent = entity_lookup.get(result.actor_mention.lower())
        if actor_ent:
            actor_id = actor_ent.id
    
    # Link target mention to entity
    target_id = None
    if result.target_mention:
        target_ent = entity_lookup.get(result.target_mention.lower())
        if target_ent:
            target_id = target_ent.id
    
    # Create Event IR object
    return Event(
        id=f"evt_{uuid4().hex[:8]}",
        type=result.type,
        description=result.description,
        source_spans=[],  # TODO: Link to span IDs from segment
        confidence=result.confidence,
        actor_id=actor_id,
        target_id=target_id,
        is_uncertain=False,
    )

