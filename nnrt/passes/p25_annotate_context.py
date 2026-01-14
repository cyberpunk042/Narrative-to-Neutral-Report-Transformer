"""
Pass 25: Annotate Context — Detect segment-level contexts.

This pass analyzes segments and annotates them with context classifications:
- CHARGE_DESCRIPTION: "charged with", "accused of" 
- DIRECT_QUOTE: Content in quotation marks
- PHYSICAL_FORCE: Observable physical actions
- PHYSICAL_ATTEMPT: "tried to say/breathe/move"
- INJURY_DESCRIPTION: Injuries described
- TIMELINE: Temporal markers
- etc.

These context annotations enable downstream passes (especially render)
to make context-aware decisions WITHOUT re-analyzing the text.
"""

import re
from uuid import uuid4

from nnrt.core.context import TransformContext
from nnrt.ir.enums import SegmentContext

PASS_NAME = "annotate_context"


# ============================================================================
# Context Detection Patterns
# ============================================================================

# Charge/accusation language
CHARGE_PATTERNS = [
    r"\bcharged?\s+(me\s+)?with\b",
    r"\baccused?\s+(me\s+)?of\b",
    r"\barrested?\s+(me\s+)?for\b",
    r"\bcharg(e|es|ing)\s+of\b",
]

# Physical force descriptors
PHYSICAL_FORCE_PATTERNS = [
    r"\b(grabbed|yanked|pulled|pushed|shoved|threw|slammed|tackled)\b",
    r"\b(punched|struck|hit|kicked|beat|choked|strangled)\b",
    r"\b(handcuff|cuff|restrain|pin|knee)\b",
    r"\b(ground|floor|wall|hood|pavement|asphalt)\b",
]

# Physical attempt (NOT intent attribution)
PHYSICAL_ATTEMPT_PATTERNS = [
    r"\btried?\s+to\s+(say|speak|talk|yell|scream|shout)\b",
    r"\btried?\s+to\s+(breathe|breath|move|stand|sit|run|walk)\b",
    r"\btried?\s+to\s+(open|close|reach|grab|pull|push)\b",
    r"\btrying\s+to\s+(say|speak|talk|breathe|move)\b",
    r"\bcouldn'?t\s+(breathe|move|speak|see)\b",
]

# Injury descriptions
INJURY_PATTERNS = [
    r"\b(bleed|bleeding|blood|bruise|bruises|bruising)\b",
    r"\b(broken|fractured|cracked|swollen|swelling)\b",
    r"\b(pain|hurt|hurts|painful|injury|injuries)\b",
    r"\b(hospital|doctor|medical|ER|emergency)\b",
    r"\b(nerve\s+damage|permanent|surgery)\b",
]

# Timeline/temporal markers
TIMELINE_PATTERNS = [
    r"\b\d{1,2}:\d{2}\s*(AM|PM|am|pm)?\b",
    r"\b\d{1,2}\s*(AM|PM|am|pm)\b",
    r"\b\d{4}\s*hours?\b",
    r"\b(before|after|then|during|while|when)\b",
    r"\b(first|next|finally|immediately|eventually)\b",
    r"\b\d+\s*(second|minute|hour|day|week|month)s?\b",
]

# Credibility assertions (meta-commentary)
CREDIBILITY_PATTERNS = [
    r"\bi\s+swear\b",
    r"\bi'?m\s+(not\s+)?lying\b",
    r"\bi'?m\s+telling\s+(you\s+)?the\s+truth\b",
    r"\byou\s+(probably\s+)?won'?t\s+believe\b",
    r"\bthis\s+sounds\s+crazy\b",
]

# Official/neutral report language
OFFICIAL_REPORT_PATTERNS = [
    r"\b\d{4}\s*hours\b",  # Military time
    r"\bsubject\s+(was|is|did)\b",
    r"\bI\s+observed\b",
    r"\bupon\s+arrival\b",
    r"\bthe\s+vehicle\s+(was|is)\b",
]

# ============================================================================
# M3: Biased Language Detection (for meta-detection)
# If NONE of these match, segment is likely already neutral
# ============================================================================

# Inflammatory language markers
BIASED_INFLAMMATORY = [
    r"\b(brutal|vicious|violent|savage|ruthless)\b",
    r"\b(thug|pig|goon|bully|monster)\b",
    r"\b(attacked|assaulted|brutalized)\b",
    r"\b(terrified|horrified|traumatized)\b",
]

