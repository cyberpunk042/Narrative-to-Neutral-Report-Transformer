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
    
    # V4: Deduplicate entities - remove token fragments and duplicates
    entities = _deduplicate_entities(entities)
    
    # V4: Refine roles based on context in source text
    source_text = " ".join(seg.text for seg in ctx.segments)
    entities = _refine_entity_roles(entities, source_text)
    
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


def _normalize_entity_label(label: str) -> str:
    """
    V4: Normalize entity labels to fix common spaCy extraction issues.
    
    Fixes:
    - "Officers Jenkins" -> "Officer Jenkins" (plural to singular)
    - "Sergeants Williams" -> "Sergeant Williams"
    """
    if not label:
        return label
    
    # Plural title corrections
    plural_corrections = {
        "Officers ": "Officer ",
        "Sergeants ": "Sergeant ",
        "Deputies ": "Deputy ",
        "Detectives ": "Detective ",
        "Lieutenants ": "Lieutenant ",
    }
    
    for plural, singular in plural_corrections.items():
        if label.startswith(plural):
            corrected = singular + label[len(plural):]
            log.debug(
                "normalized_entity_label",
                original=label,
                corrected=corrected,
            )
            return corrected
    
    return label


def _deduplicate_entities(entities: List[Entity]) -> List[Entity]:
    """
    V4: Remove duplicate and fragment entities.
    
    This function:
    1. Normalizes labels (e.g., "Officers Jenkins" -> "Officer Jenkins")
    2. Removes single-token entities that are substrings of multi-token entities
       (e.g., removes "Sarah" and "Mitchell" when "Sarah Mitchell" exists)
    3. Removes exact label duplicates (keeps first occurrence)
    4. Keeps Reporter entity regardless
    """
    if not entities:
        return entities
    
    # V4: Normalize labels first
    for ent in entities:
        if ent.label:
            ent.label = _normalize_entity_label(ent.label)
    
    # Build set of multi-word labels (normalized)
    multi_word_labels = set()
    for ent in entities:
        if ent.label and len(ent.label.split()) > 1:
            multi_word_labels.add(ent.label.lower())
    
    # Check if a single word is a substring of any multi-word label
    def is_fragment(label: str) -> bool:
        if not label:
            return False
        label_lower = label.lower().strip()
        words = label_lower.split()
        if len(words) > 1:
            return False  # Multi-word labels are not fragments
        
        # Check if this single word appears in any multi-word label
        for multi in multi_word_labels:
            multi_words = multi.split()
            if label_lower in multi_words:
                return True
        return False
    
    # Track seen labels for exact duplicate removal
    seen_labels = set()
    result = []
    fragment_count = 0
    duplicate_count = 0
    
    for ent in entities:
        # Always keep Reporter
        if ent.role == EntityRole.REPORTER:
            result.append(ent)
            seen_labels.add(ent.label.lower() if ent.label else "reporter")
            continue
        
        # Check for fragment
        if is_fragment(ent.label):
            fragment_count += 1
            log.debug(
                "removed_fragment_entity",
                label=ent.label,
                reason="single_token_in_multiword_entity",
            )
            continue
        
        # Check for exact duplicate
        label_key = ent.label.lower() if ent.label else ""
        if label_key in seen_labels:
            duplicate_count += 1
            log.debug(
                "removed_duplicate_entity",
                label=ent.label,
            )
            continue
        
        seen_labels.add(label_key)
        result.append(ent)
    
    if fragment_count or duplicate_count:
        log.info(
            "v4_entity_dedup",
            fragments_removed=fragment_count,
            duplicates_removed=duplicate_count,
            before=len(entities),
            after=len(result),
        )
    
    return result


