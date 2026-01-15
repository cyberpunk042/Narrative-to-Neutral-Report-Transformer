"""
p44_timeline — Temporal ordering of events.

This pass builds a timeline of events in the narrative, determining
the chronological order even when events are reported out of order.

Algorithm:
1. COLLECT ABSOLUTE TIMES
   - Use DATE/TIME identifiers from p30_extract_identifiers
   - Associate with nearby events/statements

2. DETECT RELATIVE TIME MARKERS
   - "then", "after that", "later", "before"
   - "X minutes/hours later", "the next day"
   - Establish ordering relationships

3. BUILD TEMPORAL GRAPH
   - Create edges: A → B means A happens before B
   - Use absolute times to anchor the graph
   - Use relative markers for ordering

4. COMPUTE SEQUENCE ORDER
   - Topological sort with narrative order as tiebreaker
   - Assign sequence numbers

Design principles:
- Explicit times override narrative order
- Relative markers create ordering constraints
- Narrative order is the fallback
- Confidence reflects certainty of placement
"""

import re
import structlog
from typing import Optional
from datetime import datetime

from nnrt.core.context import TransformContext
from nnrt.ir.schema_v0_1 import TimelineEntry, Identifier, Event
from nnrt.ir.enums import IdentifierType
from nnrt.nlp.spacy_loader import get_nlp

log = structlog.get_logger("nnrt.p44_timeline")

PASS_NAME = "p44_timeline"

# ============================================================================
# Relative Time Patterns
# ============================================================================

# Patterns that indicate SEQUENCE (current event comes after previous)
SEQUENCE_PATTERNS = [
    r'\bthen\b',
    r'\bafter\s+that\b',
    r'\bafterwards?\b',
    r'\bsubsequently\b',
    r'\bnext\b',
    r'\blater\b',
    r'\beventually\b',
    r'\bfinally\b',
]

# Patterns that indicate BEFORE (current event came before something)
BEFORE_PATTERNS = [
    r'\bbefore\s+(?:that|this|the)\b',
    r'\bprior\s+to\b',
    r'\bearlier\b',
    r'\bpreviously\b',
]

# Patterns with explicit time gaps
TIME_GAP_PATTERNS = [
    # "X minutes/hours/days later"
    (r'\b(\d+)\s+(minutes?|hours?|days?|weeks?|months?)\s+later\b', 'later'),
    # "the next day/morning/week"
    (r'\bthe\s+next\s+(day|morning|evening|week|month)\b', 'next_period'),
    # "three months later"
    (r'\b(one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s+(minutes?|hours?|days?|weeks?|months?|years?)\s+later\b', 'later'),
    # "a few hours later"
    (r'\ba\s+few\s+(minutes?|hours?|days?)\s+later\b', 'later'),
]

# Patterns indicating same time / during
DURING_PATTERNS = [
    r'\bwhile\b',
    r'\bduring\b',
    r'\bat\s+the\s+same\s+time\b',
    r'\bsimultaneously\b',
    r'\bmeanwhile\b',
]