# Intent attribution markers
BIASED_INTENT = [
    r"\b(wanted\s+to|tried\s+to|meant\s+to)\b",
    r"\b(clearly|obviously|deliberately|intentionally)\b",
    r"\b(on\s+purpose)\b",
]

# Legal conclusion markers
BIASED_LEGAL = [
    r"\b(assaulted|guilty|innocent|convicted)\b",
    r"\b(illegal|unlawful|unconstitutional)\b",
    r"\b(rights\s+violated|excessive\s+force)\b",
]

# Opinion/interpretation markers
OPINION_MARKERS = [
    r"\b(I\s+think|I\s+believe|I\s+feel\s+like)\b",
    r"\b(probably|maybe|might\s+have)\b",
    r"\b(seemed\s+like|looked\s+like|appeared\s+to)\b",
    r"\b(in\s+my\s+opinion)\b",
]

# Sarcasm indicators
SARCASM_PATTERNS = [
    r"\bso\s+(gentle|nice|kind|polite|helpful)\b",  # Exaggerated positive
    r'["\'](?:safety|protection|help)["\']',  # Quoted positive words
    r"\byeah\s+right\b",
    r"\bof\s+course\b.*\bnot\b",
]

# ============================================================================
# M3: Ambiguity Detection Patterns
# ============================================================================

# Pronouns that often lead to ambiguity
AMBIGUOUS_PRONOUNS = [
    # Multiple pronouns in interactions (who did what to whom?)
    r"\bhe\s+\w+\s+him\b",          # "he hit him"  
    r"\bshe\s+\w+\s+her\b",          # "she pushed her"
    r"\bthey\s+\w+\s+them\b",        # "they attacked them"
]

# Vague references without clear antecedents
VAGUE_REFERENCES = [
    r"\bthey\s+said\b",              # "they said I was..." (who is they?)
    r"\bthey\s+told\s+me\b",         # "they told me to..." 
    r"\bsomeone\s+(said|told)\b",    # "someone said..."
    r"\bpeople\s+(said|told)\b",     # "people said..."
    r"\bhe\s+said\s+he\b",           # "he said he would..." (which he?)
    r"\bshe\s+said\s+she\b",         # "she said she would..."
]

# Start-of-sentence pronouns after unclear context
DANGLING_PRONOUNS = [
    r"^\s*(He|She|They|It)\s+(was|were|did|had|is|are)\b",  # Starts with pronoun
]

# Contradictory or confusing qualifiers
CONFUSING_QUALIFIERS = [
    r"\b(sort\s+of|kind\s+of)\s+\w+\s+(but|and)\s+",  # "sort of hit but also"
    r"\b(maybe|probably)\s+\w+\s+(or|but)\s+",        # "maybe pushed or maybe"
]


