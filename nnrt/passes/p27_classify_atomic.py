"""
Pass 27: Classify Atomic Statements

Classifies each atomic statement (from p26_decompose) using linguistic markers.

Classification hierarchy:
1. QUOTE - Contains quoted speech
2. OBSERVATION - First-person + sensory/factive verb ("I saw", "I heard")
3. INTERPRETATION - Intent verbs/adverbs ("wanted to", "deliberately") 
4. CLAIM - Default for assertions

This uses research-grounded linguistic markers for epistemic status classification.
"""

import re
from typing import Optional

from nnrt.core.context import TransformContext
from nnrt.core.logging import get_pass_logger
from nnrt.ir.enums import StatementType
from nnrt.nlp.spacy_loader import get_nlp

PASS_NAME = "p27_classify_atomic"
log = get_pass_logger(PASS_NAME)

# ============================================================================
# Linguistic Markers (Research-Grounded)
# ============================================================================

# Sensory/factive verbs - indicate direct witnessing
SENSORY_VERBS = {
    # Original sensory
    "see", "saw", "seen",
    "hear", "heard", 
    "feel", "felt",
    "notice", "noticed",
    "watch", "watched",
    "observe", "observed",
    "witness", "witnessed",
    "smell", "smelled",
    "taste", "tasted",
}

# Experiential verbs - first-person experience (NEW)
EXPERIENTIAL_VERBS = {
    # Physical reactions
    "freeze", "froze", "frozen",
    "jump", "jumped",
    "fall", "fell", "fallen",
    "run", "ran",
    "move", "moved",
    "step", "stepped",
    "back", "backed",
    "duck", "ducked",
    "flinch", "flinched",
    "shake", "shook", "shaking",
    "cry", "cried", "crying",
    "bleed", "bled", "bleeding",
    
    # Speech acts
    "say", "said",
    "ask", "asked",
    "tell", "told",
    "yell", "yelled",
    "scream", "screamed",
    "call", "called",
    "shout", "shouted",
    "beg", "begged",
    "plead", "pleaded",
    "explain", "explained",
    "reply", "replied",
    "answer", "answered",
    
    # Actions
    "go", "went", "gone",
    "walk", "walked",
    "arrive", "arrived",
    "leave", "left",
    "stay", "stayed",
    "wait", "waited",
    "file", "filed",
    "receive", "received",
}

# Intent verbs - indicate interpretation of others' mental states
INTENT_VERBS = {
    "want", "wanted", "wants",
    "try", "tried", "tries", "trying",
    "intend", "intended", "intends",
    "mean", "meant", "means",
    "plan", "planned", "plans",
    "decide", "decided", "decides",
}

# Intent adverbs - signal intent attribution
INTENT_ADVERBS = {
    "deliberately",
    "intentionally", 
    "purposely",
    "purposefully",
    "knowingly",
    "willfully",
}

# Certainty adverbs - often signal interpretation
CERTAINTY_ADVERBS = {
    "obviously",
    "clearly", 
    "definitely",
    "certainly",
    "surely",
    "undoubtedly",
}

# Opinion markers
OPINION_MARKERS = [
    r"\bI\s+think\b",
    r"\bI\s+believe\b",
    r"\bI\s+feel\s+like\b",
    r"\bin\s+my\s+opinion\b",
    r"\bit\s+seems?\b",
    r"\bit\s+appears?\b",
]

# hedging markers - uncertainty
HEDGING_MARKERS = [
    r"\bprobably\b",
    r"\bmaybe\b",
    r"\bmight\s+have\b",
    r"\bcould\s+have\b",
    r"\bseemed?\s+like\b",
    r"\blooked?\s+like\b",
    r"\bappeared?\s+to\b",
]

# ============================================================================
# V7 / Stage 1: Medical Content Routing (from V1 lines 1125-1134)
# ============================================================================

# Medical provider terms
MEDICAL_PROVIDERS = {
    'dr.', 'dr ', 'doctor', 'nurse', 'emt', 'paramedic', 
    'physician', 'therapist', 'surgeon', 'medic',
}

# Medical action verbs
MEDICAL_VERBS = {
    'documented', 'diagnosed', 'noted', 'observed', 'confirmed',
    'treated', 'examined', 'assessed', 'determined', 'concluded',
}


def _is_medical_provider_content(text: str) -> bool:
    """Check if content is from a medical provider (should go to MEDICAL_FINDINGS)."""
    text_lower = text.lower()
    has_provider = any(p in text_lower for p in MEDICAL_PROVIDERS)
    has_verb = any(v in text_lower for v in MEDICAL_VERBS)
    return has_provider and has_verb


