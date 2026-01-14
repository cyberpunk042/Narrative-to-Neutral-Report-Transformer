"""
Pass 70 — Constrained Rendering

Renders the IR into neutral narrative text.

Supports two modes:
1. Template-based (default): Fast, deterministic, uses policy rules
2. LLM-based (optional): More fluent, uses constrained Flan-T5

Per LLM policy:
- Generator input is IR ONLY, never raw input text
- LLM proposes candidates, does not decide
- All outputs are validated before use
- Fallback to template if LLM fails validation
"""

import os
from nnrt.core.context import TransformContext
from nnrt.ir.enums import SpanLabel
from nnrt.policy.engine import get_policy_engine

PASS_NAME = "p70_render"


def _use_llm_render() -> bool:
    """Check if LLM rendering is enabled (checked at runtime)."""
    return os.environ.get("NNRT_USE_LLM", "").lower() in ("1", "true", "yes")


def render(ctx: TransformContext) -> TransformContext:
    """
    Render IR to neutral text.
    
    Mode selection:
    - Set NNRT_USE_LLM=1 to enable LLM rendering
    - Default is template-based rendering
    """
    if not ctx.segments:
        ctx.rendered_text = ""
        ctx.add_trace(
            pass_name=PASS_NAME,
            action="render_empty",
            after="No segments to render",
        )
        return ctx

    if _use_llm_render() and _llm_available():
        return _render_llm(ctx)
    else:
        return _render_template(ctx)


def _llm_available() -> bool:
    """Check if LLM rendering is available."""
    try:
        from nnrt.render.constrained import is_available
        return is_available()
    except ImportError:
        return False


def _render_llm(ctx: TransformContext) -> TransformContext:
    """Render using constrained LLM."""
    from nnrt.render.constrained import ConstrainedLLMRenderer
    
    renderer = ConstrainedLLMRenderer()
    rendered_segments: list[str] = []
    
    for segment in ctx.segments:
        # Get related IR components
        segment_spans = [s for s in ctx.spans if s.segment_id == segment.id]
        segment_entities = [e for e in ctx.entities if any(
            m in [s.id for s in segment_spans] for m in e.mentions
        )]
        segment_events = [e for e in ctx.events if any(
            s in [sp.id for sp in segment_spans] for s in e.source_spans
        )]
        
        # First apply policy rules to get fallback
        engine = get_policy_engine()
        fallback_text, _ = engine.apply_rules(segment.text)
        
        # Then render with LLM (falls back if validation fails)
        rendered = renderer.render(
            segment=segment,
            spans=segment_spans,
            entities=segment_entities,
            events=segment_events,
            fallback_text=fallback_text,
        )
        
        rendered = _clean_text(rendered)
        if rendered.strip():
            rendered_segments.append(rendered)
    
    ctx.rendered_text = " ".join(rendered_segments)
    ctx.add_trace(
        pass_name=PASS_NAME,
        action="rendered_llm",
        after=f"{len(rendered_segments)} segments via LLM",
    )
    
    return ctx


def _render_template(ctx: TransformContext) -> TransformContext:
    """Render using template-based policy rules."""
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
            # NEW: Check if span is protected or has a decision already
            if ctx.is_protected(segment.id, span.start_char, span.end_char):
                continue  # Protected - skip transformation
            
            existing_decision = ctx.get_span_decision(span.id)
            if existing_decision and existing_decision.action.value == "preserve":
                continue  # Policy said preserve - skip
            
            if span.label == SpanLabel.LEGAL_CONCLUSION:
                # REFACTORED: Use context annotation instead of re-analyzing
                # SegmentContext.CHARGE_DESCRIPTION = "charge"
                is_charge_context = "charge" in segment.contexts
                
                if span.text in rendered and not is_charge_context:
                    rendered = _remove_phrase(rendered, span.text)
                    total_span_transforms += 1
                    ctx.add_trace(
                        pass_name=PASS_NAME,
                        action="removed_legal_conclusion",
                        before=span.text,
                        affected_ids=[span.id],
                    )
            
            elif span.label == SpanLabel.INTENT_ATTRIBUTION:
                # REFACTORED: Check for physical attempt context
                # SegmentContext.PHYSICAL_ATTEMPT = "physical_attempt"
                is_physical_attempt = "physical_attempt" in segment.contexts
                
                if is_physical_attempt:
                    # Physical attempt (tried to say/breathe) - preserve
                    continue
                
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
        
        rendered = _clean_text(rendered)
        if rendered.strip():
            rendered_segments.append(rendered)

    ctx.rendered_text = " ".join(rendered_segments)
    
    ctx.add_trace(
        pass_name=PASS_NAME,
        action="rendered_template",
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
    
    # Physical action words - if "tried to" is followed by these, preserve it
    physical_actions = [
        "say", "speak", "talk", "call", "shout", "yell",
        "breathe", "move", "run", "walk", "stand", "sit",
        "open", "close", "grab", "reach", "pull", "push",
        "get up", "get away", "get out",
    ]
    
    # Check if this is a physical attempt (not intent attribution)
    if "tried to" in phrase_lower or "trying to" in phrase_lower:
        for action in physical_actions:
            if action in phrase_lower:
                return None  # Preserve - this is a physical attempt, not intent
    
    replacements = {
        "intentionally": "",
        "deliberately": "",
        "purposely": "",
        "on purpose": "",
        "wanted to": "appeared to",
        "meant to": "appeared to",
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
