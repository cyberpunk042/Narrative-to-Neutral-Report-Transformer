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

PASS_NAME = "p75_cleanup_punctuation"


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
    
    # 1. Fix multiple spaces
    if "  " in text:
        text = re.sub(r'  +', ' ', text)
        changes_made.append("multiple_spaces")
    
    # 2. Fix dangling comma after articles (e.g., "the, psychotic")
    # Pattern: article + comma + space + word
    pattern = r'\b(the|a|an),\s+(\w)'
    if re.search(pattern, text, re.IGNORECASE):
        text = re.sub(pattern, r'\1 \2', text, flags=re.IGNORECASE)
        changes_made.append("dangling_comma_after_article")
    
    # 3. Fix dangling comma at start of sentence/clause
    # Pattern: comma at start or after period/semicolon
    if re.search(r'(?:^|[.;!?])\s*,\s*', text):
        text = re.sub(r'(?:^|([.;!?]))\s*,\s*', r'\1 ', text)
        changes_made.append("comma_at_start")
    
    # 4. Fix double punctuation (e.g., ",.." or ",,")
    if re.search(r'[.,!?;:]{2,}', text):
        # Keep only the first punctuation mark
        text = re.sub(r'([.,!?;:])[.,!?;:]+', r'\1', text)
        changes_made.append("double_punctuation")
    
    # 5. Fix space before punctuation
    if re.search(r'\s+[.,!?;:]', text):
        text = re.sub(r'\s+([.,!?;:])', r'\1', text)
        changes_made.append("space_before_punctuation")
    
    # 6. Fix comma followed by period (e.g., ",.")
    if ",." in text or ".," in text:
        text = text.replace(",.", ".").replace(".,", ".")
        changes_made.append("comma_period_collision")
    
    # 7. Fix orphaned commas (comma with only whitespace around it)
    if re.search(r'\s,\s', text):
        text = re.sub(r'\s,\s', ' ', text)
        changes_made.append("orphaned_comma")
    
    # 8. Normalize sentence spacing (ensure single space after periods)
    if re.search(r'[.!?]\s{2,}', text):
        text = re.sub(r'([.!?])\s{2,}', r'\1 ', text)
        changes_made.append("sentence_spacing")
    # 9. Fix article agreement: "a" before vowel should be "an"
    if re.search(r'\ba\s+[aeiouAEIOU]', text):
        text = re.sub(r'\ba\s+([aeiouAEIOU])', r'an \1', text)
        changes_made.append("article_agreement")
    
    # 10. Strip and ensure proper ending
    text = text.strip()
    if text and text[-1] not in ".!?":
        text += "."
    
    ctx.rendered_text = text
    
    if changes_made:
        ctx.add_trace(
            pass_name=PASS_NAME,
            action="cleanup_punctuation",
            before=original[:100] + "..." if len(original) > 100 else original,
            after=f"Applied fixes: {', '.join(changes_made)}",
        )
    
    return ctx
