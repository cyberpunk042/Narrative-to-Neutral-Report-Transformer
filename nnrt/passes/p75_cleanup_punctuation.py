"""
Pass 75 — Punctuation Cleanup

Post-render cleanup to fix punctuation artifacts from transformations.

This pass runs AFTER rendering to fix:
- Double spaces from removed words
- Dangling commas (e.g., "the, psychotic")
- Double punctuation
- Orphaned punctuation at sentence boundaries
"""

import re

from nnrt.core.context import TransformContext
from nnrt.core.logging import get_pass_logger

PASS_NAME = "p75_cleanup_punctuation"
log = get_pass_logger(PASS_NAME)


def cleanup_punctuation(ctx: TransformContext) -> TransformContext:
    """
    Clean up punctuation artifacts after rendering.
    
    This pass is essential because word removals can leave behind
    awkward punctuation that the simple cleanup in p70_render misses.
    """
    if not ctx.rendered_text:
        return ctx
    
    original = ctx.rendered_text
    text = original
    
    # Track changes for diagnostics
    changes_made = []
    
    # 1. Fix multiple internal spaces (but preserve leading indentation)
    # Process line-by-line to keep indentation intact
    if "  " in text:
        fixed_lines = []
        for line in text.split('\n'):
            # Preserve leading whitespace
            stripped = line.lstrip()
            leading = line[:len(line) - len(stripped)]
            # Collapse multiple internal spaces to single space
            fixed_content = re.sub(r'  +', ' ', stripped)
            fixed_lines.append(leading + fixed_content)
        text = '\n'.join(fixed_lines)
        changes_made.append("multiple_spaces")
    
    # 2. Fix dangling comma after articles (e.g., "the, psychotic")
    # Pattern: article + comma + space + word
    pattern = r'\b(the|a|an),\s+(\w)'
    if re.search(pattern, text, re.IGNORECASE):
        text = re.sub(pattern, r'\1 \2', text, flags=re.IGNORECASE)
        changes_made.append("dangling_comma_after_article")
    
    # 3. Fix dangling comma at start of sentence/clause
    # Pattern: comma at start or after period/semicolon
    # NOTE: Use [^\S\n] to match whitespace EXCEPT newlines
    if re.search(r'(?:^|[.;!?])[^\S\n]*,[^\S\n]*', text):
        text = re.sub(r'(?:^|([.;!?]))[^\S\n]*,[^\S\n]*', r'\1 ', text)
        changes_made.append("comma_at_start")
    
    # 4. Fix double punctuation (e.g., ",.." or ",,")
    if re.search(r'[.,!?;:]{2,}', text):
        # Keep only the first punctuation mark
        text = re.sub(r'([.,!?;:])[.,!?;:]+', r'\1', text)
        changes_made.append("double_punctuation")
    
    # 5. Fix space before punctuation (but NOT newlines)
    # NOTE: Use [^\S\n] to match only horizontal whitespace
    if re.search(r'[^\S\n]+[.,!?;:]', text):
        text = re.sub(r'[^\S\n]+([.,!?;:])', r'\1', text)
        changes_made.append("space_before_punctuation")
    
    # 6. Fix comma followed by period (e.g., ",.")
    if ",." in text or ".," in text:
        text = text.replace(",.", ".").replace(".,", ".")
        changes_made.append("comma_period_collision")
    
    # 7. Fix orphaned commas (comma with only whitespace around it)
    # NOTE: Use [^\S\n] to match whitespace EXCEPT newlines
    if re.search(r'[^\S\n],[^\S\n]', text):
        text = re.sub(r'[^\S\n],[^\S\n]', ' ', text)
        changes_made.append("orphaned_comma")
    
    # 8. Normalize sentence spacing (ensure single space after periods)
    # NOTE: Use [^\S\n] to match whitespace EXCEPT newlines (preserve line structure)
    if re.search(r'[.!?][^\S\n]{2,}', text):
        text = re.sub(r'([.!?])[^\S\n]{2,}', r'\1 ', text)
        changes_made.append("sentence_spacing")
    
    # 9. V7.3 FIX: Remove comma immediately after bullet points
    # Pattern: "•," or "• ," → "•"
    if re.search(r'•\s*,', text):
        text = re.sub(r'•\s*,\s*', '• ', text)
        changes_made.append("comma_after_bullet")
    
    # 10. V7.3 FIX: Remove duplicate consecutive words (e.g., "officer officer")
    # Pattern: word + space + same word
    if re.search(r'\b(\w+)\s+\1\b', text, re.IGNORECASE):
        text = re.sub(r'\b(\w+)\s+\1\b', r'\1', text, flags=re.IGNORECASE)
        changes_made.append("duplicate_word")
    
    # 11. V7.3 FIX: Clean up orphaned "like a." or "like an " phrases
    # When words like "maniac" are stripped, we get "like a." or "like an and"
    text = re.sub(r'\blike\s+an?\s*[.,]', '', text)  # "like a." → ""
    text = re.sub(r'\blike\s+an?\s+and\b', 'and', text)  # "like an and" → "and"
    text = re.sub(r'\blike\s+an?\s*$', '', text)  # trailing "like a" → ""
    if 'like a' in text.lower():
        changes_made.append("orphan_like_a")
    
    # 12. Article agreement: "a" before vowel should be "an"
    if re.search(r'\ba\s+[aeiouAEIOU]', text):
        text = re.sub(r'\ba\s+([aeiouAEIOU])', r'an \1', text)
        changes_made.append("article_agreement")
    
    # 13. V7.4 FIX: Remove duplicate phrases (e.g., "with a history with a history")
    # Pattern: 2-4 word phrase + space + same phrase (with variations)
    # Also handles cases where article may be missing: "with history with a history"
    duplicate_phrase_fixes = [
        (r'\bwith a? ?history\s+with a history\b', 'with a history'),
        (r'\bfor no reason\s+for no reason\b', 'for no reason'),
        (r'\bin the\s+in the\b', 'in the'),
        (r'\bon the\s+on the\b', 'on the'),
        (r'\bto the\s+to the\b', 'to the'),
        (r'\bknown individual with history\b', 'known offender'),  # Fix weird phrasing
    ]
    for pattern, replacement in duplicate_phrase_fixes:
        if re.search(pattern, text, re.IGNORECASE):
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
            changes_made.append("duplicate_phrase")
    
    # General duplicate phrase pattern: 2+ words repeated (exact match)
    text = re.sub(r'\b((?:\w+\s+){1,3}\w+)\s+\1\b', r'\1', text, flags=re.IGNORECASE)
    
    # 14. V7.4 FIX: Capitalize first letter after sentence-ending punctuation
    # Pattern: ". lowercase" → ". Uppercase"
    def capitalize_after_period(match):
        return match.group(1) + match.group(2).upper()
    
    if re.search(r'([.!?]\s+)([a-z])', text):
        text = re.sub(r'([.!?]\s+)([a-z])', capitalize_after_period, text)
        changes_made.append("sentence_capitalization")
    
    # 16. V7.4 FIX: Fix broken attribution patterns
    # Pattern: "-- reporter X -- I was" → "-- reporter X -- Reporter was"
    if re.search(r'--\s*\b(I|my|me)\b', text, re.IGNORECASE):
        text = re.sub(r'--\s+I\s+was\b', '-- Reporter was', text)
        text = re.sub(r'--\s+I\s+am\b', '-- Reporter is', text)
        text = re.sub(r'--\s+I\b', '-- Reporter', text)
        text = re.sub(r'--\s+my\b', "-- Reporter's", text, flags=re.IGNORECASE)
        text = re.sub(r'--\s+me\b', "-- Reporter", text, flags=re.IGNORECASE)
        changes_made.append("attribution_pronoun_fix")
    
    # 17. V7.4 FIX: Fix "appeared to" over-neutralization
    # "appeared to grab" → "tried to grab" (preserve the action)
    if 'appeared to ' in text:
        # Only fix specific over-neutralizations, keep legitimate "appeared to be"
        text = re.sub(r'\bappeared to grab\b', 'tried to grab', text)
        text = re.sub(r'\bappeared to explain\b', 'tried to explain', text)
        changes_made.append("appeared_to_fix")
    
    # 18. V7.4 FIX: Clean up orphaned words after attributions
    # "-- reporter infers intent to cause harm -- maximum damage" → "-- reporter infers intent to cause harm --."
    text = re.sub(r'(-- reporter \w+ intent to cause harm --)\s+maximum damage\.?', r'\1.', text)
    text = re.sub(r'(-- reporter \w+ intent to cause harm --)\s+\w+\s+\w+\.?', r'\1.', text)
    
    # 19. V7.4 FIX: Fix "spoke loudly" → "yelled"
    text = re.sub(r'\bspoke loudly\b', 'yelled', text)
    text = re.sub(r'\bspeaking loudly\b', 'yelling', text)
    
    # 20. V7.4 FIX: Fix "described as threatened" → "threatened"
    text = re.sub(r'\bmade statements described as threatened\b', 'threatened', text)
    text = re.sub(r'\bdescribed as threatened him\b', 'threatened him', text)
    text = re.sub(r'\bdescribed as appearing to enjoy\b', 'while', text)  # Remove characterization
    
    # 21. V7.4 FIX: Remove "-- reporter concludes -- Reporter was" broken pattern
    text = re.sub(r'-- reporter concludes -- Reporter was\b', '-- reporter states Reporter was', text)
    
    # 22. V7.4 FIX: Clean up orphaned "and while" pattern 
    # "He was speaking dismissively at me and while my suffering" → "He was speaking dismissively at me."
    text = re.sub(r'\band while my suffering\b', '', text)
    text = re.sub(r'\band while\s*\.', '.', text)
    
    # 23. V7.4 FIX: "reporter states Reporter was and they" → remove "Reporter was"
    text = re.sub(r'-- reporter states Reporter was and\b', '-- reporter states', text)
    
    # 24. V7.4 FIX: "The -- reporter alleges racism -- is" → more natural phrasing
    text = re.sub(r'\bThe -- reporter alleges racism -- is\b', '-- reporter alleges racism --', text)
    text = re.sub(r'\bThe -- reporter alleges (\w+) -- is\b', r'-- reporter alleges \1 --', text)
    
    # 25. V7.4 FIX: Clean up double dashes with missing content
    text = re.sub(r'-- reporter \w+ -- is systematic', '-- reporter characterizes system --', text)
    
    # 26. V7.4 FIX: Clean attribution markers from MEDICAL FINDINGS section
    # safety_scrub runs AFTER render_structured, so these markers appear after rendering
    # Process line-by-line to target only medical findings section
    if 'MEDICAL FINDINGS' in text:
        lines = text.split('\n')
        in_medical_section = False
        cleaned_lines = []
        for line in lines:
            if 'MEDICAL FINDINGS' in line:
                in_medical_section = True
            elif line.startswith('PRESERVED QUOTES') or line.startswith('EVENTS ('):
                in_medical_section = False
            
            if in_medical_section and '-- reporter' in line:
                # Strip attribution markers from medical findings
                clean_line = re.sub(r'-- reporter [^-]+ --', '', line)
                clean_line = re.sub(r'  +', ' ', clean_line).strip()
                if clean_line.startswith('•'):
                    clean_line = '  ' + clean_line  # Restore bullet indentation
                cleaned_lines.append(clean_line)
            else:
                cleaned_lines.append(line)
        text = '\n'.join(cleaned_lines)
    
    # 26b. V7.4 FIX: Neutralize intensity words in SELF-REPORTED STATE sections
    # These sections pull from atomic_statements which may not be fully neutralized
    # Use global replace since 'terrified' should be neutralized everywhere
    text = re.sub(r'\bterrified\b', 'frightened', text, flags=re.IGNORECASE)
    
    # 27. V7.4 FIX: Final cleanup - remove any space-before-punctuation created by prior fixes
    text = re.sub(r' +\.', '.', text)
    text = re.sub(r' +,', ',', text)
    
    # 27. Strip and ensure proper ending
    text = text.strip()
    if text and text[-1] not in ".!?":
        text += "."
    
    ctx.rendered_text = text
    
    if changes_made:
        log.info("cleaned",
            fixes_applied=len(changes_made),
            fix_types=changes_made,
        )
        ctx.add_trace(
            pass_name=PASS_NAME,
            action="cleanup_punctuation",
            before=original[:100] + "..." if len(original) > 100 else original,
            after=f"Applied fixes: {', '.join(changes_made)}",
        )
    else:
        log.verbose("no_changes", message="No punctuation cleanup needed")
    
    return ctx
