"""
Pass 34 — Event Extraction

Extracts events (actions, interactions) by analyzing verbs and linking them
to the high-fidelity entities extracted in Pass 32.
"""

from typing import Optional, List, Dict
from uuid import uuid4

import spacy

from nnrt.core.context import TransformContext
from nnrt.ir.enums import EventType, EntityRole
from nnrt.ir.schema_v0_1 import Event, Entity

PASS_NAME = "p34_extract_events"

_nlp = None

def _get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp

# -----------------------------------------------------------------------------
# Event Taxonomy Mappings
# -----------------------------------------------------------------------------

# Verbs mapping to EventTypes
VERB_TYPES = {
    # Physical
    "grab": EventType.ACTION,
    "hit": EventType.ACTION,
    "punch": EventType.ACTION,
    "push": EventType.ACTION,
    "shove": EventType.ACTION,
    "strike": EventType.ACTION,
    "kick": EventType.ACTION,
    "tackle": EventType.ACTION,
    "restrain": EventType.ACTION,
    "cuff": EventType.ACTION,
    "handcuff": EventType.ACTION,
    
    # Movement
    "walk": EventType.MOVEMENT,
    "run": EventType.MOVEMENT,
    "drive": EventType.MOVEMENT,
    "approach": EventType.MOVEMENT,
    "leave": EventType.MOVEMENT,
    "arrive": EventType.MOVEMENT,
    "enter": EventType.MOVEMENT,
    "exit": EventType.MOVEMENT,
    
    # Verbal
    "say": EventType.VERBAL,
    "yell": EventType.VERBAL,
    "scream": EventType.VERBAL,
    "shout": EventType.VERBAL,
    "tell": EventType.VERBAL,
    "ask": EventType.VERBAL,
    "command": EventType.VERBAL,
    "order": EventType.VERBAL,
}

# -----------------------------------------------------------------------------
# Pass Implementation
# -----------------------------------------------------------------------------

def extract_events(ctx: TransformContext) -> TransformContext:
    nlp = _get_nlp()
    events: List[Event] = []
    
    # Build Entity Lookup (Text -> Entity)
    # This is a heuristic lookup. p32 should ideally pass this map, 
    # but rebuilding it from mentions is okay for now.
    text_to_entity: Dict[str, Entity] = {}
    
    # Optimizing lookup: map identifying tokens to entities
    for ent in ctx.entities:
        for mention in ent.mentions:
            text_to_entity[mention.lower()] = ent
            
        # Also map label parts? "Officer Smith" -> "Smith"
        if ent.label:
            text_to_entity[ent.label.lower()] = ent
            for part in ent.label.split():
                 if len(part) > 2: # Skip initials
                     text_to_entity[part.lower()] = ent

    # Process Segments
    for segment in ctx.segments:
        doc = nlp(segment.text)
        
        for token in doc:
            if token.pos_ == "VERB":
                lemma = token.lemma_.lower()
                
                # Determine Event Type
                event_type = VERB_TYPES.get(lemma)
                if not event_type:
                    # Generic fallback
                    event_type = EventType.ACTION
                
                # Find Actor (Subject)
                actor_id = None
                nsubj = next((c for c in token.children if c.dep_ in ("nsubj", "nsubjpass")), None)
                if nsubj:
                    actor_ent = _resolve_entity(nsubj.text, text_to_entity)
                    if actor_ent:
                        actor_id = actor_ent.id
                
                # Find Target (Object)
                target_id = None
                dobj = next((c for c in token.children if c.dep_ in ("dobj", "pobj")), None)
                if dobj:
                    target_ent = _resolve_entity(dobj.text, text_to_entity)
                    if target_ent:
                        target_id = target_ent.id
                
                # Only create event if we have at least an Actor or specific verb type
                if actor_id or lemma in VERB_TYPES:
                    # Construct description (verb + obj)
                    desc = token.text
                    if dobj:
                        desc += f" {dobj.text}"
                    
                    event = Event(
                        id=f"evt_{uuid4().hex[:8]}",
                        type=event_type,
                        description=desc,
                        source_spans=[], # TODO: Link to span ID
                        confidence=0.8,
                        actor_id=actor_id,
                        target_id=target_id,
                        is_uncertain=False # Could check modifiers
                    )
                    events.append(event)

    ctx.events = events
    
    ctx.add_trace(
        pass_name=PASS_NAME,
        action="extracted_events",
        after=f"{len(events)} events extracted",
    )
    
    return ctx

def _resolve_entity(text: str, lookup: Dict[str, Entity]) -> Optional[Entity]:
    """Resolve text to an entity using the lookup map."""
    text_lower = text.lower()
    return lookup.get(text_lower)