def annotate_context(ctx: TransformContext) -> TransformContext:
    """
    Annotate segments with context classifications.
    
    This pass does NOT transform text. It only adds metadata
    that downstream passes can use to make decisions.
    """
    total_annotations = 0
    
    for segment in ctx.segments:
        text = segment.text
        text_lower = text.lower()
        contexts: list[str] = []
        
        # Check for charge/accusation context
        if _matches_any(text_lower, CHARGE_PATTERNS):
            contexts.append(SegmentContext.CHARGE_DESCRIPTION.value)
        
        # Check for physical force
        if _matches_any(text_lower, PHYSICAL_FORCE_PATTERNS):
            contexts.append(SegmentContext.PHYSICAL_FORCE.value)
        
        # Check for physical attempt (NOT intent attribution)
        if _matches_any(text_lower, PHYSICAL_ATTEMPT_PATTERNS):
            contexts.append(SegmentContext.PHYSICAL_ATTEMPT.value)
        
        # Check for injury description
        if _matches_any(text_lower, INJURY_PATTERNS):
            contexts.append(SegmentContext.INJURY_DESCRIPTION.value)
        
        # Check for timeline markers
        if _matches_any(text_lower, TIMELINE_PATTERNS):
            contexts.append(SegmentContext.TIMELINE.value)
        
        # Check for credibility assertions
        if _matches_any(text_lower, CREDIBILITY_PATTERNS):
            contexts.append(SegmentContext.CREDIBILITY_ASSERTION.value)
        
        # Check for official report language
        if _matches_any(text_lower, OFFICIAL_REPORT_PATTERNS):
            contexts.append(SegmentContext.OFFICIAL_REPORT.value)
        
        # Detect direct quotes (straight and curly)
        quote_count = (
            text.count('"') +      # Straight double
            text.count("'") +      # Straight single
            text.count('\u201c') + # Left curly double "
            text.count('\u201d') + # Right curly double "
            text.count('\u2018') + # Left curly single '
            text.count('\u2019')   # Right curly single '
        )
        if quote_count >= 2:  # At least one pair of quotes
            contexts.append(SegmentContext.DIRECT_QUOTE.value)
            segment.quote_depth = 1
        
        # ================================================================
        # M3: Meta-Detection — Check for biased language
        # ================================================================
        
        # Check for sarcasm indicators
        has_sarcasm = _matches_any(text_lower, SARCASM_PATTERNS)
        if has_sarcasm:
            contexts.append(SegmentContext.SARCASM.value)
            ctx.add_diagnostic(
                level="warning",
                code="SARCASM_DETECTED",
                message=f"Possible sarcasm detected - literal meaning may differ: '{text[:50]}...'",
                source=PASS_NAME,
                affected_ids=[segment.id],
            )
        
        # ================================================================
        # M3: Ambiguity Detection
        # ================================================================
        
        # Check for ambiguous pronouns (he hit him, etc.)
        has_ambiguous_pronouns = _matches_any(text_lower, AMBIGUOUS_PRONOUNS)
        
        # Check for vague references (they said, someone told me)
        has_vague_references = _matches_any(text_lower, VAGUE_REFERENCES)
        
        # Check for confusing qualifiers
        has_confusing = _matches_any(text_lower, CONFUSING_QUALIFIERS)
        
        # Combined ambiguity check
        has_ambiguity = has_ambiguous_pronouns or has_vague_references or has_confusing
        
        if has_ambiguity:
            contexts.append(SegmentContext.AMBIGUOUS.value)
            
            # Specific diagnostics
            if has_ambiguous_pronouns:
                ctx.add_diagnostic(
                    level="warning",
                    code="AMBIGUOUS_PRONOUN",
                    message=f"Ambiguous pronoun reference - unclear who did what: '{text[:60]}...'",
                    source=PASS_NAME,
                    affected_ids=[segment.id],
                )
            if has_vague_references:
                ctx.add_diagnostic(
                    level="warning",
                    code="VAGUE_REFERENCE",
                    message=f"Vague reference - unclear who 'they'/'someone' refers to: '{text[:60]}...'",
                    source=PASS_NAME,
                    affected_ids=[segment.id],
                )
        
        # Check for biased language (inflammatory, intent, legal conclusions)
        has_biased_content = (
            _matches_any(text_lower, BIASED_INFLAMMATORY) or
            _matches_any(text_lower, BIASED_INTENT) or
            _matches_any(text_lower, BIASED_LEGAL) or
            has_sarcasm  # Sarcasm also counts as needing transformation
        )
        
        # Check for opinion-only content
        is_opinion_only = (
            _matches_any(text_lower, OPINION_MARKERS) and
            not _matches_any(text_lower, PHYSICAL_FORCE_PATTERNS) and
            not _matches_any(text_lower, INJURY_PATTERNS) and
            not _matches_any(text_lower, TIMELINE_PATTERNS)
        )
        
        if is_opinion_only:
            contexts.append(SegmentContext.OPINION_ONLY.value)
        
        # If NO biased content detected, mark as already neutral
        if not has_biased_content and not is_opinion_only:
            contexts.append(SegmentContext.ALREADY_NEUTRAL.value)
        
        # If no specific context, mark as observation (default)
        if not contexts:
            contexts.append(SegmentContext.OBSERVATION.value)
        
        # Update segment
        segment.contexts = contexts
        total_annotations += len(contexts)
        
        # Add trace
        ctx.add_trace(
            pass_name=PASS_NAME,
            action="annotated_contexts",
            after=f"{segment.id}: {contexts}",
            affected_ids=[segment.id],
        )
    
    # ================================================================
    # M3: Global meta-detection — Is the entire input neutral?
    # ================================================================
    all_neutral = all(
        SegmentContext.ALREADY_NEUTRAL.value in seg.contexts
        for seg in ctx.segments
    )
    if all_neutral:
        ctx.add_diagnostic(
            level="info",
            code="INPUT_ALREADY_NEUTRAL",
            message="Input appears to be already neutral. No transformation needed.",
            source=PASS_NAME,
        )
    
    ctx.add_trace(
        pass_name=PASS_NAME,
        action="completed",
        after=f"{len(ctx.segments)} segments, {total_annotations} context annotations" +
              (" (all neutral)" if all_neutral else ""),
    )
    
    return ctx


def _matches_any(text: str, patterns: list[str]) -> bool:
    """Check if text matches any of the regex patterns."""
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False
