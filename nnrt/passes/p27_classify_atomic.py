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
from nnrt.ir.enums import StatementType
from nnrt.nlp.spacy_loader import get_nlp

PASS_NAME = "p27_classify_atomic"

# ============================================================================
# Linguistic Markers (Research-Grounded)
# ============================================================================

# Sensory/factive verbs - indicate direct witnessing
SENSORY_VERBS = {
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
    # Priority 3: OBSERVATION - direct witnessing
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
    
    if has_first_person and has_sensory_verb:
        flags.append("first_person_witness")
        return StatementType.OBSERVATION, 0.85, flags
    
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
