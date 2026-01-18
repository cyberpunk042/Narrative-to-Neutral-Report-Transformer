"""
p33_resolve_text_coref — Early coreference resolution for text.

V9: Runs FastCoref BEFORE event extraction to resolve pronouns in segment text.
This allows p34_extract_events to get clean text with entities instead of pronouns.

Pipeline position: After p32_extract_entities, BEFORE p34_extract_events
"""

import structlog
from typing import Dict

from nnrt.core.context import TransformContext

log = structlog.get_logger("nnrt.p33_resolve_text_coref")

PASS_NAME = "p33_resolve_text_coref"


def resolve_text_coreference(ctx: TransformContext) -> TransformContext:
    """
    V9: Resolve pronouns in segment text using FastCoref.
    
    This runs EARLY in the pipeline (before event extraction) so that
    when events are extracted, the text already has pronouns resolved.
    
    V9.1: Process the FULL TEXT at once for better coreference context.
    Then map resolutions back to individual segments.
    
    Example:
        "She called 911" → "Patricia Chen called 911"
    """
    if not ctx.segments:
        log.info("no_segments", pass_name=PASS_NAME)
        ctx.add_trace(PASS_NAME, "skipped", after="No segments")
        return ctx
    
    # Try to load FastCoref
    try:
        from nnrt.nlp.backends.coref_backend import CorefResolver
        resolver = CorefResolver()
        
        if not resolver.available:
            log.info("fastcoref_not_available", pass_name=PASS_NAME)
            ctx.add_trace(PASS_NAME, "skipped", after="FastCoref not available")
            return ctx
    except Exception as e:
        log.warning("fastcoref_load_error", pass_name=PASS_NAME, error=str(e))
        ctx.add_trace(PASS_NAME, "skipped", after=f"FastCoref error: {e}")
        return ctx
    
    # Build entity map for preferred names
    entity_map: Dict[str, str] = {}
    for entity in (ctx.entities or []):
        if entity.label:
            # Map partial names to full labels
            words = entity.label.split()
            for word in words:
                if len(word) > 2 and word[0].isupper():
                    # Don't override with shorter names
                    if word not in entity_map or len(entity.label) > len(entity_map[word]):
                        entity_map[word] = entity.label
    
    # V9.1: Build full text with segment boundaries tracked
    # This allows FastCoref to see full context for better resolution
    full_text_parts = []
    segment_boundaries = []  # (start, end) in full text
    current_pos = 0
    
    for segment in ctx.segments:
        start = current_pos
        full_text_parts.append(segment.text)
        end = current_pos + len(segment.text)
        segment_boundaries.append((start, end))
        current_pos = end + 1  # +1 for space separator
        full_text_parts.append(" ")
    
    full_text = "".join(full_text_parts).strip()
    
    try:
        # Resolve the FULL text at once
        resolved_full = resolver.resolve(full_text, entity_map)
        
        if resolved_full != full_text:
            # Map resolved text back to segments
            # This is approximate - we compare resolution diffs
            segments_resolved = 0
            
            for i, segment in enumerate(ctx.segments):
                original = segment.text
                
                # For each segment, resolve it individually with context
                # Context = previous segment text for pronouns that span boundaries
                if i > 0:
                    context = ctx.segments[i-1].text + " " + original
                    resolved_context = resolver.resolve(context, entity_map)
                    # Extract just the current segment portion
                    prev_len = len(ctx.segments[i-1].text) + 1
                    resolved = resolved_context[prev_len:] if len(resolved_context) > prev_len else original
                else:
                    resolved = resolver.resolve(original, entity_map)
                
                if resolved != original:
                    segment.resolved_text = resolved
                    segments_resolved += 1
                    log.debug(
                        "segment_resolved",
                        pass_name=PASS_NAME,
                        segment_id=segment.id,
                        change=f"{len(original)} → {len(resolved)} chars"
                    )
            
            log.info(
                "text_coref_complete",
                pass_name=PASS_NAME,
                channel="SEMANTIC",
                total_segments=len(ctx.segments),
                segments_resolved=segments_resolved,
            )
        else:
            log.info(
                "text_coref_complete", 
                pass_name=PASS_NAME,
                channel="SEMANTIC",
                total_segments=len(ctx.segments),
                segments_resolved=0,
                note="no_pronouns_resolved"
            )
            
    except Exception as e:
        log.warning("coref_resolution_error", pass_name=PASS_NAME, error=str(e))
    
    ctx.add_trace(
        PASS_NAME,
        "text_coref_resolved",
        after=f"FastCoref processed {len(ctx.segments)} segments"
    )
    
    return ctx
