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
from nnrt.core.logging import get_pass_logger
from nnrt.ir.enums import EntityRole, EntityType, IdentifierType, UncertaintyType
from nnrt.ir.schema_v0_1 import Entity, UncertaintyMarker, SemanticSpan
from nnrt.nlp.interfaces import EntityExtractor, EntityExtractResult
from nnrt.nlp.backends.spacy_backend import get_entity_extractor

PASS_NAME = "p32_extract_entities"
log = get_pass_logger(PASS_NAME)

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

# =============================================================================
# V4: Entity Validation - Reject Invalid Extractions
# =============================================================================

# Bare titles - these are NOT entities, they're descriptors
# "Officer", "Detective" without a name should be rejected
BARE_TITLES = {
    "officer", "deputy", "sergeant", "detective", "lieutenant",
    "chief", "sheriff", "trooper", "captain", "commander",
    "dr", "dr.", "doctor", "nurse", "emt", "paramedic",
    "attorney", "lawyer", "counselor",
    "mr", "mr.", "mrs", "mrs.", "ms", "ms.", "miss",
}

# Bare roles - relationships, not named individuals
BARE_ROLES = {
    "partner", "passenger", "driver", "suspect", "victim",
    "witness", "bystander", "pedestrian", "manager", "supervisor",
    "coworker", "colleague", "employer", "employee",
    "neighbor", "friend", "family", "relative",
    "person", "individual", "someone", "man", "woman", "guy", "lady",
}

# Descriptors - characteristics, not named entities
BARE_DESCRIPTORS = {
    "male", "female", "white", "black", "hispanic", "asian",
    "tall", "short", "young", "old", "elderly",
}

# Medical role patterns - to classify as MEDICAL_PROVIDER
MEDICAL_ROLE_PATTERNS = {"dr", "dr.", "doctor", "nurse", "emt", "paramedic", "therapist", "psychiatrist", "physician"}

# Legal role patterns - to classify as LEGAL_COUNSEL
LEGAL_ROLE_PATTERNS = {"attorney", "lawyer", "counselor", "counsel", "defender"}

# Investigator patterns - to classify as INVESTIGATOR
INVESTIGATOR_PATTERNS = {"detective", "investigator", "inspector"}

# Supervisor patterns - to classify as SUPERVISOR
SUPERVISOR_PATTERNS = {"sergeant", "lieutenant", "captain", "commander", "chief"}


def _is_valid_entity(label: str) -> tuple[bool, str]:
    """
    V4: Check if an extracted entity is valid.
    
    Returns (is_valid, entity_type) where entity_type is:
    - "named"       : Properly named entity (Officer Jenkins)
    - "contextual"  : Valid contextual reference (his partner, the manager)
    - "invalid"     : Should be rejected (bare title, badge number as name)
    
    Key insight: "partner", "manager" etc. ARE valid entity references
    when they refer to distinct people. They just don't have names.
    The problem is only when JUST a title ("Officer") is extracted alone.
    """
    if not label:
        return (False, "invalid")
    
    label_lower = label.lower().strip()
    words = label_lower.split()
    
    # ==========================================================================
    # REJECT: Pure numbers (badge numbers being extracted as person names)
    # ==========================================================================
    if label.isdigit() or label_lower.replace(" ", "").isdigit():
        return (False, "invalid")  # "4821" is not a person name
    
    # ==========================================================================
    # REJECT: Single-word bare titles without any name
    # ==========================================================================
    if len(words) == 1 and label_lower in BARE_TITLES:
        return (False, "invalid")  # "Officer" alone is not an entity
    
    # ==========================================================================
    # REJECT: Single-word descriptors that aren't people
    # ==========================================================================
    if len(words) == 1 and label_lower in BARE_DESCRIPTORS:
        return (False, "invalid")  # "male" is not an entity
    
    # ==========================================================================
    # ACCEPT as CONTEXTUAL: Role-based references (track as unidentified)
    # ==========================================================================
    # "partner", "manager", "driver" - these ARE references to real people
    # They just don't have names. Track them for coreference/ambiguity.
    if len(words) == 1 and label_lower in BARE_ROLES:
        return (True, "contextual")
    
    # "the partner", "his manager" - valid contextual references
    if len(words) == 2 and words[0] in {"the", "a", "an", "his", "her", "their", "my"}:
        if words[1] in BARE_ROLES or words[1] in BARE_TITLES:
            return (True, "contextual")
    
    # ==========================================================================
    # ACCEPT as NAMED: Everything else (proper names, titled names)
    # ==========================================================================
    return (True, "named")



