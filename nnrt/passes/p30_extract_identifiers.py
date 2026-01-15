"""
Pass 30 — Identifier Extraction

Extracts identifiers (badge numbers, locations, times, etc.)
from segments using regex patterns and NER.

Identifiers are critical for legal documentation and must
be preserved exactly as stated in the original narrative.
"""

import re
from uuid import uuid4

from nnrt.core.context import TransformContext
from nnrt.core.logging import get_pass_logger
from nnrt.ir.enums import IdentifierType
from nnrt.ir.schema_v0_1 import Identifier
from nnrt.nlp.spacy_loader import get_nlp

PASS_NAME = "p30_extract_identifiers"
log = get_pass_logger(PASS_NAME)

# Regex patterns for common identifiers
IDENTIFIER_PATTERNS = {
    IdentifierType.BADGE_NUMBER: [
        r'\b[Bb]adge\s*#?\s*(\d{3,8})\b',
        r'\b[Bb]adge\s+(?:number|no\.?)\s*:?\s*(\d{3,8})\b',
        r'\b[Oo]fficer\s+#?\s*(\d{3,8})\b',
        r'\b[Uu]nit\s*#?\s*(\d{2,6})\b',
    ],
    IdentifierType.EMPLOYEE_ID: [
        r'\b[Ee]mployee\s*(?:ID|#)\s*:?\s*(\w{4,12})\b',
        r'\b[Ii][Dd]\s*#?\s*:?\s*(\d{4,10})\b',
    ],
    IdentifierType.VEHICLE_PLATE: [
        r'\b(?:license\s+)?plate\s*:?\s*([A-Z0-9]{5,8})\b',
        r'\b([A-Z]{2,3}[-\s]?\d{3,4}[-\s]?[A-Z]{0,3})\b',
    ],
    IdentifierType.TIME: [
        # Full time with minutes required: "11:30 PM"
        r'\b(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?)\b',
        # Hour only with AM/PM: "11 PM" but not just digits
        r'\b(\d{1,2}\s+(?:AM|PM|am|pm))\b',
        # "around 11:30 PM" - capture the time part only
        r'\b(?:around|approximately|about)\s+(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))\b',
    ],
    IdentifierType.DATE: [
        r'\b(\d{1,2}/\d{1,2}/\d{2,4})\b',
        r'\b(\d{1,2}-\d{1,2}-\d{2,4})\b',
        r'\b((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?)\b',
        r'\b(\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:January|February|March|April|May|June|July|August|September|October|November|December)(?:,?\s+\d{4})?)\b',
    ],
    IdentifierType.LOCATION: [
        # Street addresses MUST have a street suffix to match
        # "near Main Street", "at Oak Avenue" - requires Street/Ave/etc.
        r'\b(?:at|on|near)\s+(?:the\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s+(?:Street|St\.?|Avenue|Ave\.?|Boulevard|Blvd\.?|Road|Rd\.?|Drive|Dr\.?|Lane|Ln\.?|Highway|Hwy\.?))\b',
        
        # "corner of Main and Oak" - intersection without suffix
        r'\b(?:corner\s+of|intersection\s+of)\s+([A-Z][a-z]+(?:\s+(?:Street|St\.?))?\s+(?:and|&)\s+[A-Z][a-z]+(?:\s+(?:Avenue|Ave\.?))?)\b',
        
        # Numbered addresses: "123 Main Street"
        r'\b(\d+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s+(?:Street|St\.?|Avenue|Ave\.?|Boulevard|Blvd\.?|Road|Rd\.?|Drive|Dr\.?|Lane|Ln\.?))\b',
    ],
}

# =============================================================================
# V4: Identifier Validation
# =============================================================================

# Invalid time patterns - these are parsing artifacts, not real times
INVALID_TIME_PATTERNS = [
    r'^\d{1,2}\s*(PM|AM|pm|am)$',  # "30 PM" - minute without hour
    r'^:\d{2}',                    # ":30" - orphaned minutes
]

# Duration patterns - should be classified differently if we add DURATION type
DURATION_PATTERNS = [
    r'(?:about|around|approximately)?\s*\d+\s*(?:minutes?|hours?|mins?|hrs?)',
]

# Vague temporal - low confidence markers
VAGUE_TEMPORAL_PATTERNS = [
    r'^(?:night|morning|afternoon|evening|later|earlier)$',
    r'^(?:hours?|days?|weeks?|months?)$',  # Just "hours" is vague
]

# Not temporal - age patterns that look like decades
NOT_TEMPORAL_PATTERNS = [
    r'^\d{2}s$',          # "40s" as age
    r'^(?:in )?(?:his|her|their) \d{2}s$',  # "in his 40s"
]


