"""
p48_classify_evidence — Evidence type classification.

This pass classifies each atomic statement by its source/type of evidence,
computing reliability scores and detecting corroboration/contradiction.

Evidence Types:
- DIRECT_WITNESS: First-person sensory observation ("I saw", "I felt")
- REPORTED: Hearsay, told by someone else ("He said", "Marcus told me")
- DOCUMENTARY: Official records, reports ("The report states")
- PHYSICAL: Physical evidence ("bruises", "injuries", "damage")
- CIRCUMSTANTIAL: Inferred from context, no direct evidence

Algorithm:
1. CLASSIFY EACH STATEMENT
   - Check for first-person sensory markers → DIRECT_WITNESS
   - Check for reported speech patterns → REPORTED
   - Check for document references → DOCUMENTARY
   - Check for physical evidence markers → PHYSICAL
   - Default → CIRCUMSTANTIAL

2. IDENTIFY SOURCE ENTITIES
   - For REPORTED evidence, who said it?
   - Track source_entity_id for attribution

3. DETECT CORROBORATION
   - Find statements about similar events
   - Link statements that support each other

4. COMPUTE RELIABILITY
   - DOCUMENTARY highest
   - DIRECT_WITNESS high
   - PHYSICAL high
   - REPORTED medium
   - INFERENCE low
"""

import re
import structlog
from typing import Optional
from collections import defaultdict

from nnrt.core.context import TransformContext
from nnrt.ir.schema_v0_1 import EvidenceClassification, Entity
from nnrt.ir.enums import EvidenceType, EntityRole

log = structlog.get_logger("nnrt.p48_classify_evidence")

PASS_NAME = "p48_classify_evidence"

# ============================================================================
# Evidence Pattern Matching
# ============================================================================

# DIRECT_WITNESS: First-person observation
DIRECT_WITNESS_PATTERNS = [
    r'\bi\s+saw\b',
    r'\bi\s+watched\b',
    r'\bi\s+witnessed\b',
    r'\bi\s+observed\b',
    r'\bi\s+heard\b',
    r'\bi\s+felt\b',
    r'\bi\s+noticed\b',
    r'\bi\s+was\b',
    r'\bi\s+had\b',
    r'\bmy\s+',
    r'\bme\b',
    r'\bi\s+could\b',
    r'\bi\s+couldn\'t\b',
]

# REPORTED: Hearsay, told by someone
REPORTED_PATTERNS = [
    r'\b(\w+)\s+said\b',
    r'\b(\w+)\s+told\s+me\b',
    r'\b(\w+)\s+claimed\b',
    r'\b(\w+)\s+stated\b',
    r'\b(\w+)\s+reported\b',
    r'\baccording\s+to\b',
    r'\breportedly\b',
    r'\ballegedly\b',
    r'\bI\s+was\s+told\b',
    r'\bthey\s+said\b',
    r'\bhe\s+said\b',
    r'\bshe\s+said\b',
]

# DOCUMENTARY: Official records, documents
DOCUMENTARY_PATTERNS = [
    r'\breport\s+(?:states?|shows?|documents?|indicates?)\b',
    r'\brecords?\s+(?:show|indicate|state)\b',
    r'\bfootage\s+(?:shows?|captures?)\b',
    r'\bvideo\s+(?:shows?|captures?)\b',
    r'\bmedical\s+(?:report|record|documentation)\b',
    r'\bpolice\s+report\b',
    r'\bincident\s+report\b',
    r'\bbody\s+camera\b',
    r'\bdocumented\b',
    r'\bofficial\s+record\b',
]

# PHYSICAL: Physical evidence, injuries
PHYSICAL_PATTERNS = [
    r'\bbruise[ds]?\b',
    r'\binjur(?:y|ies|ed)\b',
    r'\bwound[s]?\b',
    r'\bfracture[ds]?\b',
    r'\bbleeding\b',
    r'\bswelling\b',
    r'\bvisible\b',
    r'\bphysical\s+evidence\b',
    r'\bdamage[ds]?\b',
    r'\bmarks?\b',
    r'\bscar[s]?\b',
]

