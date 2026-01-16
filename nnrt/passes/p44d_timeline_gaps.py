"""
p44d_timeline_gaps — Detect gaps in the timeline.

V6 Timeline Reconstruction: Stage 4

This pass analyzes the timeline to detect unexplained gaps that may
require investigation. Gaps are classified as EXPLAINED, UNEXPLAINED,
or DAY_BOUNDARY, and can generate suggested questions.

Algorithm:
1. For each pair of adjacent timeline entries
2. Calculate time gap if possible
3. Classify gap based on markers and thresholds
4. Flag UNEXPLAINED gaps for investigation
5. Generate suggested follow-up questions

Design decisions:
- Gaps > 5 minutes without marker are flagged
- Day boundaries are always noted
- Questions are generated for unexplained gaps
"""

import re
import structlog
from typing import Optional, List

from nnrt.core.context import TransformContext
from nnrt.ir.schema_v0_1 import TimeGap, TimelineEntry
from nnrt.ir.enums import TimeGapType

log = structlog.get_logger("nnrt.p44d_timeline_gaps")

PASS_NAME = "p44d_timeline_gaps"

# Minimum gap in minutes to consider significant
MIN_GAP_MINUTES = 5


def _parse_duration_from_marker(marker_text: str) -> Optional[int]:
    """Extract duration in minutes from a marker like '20 minutes later'."""
    if not marker_text:
        return None
    
    lower = marker_text.lower()
    
    # Try "X minutes later"
    match = re.search(r'(\d+)\s*minutes?', lower)
    if match:
        return int(match.group(1))
    
    # Try "X hours later"
    match = re.search(r'(\d+)\s*hours?', lower)
    if match:
        return int(match.group(1)) * 60
    
    # "A few minutes" ≈ 5 minutes
    if 'few minutes' in lower:
        return 5
    
    # "A few hours" ≈ 3 hours
    if 'few hours' in lower:
        return 180
    
    return None


def _is_explained_gap(entry_after: TimelineEntry) -> tuple[bool, Optional[str], Optional[int]]:
    """Check if the gap before this entry is explained by a marker."""
    if entry_after.relative_time:
        # Has a relative time marker
        duration = _parse_duration_from_marker(entry_after.relative_time)
        return True, entry_after.relative_time, duration
    
    return False, None, None


def _calculate_gap_minutes(
    entry_a: TimelineEntry,
    entry_b: TimelineEntry,
) -> Optional[int]:
    """Calculate gap in minutes between two entries."""
    # If both have estimated_minutes_from_start, use that
    if (entry_a.estimated_minutes_from_start is not None and 
        entry_b.estimated_minutes_from_start is not None):
        return entry_b.estimated_minutes_from_start - entry_a.estimated_minutes_from_start
    
    # If day_offset differs, calculate day-based gap
    if entry_a.day_offset != entry_b.day_offset:
        days_diff = entry_b.day_offset - entry_a.day_offset
        return days_diff * 24 * 60  # Minutes in days
    
    return None


def _get_event_description(entry: TimelineEntry, ctx: TransformContext) -> str:
    """Get human-readable description for a timeline entry."""
    if entry.event_id:
        for event in ctx.events:
            if event.id == entry.event_id:
                return event.description or event.id
    return entry.id


