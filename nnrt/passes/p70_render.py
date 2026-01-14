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
    """
    Render using template-based policy rules.
    
    ARCHITECTURE NOTE (Post-Refactor):
    - Policy rules are the SINGLE source of transformation decisions
    - Context annotations (from p25_annotate_context) inform rule conditions
    - This pass ONLY applies policy decisions, no independent logic
    - span_decisions and protected_ranges enable cross-pass communication
    - neutral_text and applied_rules stored on each segment for traceability
    """
    engine = get_policy_engine()
    
    rendered_segments: list[str] = []
    total_transforms = 0

    for segment in ctx.segments:
        # Apply policy rules WITH segment context
        # The policy engine will:
        # 1. Find matching rules
        # 2. Check rule conditions against segment.contexts
        # 3. Apply only rules whose conditions are met
        rendered, decisions = engine.apply_rules_with_context(
            segment.text, segment.contexts
        )
        total_transforms += len(decisions)
        
        # Store per-segment neutral text for traceability
        cleaned_rendered = _clean_text(rendered)
        if cleaned_rendered != segment.text:
            segment.neutral_text = cleaned_rendered
        
        # Store applied rule IDs for traceability
        segment.applied_rules = [d.rule_id for d in decisions]
        
        # Record decisions for each affected span (for downstream traceability)
        segment_spans = [s for s in ctx.spans if s.segment_id == segment.id]
        for decision in decisions:
            # Find spans that overlap with this decision
            for span in segment_spans:
                if span.id in decision.affected_ids:
                    ctx.set_span_decision(span.id, decision)
        
        # Add to combined output
        if cleaned_rendered.strip():
            rendered_segments.append(cleaned_rendered)

    ctx.rendered_text = " ".join(rendered_segments)
    
    ctx.add_trace(
        pass_name=PASS_NAME,
        action="rendered_template",
        after=f"{len(rendered_segments)} segments, {total_transforms} policy transforms",
    )

    return ctx


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

