"""
Pass 72 — V4 Safety Scrub

Final safety net that scrubs any dangerous epistemic content that slipped
through the rendering pipeline.

This pass runs AFTER p70_render to ensure:
1. Legal characterizations are in attributed form
2. Conspiracy language is removed
3. Invective is removed

ARCHITECTURE NOTE:
This is a safety net, not the primary defense. The proper defense is:
- p27_epistemic_tag: Classify statements
- p27b_attribute_statements: Attribute or aberrate

This pass catches anything that slipped through segment-level rendering.
"""

import re
from nnrt.core.context import TransformContext
from nnrt.core.logging import get_pass_logger

PASS_NAME = "p72_safety_scrub"
log = get_pass_logger(PASS_NAME)


# =============================================================================
# DANGEROUS PATTERNS TO TRANSFORM IN RENDERED OUTPUT
# =============================================================================

# Legal characterizations that should be attributed
# (pattern, replacement)
LEGAL_SCRUB_PATTERNS = [
    # Direct legal claims → attributed form
    (r'\b[Tt]his\s+was\s+(clearly\s+)?(racial\s+profiling)', 
     "-- reporter characterizes the stop as racial profiling --"),
    (r'\b[Tt]his\s+was\s+(clearly\s+)?(police\s+brutality)',
     "-- reporter characterizes conduct as police brutality --"),
    (r'\bracial\s+profiling\s+and\s+harassment',
     "-- reporter characterizes conduct as racial profiling and harassment --"),
    (r'\bexcessive\s+force',
     "described force"),  # Neutral phrasing
    (r'\bpolice\s+brutality',
     "-- reporter characterizes conduct --"),
]

# Conspiracy language to remove entirely
CONSPIRACY_SCRUB_PATTERNS = [
    (r'\b[Ii]\s+know\s+they\s+always\s+protect\s+their\s+own\.?',
     ""),  # Remove entirely
    (r'\bthey\s+always\s+protect\s+their\s+own\.?',
     ""),
    (r'\bmassive\s+cover.?up',
     ""),
    (r'\bwhitewash',
     ""),
]

# Invective to remove
INVECTIVE_SCRUB_PATTERNS = [
    (r'\bthug\s+cop[s]?', "officer"),
    (r'\bpsychotic', ""),
    (r'\bmaniac', ""),
    (r'\bbrutally', ""),
    (r'\bviciously', ""),
]


def safety_scrub(ctx: TransformContext) -> TransformContext:
    """
    Final safety scrub of rendered text.
    
    Catches and transforms any dangerous content that slipped through
    the segment-level rendering.
    """
    if not ctx.rendered_text:
        return ctx
    
    original = ctx.rendered_text
    scrubbed = original
    scrub_count = 0
    
    # Apply legal scrubs
    for pattern, replacement in LEGAL_SCRUB_PATTERNS:
        new_text, count = re.subn(pattern, replacement, scrubbed, flags=re.IGNORECASE)
        if count > 0:
            scrubbed = new_text
            scrub_count += count
            log.info("legal_scrub", pattern=pattern[:30], count=count)
    
    # Apply conspiracy scrubs
    for pattern, replacement in CONSPIRACY_SCRUB_PATTERNS:
        new_text, count = re.subn(pattern, replacement, scrubbed, flags=re.IGNORECASE)
        if count > 0:
            scrubbed = new_text
            scrub_count += count
            log.info("conspiracy_scrub", pattern=pattern[:30], count=count)
    
    # Apply invective scrubs
    for pattern, replacement in INVECTIVE_SCRUB_PATTERNS:
        new_text, count = re.subn(pattern, replacement, scrubbed, flags=re.IGNORECASE)
        if count > 0:
            scrubbed = new_text
            scrub_count += count
            log.info("invective_scrub", pattern=pattern[:30], count=count)
    
    # Clean up artifacts
    scrubbed = _clean_artifacts(scrubbed)
    
    if scrub_count > 0:
        ctx.rendered_text = scrubbed
        log.info("safety_scrub_complete", 
            scrubs_applied=scrub_count,
            original_len=len(original),
            scrubbed_len=len(scrubbed))
        
        ctx.add_diagnostic(
            level="info",
            code="V4_SAFETY_SCRUB",
            message=f"Applied {scrub_count} safety scrubs to rendered output",
            source=PASS_NAME,
        )
    
    ctx.add_trace(
        pass_name=PASS_NAME,
        action="safety_scrub",
        after=f"Applied {scrub_count} scrubs" if scrub_count else "No scrubs needed",
    )
    
    return ctx


def _clean_artifacts(text: str) -> str:
    """Clean up artifacts from scrubbing."""
    result = text
    
    # Remove double spaces
    while "  " in result:
        result = result.replace("  ", " ")
    
    # Remove orphaned punctuation
    result = result.replace(" .", ".").replace(" ,", ",")
    result = result.replace(".,", ".").replace(",.", ".")
    
    # Remove empty parentheses/brackets
    result = re.sub(r'\(\s*\)', '', result)
    result = re.sub(r'\[\s*\]', '', result)
    
    # Remove leftover "-- --" patterns
    result = re.sub(r'--\s*--', '', result)
    
    # Trim extra whitespace
    result = result.strip()
    
    return result
