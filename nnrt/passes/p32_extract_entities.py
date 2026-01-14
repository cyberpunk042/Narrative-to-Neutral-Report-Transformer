"""
Pass 32 — Entity Extraction

Extracts and resolves entities (people, vehicles, objects) from the narrative.

This pass:
- Delegates NLP detection to EntityExtractor interface
- Handles pronoun resolution and ambiguity detection
- Links to identifiers from p30
- Stores span IDs (not text) in Entity.mentions per IR schema contract
- Does NOT directly access spaCy (that's the backend's job)
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import Optional, Dict, List
from uuid import uuid4

from nnrt.core.context import TransformContext
from nnrt.ir.enums import EntityRole, EntityType, IdentifierType, UncertaintyType
from nnrt.ir.schema_v0_1 import Entity, UncertaintyMarker, SemanticSpan
from nnrt.nlp.interfaces import EntityExtractor, EntityExtractResult
from nnrt.nlp.backends.spacy_backend import get_entity_extractor

PASS_NAME = "p32_extract_entities"

# Default extractor (can be swapped for testing)
_extractor: Optional[EntityExtractor] = None


def get_extractor() -> EntityExtractor:
    """Get the entity extractor instance."""
    global _extractor
    if _extractor is None:
        _extractor = get_entity_extractor()
    return _extractor


def set_extractor(extractor: EntityExtractor) -> None:
    """Set a custom extractor (for testing)."""
    global _extractor
    _extractor = extractor


def reset_extractor() -> None:
    """Reset to default extractor."""
    global _extractor
    _extractor = None


# -----------------------------------------------------------------------------
# Constants for Pass-Level Logic
# -----------------------------------------------------------------------------

# These are used for RESOLUTION logic, not NLP detection
# NLP detection patterns are in the backend
AUTHORITY_TITLES = {
    "officer", "deputy", "sergeant", "detective",
    "lieutenant", "chief", "sheriff", "trooper"
}


@dataclass
class MentionLocation:
    """Temporary storage for mention location before span ID resolution."""
    segment_id: str
    start_char: int
    end_char: int
    text: str


# -----------------------------------------------------------------------------
# Pass Implementation
# -----------------------------------------------------------------------------


def extract_entities(ctx: TransformContext) -> TransformContext:
    """
    Extract entities using the EntityExtractor interface.
    
    This pass:
    1. Uses EntityExtractor to get raw extraction results
    2. Handles pronoun resolution and ambiguity detection
    3. Links to identifiers from p30
    4. Creates Entity IR objects with proper span IDs
    """
    extractor = get_extractor()
    
    # Initialize canonical entities
    entities: List[Entity] = []
    pending_mentions: Dict[str, List[MentionLocation]] = defaultdict(list)
    
    # Always exists: Reporter
    reporter = Entity(
        id=f"ent_{uuid4().hex[:8]}",
        type=EntityType.PERSON,
        role=EntityRole.REPORTER,
        label="Reporter",
        mentions=[]
    )
    entities.append(reporter)
    
    # Seed from Identifiers (p30)
    identifier_entities = _seed_from_identifiers(ctx.identifiers, entities)
    
    # Track recently mentioned entities for resolution
    recent_entities: List[Entity] = []
    
    # Process each segment using the interface
    for segment in ctx.segments:
        # Use the interface - not direct spaCy
        extraction_results = extractor.extract(segment.text)
        
        # Process each extraction result
        for result in extraction_results:
            entity = _process_extraction_result(
                result=result,
                segment_id=segment.id,
                reporter=reporter,
                entities=entities,
                recent_entities=recent_entities,
                pending_mentions=pending_mentions,
                ctx=ctx,
            )
            
            if entity and entity not in recent_entities:
                recent_entities.append(entity)
                if len(recent_entities) > 5:
                    recent_entities.pop(0)
    
    # Resolve mention locations to span IDs
    _resolve_mentions_to_spans(entities, pending_mentions, ctx.spans)
    
    ctx.entities = entities
    
    ctx.add_trace(
        pass_name=PASS_NAME,
        action="extracted_entities",
        after=f"{len(entities)} entities extracted (via {extractor.name})",
    )
    
    return ctx


def _seed_from_identifiers(
    identifiers: list,
    entities: List[Entity]
) -> Dict[str, Entity]:
    """Create entities from identifiers extracted in p30."""
    identifier_map: Dict[str, Entity] = {}
    
    for ident in identifiers:
        if ident.type in (IdentifierType.NAME, IdentifierType.BADGE_NUMBER, IdentifierType.EMPLOYEE_ID):
            is_authority = (
                ident.type != IdentifierType.NAME or
                any(t in ident.value.lower() for t in AUTHORITY_TITLES)
            )
            role = EntityRole.AUTHORITY if is_authority else EntityRole.WITNESS
            
            # Check for existing entity with same label
            existing = next((e for e in entities if e.label == ident.value), None)
            
            if existing:
                ent = existing
            else:
                ent = Entity(
                    id=f"ent_{uuid4().hex[:8]}",
                    type=EntityType.PERSON,
                    role=role,
                    label=ident.value,
                    mentions=[]
                )
                entities.append(ent)
            
            identifier_map[ident.id] = ent
    
    return identifier_map


def _process_extraction_result(
    result: EntityExtractResult,
    segment_id: str,
    reporter: Entity,
    entities: List[Entity],
    recent_entities: List[Entity],
    pending_mentions: Dict[str, List[MentionLocation]],
    ctx: TransformContext,
) -> Optional[Entity]:
    """
    Process a single extraction result from the backend.
    
    Handles:
    - Reporter linking
    - Pronoun resolution with ambiguity detection
    - Entity creation or matching
    """
    match_entity = None
    
    # Check if this is a Reporter mention
    if result.role == EntityRole.REPORTER:
        match_entity = reporter
    
    # Check if this needs resolution (pronoun or unidentified)
    elif result.label == "Individual (Unidentified)" and result.confidence < 0.7:
        # This is a resolvable pronoun - try to resolve
        candidates = [
            e for e in reversed(recent_entities)
            if e != reporter and e.type == EntityType.PERSON
        ]
        
        if candidates:
            # Check for ambiguity
            if len(candidates) > 1:
                lbls = [c.label or "Unknown" for c in candidates[:3]]
                mention_text = result.mentions[0][2] if result.mentions else "pronoun"
                
                marker = UncertaintyMarker(
                    id=f"unc_{uuid4().hex[:8]}",
                    type=UncertaintyType.AMBIGUOUS_REFERENCE,
                    text=mention_text,
                    description=f"Ambiguous pronoun '{mention_text}' could refer to: {', '.join(lbls)}",
                    affected_ids=[segment_id],
                    source=PASS_NAME,
                )
                ctx.uncertainty.append(marker)
            
            match_entity = candidates[0]
        else:
            # No candidates - create new unidentified entity
            match_entity = Entity(
                id=f"ent_{uuid4().hex[:8]}",
                type=result.type,
                role=EntityRole.SUBJECT,
                label="Individual (Unidentified)",
                mentions=[]
            )
            entities.append(match_entity)
    
    # Check for authority titles that might link to existing
    elif result.role == EntityRole.AUTHORITY:
        # Look for existing authority to link to
        candidates = [
            e for e in reversed(recent_entities)
            if e.role == EntityRole.AUTHORITY
        ]
        
        if candidates:
            match_entity = candidates[0]
        else:
            # Create new authority entity
            match_entity = Entity(
                id=f"ent_{uuid4().hex[:8]}",
                type=result.type,
                role=result.role,
                label=result.label,
                mentions=[]
            )
            entities.append(match_entity)
    
    # Check for existing entity with same label
    elif result.label:
        for ent in entities:
            if ent.label and ent.label.lower() == result.label.lower():
                match_entity = ent
                break
        
        if not match_entity and result.is_new:
            # Create new entity
            match_entity = Entity(
                id=f"ent_{uuid4().hex[:8]}",
                type=result.type,
                role=result.role,
                label=result.label,
                mentions=[]
            )
            entities.append(match_entity)
    
    # Record mention locations
    if match_entity and result.mentions:
        for start, end, text in result.mentions:
            pending_mentions[match_entity.id].append(MentionLocation(
                segment_id=segment_id,
                start_char=start,
                end_char=end,
                text=text
            ))
    
    return match_entity


def _resolve_mentions_to_spans(
    entities: List[Entity],
    pending_mentions: Dict[str, List[MentionLocation]],
    spans: List[SemanticSpan]
) -> None:
    """
    Resolve pending mention locations to span IDs.
    
    For each mention, find the span that contains or overlaps with it.
    Store the span ID (not text) in Entity.mentions.
    """
    # Build span index by segment for efficient lookup
    spans_by_segment: Dict[str, List[SemanticSpan]] = defaultdict(list)
    for span in spans:
        spans_by_segment[span.segment_id].append(span)
    
    for entity in entities:
        resolved_span_ids = []
        
        for mention in pending_mentions.get(entity.id, []):
            # Find span that contains this mention
            matching_span = _find_overlapping_span(
                mention.segment_id,
                mention.start_char,
                mention.end_char,
                spans_by_segment
            )
            
            if matching_span:
                # Avoid duplicates
                if matching_span.id not in resolved_span_ids:
                    resolved_span_ids.append(matching_span.id)
            else:
                # No matching span found - store as text fallback with marker
                fallback = f"text:{mention.text}"
                if fallback not in resolved_span_ids:
                    resolved_span_ids.append(fallback)
        
        entity.mentions = resolved_span_ids


def _find_overlapping_span(
    segment_id: str,
    start_char: int,
    end_char: int,
    spans_by_segment: Dict[str, List[SemanticSpan]]
) -> Optional[SemanticSpan]:
    """Find a span that overlaps with the given character range."""
    for span in spans_by_segment.get(segment_id, []):
        # Check if ranges overlap
        if span.start_char <= start_char and end_char <= span.end_char:
            return span
        elif start_char <= span.start_char and span.end_char <= end_char:
            return span
        elif span.start_char <= start_char < span.end_char:
            return span
        elif span.start_char < end_char <= span.end_char:
            return span
    
    return None


