"""
Pass 27b — Statement Attribution & Aberration

V4 Alpha: Transforms dangerous epistemic content into safe attributed forms
or aberrates (quarantines) content that cannot be safely attributed.

The Two Paths:
1. REPHRASE: Extract claim, generate attributed form
   "This was racial profiling" → "reporter characterizes the stop as racial profiling"

2. ABERRATE: Quarantine content that cannot be safely attributed
   "psychotic thug cops" → is_aberrated=True, no text exposed

Decision Logic:
1. Check for INVECTIVE (thug, maniac, psychotic) → ABERRATE
2. Check for CONSPIRACY (cover-up, they always protect) → ABERRATE 
3. Check if claim is extractable → REPHRASE
4. Otherwise → ABERRATE (cannot safely transform)
"""

import re
from typing import Optional, Tuple
from nnrt.core.context import TransformContext
from nnrt.core.logging import get_pass_logger

PASS_NAME = "p27b_attribute"
log = get_pass_logger(PASS_NAME)


# =============================================================================
# ABERRATION PATTERNS (Cannot be safely attributed)
# =============================================================================

# Invective: Pure insults with no factual claim
INVECTIVE_PATTERNS = [
    (r'\bthug\s+cop', "invective: 'thug cop'"),
    (r'\bpsychotic\b', "invective: 'psychotic'"),
    (r'\bmaniac\b', "invective: 'maniac'"),
    (r'\bbrutally\b', "invective: 'brutally'"),
    (r'\bviciously\b', "invective: 'viciously'"),
    (r'\bsavagely\b', "invective: 'savagely'"),
    (r'\bmonster\b', "invective: 'monster'"),
    (r'\bcorrupt\s+cop', "invective: 'corrupt cop'"),
    (r'\bdirty\s+cop', "invective: 'dirty cop'"),
    (r'\bpig[s]?\b', "invective: 'pig'"),
    (r'\bfascist\b', "invective: 'fascist'"),
    (r'\bsadist\b', "invective: 'sadist'"),
    (r'\bsadistic\b', "invective: 'sadistic'"),
]

# Unfalsifiable conspiracy claims
UNFALSIFIABLE_PATTERNS = [
    (r'\bthey\s+always\s+protect\s+their\s+own\b', "unfalsifiable: systemic conspiracy claim"),
    (r'\bmassive\s+cover[-\s]?up\b', "unfalsifiable: conspiracy claim"),
    (r'\bmysteriously\s+(?:lost|disappeared|deleted|missing)\b', "unfalsifiable: implies conspiracy"),
    (r'\bthey\s+(?:are|were)\s+all\s+in\s+on\s+it\b', "unfalsifiable: conspiracy claim"),
    (r'\bblue\s+wall\s+of\s+silence\b', "unfalsifiable: systemic allegation"),
    (r'\bcode\s+of\s+silence\b', "unfalsifiable: systemic allegation"),
    (r'\bwhitewash\b', "unfalsifiable: implies cover-up"),
    (r'\bproves?\s+(?:there\'?s?\s+)?(?:a\s+)?(?:conspiracy|cover[-\s]?up)\b', "unfalsifiable: proof claim"),
]

# Combination patterns (invective + claim = too toxic to attribute)
TOXIC_COMBINATION_PATTERNS = [
    (r'\b(?:brutal|vicious|savage)\s+(?:attack|assault|beating)\b', "toxic: invective + action"),
    (r'\bfor\s+(?:absolutely\s+)?no\s+reason\b', "toxic: unfalsifiable motivation claim"),
]


# =============================================================================
# LEGAL CHARACTERIZATION EXTRACTION
# =============================================================================