def _refine_entity_roles(entities: List[Entity], source_text: str) -> List[Entity]:
    """
    V4: Refine entity roles based on context in source text.
    
    Scans the source text for professional role indicators near entity names:
    - "Dr. Amanda Foster" → MEDICAL_PROVIDER
    - "attorney Jennifer Walsh" → LEGAL_COUNSEL
    - "my therapist, Michael Thompson" → MEDICAL_PROVIDER
    - "Detective Sarah Monroe" → INVESTIGATOR
    """
    source_lower = source_text.lower()
    
    # Role patterns to search for near entity names
    role_patterns = {
        EntityRole.MEDICAL_PROVIDER: [
            r"dr\.?\s+{name}",
            r"doctor\s+{name}",
            r"nurse\s+{name}",
            r"therapist[,\s]+(?:\w+\s+)?{name}",
            r"therapist[,\s]+{name}",
            r"physician\s+{name}",
            r"emt\s+{name}",
            r"paramedic\s+{name}",
            r"my\s+therapist[,\s]+{name}",
            r"treated\s+by\s+(?:dr\.?\s+)?{name}",
        ],
        EntityRole.LEGAL_COUNSEL: [
            r"attorney[,\s]+{name}",
            r"lawyer[,\s]+{name}",
            r"my\s+attorney[,\s]+{name}",
            r"counselor\s+{name}",
        ],
        EntityRole.INVESTIGATOR: [
            r"detective\s+{name}",
            r"internal\s+affairs[,\s]+{name}",
            r"investigator\s+{name}",
        ],
        EntityRole.SUPERVISOR: [
            r"sergeant\s+{name}",
            r"sgt\.?\s+{name}",
            r"lieutenant\s+{name}",
            r"captain\s+{name}",
        ],
        EntityRole.SUBJECT_OFFICER: [
            r"officer\s+{name}",
            r"deputy\s+{name}",
        ],
        # V5: Workplace contacts - mentioned for verification, not incident
        EntityRole.WORKPLACE_CONTACT: [
            r"my\s+manager\s+{name}",
            r"manager\s+{name}",
            r"my\s+boss\s+{name}",
            r"coworker\s+{name}",
            r"colleague\s+{name}",
            r"supervisor\s+{name}",  # Workplace supervisor, not police
            r"call\s+my\s+\w+\s+{name}\s+to\s+verify",
        ],
    }
    
    # Title prefixes that indicate roles (for labels that already have them)
    title_role_map = {
        "officer ": EntityRole.SUBJECT_OFFICER,
        "deputy ": EntityRole.SUBJECT_OFFICER,
        "sergeant ": EntityRole.SUPERVISOR,
        "sgt. ": EntityRole.SUPERVISOR,
        "detective ": EntityRole.INVESTIGATOR,
        "dr. ": EntityRole.MEDICAL_PROVIDER,
        "dr ": EntityRole.MEDICAL_PROVIDER,
    }
    
    refined_count = 0
    
    for ent in entities:
        if not ent.label:
            continue
        
        # Skip Reporter
        if ent.role == EntityRole.REPORTER:
            continue
        
        label_lower = ent.label.lower()
        
        # First check: Does the label itself start with a title?
        for title, role in title_role_map.items():
            if label_lower.startswith(title):
                if ent.role != role:
                    old_role = ent.role
                    ent.role = role
                    refined_count += 1
                    log.debug(
                        "refined_role_from_label",
                        label=ent.label,
                        old_role=old_role.value,
                        new_role=role.value,
                    )
                break
        else:
            # Second check: Search for role patterns in source text
            import re
            name_escaped = re.escape(label_lower)
            
            # Check each role pattern
            for role, patterns in role_patterns.items():
                if ent.role == role:
                    continue  # Already has this role
                
                found = False
                for pattern_template in patterns:
                    pattern = pattern_template.format(name=name_escaped)
                    if re.search(pattern, source_lower):
                        old_role = ent.role
                        ent.role = role
                        refined_count += 1
                        log.debug(
                            "refined_entity_role",
                            label=ent.label,
                            old_role=old_role.value,
                            new_role=role.value,
                            pattern=pattern_template,
                        )
                        found = True
                        break
                
                if found:
                    break

    
    if refined_count:
        log.info(
            "v4_role_refinement",
            entities_refined=refined_count,
        )
    
    return entities


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