def _is_valid_time(value: str) -> tuple[bool, float]:
    """
    V4: Validate a time identifier.
    
    Returns (is_valid, confidence).
    Rejects parsing artifacts like "30 PM".
    """
    value = value.strip()
    
    # Check for invalid patterns
    for pattern in INVALID_TIME_PATTERNS:
        if re.match(pattern, value, re.IGNORECASE):
            return (False, 0.0)
    
    # Proper times: "11:30 PM", "3:45 am", "11 PM"
    if re.match(r'^\d{1,2}:\d{2}\s*(AM|PM|am|pm)?$', value):
        return (True, 0.95)  # High confidence
    
    if re.match(r'^\d{1,2}\s+(AM|PM|am|pm)$', value):
        return (True, 0.9)  # Hour only, still valid
    
    # If no AM/PM and no colon, it's low confidence
    if not re.search(r'(AM|PM|am|pm|:|hour)', value):
        return (True, 0.5)  # Low confidence
    
    return (True, 0.8)


def _is_valid_date(value: str) -> tuple[bool, float]:
    """
    V4: Validate a date identifier.
    
    Returns (is_valid, confidence).
    Rejects non-date patterns like "40s" (age).
    """
    value = value.strip()
    
    # Check for non-temporal patterns
    for pattern in NOT_TEMPORAL_PATTERNS:
        if re.match(pattern, value, re.IGNORECASE):
            return (False, 0.0)
    
    # Check for vague temporal
    for pattern in VAGUE_TEMPORAL_PATTERNS:
        if re.match(pattern, value, re.IGNORECASE):
            return (True, 0.3)  # Valid but very low confidence
    
    return (True, 0.9)


def _deduplicate_identifiers(identifiers: list[Identifier]) -> list[Identifier]:
    """
    V4: Remove duplicate identifiers.
    
    Keeps the first occurrence of each (type, value) pair.
    """
    seen = set()
    result = []
    
    for ident in identifiers:
        key = (ident.type, ident.value.lower().strip())
        if key not in seen:
            seen.add(key)
            result.append(ident)
    
    return result

def extract_identifiers(ctx: TransformContext) -> TransformContext:
    """
    Extract identifiers from segments.
    
    This pass:
    - Uses regex patterns for structured identifiers
    - Uses spaCy NER for names and locations
    - Creates Identifier objects with exact source text
    - Links identifiers to source segments
    """
    if not ctx.segments:
        ctx.add_diagnostic(
            level="warning",
            code="NO_SEGMENTS",
            message="No segments to extract from",
            source=PASS_NAME,
        )
        return ctx

    identifiers: list[Identifier] = []
    id_counter = 0

    for segment in ctx.segments:
        # Extract via regex patterns
        regex_ids = _extract_regex_identifiers(segment.text, segment.id)
        identifiers.extend(regex_ids)
        id_counter += len(regex_ids)
        
        # Extract via NER
        ner_ids = _extract_ner_identifiers(segment.text, segment.id)
        
        # Deduplicate against regex matches
        for ner_id in ner_ids:
            # Check if this overlaps with a regex match
            overlaps = any(
                _ranges_overlap(
                    (ner_id.start_char, ner_id.end_char),
                    (rid.start_char, rid.end_char)
                )
                for rid in regex_ids
            )
            if not overlaps:
                identifiers.append(ner_id)
                id_counter += 1

    # V4: Deduplicate identifiers (removes duplicate time/date/etc. values)
    before_count = len(identifiers)
    identifiers = _deduplicate_identifiers(identifiers)
    if len(identifiers) < before_count:
        log.debug(
            "deduplicated_identifiers",
            before=before_count,
            after=len(identifiers),
            removed=before_count - len(identifiers),
        )
    
    ctx.identifiers = identifiers
    
    # Count by type
    type_counts = {}
    for ident in identifiers:
        type_counts[ident.type.value] = type_counts.get(ident.type.value, 0) + 1
    
    log.info("extracted",
        total_identifiers=len(identifiers),
        **type_counts,
    )
    
    ctx.add_trace(
        pass_name=PASS_NAME,
        action="extracted_identifiers",
        after=f"{len(identifiers)} identifiers: {type_counts}",
    )

    return ctx


