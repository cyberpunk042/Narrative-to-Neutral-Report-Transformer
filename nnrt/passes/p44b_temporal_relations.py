"""
p44b_temporal_relations — Extract Allen-style temporal relations.

V6 Timeline Reconstruction: Stage 2

This pass analyzes temporal expressions and event pairs to determine
their temporal relationships using Allen's 13 interval relations.

Algorithm:
1. For each pair of adjacent events/statements in narrative order
2. Look for temporal markers between them
3. Classify the relation using Allen's algebra
4. Create TemporalRelationship objects with evidence

Design decisions:
- Uses narrative order as baseline (BEFORE relation)
- Temporal markers override/refine the baseline
- Full Allen's 13 captured, displayed as simplified 7
"""

import re
import structlog
from typing import Optional, List, Tuple

from nnrt.core.context import TransformContext
from nnrt.ir.schema_v0_1 import TemporalRelationship, TemporalExpression, Event
from nnrt.ir.enums import AllenRelation, RelationEvidence, TemporalExpressionType

log = structlog.get_logger("nnrt.p44b_temporal_relations")

PASS_NAME = "p44b_temporal_relations"


# =============================================================================
# Marker → Allen Relation Mapping
# =============================================================================

# Maps anchor_type from TemporalExpression to Allen relation
ANCHOR_TO_RELATION = {
    # Sequence markers → source BEFORE target
    'sequence': AllenRelation.BEFORE,
    'gap': AllenRelation.BEFORE,           # With gap
    'next_day': AllenRelation.BEFORE,      # Day boundary
    'days_later': AllenRelation.BEFORE,
    'months_later': AllenRelation.BEFORE,
    
    # Simultaneous markers
    'during': AllenRelation.DURING,
    'simultaneous': AllenRelation.EQUALS,
    
    # Before markers → source AFTER target (inverted)
    'before': AllenRelation.AFTER,
    
    # Vague markers - use narrative order
    'night': AllenRelation.BEFORE,
    'day_part': AllenRelation.BEFORE,
    'later_same_day': AllenRelation.BEFORE,
}

# Direct text patterns for immediate adjacency
MEETS_PATTERNS = [
    re.compile(r'\bimmediately\s+after\b', re.I),
    re.compile(r'\bimmediately\s+following\b', re.I),
    re.compile(r'\bas\s+soon\s+as\b', re.I),
    re.compile(r'\bright\s+after\b', re.I),
    re.compile(r'\bdirectly\s+after\b', re.I),
]

OVERLAPS_PATTERNS = [
    re.compile(r'\bstarted\s+while\b', re.I),
    re.compile(r'\bbegan\s+as\b', re.I),
    re.compile(r'\bstarted\s+when\b', re.I),
]

CONTAINS_PATTERNS = [
    re.compile(r'\bthroughout\b', re.I),
    re.compile(r'\bthe\s+whole\s+time\b', re.I),
    re.compile(r'\ball\s+the\s+while\b', re.I),
]


def _find_expression_between(
    expressions: List[TemporalExpression],
    start_pos: int,
    end_pos: int,
) -> Optional[TemporalExpression]:
    """Find a temporal expression that falls between two character positions."""
    for expr in expressions:
        if start_pos <= expr.start_char < end_pos:
            return expr
    return None


def _get_event_position(event: Event, text: str) -> int:
    """Estimate the character position of an event in the text."""
    # Try to find a keyword from the event description
    if event.description:
        keywords = event.description.lower().split()
        for word in keywords:
            if len(word) > 3:  # Skip short words
                pos = text.lower().find(word)
                if pos >= 0:
                    return pos
    return -1


def _check_pattern_between(
    patterns: List[re.Pattern],
    text: str,
    start_pos: int,
    end_pos: int,
) -> Optional[str]:
    """Check if any pattern matches in the text between two positions."""
    segment = text[start_pos:end_pos] if 0 <= start_pos < end_pos <= len(text) else ""
    for pattern in patterns:
        match = pattern.search(segment)
        if match:
            return match.group()
    return None