# =============================================================================
# V4: EPISTEMIC CLASSIFICATION PATTERNS
# =============================================================================
# These patterns detect DANGEROUS epistemic types that MUST be flagged.

# INTENT_ATTRIBUTION: Assigning mental states to others
# ⚠️ DANGEROUS - Cannot know someone's intent
INTENT_ATTRIBUTION_PATTERNS = [
    r'\bclearly\s+(?:looking\s+for|wanting|trying\s+to|ready\s+to)\b',
    r'\b(?:wanted|intended|meant)\s+to\s+(?:inflict|hurt|harm|damage|intimidate)\b',
    r'\b(?:obviously|clearly)\s+(?:didn\'?t\s+care|enjoying|conspiring)\b',
    r'\bit\s+was\s+(?:obvious|clear)\s+(?:that\s+)?they?\s+were\b',
    r'\bdeliberately\s+(?:trying|ignoring|hurting|causing)\b',
    r'\bintentionally\s+(?:trying|ignoring|hurting|causing)\b',
    r'\bpurposely\s+(?:trying|ignoring|hurting|causing)\b',
    r'\b(?:he|she|they)\s+wanted\s+to\b',
    r'\bdesigned\s+to\s+(?:protect|harm|cover|hide|conceal)\b',
    r'\bknew\s+(?:exactly\s+)?what\s+(?:he|she|they)\s+(?:was|were)\s+doing\b',
    r'\benjoying\s+(?:my|the|their)\s+(?:pain|suffering|fear)\b',
]

# LEGAL_CHARACTERIZATION: Legal conclusions by non-attorney
# ⚠️ DANGEROUS - Reporter cannot make legal determinations
LEGAL_CHARACTERIZATION_PATTERNS = [
    r'\bracial\s+profiling\b',
    r'\bpolice\s+brutality\b',
    r'\bexcessive\s+force\b',
    r'\bfalse\s+arrest\b',
    r'\bunlawful\s+(?:detention|search|stop)\b',
    r'\bobstruction\s+of\s+justice\b',
    r'\bviolation\s+of\s+(?:my|his|her|their|civil|constitutional)\s+rights?\b',
    r'\b(?:first|second|third|fourth|fifth)\s+amendment\b',
    r'\bcivil\s+rights?\s+violation\b',
    r'\billegal(?:ly)?\s+(?:detained|searched|arrested|stopped)\b',
    r'\bwrongful\s+(?:arrest|detention|imprisonment)\b',
    r'\bconstitutes?\s+(?:assault|battery|misconduct)\b',
    r'\bcommitted\s+(?:assault|battery|crime|perjury)\b',
    r'\bis\s+(?:guilty|liable)\s+(?:of|for)\b',
]

# CONSPIRACY_CLAIM: Unfalsifiable conspiracy allegations
# ⚠️ DANGEROUS - Speculation presented as fact
CONSPIRACY_CLAIM_PATTERNS = [
    r'\bproves?\s+(?:there\'?s?\s+(?:a\s+)?)?(?:cover[-\s]?up|conspiracy)\b',
    r'\bthey\s+(?:are|were)\s+(?:all\s+)?(?:covering|hiding)\b',
    r'\bwhitewash\b',
    r'\bconspiracy\s+(?:to\s+)?\b',
    r'\bthey\'?re?\s+all\s+in\s+(?:on\s+)?it\b',
    r'\b(?:protecting|covering\s+for)\s+(?:each\s+)?other\b',
    r'\bblue\s+wall\s+of\s+silence\b',
    r'\bcode\s+of\s+silence\b',
    r'\bhiding\s+(?:the\s+)?evidence\b',
    r'\bdestroyed?\s+(?:the\s+)?evidence\b',
]

# NARRATIVE_GLUE: Rhetorical phrases with no factual content
# These should be stripped, not neutralized
NARRATIVE_GLUE_PATTERNS = [
    r'\bit\s+all\s+(?:started|began)\b',
    r'\bout\s+of\s+nowhere\b',
    r'\blittle\s+did\s+(?:I|we)\s+know\b',
    r'\bneedless\s+to\s+say\b',
    r'\blong\s+story\s+short\b',
    r'\bthe\s+next\s+thing\s+(?:I\s+)?knew\b',
    r'\bcan\s+you\s+believe\b',
    r'\bi\s+(?:swear|promise)\b',
    r'\bhonestly\b',
    r'\btruthfully\b',
]