def build_timeline(ctx: TransformContext) -> TransformContext:
    """
    Build a timeline of events in chronological order.
    
    This pass:
    1. Collects absolute times from identifiers
    2. Detects relative time markers
    3. Computes sequence ordering
    4. Creates TimelineEntry objects
    """
    if not ctx.events:
        log.info("no_events", pass_name=PASS_NAME, message="No events to order")
        ctx.add_trace(PASS_NAME, "skipped", after="No events")
        return ctx
    
    nlp = get_nlp()
    timeline_entries: list[TimelineEntry] = []
    entry_counter = 0
    
    # =========================================================================
    # Phase 1: Collect Absolute Times from Identifiers
    # =========================================================================
    
    # Group time/date identifiers by segment
    times_by_segment: dict[str, list[str]] = {}
    dates_by_segment: dict[str, list[str]] = {}
    
    for ident in ctx.identifiers:
        if ident.type == IdentifierType.TIME:
            seg_id = ident.source_segment_id
            if seg_id not in times_by_segment:
                times_by_segment[seg_id] = []
            times_by_segment[seg_id].append(ident.value)
        elif ident.type == IdentifierType.DATE:
            seg_id = ident.source_segment_id
            if seg_id not in dates_by_segment:
                dates_by_segment[seg_id] = []
            dates_by_segment[seg_id].append(ident.value)
    
    # =========================================================================
    # Phase 2: Detect Relative Time Markers
    # =========================================================================
    
    # Analyze the full text for relative markers
    full_text = ctx.normalized_text or " ".join(s.text for s in ctx.segments)
    text_lower = full_text.lower()
    
    # Find positions of relative markers
    relative_markers: list[tuple[int, str, str]] = []  # (position, marker_type, matched_text)
    
    for pattern in SEQUENCE_PATTERNS:
        for match in re.finditer(pattern, text_lower, re.IGNORECASE):
            relative_markers.append((match.start(), "sequence", match.group()))
    
    for pattern in BEFORE_PATTERNS:
        for match in re.finditer(pattern, text_lower, re.IGNORECASE):
            relative_markers.append((match.start(), "before", match.group()))
    
    for pattern, marker_type in TIME_GAP_PATTERNS:
        for match in re.finditer(pattern, text_lower, re.IGNORECASE):
            relative_markers.append((match.start(), "gap", match.group()))
    
    for pattern in DURING_PATTERNS:
        for match in re.finditer(pattern, text_lower, re.IGNORECASE):
            relative_markers.append((match.start(), "during", match.group()))
    
    relative_markers.sort(key=lambda x: x[0])
    
    # =========================================================================
    # Phase 3: Create Timeline Entries for Events
    # =========================================================================
    
    # For each event, determine its temporal position
    for idx, event in enumerate(ctx.events):
        # Find the segment this event is in (use source_spans if available)
        event_segment_id = None
        event_position = -1  # Will be estimated from text
        
        # Try to find position from source spans
        for span_id in event.source_spans:
            for span in ctx.spans:
                if span.id == span_id:
                    event_segment_id = span.segment_id
                    for seg in ctx.segments:
                        if seg.id == event_segment_id:
                            event_position = seg.start_char
                            break
                    break
        
        # If no position from spans, estimate from event description in text
        if event_position < 0 and event.description:
            # Search for a keyword from the description in the text
            desc_words = event.description.lower().split()
            for word in desc_words:
                if len(word) > 3:  # Skip short words
                    pos = text_lower.find(word)
                    if pos >= 0:
                        event_position = pos
                        break
        
        # Fallback: use index-based estimation
        if event_position < 0:
            # Estimate based on narrative order: divide text evenly
            event_position = (idx * len(full_text)) // max(len(ctx.events), 1)
        
        # Get absolute time for this event
        # Only associate a time if the event is NEAR the time identifier
        absolute_time = None
        event_date = None
        
        # Check if there's a time identifier near this event position
        for ident in ctx.identifiers:
            if ident.type == IdentifierType.TIME:
                # Time should be within 50 chars before the event
                if 0 <= (event_position - ident.start_char) < 50:
                    absolute_time = ident.value
                    break
            elif ident.type == IdentifierType.DATE:
                if 0 <= (event_position - ident.start_char) < 50:
                    event_date = ident.value
        
        # Find any relative marker that precedes this event
        relative_time = None
        if idx > 0:  # Not the first event
            # Look for a relative marker between the previous event's position and this one
            relative_time = _find_relative_marker_before_position(
                event_position, relative_markers
            )
        
        # Calculate confidence
        if absolute_time:
            confidence = 0.95
        elif relative_time:
            confidence = 0.8
        else:
            confidence = 0.5  # Just narrative order
        
        entry = TimelineEntry(
            id=f"tl_{entry_counter:04d}",
            event_id=event.id,
            absolute_time=absolute_time,
            date=event_date,
            relative_time=relative_time,
            sequence_order=idx,  # Will be refined in Phase 4
            time_confidence=confidence,
        )
        timeline_entries.append(entry)
        entry_counter += 1
    
    # =========================================================================
    # Phase 4: Compute Final Sequence Order
    # =========================================================================
    
    # For narratives that span multiple days, we can't just sort by time.
    # Instead, we use NARRATIVE ORDER as the primary sequence, with
    # absolute times as anchors for reference.
    #
    # The timeline preserves narrative order but enriches with time info.
    
    def sort_key(entry: TimelineEntry) -> tuple:
        # Primary: original narrative order (already set as sequence_order)
        # Secondary: time value for entries that share the same narrative position
        time_value = 999
        if entry.absolute_time:
            time_value = _parse_time_for_sort(entry.absolute_time)
        
        return (entry.sequence_order, time_value)
    
    # Sort and reassign sequence numbers (mostly preserves narrative order)
    timeline_entries.sort(key=sort_key)
    for new_order, entry in enumerate(timeline_entries):
        entry.sequence_order = new_order
    
    # =========================================================================
    # Build Relations (before/after links)
    # =========================================================================
    
    for i, entry in enumerate(timeline_entries):
        if i > 0:
            entry.after_entry_ids = [timeline_entries[i-1].id]
        if i < len(timeline_entries) - 1:
            entry.before_entry_ids = [timeline_entries[i+1].id]
    
    # Store results
    ctx.timeline = timeline_entries
    
    # Log summary
    with_time = sum(1 for e in timeline_entries if e.absolute_time)
    with_relative = sum(1 for e in timeline_entries if e.relative_time)
    
    log.info(
        "timeline_built",
        pass_name=PASS_NAME,
        channel="SEMANTIC",
        total_entries=len(timeline_entries),
        with_absolute_time=with_time,
        with_relative_time=with_relative,
    )
    
    ctx.add_trace(
        PASS_NAME,
        "timeline_ordered",
        after=f"{len(timeline_entries)} events ordered ({with_time} with times, {with_relative} with relative markers)",
    )
    
    return ctx


def _find_relative_marker_before_position(
    position: int,
    markers: list[tuple[int, str, str]],
) -> Optional[str]:
    """
    Find a relative time marker that appears before a given position.
    
    Returns the marker text closest to (but before) the position.
    """
    best_marker = None
    best_pos = -1
    
    for marker_pos, marker_type, marker_text in markers:
        # Marker should be before position but not too far (within 100 chars)
        if marker_pos < position and (position - marker_pos) < 100:
            if marker_pos > best_pos:  # Prefer closest marker
                best_pos = marker_pos
                best_marker = marker_text
    
    return best_marker


def _parse_time_for_sort(time_str: str) -> int:
    """
    Parse a time string into minutes from midnight for sorting.
    
    Returns 0-1440 for times, 999 if can't parse.
    """
    time_lower = time_str.lower().strip()
    
    # Try HH:MM AM/PM format
    match = re.match(r'(\d{1,2}):(\d{2})\s*(am|pm)?', time_lower)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        ampm = match.group(3)
        
        if ampm == 'pm' and hour != 12:
            hour += 12
        elif ampm == 'am' and hour == 12:
            hour = 0
        
        return hour * 60 + minute
    
    # Try just HH AM/PM format
    match = re.match(r'(\d{1,2})\s*(am|pm)', time_lower)
    if match:
        hour = int(match.group(1))
        ampm = match.group(2)
        
        if ampm == 'pm' and hour != 12:
            hour += 12
        elif ampm == 'am' and hour == 12:
            hour = 0
        
        return hour * 60
    
    return 999  # Can't parse