# Legal terms that can be extracted and attributed
LEGAL_TERM_EXTRACTIONS = [
    # (pattern, legal_term, attribution_template)
    (r'\bracial\s+profiling\b', "racial profiling", 
     "reporter characterizes the stop as racial profiling"),
    (r'\bexcessive\s+force\b', "excessive force",
     "reporter characterizes the use of force as excessive"),
    (r'\bpolice\s+brutality\b', "police brutality",
     "reporter characterizes the conduct as police brutality"),
    (r'\bfalse\s+arrest\b', "false arrest",
     "reporter characterizes the arrest as false"),
    (r'\bunlawful\s+(?:detention|stop|search)\b', "unlawful detention/stop/search",
     "reporter characterizes the action as unlawful"),
    (r'\bobstruction\s+of\s+justice\b', "obstruction of justice",
     "reporter alleges obstruction of justice"),
    (r'\bwitness\s+intimidation\b', "witness intimidation",
     "reporter alleges witness intimidation"),
    (r'\b(?:civil|constitutional)\s+rights?\s+violation\b', "rights violation",
     "reporter alleges a violation of rights"),
    (r'\billegal(?:ly)?\s+(?:detained|searched|arrested|stopped)\b', "illegal action",
     "reporter characterizes the action as illegal"),
    (r'\bharassment\b', "harassment",
     "reporter characterizes the conduct as harassment"),
]


# =============================================================================
# INTERPRETATION EXTRACTION
# =============================================================================

# Intent/interpretation patterns that can be attributed
INTERPRETATION_EXTRACTIONS = [
    # (pattern, extraction_key, attribution_template)
    (r'\b(?:obviously|clearly)\s+(?:wanted|intended|trying)\s+to\s+(\w+)', "intent",
     "reporter believes the officer intended to {action}"),
    (r'\b(?:obviously|clearly)\s+didn\'?t\s+care\s+about\b', "disregard",
     "reporter believes the officer disregarded the reporter's rights"),
    (r'\bready\s+to\s+(?:shoot|attack|assault)\b', "threat perception",
     "reporter perceived a threat of violence"),
    (r'\blooking\s+for\s+trouble\b', "hostile intent",
     "reporter perceived hostile intent"),
    (r'\benjoying\s+(?:my|the)\s+(?:pain|suffering|fear)\b', "sadism perception",
     "reporter perceived the officer as enjoying the situation"),
    (r'\bdeliberately\s+(?:trying|ignoring|hurting)\b', "deliberate action",
     "reporter believes the action was deliberate"),
    (r'\bwanted\s+to\s+(?:inflict|hurt|harm|punish)\b', "harmful intent",
     "reporter believes there was intent to cause harm"),
    # V4: Additional patterns
    (r'\bdesigned\s+to\s+(?:protect|cover|hide|intimidate)\b', "systemic intent",
     "reporter alleges systemic intent"),
    (r'\bit\s+was\s+(?:obvious|clear)\s+that\b', "inference",
     "reporter draws an inference from events"),
    (r'\bmocking\b', "perceived mockery",
     "reporter perceived mockery"),
]


# =============================================================================
# CORE LOGIC
# =============================================================================

def _check_aberration(text: str) -> Tuple[bool, Optional[str]]:
    """
    Check if statement must be aberrated (quarantined).
    
    Returns (is_aberrated, reason) tuple.
    """
    text_lower = text.lower()
    
    # Check invective patterns
    for pattern, reason in INVECTIVE_PATTERNS:
        if re.search(pattern, text_lower):
            return (True, reason)
    
    # Check unfalsifiable patterns
    for pattern, reason in UNFALSIFIABLE_PATTERNS:
        if re.search(pattern, text_lower):
            return (True, reason)
    
    # Check toxic combinations
    for pattern, reason in TOXIC_COMBINATION_PATTERNS:
        if re.search(pattern, text_lower):
            return (True, reason)
    
    return (False, None)