def extract_temporal_relations(ctx: TransformContext) -> TransformContext:
    """
    Extract Allen-style temporal relations between events.
    
    This pass:
    1. Pairs adjacent events in narrative order
    2. Looks for temporal markers between them
    3. Determines the Allen relation
    4. Creates TemporalRelationship objects
    """
    relationships: List[TemporalRelationship] = []
    rel_counter = 0
    
    text = ctx.normalized_text or " ".join(s.text for s in ctx.segments)
    expressions = ctx.temporal_expressions
    events = ctx.events
    
    if not events:
        log.info("no_events", pass_name=PASS_NAME, message="No events to relate")
        ctx.add_trace(PASS_NAME, "skipped", after="No events")
        return ctx
    
    # =========================================================================
    # Phase 1: Create relations between adjacent events
    # =========================================================================
    
    for i in range(len(events) - 1):
        event_a = events[i]
        event_b = events[i + 1]
        
        # Get approximate positions
        pos_a = _get_event_position(event_a, text)
        pos_b = _get_event_position(event_b, text)
        
        # Default: narrative order implies BEFORE
        relation = AllenRelation.BEFORE
        evidence_type = RelationEvidence.NARRATIVE_ORDER
        evidence_text = None
        confidence = 0.5
        
        # Look for temporal expression between events OR before first event
        if pos_a >= 0 and pos_b > pos_a:
            # Look between events first
            expr = _find_expression_between(expressions, pos_a, pos_b)
            
            # Also look for markers just before the first event (like "While he was running")
            if not expr and pos_a > 0:
                # Check in the 50 chars before first event
                expr = _find_expression_between(expressions, max(0, pos_a - 50), pos_a)
            
            if expr and expr.anchor_type:
                # Use the marker to determine relation
                mapped_relation = ANCHOR_TO_RELATION.get(expr.anchor_type)
                if mapped_relation:
                    relation = mapped_relation
                    evidence_type = RelationEvidence.EXPLICIT_MARKER
                    evidence_text = expr.original_text
                    confidence = 0.8
        
        # Check for more specific patterns
        if pos_a >= 0 and pos_b > pos_a:
            # Check MEETS patterns (immediately after)
            match_text = _check_pattern_between(MEETS_PATTERNS, text, pos_a, pos_b)
            if match_text:
                relation = AllenRelation.MEETS
                evidence_type = RelationEvidence.EXPLICIT_MARKER
                evidence_text = match_text
                confidence = 0.85
            
            # Check OVERLAPS patterns (started while)
            match_text = _check_pattern_between(OVERLAPS_PATTERNS, text, pos_a, pos_b)
            if match_text:
                relation = AllenRelation.OVERLAPS
                evidence_type = RelationEvidence.EXPLICIT_MARKER
                evidence_text = match_text
                confidence = 0.85
            
            # Check CONTAINS patterns (throughout)
            match_text = _check_pattern_between(CONTAINS_PATTERNS, text, pos_a, pos_b)
            if match_text:
                relation = AllenRelation.CONTAINS
                evidence_type = RelationEvidence.EXPLICIT_MARKER
                evidence_text = match_text
                confidence = 0.85
        
        # Create the relationship
        rel = TemporalRelationship(
            id=f"trel_{rel_counter:04d}",
            source_id=event_a.id,
            target_id=event_b.id,
            relation=relation,
            evidence_type=evidence_type,
            evidence_text=evidence_text,
            confidence=confidence,
        )
        relationships.append(rel)
        rel_counter += 1
    
    # =========================================================================
    # Phase 2: Handle "while" and "during" relations
    # =========================================================================
    
    # Look for expressions with 'during' anchor that might span multiple events
    for expr in expressions:
        if expr.anchor_type == 'during':
            # Find events near this marker and potentially create DURING relations
            nearby_events = []
            for event in events:
                pos = _get_event_position(event, text)
                # Event should be within 200 chars of the marker
                if pos >= 0 and abs(pos - expr.start_char) < 200:
                    nearby_events.append((event, pos))
            
            # If we have at least 2 events near a "during" marker,
            # the second might be DURING the first
            if len(nearby_events) >= 2:
                nearby_events.sort(key=lambda x: x[1])
                event_a, _ = nearby_events[0]
                event_b, _ = nearby_events[1]
                
                # Check if we already have a relation between these
                existing = any(
                    r.source_id == event_a.id and r.target_id == event_b.id
                    for r in relationships
                )
                if not existing:
                    rel = TemporalRelationship(
                        id=f"trel_{rel_counter:04d}",
                        source_id=event_b.id,  # B is DURING A
                        target_id=event_a.id,
                        relation=AllenRelation.DURING,
                        evidence_type=RelationEvidence.EXPLICIT_MARKER,
                        evidence_text=expr.original_text,
                        confidence=0.75,
                    )
                    relationships.append(rel)
                    rel_counter += 1
    
    # =========================================================================
    # Phase 3: Handle absolute time comparisons
    # =========================================================================
    
    # If we have events with normalized times, compare them directly
    time_expressions = [e for e in expressions if e.normalized_value and e.type == TemporalExpressionType.TIME]
    
    if len(time_expressions) >= 2:
        # Sort by position and compare times
        time_expressions.sort(key=lambda e: e.start_char)
        
        for i in range(len(time_expressions) - 1):
            expr_a = time_expressions[i]
            expr_b = time_expressions[i + 1]
            
            # Parse normalized times (T23:30:00 format)
            time_a = expr_a.normalized_value
            time_b = expr_b.normalized_value
            
            if time_a and time_b:
                # Simple string comparison works for ISO times
                if time_a < time_b:
                    # A is before B chronologically
                    log.debug("time_comparison", time_a=time_a, time_b=time_b, result="a_before_b")
                elif time_a > time_b:
                    # B is before A - possible cross-midnight scenario
                    log.debug("time_comparison", time_a=time_a, time_b=time_b, result="cross_midnight")
    
    # Store results
    ctx.temporal_relationships = relationships
    
    # Log summary
    by_relation = {}
    for r in relationships:
        rel_name = r.relation.value
        by_relation[rel_name] = by_relation.get(rel_name, 0) + 1
    
    log.info(
        "temporal_relations_extracted",
        pass_name=PASS_NAME,
        channel="TEMPORAL",
        total=len(relationships),
        by_relation=by_relation,
    )
    
    ctx.add_trace(
        PASS_NAME,
        "relations_extracted",
        after=f"{len(relationships)} temporal relations ({by_relation})",
    )
    
    return ctx