# Reliability scores by evidence type
RELIABILITY_SCORES = {
    EvidenceType.DOCUMENTARY: 0.9,
    EvidenceType.PHYSICAL: 0.85,
    EvidenceType.DIRECT_WITNESS: 0.8,
    EvidenceType.REPORTED: 0.6,
    EvidenceType.INFERENCE: 0.4,
    EvidenceType.UNKNOWN: 0.3,
}

# V4: Epistemic reliability - lower = more dangerous
EPISTEMIC_RELIABILITY = {
    "direct_observation": 0.9,
    "sensory_experience": 0.85,
    "emotional_state": 0.7,
    "physical_symptom": 0.75,
    "intent_attribution": 0.2,    # ⚠️ VERY LOW - likely biased
    "legal_characterization": 0.15,  # ⚠️ VERY LOW - not qualified
    "conspiracy_claim": 0.1,      # ⚠️ LOWEST - unfalsifiable
    "narrative_glue": 0.0,        # No reliability - filler
}


def classify_evidence(ctx: TransformContext) -> TransformContext:
    """
    Classify atomic statements by evidence type.
    
    This pass:
    1. Classifies each statement's evidence type
    2. Identifies source entities for REPORTED evidence
    3. Detects corroboration between statements
    4. Computes reliability scores
    """
    if not ctx.atomic_statements:
        log.info("no_statements", pass_name=PASS_NAME, message="No statements to classify")
        ctx.add_trace(PASS_NAME, "skipped", after="No statements")
        return ctx
    
    classifications: list[EvidenceClassification] = []
    classification_counter = 0
    
    # =========================================================================
    # Phase 1 & 2: Classify Each Statement
    # =========================================================================
    
    for stmt in ctx.atomic_statements:
        evidence_type = _classify_statement_evidence(stmt.text)
        source_entity_id = None
        
        # For REPORTED evidence, find who said it
        if evidence_type == EvidenceType.REPORTED:
            source_entity_id = _find_source_entity(stmt.text, ctx.entities)
        
        # Calculate reliability
        reliability = RELIABILITY_SCORES.get(evidence_type, 0.5)
        
        classification = EvidenceClassification(
            id=f"ev_{classification_counter:04d}",
            statement_id=stmt.id,
            evidence_type=evidence_type,
            source_entity_id=source_entity_id,
            reliability=reliability,
        )
        classifications.append(classification)
        classification_counter += 1
    
    # =========================================================================
    # Phase 3: Detect Corroboration
    # =========================================================================
    
    _detect_corroboration(classifications, ctx.atomic_statements)
    
    # =========================================================================
    # Phase 4: Adjust Reliability Based on Corroboration
    # =========================================================================
    
    for classification in classifications:
        # Boost reliability if corroborated
        if classification.corroborating_ids:
            classification.reliability = min(
                classification.reliability + 0.1 * len(classification.corroborating_ids),
                1.0
            )
        # Reduce reliability if contradicted
        if classification.contradicting_ids:
            classification.reliability = max(
                classification.reliability - 0.1 * len(classification.contradicting_ids),
                0.1
            )
    
    # Store results
    ctx.evidence_classifications = classifications
    
    # Log summary
    type_counts = defaultdict(int)
    for c in classifications:
        type_counts[c.evidence_type.value] += 1
    
    avg_reliability = sum(c.reliability for c in classifications) / len(classifications) if classifications else 0
    
    log.info(
        "evidence_classified",
        pass_name=PASS_NAME,
        channel="SEMANTIC",
        total_classifications=len(classifications),
        avg_reliability=round(avg_reliability, 2),
        **dict(type_counts),
    )
    
    ctx.add_trace(
        PASS_NAME,
        "evidence_classified",
        after=f"{len(classifications)} statements classified, avg reliability: {avg_reliability:.2f}",
    )
    
    # V4: Run epistemic classification to detect dangerous patterns
    ctx = classify_epistemic_v4(ctx)
    
    return ctx


