"""
p44_timeline_v6 — V6 Enhanced Timeline Reconstruction.

This module provides a unified interface to the V6 timeline pipeline:
- p44a: Temporal Expression Extraction
- p44b: Temporal Relation Extraction  
- p44c: Timeline Ordering (multi-day support)
- p44d: Gap Detection

Usage:
    from nnrt.passes.p44_timeline_v6 import build_enhanced_timeline
    ctx = build_enhanced_timeline(ctx)

This replaces the original p44_timeline pass.
"""

import structlog
from nnrt.core.context import TransformContext

# Import the V6 passes
from nnrt.passes.p44a_temporal_expressions import extract_temporal_expressions
from nnrt.passes.p44b_temporal_relations import extract_temporal_relations
from nnrt.passes.p44c_timeline_ordering import build_timeline_ordering
from nnrt.passes.p44d_timeline_gaps import detect_timeline_gaps

log = structlog.get_logger("nnrt.p44_timeline_v6")

PASS_NAME = "p44_timeline_v6"


def build_enhanced_timeline(ctx: TransformContext) -> TransformContext:
    """
    Build an enhanced timeline using V6 multi-stage pipeline.
    
    Stages:
        1. Extract temporal expressions (times, dates, relative markers)
        2. Extract temporal relations (Allen's algebra)
        3. Order timeline entries (multi-day support)
        4. Detect gaps (unexplained periods needing investigation)
    
    Args:
        ctx: TransformContext with events and segments
        
    Returns:
        TransformContext with:
            - ctx.temporal_expressions: Extracted time references
            - ctx.temporal_relationships: Allen-style relations
            - ctx.timeline: Ordered TimelineEntry objects  
            - ctx.time_gaps: Detected gaps with investigation flags
    """
    log.info("starting_enhanced_timeline", pass_name=PASS_NAME, channel="TEMPORAL")
    
    # Stage 1: Extract temporal expressions
    ctx = extract_temporal_expressions(ctx)
    
    # Stage 2: Extract temporal relations
    ctx = extract_temporal_relations(ctx)
    
    # Stage 3: Build ordered timeline
    ctx = build_timeline_ordering(ctx)
    
    # Stage 4: Detect gaps
    ctx = detect_timeline_gaps(ctx)
    
    # Summary
    num_entries = len(ctx.timeline) if ctx.timeline else 0
    num_gaps = len(ctx.time_gaps) if ctx.time_gaps else 0
    investigation_needed = sum(1 for g in (ctx.time_gaps or []) if g.requires_investigation)
    
    log.info(
        "enhanced_timeline_complete",
        pass_name=PASS_NAME,
        channel="TEMPORAL",
        timeline_entries=num_entries,
        gaps_detected=num_gaps,
        gaps_needing_investigation=investigation_needed,
    )
    
    ctx.add_trace(
        PASS_NAME,
        "complete",
        after=f"{num_entries} entries, {num_gaps} gaps ({investigation_needed} need investigation)",
    )
    
    return ctx


# Alias for backward compatibility
build_timeline = build_enhanced_timeline
