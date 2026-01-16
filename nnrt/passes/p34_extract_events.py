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
from nnrt.core.logging import get_pass_logger
from nnrt.ir.enums import EventType, EntityRole
from nnrt.ir.schema_v0_1 import Event, Entity
from nnrt.nlp.interfaces import EventExtractor, EventExtractResult
from nnrt.nlp.backends.spacy_backend import get_event_extractor

PASS_NAME = "p34_extract_events"
log = get_pass_logger(PASS_NAME)

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
    
    # Count by type
    type_counts = {}
    for evt in events:
        type_counts[evt.type.value] = type_counts.get(evt.type.value, 0) + 1
    
    log.info("extracted",
        total_events=len(events),
        backend=extractor.name,
        **type_counts,
    )
    
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
    """
    Convert an EventExtractResult to an Event IR object.
    
    V5: Enhanced with pronoun resolution using source_sentence context.
    """
    # V5: Pronouns that need resolution
    PRONOUNS = {'he', 'she', 'they', 'it', 'him', 'her', 'them', 'i', 'we'}
    
    def find_entity(mention: str) -> Optional[Entity]:
        """Find entity from mention text."""
        if not mention:
            return None
        
        mention_lower = mention.lower().strip()
        
        # Try exact match
        ent = entity_lookup.get(mention_lower)
        if ent:
            return ent
        
        # Try stripping determiners (the, a, an)
        determiners = {"the ", "a ", "an ", "my ", "his ", "her ", "their "}
        for det in determiners:
            if mention_lower.startswith(det):
                stripped = mention_lower[len(det):]
                ent = entity_lookup.get(stripped)
                if ent:
                    return ent
        
        # Try each word in the mention
        for word in mention_lower.split():
            if len(word) > 2:  # Skip tiny words
                ent = entity_lookup.get(word)
                if ent:
                    return ent
        
        return None
    
    def resolve_pronoun(pronoun: str, source_sentence: str) -> Optional[Entity]:
        """
        V5: Resolve pronoun using context from source sentence.
        
        Strategy: Look for named entities mentioned in the same sentence.
        """
        if not source_sentence:
            return None
        
        sentence_lower = source_sentence.lower()
        
        # Find entities mentioned in the sentence
        mentioned_entities = []
        for key, ent in entity_lookup.items():
            if key in sentence_lower and not key in PRONOUNS:
                mentioned_entities.append(ent)
        
        # If exactly one entity found, resolve to it
        if len(mentioned_entities) == 1:
            return mentioned_entities[0]
        
        # If pronoun is 'I', look for reporter entity
        if pronoun.lower() == 'i':
            for ent in entity_lookup.values():
                if ent.role == EntityRole.REPORTER:
                    return ent
        
        # For 'he', prefer officers if sentence mentions police context
        if pronoun.lower() in {'he', 'him'}:
            if 'officer' in sentence_lower or 'jenkins' in sentence_lower or 'rodriguez' in sentence_lower:
                for ent in mentioned_entities:
                    if ent.role == EntityRole.SUBJECT_OFFICER:
                        return ent
        
        return None
    
    # Resolve actor
    actor_id = None
    actor_label = None  # V6: Don't default to raw mention - must be resolved
    
    if result.actor_mention:
        mention_lower = result.actor_mention.lower().strip()
        
        if mention_lower in PRONOUNS:
            # V6: CRITICAL - Pronoun MUST be resolved or actor_label stays None
            # This ensures events with unresolved pronouns fail the invariant
            resolved = resolve_pronoun(mention_lower, result.source_sentence)
            if resolved:
                actor_id = resolved.id
                actor_label = resolved.label
            else:
                # V6: Pronoun not resolved - leave actor_label as None
                # This will cause the event to fail EVENT_HAS_ACTOR invariant
                log.debug(
                    "unresolved_pronoun_actor",
                    pronoun=mention_lower,
                    source=result.source_sentence[:50] if result.source_sentence else None,
                )
        else:
            # Not a pronoun - try direct lookup
            actor_ent = find_entity(result.actor_mention)
            if actor_ent:
                actor_id = actor_ent.id
                actor_label = actor_ent.label
            else:
                # V6: Named mention but not in entity lookup - use raw mention
                # This is acceptable (e.g., "Officer Jenkins" not yet in entities)
                actor_label = result.actor_mention
    
    # Resolve target
    target_id = None
    target_label = None  # V6: Don't default to raw mention for pronouns
    target_object = None  # For non-entity targets like "the door"
    
    if result.target_mention:
        mention_lower = result.target_mention.lower().strip()
        
        if mention_lower in PRONOUNS:
            # V6: Target is pronoun - must resolve or leave as None
            resolved = resolve_pronoun(mention_lower, result.source_sentence)
            if resolved:
                target_id = resolved.id
                target_label = resolved.label
            # If not resolved, target_label stays None (pronoun dropped)
        else:
            # Not a pronoun - try entity lookup
            target_ent = find_entity(result.target_mention)
            if target_ent:
                target_id = target_ent.id
                target_label = target_ent.label
            else:
                # V6: Non-pronoun target not in entities - it's likely an object
                # e.g., "grabbed the door" -> target_object = "the door"
                target_object = result.target_mention
    
    # V5: Build formatted description with resolved actors
    # Format: [ACTOR] [ACTION] [TARGET]
    formatted_parts = []
    if actor_label:
        formatted_parts.append(actor_label)
    if result.action_verb:
        formatted_parts.append(result.action_verb)
    elif result.description:
        # Fall back to first verb-like word from description
        formatted_parts.append("[action]")
    if target_label:
        formatted_parts.append(target_label)
    elif target_object:
        formatted_parts.append(target_object)
    
    formatted_description = " ".join(formatted_parts) if formatted_parts else result.description
    
    # V6: Create Event IR object with properly resolved fields
    # actor_label is None if actor was unresolved pronoun -> fails invariant
    return Event(
        id=f"evt_{uuid4().hex[:8]}",
        type=result.type,
        description=result.description,  # Keep original verbatim
        source_spans=[segment_id],
        confidence=result.confidence,
        actor_id=actor_id,
        target_id=target_id,
        temporal_marker=None,
        # V6: Resolved labels for rendering
        actor_label=actor_label,  # None if unresolved pronoun
        action_verb=result.action_verb,
        target_label=target_label,  # None if unresolved pronoun
        target_object=target_object,  # Non-entity target (e.g., "the door")
        is_uncertain=False,
    )