def _classify_statement_evidence(text: str) -> EvidenceType:
    """
    Classify a statement's evidence type based on text patterns.
    """
    text_lower = text.lower()
    
    # Check patterns in priority order
    
    # DOCUMENTARY has highest priority - explicit document references
    if _matches_any(text_lower, DOCUMENTARY_PATTERNS):
        return EvidenceType.DOCUMENTARY
    
    # PHYSICAL - evidence of injuries/damage
    if _matches_any(text_lower, PHYSICAL_PATTERNS):
        return EvidenceType.PHYSICAL
    
    # REPORTED - hearsay markers
    if _matches_any(text_lower, REPORTED_PATTERNS):
        return EvidenceType.REPORTED
    
    # DIRECT_WITNESS - first-person experience
    if _matches_any(text_lower, DIRECT_WITNESS_PATTERNS):
        return EvidenceType.DIRECT_WITNESS
    
    # Default to INFERENCE (reporter's conclusion)
    return EvidenceType.INFERENCE


def _matches_any(text: str, patterns: list[str]) -> bool:
    """Check if text matches any of the regex patterns."""
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def _classify_epistemic_type(text: str) -> tuple[Optional[str], Optional[str]]:
    """
    V4: Classify the epistemic type of a statement.
    
    Returns (epistemic_type, matched_phrase) or (None, None) if no dangerous patterns found.
    
    This is critical for detecting:
    - Intent attribution (claims about others' mental states)
    - Legal characterization (legal conclusions by non-attorney)
    - Conspiracy claims (unfalsifiable allegations)
    - Narrative glue (filler with no factual content)
    """
    text_lower = text.lower()
    
    # Check INTENT_ATTRIBUTION first - very dangerous
    for pattern in INTENT_ATTRIBUTION_PATTERNS:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            return ("intent_attribution", match.group())
    
    # Check LEGAL_CHARACTERIZATION - reporter making legal conclusions
    for pattern in LEGAL_CHARACTERIZATION_PATTERNS:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            return ("legal_characterization", match.group())
    
    # Check CONSPIRACY_CLAIM - unfalsifiable allegations
    for pattern in CONSPIRACY_CLAIM_PATTERNS:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            return ("conspiracy_claim", match.group())
    
    # Check NARRATIVE_GLUE - filler phrases
    for pattern in NARRATIVE_GLUE_PATTERNS:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            return ("narrative_glue", match.group())
    
    return (None, None)


def classify_epistemic_v4(ctx: TransformContext) -> TransformContext:
    """
    V4: Classify statements by epistemic type and add diagnostics.
    
    This runs after evidence classification to add epistemic markers
    for dangerous patterns like intent attribution and legal characterization.
    """
    if not ctx.atomic_statements:
        return ctx
    
    intent_count = 0
    legal_count = 0
    conspiracy_count = 0
    
    for stmt in ctx.atomic_statements:
        epistemic_type, matched_phrase = _classify_epistemic_type(stmt.text)
        
        if epistemic_type:
            # Store on the statement (if schema allows) or add diagnostic
            reliability = EPISTEMIC_RELIABILITY.get(epistemic_type, 0.5)
            
            if epistemic_type == "intent_attribution":
                intent_count += 1
                ctx.add_diagnostic(
                    level="warning",
                    code="V4_INTENT_ATTRIBUTION",
                    message=f"Intent attributed to another person: '{matched_phrase}'",
                    source=PASS_NAME,
                    affected_ids=[stmt.segment_id] if stmt.segment_id else [],
                )
                log.warning(
                    "intent_attribution_detected",
                    statement_id=stmt.id,
                    phrase=matched_phrase,
                    reliability=reliability,
                )
            
            elif epistemic_type == "legal_characterization":
                legal_count += 1
                ctx.add_diagnostic(
                    level="warning",
                    code="V4_LEGAL_CHARACTERIZATION",
                    message=f"Legal conclusion by reporter: '{matched_phrase}'",
                    source=PASS_NAME,
                    affected_ids=[stmt.segment_id] if stmt.segment_id else [],
                )
                log.warning(
                    "legal_characterization_detected",
                    statement_id=stmt.id,
                    phrase=matched_phrase,
                    reliability=reliability,
                )
            
            elif epistemic_type == "conspiracy_claim":
                conspiracy_count += 1
                ctx.add_diagnostic(
                    level="warning",
                    code="V4_CONSPIRACY_CLAIM",
                    message=f"Unfalsifiable conspiracy claim: '{matched_phrase}'",
                    source=PASS_NAME,
                    affected_ids=[stmt.segment_id] if stmt.segment_id else [],
                )
                log.warning(
                    "conspiracy_claim_detected",
                    statement_id=stmt.id,
                    phrase=matched_phrase,
                    reliability=reliability,
                )
    
    # Summary logging
    if intent_count or legal_count or conspiracy_count:
        log.info(
            "v4_epistemic_classification_complete",
            intent_attributions=intent_count,
            legal_characterizations=legal_count,
            conspiracy_claims=conspiracy_count,
        )
    
    return ctx