def _extract_legal_claim(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract legal characterization and generate attributed form.
    
    Returns (extracted_claim, attributed_text) tuple.
    """
    text_lower = text.lower()
    
    for pattern, legal_term, template in LEGAL_TERM_EXTRACTIONS:
        if re.search(pattern, text_lower):
            return (legal_term, template)
    
    return (None, None)


def _extract_interpretation(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract interpretation and generate attributed form.
    
    Returns (extracted_claim, attributed_text) tuple.
    """
    text_lower = text.lower()
    
    for pattern, claim_type, template in INTERPRETATION_EXTRACTIONS:
        match = re.search(pattern, text_lower)
        if match:
            # Try to extract action if template has placeholder
            if '{action}' in template and match.groups():
                action = match.group(1)
                attributed = template.format(action=action)
            else:
                attributed = template
            return (claim_type, attributed)
    
    return (None, None)


def attribute_statements(ctx: TransformContext) -> TransformContext:
    """
    Transform dangerous epistemic content into attributed forms or aberrate.
    
    This pass runs after p27_epistemic_tag and processes statements that were
    flagged as interpretation, legal_claim, or conspiracy_claim.
    
    For each flagged statement:
    1. Check if it must be aberrated (invective, conspiracy)
    2. If not, extract the claim and generate attributed form
    3. If extraction fails, aberrate as "cannot safely transform"
    """
    if not ctx.atomic_statements:
        log.warning("no_statements", message="No statements to process")
        return ctx
    
    aberrated_count = 0
    attributed_count = 0
    skipped_count = 0
    
    for stmt in ctx.atomic_statements:
        # Only process dangerous epistemic types
        if stmt.epistemic_type not in (
            "interpretation", "legal_claim", "conspiracy_claim", 
            "intent_attribution", "legal_characterization"
        ):
            skipped_count += 1
            continue
        
        # Step 1: Check for aberration
        is_aberrated, reason = _check_aberration(stmt.text)
        
        if is_aberrated:
            stmt.is_aberrated = True
            stmt.aberration_reason = reason
            aberrated_count += 1
            log.info("aberrated", 
                statement_id=stmt.id, 
                reason=reason,
                text_preview=stmt.text[:50])
            continue
        
        # Step 2: Try to extract and attribute
        extracted_claim = None
        attributed_text = None
        
        # Try legal claim extraction first
        if stmt.epistemic_type in ("legal_claim", "legal_characterization"):
            extracted_claim, attributed_text = _extract_legal_claim(stmt.text)
        
        # Then try interpretation extraction
        if not attributed_text and stmt.epistemic_type in ("interpretation", "intent_attribution"):
            extracted_claim, attributed_text = _extract_interpretation(stmt.text)
        
        # Fallback: generic attribution if no specific template matched
        if not attributed_text:
            # Generate generic attribution based on type
            if stmt.epistemic_type in ("legal_claim", "legal_characterization"):
                attributed_text = f"reporter makes a legal characterization regarding this incident"
                extracted_claim = "unspecified legal claim"
            elif stmt.epistemic_type in ("interpretation", "intent_attribution"):
                attributed_text = f"reporter expresses an interpretation of events"
                extracted_claim = "unspecified interpretation"
            else:
                # Conspiracy without invective - still aberrate
                stmt.is_aberrated = True
                stmt.aberration_reason = "conspiracy claim: cannot safely attribute"
                aberrated_count += 1
                continue
        
        # Store attribution
        stmt.attributed_text = attributed_text
        stmt.extracted_claim = extracted_claim
        attributed_count += 1
        
        log.debug("attributed",
            statement_id=stmt.id,
            epistemic_type=stmt.epistemic_type,
            extracted_claim=extracted_claim,
            attributed_text=attributed_text[:50] if attributed_text else None)
    
    log.info("attribution_complete",
        total=len(ctx.atomic_statements),
        aberrated=aberrated_count,
        attributed=attributed_count,
        skipped=skipped_count)
    
    ctx.add_trace(
        pass_name=PASS_NAME,
        action="attributed_statements",
        after=f"Aberrated: {aberrated_count}, Attributed: {attributed_count}, Skipped: {skipped_count}",
    )
    
    return ctx