def _extract_regex_identifiers(text: str, segment_id: str) -> list[Identifier]:
    """
    Extract identifiers using regex patterns.
    
    V4: Applies validation to reject artifacts and adjust confidence.
    """
    results: list[Identifier] = []
    
    for id_type, patterns in IDENTIFIER_PATTERNS.items():
        for pattern in patterns:
            try:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    # Get the captured group or full match
                    value = match.group(1) if match.groups() else match.group()
                    confidence = 0.9  # Default confidence
                    
                    # V4: Validate time identifiers
                    if id_type == IdentifierType.TIME:
                        is_valid, conf = _is_valid_time(value)
                        if not is_valid:
                            log.debug(
                                "rejected_invalid_time",
                                value=value,
                                reason="parsing_artifact",
                            )
                            continue  # Skip invalid times
                        confidence = conf
                    
                    # V4: Validate date identifiers
                    elif id_type == IdentifierType.DATE:
                        is_valid, conf = _is_valid_date(value)
                        if not is_valid:
                            log.debug(
                                "rejected_invalid_date",
                                value=value,
                                reason="not_a_date",
                            )
                            continue  # Skip invalid dates
                        confidence = conf
                    
                    results.append(Identifier(
                        id=f"id_{len(results):03d}",
                        type=id_type,
                        value=value,
                        original_text=match.group(),
                        start_char=match.start(),
                        end_char=match.end(),
                        source_segment_id=segment_id,
                        confidence=confidence,
                    ))
            except re.error:
                continue  # Skip invalid patterns
    
    return results


def _extract_ner_identifiers(text: str, segment_id: str) -> list[Identifier]:
    """Extract identifiers using spaCy NER."""
    results: list[Identifier] = []
    
    nlp = get_nlp()
    doc = nlp(text)
    
    # Map spaCy entity types to our identifier types
    type_map = {
        "PERSON": IdentifierType.NAME,
        "GPE": IdentifierType.LOCATION,  # Geopolitical entity
        "LOC": IdentifierType.LOCATION,  # Non-GPE locations
        "FAC": IdentifierType.LOCATION,  # Facilities
        "TIME": IdentifierType.TIME,
        "DATE": IdentifierType.DATE,
    }
    
    # Stopwords - common false positives
    LOCATION_STOPLIST = {
        # Pronouns (spaCy sometimes mis-classifies)
        "me", "him", "her", "them", "us", "it",
        "my", "his", "her", "their", "our", "its",
        "myself", "himself", "herself", "themselves",
        "he", "she", "they", "we", "i", "you",
        # Common false positives
        "there", "here", "where", "somewhere", "anywhere",
        "scene", "place", "area", "spot",
    }
    
    DATE_STOPLIST = {
        # Age patterns are not dates
        "year-old", "years-old", "month-old", "months-old",
        # Ordinal indicators alone
        "1st", "2nd", "3rd", "4th", "5th",
    }
    
    # Patterns to reject
    AGE_PATTERN = re.compile(r'^\d{1,3}[-\s]?year[-\s]?old', re.IGNORECASE)
    MEDICAL_TERMS = {"ptsd", "adhd", "ocd", "gad", "mdd"}
    
    for ent in doc.ents:
        if ent.label_ not in type_map:
            continue
            
        ent_text_lower = ent.text.lower().strip()
        id_type = type_map[ent.label_]
        
        # Filter 1: Skip very short entities (likely noise)
        if len(ent.text.strip()) < 2:
            continue
            
        # Filter 2: Location stoplist
        if id_type == IdentifierType.LOCATION:
            if ent_text_lower in LOCATION_STOPLIST:
                continue
            # Check if it's just a pronoun based on POS
            if len(list(ent)) == 1 and list(ent)[0].pos_ in ("PRON", "DET"):
                continue
                
        # Filter 3: Date validation
        if id_type == IdentifierType.DATE:
            # Skip age patterns
            if AGE_PATTERN.match(ent_text_lower):
                continue
            # Skip medical abbreviations
            if ent_text_lower in MEDICAL_TERMS:
                continue
            # Skip if contains stoplist terms
            if any(stop in ent_text_lower for stop in DATE_STOPLIST):
                continue
            # V4: Skip decade patterns like "40s", "30s" (age ranges)
            if re.match(r'^\d{2}s$', ent_text_lower):
                log.debug(
                    "rejected_age_range_as_date",
                    value=ent.text,
                    reason="age_decade_pattern",
                )
                continue
            # V4: Apply date validation
            is_valid, conf = _is_valid_date(ent.text)
            if not is_valid:
                continue
        
        # V4: Apply time validation for NER-extracted times
        if id_type == IdentifierType.TIME:
            is_valid, conf = _is_valid_time(ent.text)
            if not is_valid:
                log.debug(
                    "rejected_invalid_ner_time",
                    value=ent.text,
                    reason="failed_validation",
                )
                continue
        results.append(Identifier(
            id=f"id_ner_{len(results):03d}",
            type=id_type,
            value=ent.text,
            original_text=ent.text,
            start_char=ent.start_char,
            end_char=ent.end_char,
            source_segment_id=segment_id,
            confidence=0.7,  # Lower confidence for NER
        ))
    
    return results


def _ranges_overlap(r1: tuple[int, int], r2: tuple[int, int]) -> bool:
    """Check if two character ranges overlap."""
    return not (r1[1] <= r2[0] or r2[1] <= r1[0])
