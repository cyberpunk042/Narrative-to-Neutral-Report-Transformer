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
# V7: ORDER MATTERS - compound phrases FIRST to prevent partial matches
LEGAL_SCRUB_PATTERNS = [
    # =========================================================================
    # COMPOUND PHRASES - Match FIRST to prevent partial matches
    # =========================================================================
    (r'\b[Tt]his\s+was\s+(clearly\s+)?racial\s+profiling\s+and\s+harassment\b',
     "-- reporter characterizes conduct as racial profiling and harassment --"),
    (r'\bracial\s+profiling\s+and\s+harassment\b',
     "-- reporter characterizes conduct as racial profiling and harassment --"),
    (r'\b[Tt]his\s+was\s+(clearly\s+)?(a\s+)?threat\s+and\s+witness\s+intimidation\b',
     "-- reporter characterizes as threat and witness intimidation --"),
    (r'\bassault\s+and\s+battery\b',
     "-- reporter alleges assault and battery --"),
    (r'\bobstruction\s+of\s+justice\s+and\s+(witness\s+)?intimidation\b',
     "-- reporter alleges obstruction of justice and intimidation --"),
    
    # =========================================================================
    # FULL SENTENCE PATTERNS - Match before fragments
    # =========================================================================
    (r'\b[Tt]his\s+was\s+(clearly\s+)?racial\s+profiling\b',
     "-- reporter characterizes the stop as racial profiling --"),
    (r'\b[Tt]his\s+was\s+(clearly\s+)?police\s+brutality\b',
     "-- reporter characterizes conduct as police brutality --"),
    (r'\b[Tt]his\s+(was\s+)?(clearly\s+)?a\s+threat\b',
     "-- reporter perceived as threatening --"),
    
    # =========================================================================
    # SINGLE LEGAL TERMS - Match last (only if not already matched above)
    # =========================================================================
    (r'\bpolice\s+brutality\b',
     "-- reporter characterizes conduct as brutality --"),
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
    (r'\bwrongful\s+(termination|arrest|detention)\b',
     "-- reporter characterizes as wrongful --"),
    # Note: standalone "harassment" and "racial profiling" moved to end
    
    # =========================================================================
    # SYSTEMIC CLAIMS - attributed
    # =========================================================================
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
    
    # =========================================================================
    # STANDALONE TERMS - Match LAST (only if not already matched above)
    # =========================================================================
    (r'\bracial\s+profiling\b',
     "-- reporter characterizes as racial profiling --"),
    (r'\bharassment\b',
     "-- reporter characterizes conduct as harassment --"),
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
    # V7.2 FIX: Use proper attribution instead of removing entirely
    (r'\bmassive\s+cover.?up',
     "-- reporter alleges cover-up --"),
    (r'\bwhitewash',
     "-- reporter alleges cover-up --"),
    (r'\bblue\s+wall\s+of\s+silence\b',
     "-- reporter alleges systemic silence --"),
    (r'\bcode\s+of\s+silence\b',
     "-- reporter alleges systemic silence --"),
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
    # Preserve plural forms: "thug cops" → "officers", "thug cop" → "officer"
    (r'\bthug\s+cops\b', "officers"),
    (r'\bthug\s+cop\b', "officer"),
    (r'\bdirty\s+cops\b', "officers"),
    (r'\bdirty\s+cop\b', "officer"),
    (r'\bcorrupt\s+cops\b', "officers"),
    (r'\bcorrupt\s+cop\b', "officer"),
    (r'\bviolent\s+cops\b', "officers"),
    (r'\bviolent\s+cop\b', "officer"),
    (r'\bpsychotic\s*,?\s*', ""),  # Remove with possible trailing comma/space
    (r'\bmaniac\s*', ""),
    (r'\bsadist(ic)?\s*', ""),
    (r'\bmonster\s*', ""),
    (r'\bfascist\s*', ""),
    (r'\bbrutally\s*', ""),
    (r'\bviciously\s*', ""),
    (r'\bsavagely\s*', ""),
    # V5 STRESS TEST: Additional invective patterns  
    # V7.2 FIX: Added \b at end to prevent matching 'brutal' inside 'brutality'
    (r'\bbrutal\b,?\s*', ""),  # "brutal, psychotic cops" or "brutal cops"
    (r'\bviolent\s+offender\b', "individual with history"),
    (r'\bcriminal\s+behavior\b', "alleged conduct"),
    (r'\bhorrifying\b', "concerning"),
    (r'\bmenacingly\b', ""),
    (r'\baggressively\b', "in a manner described as aggressive"),
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
    
    def attribution_aware_sub(pattern, replacement, text):
        """
        V7: Substitute pattern with replacement, but SKIP text already inside
        attribution markers (--...--) to prevent nested attributions.
        """
        # Split text into attributed and non-attributed segments
        result = []
        pos = 0
        count = 0
        
        # Find all attribution spans first
        attribution_spans = []
        for m in re.finditer(r'--[^-]+--', text):
            attribution_spans.append((m.start(), m.end()))
        
        def is_inside_attribution(start, end):
            for attr_start, attr_end in attribution_spans:
                if start >= attr_start and end <= attr_end:
                    return True
            return False
        
        # Now find all pattern matches and only substitute those outside attributions
        last_end = 0
        for m in re.finditer(pattern, text, re.IGNORECASE):
            if not is_inside_attribution(m.start(), m.end()):
                result.append(text[last_end:m.start()])
                result.append(replacement)
                last_end = m.end()
                count += 1
            # If inside attribution, skip (include original text later)
        
        result.append(text[last_end:])
        return ''.join(result), count
    
    # Apply legal scrubs
    for pattern, replacement in LEGAL_SCRUB_PATTERNS:
        new_text, count = attribution_aware_sub(pattern, replacement, scrubbed)
        if count > 0:
            scrubbed = new_text
            scrub_count += count
            log.info("legal_scrub", pattern=pattern[:30], count=count)

    
    # V5: Apply intent/threat scrubs (with attribution-aware substitution)
    for pattern, replacement in INTENT_SCRUB_PATTERNS:
        new_text, count = attribution_aware_sub(pattern, replacement, scrubbed)
        if count > 0:
            scrubbed = new_text
            scrub_count += count
            log.info("intent_scrub", pattern=pattern[:30], count=count)
    
    # Apply conspiracy scrubs (with attribution-aware substitution)
    for pattern, replacement in CONSPIRACY_SCRUB_PATTERNS:
        new_text, count = attribution_aware_sub(pattern, replacement, scrubbed)
        if count > 0:
            scrubbed = new_text
            scrub_count += count
            log.info("conspiracy_scrub", pattern=pattern[:30], count=count)
    
    # Apply invective scrubs (these use simple re.subn since they don't add attributions)
    for pattern, replacement in INVECTIVE_SCRUB_PATTERNS:
        new_text, count = re.subn(pattern, replacement, scrubbed, flags=re.IGNORECASE)
        if count > 0:
            scrubbed = new_text
            scrub_count += count
            log.info("invective_scrub", pattern=pattern[:30], count=count)
    
    # Always clean up artifacts (article agreement, double spaces, etc.)
    # This must run even if no scrubs were applied, since policy may have
    # created issues like "an person" (when "innocent" was removed)
    scrubbed = _clean_artifacts(scrubbed)
    
    # Always update the rendered text with the cleaned version
    ctx.rendered_text = scrubbed
    
    if scrub_count > 0:
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
    
    # NOTE: Removed global double-space replacement here.
    # It was destroying leading indentation (e.g., "  • bullet" -> " • bullet").
    # Internal double spaces are handled in the line-by-line processing below.
    
    # Remove orphaned punctuation
    result = result.replace(" .", ".").replace(" ,", ",")
    result = result.replace(".,", ".").replace(",.", ".")
    
    # Remove empty parentheses/brackets
    result = re.sub(r'\(\s*\)', '', result)
    result = re.sub(r'\[\s*\]', '', result)
    
    # Remove leftover "-- --" patterns
    result = re.sub(r'--\s*--', '', result)
    
    # V7: Fix nested attributions - multiple "--" patterns in same sentence
    # Pattern: "-- reporter X -- reporter Y --" -> "-- reporter X; reporter Y --"
    # Or simply collapse to first attribution
    while True:
        # Find patterns like "-- something -- --" (nested/broken)
        match = re.search(r'--\s*([^-]+?)\s*--\s*--\s*([^-]+?)\s*--', result)
        if match:
            # Combine into single attribution
            combined = f"-- {match.group(1).strip()}; {match.group(2).strip()} --"
            result = result[:match.start()] + combined + result[match.end():]
        else:
            break
    
    # Fix patterns like "-- reporter X as -- reporter Y --" (mid-attribution break)
    result = re.sub(
        r'--\s*(reporter\s+\w+)\s+as\s*--\s*(reporter[^-]+)--',
        r'-- \2--',
        result,
        flags=re.IGNORECASE
    )
    
    # Fix "described as described as" duplication
    result = re.sub(r'\bdescribed as\s+described as\b', 'described as', result, flags=re.IGNORECASE)
    
    # Fix "characterized as characterized as" etc
    result = re.sub(r'\b(characterized|perceived|reported)\s+as\s+\1\s+as\b', r'\1 as', result, flags=re.IGNORECASE)
    
    # Fix article agreement: "an person" → "a person", "a individual" → "an individual"
    # When a word is removed, we may have wrong article
    result = re.sub(r'\ban\s+([bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ])', r'a \1', result)
    result = re.sub(r'\ba\s+([aeiouAEIOU])', r'an \1', result)
    
    # Remove leftover broken attributions (empty or whitespace only)
    result = re.sub(r'--\s+--', '', result)
    
    # Trim extra whitespace on each line, but PRESERVE newlines AND leading indentation
    # The old code used ' '.join(result.split()) which destroys all newlines
    # Then we used ' '.join(line.split()) which destroys leading indentation
    lines = result.split('\n')
    cleaned_lines = []
    for line in lines:
        # Preserve leading whitespace (indentation/centering)
        stripped = line.lstrip()
        if not stripped:
            # Empty or whitespace-only line
            cleaned_lines.append('')
        else:
            leading_ws = line[:len(line) - len(stripped)]
            # Collapse multiple internal spaces to single space, but keep leading
            cleaned_content = ' '.join(stripped.split())
            cleaned_lines.append(leading_ws + cleaned_content)
    result = '\n'.join(cleaned_lines)
    
    # Remove excessive blank lines (more than 2 in a row)
    result = re.sub(r'\n{3,}', '\n\n', result)
    result = result.strip()
    
    return result
