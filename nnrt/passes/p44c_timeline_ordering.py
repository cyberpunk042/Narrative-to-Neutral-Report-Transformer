"""
p44c_timeline_ordering — Build ordered timeline from temporal data.

V6 Timeline Reconstruction: Stage 3

This pass builds TimelineEntry objects from events and statements,
ordering them using temporal expressions and relations.

Algorithm:
1. Create timeline entries for each event
2. Use temporal expressions for absolute positioning
3. Use temporal relations for relative ordering
4. Handle multi-day narratives with day_offset
5. Assign sequence numbers and link relations

Design decisions:
- Events are the primary timeline items
- Atomic statements can also be included if linked to events
- Multi-day support through day_offset field
- Normalized times for within-day ordering
"""

import re
import structlog
from typing import Optional, List, Dict, Tuple

from nnrt.core.context import TransformContext
from nnrt.ir.schema_v0_1 import (
    TimelineEntry, 
    TemporalExpression, 
    TemporalRelationship,
    Event,
)
from nnrt.ir.enums import (
    AllenRelation, 
    TimeSource, 
    TemporalExpressionType,
)

log = structlog.get_logger("nnrt.p44c_timeline_ordering")

PASS_NAME = "p44c_timeline_ordering"


# =============================================================================
# Day Offset Patterns
# =============================================================================

# Patterns that indicate transition to the next day
NEXT_DAY_PATTERNS = [
    re.compile(r'\bthe\s+next\s+day\b', re.I),
    re.compile(r'\bthe\s+following\s+day\b', re.I),
    re.compile(r'\bthe\s+following\s+morning\b', re.I),
    re.compile(r'\bnext\s+morning\b', re.I),
]

# Patterns with explicit day offset
DAY_OFFSET_PATTERNS = [
    (re.compile(r'\btwo\s+days?\s+later\b', re.I), 2),
    (re.compile(r'\bthree\s+days?\s+later\b', re.I), 3),
    (re.compile(r'\bfour\s+days?\s+later\b', re.I), 4),
    (re.compile(r'\bfive\s+days?\s+later\b', re.I), 5),
    (re.compile(r'\b(\d+)\s+days?\s+later\b', re.I), -1),  # -1 = extract from match
    (re.compile(r'\ba\s+week\s+later\b', re.I), 7),
    (re.compile(r'\bmonth\s+later\b', re.I), 30),
    (re.compile(r'\bthree\s+months?\s+later\b', re.I), 90),
]


def _estimate_event_position(event: Event, text: str) -> int:
    """Estimate character position of an event in the text."""
    if event.description:
        keywords = event.description.lower().split()
        for word in keywords:
            if len(word) > 3:
                pos = text.lower().find(word)
                if pos >= 0:
                    return pos
    return -1


def _find_nearest_expression(
    position: int,
    expressions: List[TemporalExpression],
    max_distance: int = 100,
) -> Optional[TemporalExpression]:
    """Find the temporal expression nearest to a position."""
    best = None
    best_dist = max_distance + 1
    
    for expr in expressions:
        # Prefer expressions BEFORE the event (they likely describe it)
        dist = position - expr.end_char
        if 0 <= dist < best_dist:
            best = expr
            best_dist = dist
        # Also consider expressions after, but with higher distance threshold
        elif expr.start_char - position < best_dist // 2:
            if abs(expr.start_char - position) < best_dist:
                best = expr
                best_dist = abs(expr.start_char - position)
    
    return best


def _compute_day_offset(expr: TemporalExpression, current_day: int, text: str) -> int:
    """Compute day offset from a temporal expression."""
    if not expr:
        return current_day
    
    lower_text = expr.original_text.lower()
    
    # Check for next day
    if 'next day' in lower_text or 'following day' in lower_text or 'following morning' in lower_text:
        return current_day + 1
    
    # Check for explicit day offsets
    for pattern, offset in DAY_OFFSET_PATTERNS:
        match = pattern.search(lower_text)
        if match:
            if offset == -1:  # Extract from regex
                try:
                    offset = int(match.group(1))
                except (IndexError, ValueError):
                    offset = 1
            return current_day + offset
    
    return current_day


def _normalize_time_for_sort(normalized_time: Optional[str]) -> int:
    """Convert normalized ISO time to minutes from midnight for sorting."""
    if not normalized_time:
        return 9999  # Unknown times sort last within day
    
    # Parse T23:30:00 format
    match = re.match(r'T(\d{2}):(\d{2})', normalized_time)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        return hour * 60 + minute
    
    return 9999


