"""
Pass 70 — Constrained Rendering

Renders the IR into neutral narrative text.

This pass now uses the policy engine to apply transformations
based on YAML-defined rules. It also supports span-based
transformations for NLP-detected content.

The generator can ONLY render what the IR contains.
It cannot add meaning, resolve ambiguity, or infer intent.
"""

from nnrt.core.context import TransformContext
from nnrt.ir.enums import SpanLabel
from nnrt.policy.engine import get_policy_engine

PASS_NAME = "p70_render"


def render(ctx: TransformContext) -> TransformContext:
    """
    Render IR to neutral text using policy rules.
    
    This pass:
    - Applies policy rules from YAML configuration
    - Handles span-based transformations from NLP
    - Cleans up artifacts from transformations
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

    # Get policy engine
    engine = get_policy_engine()
    
    rendered_segments: list[str] = []
    total_rule_transforms = 0
    total_span_transforms = 0

    for segment in ctx.segments:
        # Apply policy rules
        rendered, decisions = engine.apply_rules(segment.text)
        total_rule_transforms += len(decisions)
        
        # Apply span-based transformations for content not caught by rules
        segment_spans = [s for s in ctx.spans if s.segment_id == segment.id]
        for span in segment_spans:
            if span.label == SpanLabel.LEGAL_CONCLUSION:
                # Remove legal conclusions not caught by rules
                if span.text in rendered:
                    rendered = _remove_phrase(rendered, span.text)
                    total_span_transforms += 1
                    ctx.add_trace(
                        pass_name=PASS_NAME,
                        action="removed_legal_conclusion",
                        before=span.text,
                        affected_ids=[span.id],
                    )
            
            elif span.label == SpanLabel.INTENT_ATTRIBUTION:
                # Handle intent not caught by rules
                if span.text in rendered:
                    replacement = _get_intent_replacement(span.text)
                    if replacement is not None:
                        rendered = rendered.replace(span.text, replacement)
                        total_span_transforms += 1
                        ctx.add_trace(
                            pass_name=PASS_NAME,
                            action="neutralized_intent",
                            before=span.text,
                            after=replacement or "(removed)",
                            affected_ids=[span.id],
                        )
        
        # Clean up artifacts
        rendered = _clean_text(rendered)
        
        if rendered.strip():
            rendered_segments.append(rendered)

    # Join segments
    ctx.rendered_text = " ".join(rendered_segments)
    
    ctx.add_trace(
        pass_name=PASS_NAME,
        action="rendered",
        after=f"{len(rendered_segments)} segments, {total_rule_transforms} rule transforms, {total_span_transforms} span transforms",
    )

    return ctx


def _remove_phrase(text: str, phrase: str) -> str:
    """Remove a phrase from text, cleaning up whitespace."""
    result = text.replace(phrase, "")
    while "  " in result:
        result = result.replace("  ", " ")
    return result.strip()


def _get_intent_replacement(phrase: str) -> str | None:
    """Get a neutral replacement for intent attribution phrases."""
    phrase_lower = phrase.lower()
    
    replacements = {
        "intentionally": "",
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
    
    return None


def _clean_text(text: str) -> str:
    """Clean up artifacts from transformations."""
    result = text
    
    # Remove double spaces
    while "  " in result:
        result = result.replace("  ", " ")
    
    # Remove orphaned punctuation
    result = result.replace(" .", ".").replace(" ,", ",")
    
    # Fix common grammar issues from removals
    result = result.replace("He  ", "He ").replace("She  ", "She ")
    
    # Trim
    result = result.strip()
    
    # Ensure proper sentence ending
    if result and result[-1] not in ".!?":
        result += "."
    
    return result
