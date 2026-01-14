"""
Pass 70 — Constrained Rendering

Renders the IR into neutral narrative text.

This pass uses template-based rendering to produce neutral output:
- Transforms interpretive language to observational
- Removes legal conclusions
- Preserves factual content
- Maintains first-person perspective

The generator can ONLY render what the IR contains.
It cannot add meaning, resolve ambiguity, or infer intent.
"""

from nnrt.core.context import TransformContext
from nnrt.ir.enums import SpanLabel, EventType

PASS_NAME = "p70_render"

# Neutral reframings for common interpretive phrases
NEUTRAL_REFRAMINGS = {
    "suspicious": "described as suspicious",
    "aggressive": "described as aggressive",
    "threatening": "described as threatening",
    "hostile": "described as hostile",
    "intimidating": "described as intimidating",
    "clearly": "",  # Remove intensifier
    "obviously": "",
    "definitely": "",
    "certainly": "",
}

# Templates for neutral rendering by event type
EVENT_TEMPLATES = {
    EventType.ACTION: "{actor} {verb} {target}",
    EventType.VERBAL: "{actor} {verb}",
    EventType.MOVEMENT: "{actor} {verb}",
    EventType.OBSERVATION: "It was observed that {description}",
    EventType.STATE_CHANGE: "{actor} {verb}",
}


def render(ctx: TransformContext) -> TransformContext:
    """
    Render IR to neutral text.
    
    This pass:
    - Transforms each segment based on span tags
    - Removes or reframes problematic content
    - Preserves observations and factual statements
    - Produces reviewable neutral output
    """
    if not ctx.segments:
        ctx.rendered_text = ""
        ctx.add_trace(
            pass_name=PASS_NAME,
            action="render_empty",
            after="No segments to render",
        )
        return ctx

    rendered_segments: list[str] = []
    transformations = 0

    for segment in ctx.segments:
        # Get spans for this segment
        segment_spans = [s for s in ctx.spans if s.segment_id == segment.id]
        
        # Start with original text
        rendered = segment.text
        
        # Check for problematic spans and transform
        for span in segment_spans:
            if span.label == SpanLabel.LEGAL_CONCLUSION:
                # Remove or flag legal conclusions
                rendered = _remove_phrase(rendered, span.text)
                transformations += 1
                ctx.add_trace(
                    pass_name=PASS_NAME,
                    action="removed_legal_conclusion",
                    before=span.text,
                    affected_ids=[span.id],
                )
            
            elif span.label == SpanLabel.INTENT_ATTRIBUTION:
                # Replace intent attribution with neutral observation
                neutral_replacement = _get_neutral_replacement(span.text)
                if neutral_replacement:
                    rendered = rendered.replace(span.text, neutral_replacement)
                else:
                    rendered = _remove_phrase(rendered, span.text)
                transformations += 1
                ctx.add_trace(
                    pass_name=PASS_NAME,
                    action="neutralized_intent_attribution",
                    before=span.text,
                    after=neutral_replacement or "(removed)",
                    affected_ids=[span.id],
                )
            
            elif span.label == SpanLabel.INTERPRETATION:
                # Reframe interpretive language
                new_text = _reframe_interpretation(span.text)
                if new_text != span.text:
                    rendered = rendered.replace(span.text, new_text)
                    transformations += 1
                    ctx.add_trace(
                        pass_name=PASS_NAME,
                        action="reframed_interpretation",
                        before=span.text,
                        after=new_text,
                        affected_ids=[span.id],
                    )
            
            elif span.label == SpanLabel.INFLAMMATORY:
                # Neutralize inflammatory language
                new_text = _neutralize_inflammatory(span.text)
                if new_text != span.text:
                    rendered = rendered.replace(span.text, new_text)
                    transformations += 1

        # Apply general neutralization
        rendered = _apply_neutral_reframings(rendered)
        
        # Clean up any double spaces or artifacts
        rendered = _clean_text(rendered)
        
        if rendered.strip():
            rendered_segments.append(rendered)

    # Join segments
    ctx.rendered_text = " ".join(rendered_segments)
    
    ctx.add_trace(
        pass_name=PASS_NAME,
        action="rendered",
        after=f"{len(rendered_segments)} segments, {transformations} transformations",
    )

    return ctx


def _remove_phrase(text: str, phrase: str) -> str:
    """Remove a phrase from text, cleaning up whitespace."""
    result = text.replace(phrase, "")
    # Clean up double spaces
    while "  " in result:
        result = result.replace("  ", " ")
    return result.strip()


def _get_neutral_replacement(phrase: str) -> str:
    """Get a neutral replacement for intent attribution phrases."""
    phrase_lower = phrase.lower()
    
    # Intent phrases with grammatically correct replacements
    replacements = {
        "intentionally": "",  # Just remove
        "deliberately": "",
        "purposely": "",
        "on purpose": "",
        "tried to": "appeared to",
        "wanted to": "appeared to",
        "meant to": "appeared to",
        "was trying to": "appeared to",
        "clearly wanted to": "appeared to",
    }
    
    for intent_phrase, replacement in replacements.items():
        if intent_phrase in phrase_lower:
            return replacement
    
    return ""  # No replacement found, will remove


def _reframe_interpretation(text: str) -> str:
    """Reframe interpretive language to be more observational."""
    result = text
    
    # Add "appeared to" or "seemed to" for strong statements
    for word in ["clearly", "obviously", "definitely"]:
        if word in result.lower():
            result = result.replace(word, "").replace(word.capitalize(), "")
    
    return result.strip()


def _neutralize_inflammatory(text: str) -> str:
    """Neutralize inflammatory language."""
    result = text.lower()
    
    replacements = {
        "brutality": "use of force",
        "attacked": "made contact with",
        "assaulted": "made physical contact with",
        "abuse": "conduct",
    }
    
    for old, new in replacements.items():
        if old in result:
            result = result.replace(old, new)
            # Preserve original case for start of sentence
            if text[0].isupper():
                result = result[0].upper() + result[1:]
    
    return result


def _apply_neutral_reframings(text: str) -> str:
    """Apply neutral reframings for common interpretive words."""
    result = text
    
    for original, replacement in NEUTRAL_REFRAMINGS.items():
        # Case-insensitive replacement
        import re
        pattern = re.compile(re.escape(original), re.IGNORECASE)
        if replacement:
            result = pattern.sub(replacement, result)
        else:
            # Remove the word
            result = pattern.sub("", result)
    
    return result


def _clean_text(text: str) -> str:
    """Clean up artifacts from transformations."""
    result = text
    
    # Remove double spaces
    while "  " in result:
        result = result.replace("  ", " ")
    
    # Remove orphaned punctuation
    result = result.replace(" .", ".").replace(" ,", ",")
    
    # Trim
    result = result.strip()
    
    # Ensure proper sentence ending
    if result and result[-1] not in ".!?":
        result += "."
    
    return result