def build_timeline_ordering(ctx: TransformContext) -> TransformContext:
    """
    Build ordered timeline entries from events and temporal data.
    
    This pass:
    1. Creates TimelineEntry for each event
    2. Links to temporal expressions
    3. Computes day_offset for multi-day narratives
    4. Assigns sequence numbers
    5. Links temporal relations
    """
    text = ctx.normalized_text or " ".join(s.text for s in ctx.segments)
    expressions = ctx.temporal_expressions
    relationships = ctx.temporal_relationships
    events = ctx.events
    
    if not events:
        log.info("no_events", pass_name=PASS_NAME, message="No events to order")
        ctx.add_trace(PASS_NAME, "skipped", after="No events")
        return ctx
    
    timeline_entries: List[TimelineEntry] = []
    entry_counter = 0
    current_day_offset = 0
    
    # Map event_id -> relationship IDs involving that event
    event_relations: Dict[str, List[str]] = {}
    for rel in relationships:
        if rel.source_id not in event_relations:
            event_relations[rel.source_id] = []
        event_relations[rel.source_id].append(rel.id)
        if rel.target_id not in event_relations:
            event_relations[rel.target_id] = []
        event_relations[rel.target_id].append(rel.id)
    
    # =========================================================================
    # Phase 1: Create timeline entries for each event
    # =========================================================================
    
    # Track which expressions have been assigned to events
    # TIME expressions should only be used once
    used_time_expression_ids: set = set()
    
    for event in events:
        position = _estimate_event_position(event, text)
        
        # Find nearest temporal expression
        expr = _find_nearest_expression(position, expressions)
        
        # Check if this TIME expression was already used
        if expr and expr.type == TemporalExpressionType.TIME and expr.id in used_time_expression_ids:
            # Skip - this TIME was already assigned to a previous event
            expr = None
        
        # Determine time source and values
        normalized_time = None
        normalized_date = None
        absolute_time = None
        date_str = None
        relative_time = None
        time_source = TimeSource.INFERRED
        confidence = 0.5
        temporal_expression_id = None
        
        if expr:
            temporal_expression_id = expr.id
            
            if expr.type == TemporalExpressionType.TIME and expr.normalized_value:
                normalized_time = expr.normalized_value
                absolute_time = expr.original_text
                time_source = TimeSource.EXPLICIT
                confidence = 0.9
                # Mark as used so subsequent events don't inherit this time
                used_time_expression_ids.add(expr.id)
                
            elif expr.type == TemporalExpressionType.DATE and expr.normalized_value:
                normalized_date = expr.normalized_value
                date_str = expr.original_text
                time_source = TimeSource.EXPLICIT
                confidence = 0.85
                
            elif expr.type in (TemporalExpressionType.RELATIVE, TemporalExpressionType.DURATION):
                relative_time = expr.original_text
                time_source = TimeSource.RELATIVE
                confidence = 0.7
                
                # Check for day boundary transition
                new_day = _compute_day_offset(expr, current_day_offset, text)
                if new_day != current_day_offset:
                    current_day_offset = new_day
        
        # Create the entry
        entry = TimelineEntry(
            id=f"tl_{entry_counter:04d}",
            event_id=event.id,
            temporal_expression_id=temporal_expression_id,
            day_offset=current_day_offset,
            normalized_time=normalized_time,
            normalized_date=normalized_date,
            absolute_time=absolute_time,
            date=date_str,
            relative_time=relative_time,
            sequence_order=entry_counter,  # Initial order = narrative order
            time_source=time_source,
            temporal_relation_ids=event_relations.get(event.id, []),
            time_confidence=confidence,
        )
        timeline_entries.append(entry)
        entry_counter += 1
    
    # =========================================================================
    # Phase 2: Compute final sequence order
    # =========================================================================
    
    # Sort by: (day_offset, normalized_time_minutes, narrative_order)
    def sort_key(entry: TimelineEntry) -> Tuple:
        time_minutes = _normalize_time_for_sort(entry.normalized_time)
        return (
            entry.day_offset,
            time_minutes,
            entry.sequence_order,  # Tiebreaker: narrative order
        )
    
    # Sort and reassign sequence numbers
    timeline_entries.sort(key=sort_key)
    for new_order, entry in enumerate(timeline_entries):
        entry.sequence_order = new_order
    
    # =========================================================================
    # Phase 3: Build before/after links (legacy compatibility)
    # =========================================================================
    
    for i, entry in enumerate(timeline_entries):
        if i > 0:
            entry.after_entry_ids = [timeline_entries[i - 1].id]
        if i < len(timeline_entries) - 1:
            entry.before_entry_ids = [timeline_entries[i + 1].id]
    
    # =========================================================================
    # Phase 4: Estimate minutes from start
    # =========================================================================
    
    # For events with explicit times, we can calculate offset
    first_time = None
    for entry in timeline_entries:
        if entry.normalized_time and entry.day_offset == 0:
            first_time = _normalize_time_for_sort(entry.normalized_time)
            break
    
    if first_time is not None:
        for entry in timeline_entries:
            if entry.normalized_time:
                entry_time = _normalize_time_for_sort(entry.normalized_time)
                # Add day offset in minutes (24 * 60 = 1440 per day)
                entry.estimated_minutes_from_start = (
                    (entry.day_offset * 1440) + entry_time - first_time
                )
    
    # Store results
    ctx.timeline = timeline_entries
    
    # Log summary
    by_day = {}
    for e in timeline_entries:
        day = f"day_{e.day_offset}"
        by_day[day] = by_day.get(day, 0) + 1
    
    with_explicit = sum(1 for e in timeline_entries if e.time_source == TimeSource.EXPLICIT)
    with_relative = sum(1 for e in timeline_entries if e.time_source == TimeSource.RELATIVE)
    
    log.info(
        "timeline_ordered",
        pass_name=PASS_NAME,
        channel="TEMPORAL",
        total_entries=len(timeline_entries),
        by_day=by_day,
        with_explicit_time=with_explicit,
        with_relative_time=with_relative,
    )
    
    ctx.add_trace(
        PASS_NAME,
        "timeline_ordered",
        after=f"{len(timeline_entries)} entries ({by_day}), {with_explicit} explicit, {with_relative} relative",
    )
    
    return ctx