def classify_atomic(ctx: TransformContext) -> TransformContext:
    """
    Classify each atomic statement by epistemic status.
    
    Uses spaCy for robust linguistic analysis.
    """
    if not ctx.atomic_statements:
        ctx.add_trace(
            pass_name=PASS_NAME,
            action="skipped",
            after="No atomic statements to classify",
        )
        return ctx
    
    nlp = get_nlp()
    classified_counts = {t.value: 0 for t in StatementType}
    
    for stmt in ctx.atomic_statements:
        # Parse the statement
        doc = nlp(stmt.text)
        
        # Classify using linguistic analysis
        stmt_type, confidence, flags = _classify_statement(stmt.text, doc)
        
        # Update the statement
        stmt.type_hint = stmt_type
        stmt.confidence = confidence
        stmt.flags.extend(flags)
        
        classified_counts[stmt_type.value] += 1
    
    log.info("classified",
        statements=len(ctx.atomic_statements),
        **classified_counts,
    )
    
    # Trace
    ctx.add_trace(
        pass_name=PASS_NAME,
        action="classified_atomic",
        after=f"{len(ctx.atomic_statements)} statements: {classified_counts}",
    )
    
    return ctx


def _classify_statement(text: str, doc) -> tuple[StatementType, float, list[str]]:
    """
    Classify a single statement using linguistic markers.
    
    Returns (type, confidence, flags).
    """
    text_lower = text.lower()
    flags = []
    
    # =========================================================================
    # Priority 1: QUOTE - preserve verbatim
    # =========================================================================
    if _has_quotation(text):
        return StatementType.QUOTE, 1.0, ["quoted_content"]
    
    # =========================================================================
    # V7 / Stage 1: Medical Content Routing
    # =========================================================================
    # Medical provider content (Dr., Nurse documented/diagnosed) gets
    # classified as MEDICAL_FINDING so it routes to the correct section.
    # =========================================================================
    if _is_medical_provider_content(text):
        # Use OBSERVATION with a flag for medical routing
        return StatementType.OBSERVATION, 0.9, ["medical_provider_content"]
    
    # =========================================================================
    # Priority 2: INTERPRETATION - intent attribution
    # =========================================================================
    
    # Check for intent verbs (most reliable signal)
    has_intent_verb = any(
        t.lemma_.lower() in INTENT_VERBS or t.text.lower() in INTENT_VERBS
        for t in doc if t.pos_ == "VERB"
    )
    if has_intent_verb:
        flags.append("intent_verb")
        return StatementType.INTERPRETATION, 0.9, flags
    
    # Check for intent adverbs
    has_intent_adv = any(t.text.lower() in INTENT_ADVERBS for t in doc)
    if has_intent_adv:
        flags.append("intent_adverb")
        return StatementType.INTERPRETATION, 0.9, flags
    
    # Check for certainty adverbs (weaker signal)
    has_certainty_adv = any(t.text.lower() in CERTAINTY_ADVERBS for t in doc)
    if has_certainty_adv:
        flags.append("certainty_adverb")
        return StatementType.INTERPRETATION, 0.7, flags
    
    # Check for opinion markers
    if _matches_any(text_lower, OPINION_MARKERS):
        flags.append("opinion_marker")
        return StatementType.INTERPRETATION, 0.8, flags
    
    # Check for hedging (weaker interpretation signal)
    if _matches_any(text_lower, HEDGING_MARKERS):
        flags.append("hedging")
        return StatementType.INTERPRETATION, 0.6, flags
    
    # =========================================================================
    # Priority 3: OBSERVATION - direct witnessing or experience
    # =========================================================================
    
    # Check for first person subject
    has_first_person = any(
        t.text.lower() in ("i", "we") and t.dep_ in ("nsubj", "nsubjpass")
        for t in doc
    )
    
    # Check for sensory/factive verb
    has_sensory_verb = any(
        t.lemma_.lower() in SENSORY_VERBS or t.text.lower() in SENSORY_VERBS
        for t in doc if t.pos_ == "VERB"
    )
    
    # Check for experiential verb (NEW)
    has_experiential_verb = any(
        t.lemma_.lower() in EXPERIENTIAL_VERBS or t.text.lower() in EXPERIENTIAL_VERBS
        for t in doc if t.pos_ == "VERB"
    )
    
    # First person + sensory = strong observation
    if has_first_person and has_sensory_verb:
        flags.append("first_person_witness")
        return StatementType.OBSERVATION, 0.85, flags
    
    # First person + experiential = observation (NEW)
    if has_first_person and has_experiential_verb:
        flags.append("first_person_experience")
        return StatementType.OBSERVATION, 0.80, flags
    
    # Check for experiential states pattern "I was [emotional state]"
    if re.search(r'\bI\s+was\s+(?:so\s+)?(?:terrified|scared|frightened|afraid|shocked|stunned|confused|exhausted|tired|hurt|injured)\b', text_lower):
        flags.append("experiential_state")
        return StatementType.OBSERVATION, 0.80, flags
    
    # =========================================================================
    # Default: CLAIM - assertion without explicit epistemics
    # =========================================================================
    return StatementType.CLAIM, 0.5, flags


def _has_quotation(text: str) -> bool:
    """Check if text contains quotation marks with content."""
    # Look for actual quoted content, not just stray quotes
    return bool(re.search(r'["\'][^"\']+["\']', text))


def _matches_any(text: str, patterns: list[str]) -> bool:
    """Check if text matches any regex pattern."""
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)
