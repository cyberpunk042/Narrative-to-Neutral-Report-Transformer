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
# V5: ATTRIBUTION ENFORCEMENT
# Every allegation/inference MUST use "reporter asserts/perceives/characterizes"
# This is the final safety net - patterns that slip through get caught here.
# =============================================================================

# Legal characterizations that MUST be attributed
# (pattern, replacement)
LEGAL_SCRUB_PATTERNS = [
    # Direct legal claims → attributed form
    (r'\b[Tt]his\s+was\s+(clearly\s+)?(racial\s+profiling)', 
     "-- reporter characterizes the stop as racial profiling --"),
    (r'\b[Tt]his\s+was\s+(clearly\s+)?(police\s+brutality)',
     "-- reporter characterizes conduct as police brutality --"),
    (r'\bracial\s+profiling\s+and\s+harassment',
     "-- reporter characterizes conduct as racial profiling and harassment --"),
    (r'\bpolice\s+brutality',
     "-- reporter characterizes conduct as brutality --"),
    
    # V5: Legal terms that must be attributed
    (r'\bexcessive\s+force\b',
     "-- reporter describes force as excessive --"),
    (r'\bfalse\s+arrest\b',
     "-- reporter characterizes arrest as false --"),
    (r'\bunlawful\s+(detention|stop|search|arrest)\b',
     "-- reporter characterizes action as unlawful --"),
    (r'\billegal\s+(search|detention|arrest|stop)\b',
     "-- reporter characterizes action as illegal --"),
    (r'\bobstruction\s+of\s+justice\b',
     "-- reporter alleges obstruction of justice --"),
    (r'\bwitness\s+intimidation\b',
     "-- reporter alleges witness intimidation --"),
    (r'\b(civil|constitutional)\s+rights?\s+violation\b',
     "-- reporter alleges rights violation --"),
    (r'\bharassment\b',
     "-- reporter characterizes conduct as harassment --"),
    (r'\bassault\s+and\s+battery\b',
     "-- reporter alleges assault --"),
    (r'\bwrongful\s+(termination|arrest|detention)\b',
     "-- reporter characterizes as wrongful --"),
    
    # V5: Systemic claims MUST be attributed
    (r'\bsystematic\s+(racism|discrimination|abuse)\b',
     "-- reporter alleges systemic issues --"),
    (r'\bsystemic\s+(racism|discrimination|abuse|misconduct)\b',
     "-- reporter alleges systemic issues --"),
    (r'\binstitutionalized\s+(racism|discrimination)\b',
     "-- reporter alleges institutional issues --"),
    (r'\bracism\s+in\s+(this|the)\s+(department|force|police)\b',
     "-- reporter alleges racism --"),
    (r'\bpattern\s+of\s+(abuse|misconduct|violence|brutality)\b',
     "-- reporter alleges pattern of misconduct --"),
    
    # V5 STRESS TEST: Additional legal patterns
    (r'\bracial\s+profiling\b',
     "-- reporter characterizes as racial profiling --"),
    (r'\b(clearly\s+)?(illegal|unlawful)\s+(assault|stop|detention)\b',
     "-- reporter characterizes action as illegal --"),
]

# V5: Intent/threat attributions that MUST be attributed
INTENT_SCRUB_PATTERNS = [
    # Threat perceptions
    (r'\bready\s+to\s+(shoot|attack|assault|kill)\s+(me|him|her|them|us)\b',
     "-- reporter perceived threat --"),
    (r'\b(was|were)\s+going\s+to\s+(shoot|attack|kill|hurt)\b',
     "-- reporter perceived intent to harm --"),
    (r'\bwanted\s+to\s+(hurt|harm|kill|intimidate|punish)\b',
     "-- reporter perceived intent --"),
    (r'\btrying\s+to\s+(kill|hurt|harm|intimidate)\b',
     "-- reporter perceived attempt to harm --"),
    
    # Intent attribution
    (r'\b(clearly|obviously|definitely)\s+intended\s+to\b',
     "-- reporter infers intent --"),
    (r'\bdeliberately\s+(tried|attempted|wanted)\b',
     "-- reporter infers deliberate action --"),
    (r'\bintentionally\s+(hurt|harmed|ignored|denied)\b',
     "-- reporter infers intentional action --"),
    
    # Threat characterizations
    (r'\b[Tt]hreat\s+and\s+\w+\s+intimidation\b',
     "-- reporter characterizes as threatening --"),
    (r'\b(was|were)\s+(clearly\s+)?a\s+threat\b',
     "-- reporter perceived as threatening --"),
    (r'\bthreatening\s+(behavior|manner|tone)\b',
     "-- reporter perceived threatening behavior --"),
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
    (r'\bblue\s+wall\s+of\s+silence\b',
     ""),
    (r'\bcode\s+of\s+silence\b',
     ""),
    (r'\bthugs\s+with\s+badges\b',
     "officers"),
    # V5 STRESS TEST: Additional conspiracy patterns
    (r'\bcover.?up\b',
     "-- reporter alleges cover-up --"),
    (r'\bterrorize\s+(our|the)\s+communit(y|ies)\b',
     "-- reporter characterizes conduct --"),
    (r'\bwhole\s+system\s+is\s+corrupt\b',
     "-- reporter characterizes system --"),
]

# Invective to remove or neutralize
INVECTIVE_SCRUB_PATTERNS = [
    (r'\bthug\s+cop[s]?', "officer"),
    (r'\bdirty\s+cop[s]?', "officer"),
    (r'\bcorrupt\s+cop[s]?', "officer"),
    (r'\bpsychotic', ""),
    (r'\bmaniac', ""),
    (r'\bsadist(ic)?', ""),
    (r'\bmonster', ""),
    (r'\bfascist', ""),
    (r'\bbrutally', ""),
    (r'\bviciously', ""),
    (r'\bsavagely', ""),
    # V5 STRESS TEST: Additional invective patterns  
    (r'\bbrutal,?\s*', ""),  # "brutal, psychotic cops" or "brutal cops"
    (r'\bviolent\s+offender\b', "individual with history"),
    (r'\bcriminal\s+behavior\b', "alleged conduct"),
    (r'\bhorrifying\b', "concerning"),
    (r'\bmenacingly\b', ""),
    (r'\baggressively\b', ""),
    (r'\btorture\b', "treatment"),
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
    
    # V5: Apply intent/threat scrubs
    for pattern, replacement in INTENT_SCRUB_PATTERNS:
        new_text, count = re.subn(pattern, replacement, scrubbed, flags=re.IGNORECASE)
        if count > 0:
            scrubbed = new_text
            scrub_count += count
            log.info("intent_scrub", pattern=pattern[:30], count=count)
    
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