def detect_timeline_gaps(ctx: TransformContext) -> TransformContext:
    """
    Detect and classify gaps in the timeline.
    
    This pass:
    1. Analyzes pairs of adjacent timeline entries
    2. Classifies gaps as EXPLAINED, UNEXPLAINED, or DAY_BOUNDARY
    3. Generates suggested investigation questions
    4. Links gaps to timeline entries
    """
    timeline = ctx.timeline
    
    if len(timeline) < 2:
        log.info("insufficient_entries", pass_name=PASS_NAME, 
                message=f"Only {len(timeline)} entries, no gaps to detect")
        ctx.add_trace(PASS_NAME, "skipped", after=f"Only {len(timeline)} entries")
        return ctx
    
    gaps: List[TimeGap] = []
    gap_counter = 0
    
    # =========================================================================
    # Analyze each pair of adjacent entries
    # =========================================================================
    
    for i in range(len(timeline) - 1):
        entry_a = timeline[i]
        entry_b = timeline[i + 1]
        
        # Check if gap is explained by a marker
        is_explained, explanation, duration = _is_explained_gap(entry_b)
        
        # Calculate gap duration if possible
        gap_minutes = _calculate_gap_minutes(entry_a, entry_b)
        if gap_minutes is None and duration:
            gap_minutes = duration
        
        # Classify the gap
        if entry_a.day_offset != entry_b.day_offset:
            gap_type = TimeGapType.DAY_BOUNDARY
            requires_investigation = not is_explained
        elif is_explained:
            gap_type = TimeGapType.EXPLAINED
            requires_investigation = False
        elif gap_minutes is not None and gap_minutes > MIN_GAP_MINUTES:
            gap_type = TimeGapType.UNEXPLAINED
            requires_investigation = True
        elif gap_minutes == 0 and not is_explained:
            # Both events have the same estimated time but no marker
            # This suggests a narrative discontinuity (memory gap, unclear sequence)
            # Only flag if neither has an explicit time source
            both_inferred = (
                entry_a.time_source.value in ('inferred', 'relative') or
                entry_b.time_source.value in ('inferred', 'relative')
            )
            if both_inferred:
                gap_type = TimeGapType.UNCERTAIN
                requires_investigation = True  # Flag for investigation
            else:
                gap_type = TimeGapType.NONE
                requires_investigation = False
        elif gap_minutes is None and not is_explained:
            # No time marker AND can't calculate gap = narrative discontinuity
            gap_type = TimeGapType.UNCERTAIN
            requires_investigation = True
        else:
            gap_type = TimeGapType.NONE
            requires_investigation = False
        
        # Generate question for unexplained gaps
        suggested_question = None
        if requires_investigation:
            desc_a = _get_event_description(entry_a, ctx)
            desc_b = _get_event_description(entry_b, ctx)
            
            if gap_type == TimeGapType.DAY_BOUNDARY:
                suggested_question = (
                    f"What happened after '{desc_a}' and before you '{desc_b}' "
                    f"(the events are on different days)?"
                )
            elif gap_minutes:
                suggested_question = (
                    f"What happened during the approximately {gap_minutes} minutes "
                    f"between '{desc_a}' and '{desc_b}'?"
                )
            else:
                suggested_question = (
                    f"What happened between '{desc_a}' and '{desc_b}'?"
                )
        
        # Only create gap objects for significant gaps
        if gap_type not in (TimeGapType.NONE,):
            gap = TimeGap(
                id=f"gap_{gap_counter:04d}",
                after_entry_id=entry_a.id,
                before_entry_id=entry_b.id,
                gap_type=gap_type,
                estimated_duration_minutes=gap_minutes,
                explanation_text=explanation,
                requires_investigation=requires_investigation,
                suggested_question=suggested_question,
            )
            gaps.append(gap)
            
            # Link gap to the entry that follows it
            entry_b.gap_before_id = gap.id
            
            gap_counter += 1
    
    # Store results
    ctx.time_gaps = gaps
    
    # Log summary
    by_type = {}
    for g in gaps:
        t = g.gap_type.value
        by_type[t] = by_type.get(t, 0) + 1
    
    needing_investigation = sum(1 for g in gaps if g.requires_investigation)
    
    log.info(
        "gaps_detected",
        pass_name=PASS_NAME,
        channel="TEMPORAL",
        total_gaps=len(gaps),
        by_type=by_type,
        requiring_investigation=needing_investigation,
    )
    
    ctx.add_trace(
        PASS_NAME,
        "gaps_detected",
        after=f"{len(gaps)} gaps ({by_type}), {needing_investigation} need investigation",
    )
    
    return ctx