def _find_source_entity(text: str, entities: list[Entity]) -> Optional[str]:
    """
    Find the source entity for reported evidence.
    
    Looks for entity names mentioned in speech attribution patterns.
    """
    text_lower = text.lower()
    
    # Check for entity names in "X said" or "X told me" patterns
    for entity in entities:
        if not entity.label:
            continue
        
        label_lower = entity.label.lower()
        
        # Full name match before "said/told/claimed"
        for word in label_lower.split():
            if len(word) > 2:  # Skip short words
                pattern = rf'\b{re.escape(word)}\s+(?:said|told|claimed|stated|reported)\b'
                if re.search(pattern, text_lower):
                    return entity.id
    
    return None


def _detect_corroboration(
    classifications: list[EvidenceClassification],
    statements: list,
) -> None:
    """
    Detect corroboration and contradiction between statements.
    
    Uses simple keyword overlap to find related statements.
    """
    # Build statement text lookup
    stmt_texts = {stmt.id: stmt.text.lower() for stmt in statements}
    
    # Extract key action words from each statement
    action_keywords = {}
    for stmt in statements:
        text_lower = stmt.text.lower()
        # Extract verbs/actions (simplified - look for common action words)
        keywords = set()
        action_words = [
            'grab', 'grabbed', 'push', 'pushed', 'shove', 'shoved', 
            'hit', 'struck', 'punch', 'punched', 'kick', 'kicked',
            'arrest', 'arrested', 'detain', 'detained', 'handcuff', 'handcuffed',
            'approach', 'approached',
            'saw', 'see', 'watch', 'watched', 'show', 'shows',
            'hear', 'heard', 'felt', 'feel', 'notice', 'noticed',
            'said', 'told', 'yell', 'yelled', 'scream', 'screamed',
        ]
        for word in action_words:
            if word in text_lower:
                keywords.add(word)
        action_keywords[stmt.id] = keywords
    
    # Compare pairs of statements
    for i, class1 in enumerate(classifications):
        for j, class2 in enumerate(classifications):
            if i >= j:
                continue  # Skip self and duplicates
            
            keywords1 = action_keywords.get(class1.statement_id, set())
            keywords2 = action_keywords.get(class2.statement_id, set())
            
            # Check for overlap
            overlap = keywords1 & keywords2
            if len(overlap) >= 1:
                # These statements mention the same action
                # Check if from different sources (corroboration)
                if class1.evidence_type != class2.evidence_type:
                    # Different types of evidence about same thing = corroboration
                    class1.corroborating_ids.append(class2.statement_id)
                    class2.corroborating_ids.append(class1.statement_id)
                elif class1.source_entity_id != class2.source_entity_id:
                    # Same type but different sources
                    if class1.source_entity_id or class2.source_entity_id:
                        class1.corroborating_ids.append(class2.statement_id)
                        class2.corroborating_ids.append(class1.statement_id)
