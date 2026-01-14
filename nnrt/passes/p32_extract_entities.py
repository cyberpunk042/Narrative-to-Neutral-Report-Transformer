"""
Pass 32 — Entity Extraction

Extracts and resolves entities (people, vehicles, objects) from the narrative.
Resolves pronouns and links mentions to canonical entities.
Stores span IDs (not text) in Entity.mentions per IR schema contract.
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple
from uuid import uuid4

from nnrt.core.context import TransformContext
from nnrt.ir.enums import EntityRole, EntityType, IdentifierType, UncertaintyType
from nnrt.ir.schema_v0_1 import Entity, UncertaintyMarker, SemanticSpan
from nnrt.nlp.spacy_loader import get_nlp

PASS_NAME = "p32_extract_entities"

# -----------------------------------------------------------------------------
# Constants & Patterns
# -----------------------------------------------------------------------------

REPORTER_PRONOUNS = {"i", "me", "my", "mine", "myself", "we", "us", "our", "ours"}

# Pronouns to resolve
RESOLVABLE_PRONOUNS = {
    "he", "him", "his", "himself",
    "she", "her", "hers", "herself",
    "they", "them", "their", "theirs", "themselves"
}

# Generic terms that usually map to new entities if not determining
GENERIC_SUBJECTS = {"subject", "suspect", "individual", "male", "female", "driver", "passenger", "partner", "manager", "employee"}
AUTHORITY_TITLES = {"officer", "deputy", "sergeant", "detective", "lieutenant", "chief", "sheriff", "trooper"}


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
    nlp = get_nlp()
    
    # 1. Initialize Canonical Entities
    entities: List[Entity] = []
    
    # Track mention locations for later span ID resolution
    # Maps entity_id -> list of MentionLocation
    pending_mentions: Dict[str, List[MentionLocation]] = defaultdict(list)
    
    # Always exist: Reporter
    reporter = Entity(
        id=f"ent_{uuid4().hex[:8]}",
        type=EntityType.PERSON,
        role=EntityRole.REPORTER,
        label="Reporter",
        mentions=[]
    )
    entities.append(reporter)
    
    # 2. Seed from Identifiers (p30)
    identifier_map: Dict[str, Entity] = {}
    
    for ident in ctx.identifiers:
        if ident.type in (IdentifierType.NAME, IdentifierType.BADGE_NUMBER, IdentifierType.EMPLOYEE_ID):
            is_authority = (
                ident.type != IdentifierType.NAME or 
                any(t in ident.value.lower() for t in AUTHORITY_TITLES)
            )
            role = EntityRole.AUTHORITY if is_authority else EntityRole.WITNESS
            
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

    # 3. Sequential Processing (for Resolution)
    recent_entities: List[Entity] = [] 
    
    for segment in ctx.segments:
        doc = nlp(segment.text)
        
        for token in doc:
            text_lower = token.text.lower()
            
            # Skip non-nominal
            if token.pos_ not in ("PRON", "PROPN", "NOUN"):
                continue
                
            match_entity = None
            
            # A. Check Reporter
            if text_lower in REPORTER_PRONOUNS:
                match_entity = reporter
            
            # B. Check Pronoun Resolution
            elif text_lower in RESOLVABLE_PRONOUNS:
                candidates = [e for e in reversed(recent_entities) if e != reporter and e.type == EntityType.PERSON]
                if candidates:
                    if len(candidates) > 1:
                        lbls = [c.label or "Unknown" for c in candidates[:3]]
                        marker = UncertaintyMarker(
                            id=f"unc_{uuid4().hex[:8]}",
                            type=UncertaintyType.AMBIGUOUS_REFERENCE,
                            text=token.text,
                            description=f"Ambiguous pronoun '{token.text}' could refer to: {', '.join(lbls)}",
                            affected_ids=[segment.id],
                            source=PASS_NAME,
                        )
                        ctx.uncertainty.append(marker)
                        
                    match_entity = candidates[0]
                else:
                    match_entity = Entity(
                        id=f"ent_{uuid4().hex[:8]}",
                        type=EntityType.PERSON,
                        role=EntityRole.SUBJECT,
                        label="Individual (Unidentified)",
                        mentions=[]
                    )
                    entities.append(match_entity)
            
            # C. Check Named Entities / Nouns
            elif token.pos_ in ("PROPN", "NOUN"):
                for ent in entities:
                    if ent.label and ent.label.lower() in text_lower:
                         match_entity = ent
                         break
                
                if not match_entity:
                    if text_lower in AUTHORITY_TITLES:
                         candidates = [e for e in reversed(recent_entities) if e.role == EntityRole.AUTHORITY]
                         if candidates:
                             match_entity = candidates[0]
                         else:
                             match_entity = Entity(
                                 id=f"ent_{uuid4().hex[:8]}",
                                 type=EntityType.PERSON,
                                 role=EntityRole.AUTHORITY,
                                 label=token.text,
                                 mentions=[]
                             )
                             entities.append(match_entity)
                    elif text_lower in GENERIC_SUBJECTS:
                        match_entity = Entity(
                            id=f"ent_{uuid4().hex[:8]}",
                            type=EntityType.PERSON,
                            role=EntityRole.SUBJECT,
                            label=token.text,
                            mentions=[]
                        )
                        entities.append(match_entity)

            # If we found or created an entity, record the mention location
            if match_entity:
                # Record mention location for later span ID resolution
                pending_mentions[match_entity.id].append(MentionLocation(
                    segment_id=segment.id,
                    start_char=token.idx,
                    end_char=token.idx + len(token.text),
                    text=token.text
                ))
                
                if match_entity not in recent_entities:
                    recent_entities.append(match_entity)
                if len(recent_entities) > 5:
                    recent_entities.pop(0)

    # 4. Resolve mention locations to span IDs
    _resolve_mentions_to_spans(entities, pending_mentions, ctx.spans)

    ctx.entities = entities
    
    ctx.add_trace(
        pass_name=PASS_NAME,
        action="extracted_entities",
        after=f"{len(entities)} entities extracted",
    )
    
    return ctx


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
                # This preserves behavior while indicating it's not a proper span ID
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
            # Mention is fully contained in span
            return span
        elif start_char <= span.start_char and span.end_char <= end_char:
            # Span is fully contained in mention
            return span
        elif span.start_char <= start_char < span.end_char:
            # Mention starts within span
            return span
        elif span.start_char < end_char <= span.end_char:
            # Mention ends within span
            return span
    
    return None

