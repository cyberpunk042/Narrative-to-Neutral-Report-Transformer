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

    # V9: Track previous segment for cross-sentence pronoun resolution
    previous_segment_text = None
    
    # Process each segment using the interface
    for segment in ctx.segments:
        # Use the interface - not direct spaCy
        extraction_results = extractor.extract(segment.text)
        
        # Convert extraction results to Event IR objects
        for result in extraction_results:
            event = _result_to_event(
                result, 
                text_to_entity, 
                segment.id,
                previous_segment_text=previous_segment_text,  # V9: Pass context
            )
            if event:
                events.append(event)
        
        # V9: Update previous segment for next iteration
        previous_segment_text = segment.text

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
    segment_id: str,
    previous_segment_text: str = None,  # V9: Previous segment for pronoun context
) -> Optional[Event]:
    """
    Convert an EventExtractResult to an Event IR object.
    
    V9: Enhanced with cross-sentence pronoun resolution using previous segment.
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
        V9: Improved pronoun resolution with gender-awareness and better context.
        
        Strategy:
        1. 'I'/'me' → Always Reporter
        2. 'she'/'her' → Look for female entities (Mrs., Woman, etc.)
        3. 'he'/'him' → Look for male entities (Officer, Mr., etc.)
        4. 'they'/'them' → Multiple officers or unresolved
        """
        if not source_sentence:
            return None
        
        pronoun_lower = pronoun.lower().strip()
        sentence_lower = source_sentence.lower()
        
        # =================================================================
        # RULE 1: First-person pronouns → Reporter
        # =================================================================
        if pronoun_lower in {'i', 'me', 'my', 'myself'}:
            for ent in entity_lookup.values():
                if ent.role == EntityRole.REPORTER:
                    return ent
            return None  # If no Reporter entity, leave unresolved
        
        # =================================================================
        # RULE 2: Find named entities mentioned in sentence
        # Only match FULL entity labels, not partial word matches
        # =================================================================
        mentioned_entities = []
        for key, ent in entity_lookup.items():
            # Skip pronouns and short words
            if key in PRONOUNS or len(key) < 3:
                continue
            # Skip if already in list
            if ent in mentioned_entities:
                continue
            # Match only full words (prevents "police officers" matching "Officer Rodriguez")
            import re
            if re.search(r'\b' + re.escape(key) + r'\b', sentence_lower):
                # Skip generic terms that shouldn't match to specific entities
                if key in {'officer', 'officers', 'police', 'cops', 'cop', 'sergeant'}:
                    continue
                mentioned_entities.append(ent)
        
        # =================================================================
        # RULE 3: Gender-based resolution for 'she'/'her'
        # V9: Also look in previous segment if not found in current
        # =================================================================
        if pronoun_lower in {'she', 'her', 'herself'}:
            # Look for female entities in current sentence
            for ent in mentioned_entities:
                label = ent.label.lower()
                # Female indicators
                if any(x in label for x in ['mrs', 'ms', 'miss', 'woman', 'lady']):
                    return ent
                # Female first names (common)
                FEMALE_NAMES = {'patricia', 'amanda', 'sarah', 'jennifer', 'maria', 'linda', 'susan'}
                if any(name in label for name in FEMALE_NAMES):
                    return ent
            
            # V9: If not found in current sentence, check previous segment
            if previous_segment_text:
                prev_lower = previous_segment_text.lower()
                for key, ent in entity_lookup.items():
                    if key in PRONOUNS or len(key) < 3:
                        continue
                    if key in {'officer', 'officers', 'police', 'cops', 'cop', 'sergeant'}:
                        continue
                    import re
                    if re.search(r'\b' + re.escape(key) + r'\b', prev_lower):
                        label = ent.label.lower()
                        # Check for female entity
                        if any(x in label for x in ['mrs', 'ms', 'miss', 'woman', 'lady']):
                            return ent
                        FEMALE_NAMES = {'patricia', 'amanda', 'sarah', 'jennifer', 'maria', 'linda', 'susan'}
                        if any(name in label for name in FEMALE_NAMES):
                            return ent
            
            # If no female entity found, leave unresolved
            return None
        
        # =================================================================
        # RULE 4: Gender-based resolution for 'he'/'him'
        # =================================================================
        if pronoun_lower in {'he', 'him', 'his', 'himself'}:
            # Look for male entities in sentence
            for ent in mentioned_entities:
                label = ent.label.lower()
                # Officer context
                if 'officer' in label or 'sergeant' in label:
                    return ent
                # Male indicators
                if any(x in label for x in ['mr', 'dr.']):
                    return ent
            # If only one entity mentioned, use it
            if len(mentioned_entities) == 1:
                return mentioned_entities[0]
            return None
        
        # =================================================================
        # RULE 5: 'they'/'them' - usually refers to police officers (multiple)
        # =================================================================
        if pronoun_lower in {'they', 'them', 'their', 'themselves'}:
            # In police context, "they" usually means officers
            if 'officer' in sentence_lower or 'police' in sentence_lower:
                # Could return first officer, but safer to leave unresolved
                return None
            # If only one entity mentioned, could refer to it
            if len(mentioned_entities) == 1:
                return mentioned_entities[0]
            return None
        
        # Default: unresolved
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