def _classify_role(label: str, current_role: EntityRole) -> EntityRole:
    """
    V4: Classify entity role based on title/context in the label.
    
    Upgrades generic AUTHORITY/WITNESS to specific roles where possible.
    """
    label_lower = label.lower()
    first_word = label_lower.split()[0] if label_lower.split() else ""
    
    # Medical providers
    if first_word in MEDICAL_ROLE_PATTERNS or "dr." in label_lower or "doctor" in label_lower:
        return EntityRole.MEDICAL_PROVIDER
    
    # Legal counsel
    if any(p in label_lower for p in LEGAL_ROLE_PATTERNS):
        return EntityRole.LEGAL_COUNSEL
    
    # Investigators (IA, detectives doing investigations)
    if first_word in INVESTIGATOR_PATTERNS or "internal affairs" in label_lower:
        return EntityRole.INVESTIGATOR
    
    # Supervisors
    if first_word in SUPERVISOR_PATTERNS:
        return EntityRole.SUPERVISOR
    
    # Subject officers (default for "Officer X" patterns)
    if first_word == "officer" or first_word == "deputy":
        return EntityRole.SUBJECT_OFFICER
    
    # Keep current role if no upgrade found
    return current_role


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
    
    # Count by role
    role_counts = {}
    for ent in entities:
        role_counts[ent.role.value] = role_counts.get(ent.role.value, 0) + 1
    
    log.info("extracted",
        total_entities=len(entities),
        backend=extractor.name,
        **role_counts,
    )
    
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
    """
    Create entities from identifiers extracted in p30.
    
    V4: Badge numbers should NOT become standalone entities.
    They should be attached to the officers they identify.
    """
    identifier_map: Dict[str, Entity] = {}
    
    for ident in identifiers:
        # V4: Only create entities from NAMES, not badge numbers
        # Badge numbers should be attached to officers, not become entities
        if ident.type == IdentifierType.NAME:
            # Check if this looks like a proper name (not just a number)
            is_valid, category = _is_valid_entity(ident.value)
            if not is_valid:
                log.debug(
                    "skipping_invalid_identifier_entity",
                    pass_name=PASS_NAME,
                    value=ident.value,
                    reason="failed_validation",
                )
                continue
            
            is_authority = any(t in ident.value.lower() for t in AUTHORITY_TITLES)
            role = EntityRole.AUTHORITY if is_authority else EntityRole.WITNESS
            
            # Apply V4 role classification
            role = _classify_role(ident.value, role)
            
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
        
        # V4: Badge numbers are identifiers, not entities
        # They will be linked to officers during entity extraction
        elif ident.type in (IdentifierType.BADGE_NUMBER, IdentifierType.EMPLOYEE_ID):
            log.debug(
                "badge_number_skipped",
                pass_name=PASS_NAME,
                value=ident.value,
                note="Badge numbers attach to officers, not standalone entities",
            )
    
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
    - V4: Validation to reject bare titles/roles/descriptors
    - V4: Role classification for proper taxonomy
    - Reporter linking
    - Pronoun resolution with ambiguity detection
    - Entity creation or matching
    """
    match_entity = None
    
    # ==========================================================================
    # V4: Validate entity before processing
    # ==========================================================================
    is_valid = True
    entity_category = "named"
    
    if result.label:
        is_valid, entity_category = _is_valid_entity(result.label)
        
        if not is_valid:
            log.debug(
                "rejected_invalid_entity",
                pass_name=PASS_NAME,
                label=result.label,
                reason="bare_title_number_or_descriptor",
            )
            return None  # Skip this extraction
        
        # V4: Contextual references (partner, manager) become unidentified entities
        if entity_category == "contextual":
            log.debug(
                "contextual_entity",
                pass_name=PASS_NAME,
                original_label=result.label,
                will_mark_as="Individual (Unidentified)",
            )
    
    # ==========================================================================
    # V4: Classify role using new taxonomy
    # ==========================================================================
    classified_role = result.role
    if result.label and result.role in {EntityRole.AUTHORITY, EntityRole.WITNESS}:
        classified_role = _classify_role(result.label, result.role)
    
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
    elif result.role == EntityRole.AUTHORITY or classified_role in {
        EntityRole.SUBJECT_OFFICER, EntityRole.SUPERVISOR, 
        EntityRole.INVESTIGATOR, EntityRole.MEDICAL_PROVIDER,
        EntityRole.LEGAL_COUNSEL
    }:
        # Look for existing entity with same label first (deduplication)
        if result.label:
            for ent in entities:
                if ent.label and ent.label.lower() == result.label.lower():
                    match_entity = ent
                    # V4: Upgrade role if we have better classification
                    if classified_role != EntityRole.AUTHORITY and ent.role == EntityRole.AUTHORITY:
                        ent.role = classified_role
                    break
        
        if not match_entity:
            # Create new entity with classified role
            match_entity = Entity(
                id=f"ent_{uuid4().hex[:8]}",
                type=result.type,
                role=classified_role,
                label=result.label,
                mentions=[]
            )
            entities.append(match_entity)
    
    # Check for existing entity with same label (general case)
    elif result.label:
        for ent in entities:
            if ent.label and ent.label.lower() == result.label.lower():
                match_entity = ent
                break
        
        if not match_entity and result.is_new:
            # Create new entity with classified role
            match_entity = Entity(
                id=f"ent_{uuid4().hex[:8]}",
                type=result.type,
                role=classified_role,
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


