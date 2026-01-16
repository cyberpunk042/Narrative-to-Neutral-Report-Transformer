"""
p44a_temporal_expressions — Extract and normalize temporal expressions.

V6 Timeline Reconstruction: Stage 1

This pass extracts temporal expressions from the narrative and normalizes
them to ISO format for consistent timeline construction.

Algorithm:
1. Use spaCy NER to find DATE/TIME entities
2. Apply custom patterns for relative expressions
3. Normalize all expressions to ISO format
4. Link expressions to nearby statements/events

Design decisions:
- Uses spaCy en_core_web_sm DATE/TIME entities as base
- Custom patterns for relative markers ("then", "later", "the next day")
- ISO 8601 normalization for absolute times
- Preserves original text for display
"""

import re
import structlog
from typing import Optional, Tuple, List
from datetime import datetime

from nnrt.core.context import TransformContext
from nnrt.ir.schema_v0_1 import TemporalExpression
from nnrt.ir.enums import TemporalExpressionType
from nnrt.nlp.spacy_loader import get_nlp

log = structlog.get_logger("nnrt.p44a_temporal_expressions")

PASS_NAME = "p44a_temporal_expressions"


# =============================================================================
# Time Normalization Patterns
# =============================================================================

# Pattern: "11:30 PM" or "3:00 AM" or "11:30PM"
TIME_PATTERN = re.compile(
    r'\b(\d{1,2}):?(\d{2})?\s*(AM|PM|am|pm|a\.m\.|p\.m\.)\b',
    re.IGNORECASE
)

# Pattern: "January 10, 2026" or "Jan 10th, 2026" or "10/15/2026"
DATE_PATTERNS = [
    # Full month name: January 10, 2026 or January 10th 2026
    re.compile(
        r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+'
        r'(\d{1,2})(?:st|nd|rd|th)?,?\s*(\d{4})\b',
        re.IGNORECASE
    ),
    # Abbreviated month: Jan 10, 2026
    re.compile(
        r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+'
        r'(\d{1,2})(?:st|nd|rd|th)?,?\s*(\d{4})\b',
        re.IGNORECASE
    ),
    # Numeric: 01/10/2026 or 1-10-2026
    re.compile(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b'),
]

# Relative time markers
RELATIVE_PATTERNS = [
    # Sequence markers
    (re.compile(r'\bthen\b', re.I), TemporalExpressionType.RELATIVE, 'sequence'),
    (re.compile(r'\bafter\s+that\b', re.I), TemporalExpressionType.RELATIVE, 'sequence'),
    (re.compile(r'\bafterwards?\b', re.I), TemporalExpressionType.RELATIVE, 'sequence'),
    (re.compile(r'\bsubsequently\b', re.I), TemporalExpressionType.RELATIVE, 'sequence'),
    (re.compile(r'\bnext\b', re.I), TemporalExpressionType.RELATIVE, 'sequence'),
    (re.compile(r'\beventually\b', re.I), TemporalExpressionType.RELATIVE, 'sequence'),
    (re.compile(r'\bfinally\b', re.I), TemporalExpressionType.RELATIVE, 'sequence'),
    
    # Duration gaps
    (re.compile(r'\b(\d+)\s+(minutes?|hours?|days?|weeks?|months?)\s+later\b', re.I), 
     TemporalExpressionType.DURATION, 'gap'),
    (re.compile(r'\babout\s+(\d+)\s+(minutes?|hours?)\s+later\b', re.I), 
     TemporalExpressionType.DURATION, 'gap'),
    (re.compile(r'\ba\s+few\s+(minutes?|hours?|days?)\s+later\b', re.I), 
     TemporalExpressionType.DURATION, 'gap'),
    
    # Day boundaries
    (re.compile(r'\bthe\s+next\s+day\b', re.I), TemporalExpressionType.RELATIVE, 'next_day'),
    (re.compile(r'\bthe\s+following\s+(day|morning|evening|night)\b', re.I), 
     TemporalExpressionType.RELATIVE, 'next_day'),
    (re.compile(r'\b(one|two|three|four|five)\s+days?\s+later\b', re.I), 
     TemporalExpressionType.DURATION, 'days_later'),
    (re.compile(r'\b(\d+)\s+days?\s+later\b', re.I), 
     TemporalExpressionType.DURATION, 'days_later'),
    (re.compile(r'\bthree\s+months?\s+later\b', re.I), 
     TemporalExpressionType.DURATION, 'months_later'),
    
    # During/simultaneous
    (re.compile(r'\bwhile\b', re.I), TemporalExpressionType.RELATIVE, 'during'),
    (re.compile(r'\bduring\b', re.I), TemporalExpressionType.RELATIVE, 'during'),
    (re.compile(r'\bat\s+the\s+same\s+time\b', re.I), TemporalExpressionType.RELATIVE, 'simultaneous'),
    (re.compile(r'\bmeanwhile\b', re.I), TemporalExpressionType.RELATIVE, 'during'),
    
    # Before markers
    (re.compile(r'\bbefore\s+that\b', re.I), TemporalExpressionType.RELATIVE, 'before'),
    (re.compile(r'\bprior\s+to\b', re.I), TemporalExpressionType.RELATIVE, 'before'),
    (re.compile(r'\bearlier\b', re.I), TemporalExpressionType.RELATIVE, 'before'),
    
    # Vague time references
    (re.compile(r'\bthat\s+night\b', re.I), TemporalExpressionType.VAGUE, 'night'),
    (re.compile(r'\bthat\s+(morning|afternoon|evening)\b', re.I), TemporalExpressionType.VAGUE, 'day_part'),
    (re.compile(r'\blater\s+that\s+(night|day|evening)\b', re.I), TemporalExpressionType.VAGUE, 'later_same_day'),
]

# Month name to number mapping
MONTH_MAP = {
    'january': 1, 'jan': 1, 'february': 2, 'feb': 2, 'march': 3, 'mar': 3,
    'april': 4, 'apr': 4, 'may': 5, 'june': 6, 'jun': 6,
    'july': 7, 'jul': 7, 'august': 8, 'aug': 8, 'september': 9, 'sep': 9,
    'october': 10, 'oct': 10, 'november': 11, 'nov': 11, 'december': 12, 'dec': 12,
}


def normalize_time(text: str) -> Optional[str]:
    """
    Normalize a time string to ISO format (T23:30:00).
    
    Examples:
        "11:30 PM" -> "T23:30:00"
        "3:00 AM"  -> "T03:00:00"
        "3 PM"     -> "T15:00:00"
    """
    match = TIME_PATTERN.search(text)
    if not match:
        return None
    
    hour = int(match.group(1))
    minute = int(match.group(2)) if match.group(2) else 0
    ampm = match.group(3).lower().replace('.', '')
    
    # Convert to 24-hour
    if ampm in ('pm', 'p') and hour != 12:
        hour += 12
    elif ampm in ('am', 'a') and hour == 12:
        hour = 0
    
    return f"T{hour:02d}:{minute:02d}:00"


def normalize_date(text: str) -> Optional[str]:
    """
    Normalize a date string to ISO format (2026-01-10).
    
    Examples:
        "January 10, 2026"   -> "2026-01-10"
        "Jan 10th, 2026"     -> "2026-01-10"
        "01/10/2026"         -> "2026-01-10"
    """
    for pattern in DATE_PATTERNS[:2]:  # Month name patterns
        match = pattern.search(text)
        if match:
            month_str = match.group(1).lower()[:3]
            month = MONTH_MAP.get(month_str, 1)
            day = int(match.group(2))
            year = int(match.group(3))
            return f"{year:04d}-{month:02d}-{day:02d}"
    
    # Check numeric pattern
    match = DATE_PATTERNS[2].search(text)
    if match:
        month = int(match.group(1))
        day = int(match.group(2))
        year = int(match.group(3))
        return f"{year:04d}-{month:02d}-{day:02d}"
    
    return None


def extract_temporal_expressions(ctx: TransformContext) -> TransformContext:
    """
    Extract and normalize temporal expressions from the narrative.
    
    This pass:
    1. Finds DATE/TIME entities using spaCy NER
    2. Detects relative temporal markers
    3. Normalizes to ISO format
    4. Creates TemporalExpression objects
    """
    nlp = get_nlp()
    text = ctx.normalized_text or " ".join(s.text for s in ctx.segments)
    
    expressions: List[TemporalExpression] = []
    expr_counter = 0
    seen_spans: set = set()  # Avoid duplicates
    
    # =========================================================================
    # Phase 1: Extract from spaCy NER (DATE/TIME entities)
    # =========================================================================
    
    doc = nlp(text)
    
    for ent in doc.ents:
        if ent.label_ in ('DATE', 'TIME'):
            # Skip if we've already processed this span
            span_key = (ent.start_char, ent.end_char)
            if span_key in seen_spans:
                continue
            
            # =================================================================
            # Filter out false positives (badge numbers, ID numbers, etc.)
            # =================================================================
            ent_text = ent.text.strip()
            
            # Skip pure numeric values that are likely badge/ID numbers
            if ent_text.isdigit():
                # Check context around the entity for badge-related words
                context_start = max(0, ent.start_char - 50)
                context_end = min(len(text), ent.end_char + 20)
                context = text[context_start:context_end].lower()
                
                # Skip if near badge/ID indicators
                if any(indicator in context for indicator in [
                    'badge', 'badge number', 'badge #', 'badge#',
                    'id', 'id number', 'case number', 'case #',
                    'unit', 'unit number', 'officer #',
                ]):
                    log.debug("skipping_badge_number", 
                              text=ent_text, 
                              reason="near badge/ID indicator",
                              channel="TEMPORAL")
                    continue
                
                # Skip 3-5 digit numbers that aren't valid years (1900-2100)
                if len(ent_text) in (3, 4, 5):
                    try:
                        num = int(ent_text)
                        if not (1900 <= num <= 2100):
                            log.debug("skipping_numeric_entity", 
                                      text=ent_text, 
                                      reason="not a valid year",
                                      channel="TEMPORAL")
                            continue
                    except ValueError:
                        pass
            
            # Skip medical/diagnostic terms misclassified as dates
            if ent_text.upper() in ('PTSD', 'CPR', 'EMS', 'ICU', 'ER'):
                log.debug("skipping_medical_term", 
                          text=ent_text, 
                          reason="medical abbreviation",
                          channel="TEMPORAL")
                continue
            
            seen_spans.add(span_key)
            
            # Determine type and normalize
            if ent.label_ == 'TIME':
                normalized = normalize_time(ent.text)
                if normalized:
                    expr_type = TemporalExpressionType.TIME
                    anchor_type = None
                else:
                    # Check if this is a duration (e.g., "20 minutes later")
                    if re.search(r'(minutes?|hours?|days?)\s+later', ent.text, re.I):
                        expr_type = TemporalExpressionType.DURATION
                        anchor_type = 'gap'
                    elif re.search(r'(minutes?|hours?)', ent.text, re.I):
                        expr_type = TemporalExpressionType.DURATION
                        anchor_type = 'duration'
                    else:
                        expr_type = TemporalExpressionType.VAGUE
                        anchor_type = None
            else:
                # DATE could be absolute date or relative ("the next day")
                normalized = normalize_date(ent.text)
                if normalized:
                    expr_type = TemporalExpressionType.DATE
                    anchor_type = None
                else:
                    # Check for specific relative patterns
                    lower_text = ent.text.lower()
                    if 'next day' in lower_text or 'following' in lower_text:
                        expr_type = TemporalExpressionType.RELATIVE
                        anchor_type = 'next_day'
                    elif 'later' in lower_text:
                        expr_type = TemporalExpressionType.DURATION
                        anchor_type = 'gap'
                    else:
                        expr_type = TemporalExpressionType.RELATIVE
                        anchor_type = None
            
            # Find source segment
            segment_id = "seg_0"
            for seg in ctx.segments:
                if seg.start_char <= ent.start_char < seg.end_char:
                    segment_id = seg.id
                    break
            
            expr = TemporalExpression(
                id=f"tex_{expr_counter:04d}",
                original_text=ent.text,
                type=expr_type,
                normalized_value=normalized,
                anchor_type=anchor_type,
                start_char=ent.start_char,
                end_char=ent.end_char,
                segment_id=segment_id,
                confidence=0.85 if normalized else 0.7,
            )
            expressions.append(expr)
            expr_counter += 1
    
    # =========================================================================
    # Phase 2: Extract relative markers with custom patterns
    # =========================================================================
    
    text_lower = text.lower()
    
    for pattern, expr_type, anchor_type in RELATIVE_PATTERNS:
        for match in pattern.finditer(text):
            start = match.start()
            end = match.end()
            
            # Skip if overlaps with existing expression
            overlaps = any(
                (start < e.end_char and end > e.start_char)
                for e in expressions
            )
            if overlaps:
                continue
            
            span_key = (start, end)
            if span_key in seen_spans:
                continue
            seen_spans.add(span_key)
            
            # Find source segment
            segment_id = "seg_0"
            for seg in ctx.segments:
                if seg.start_char <= start < seg.end_char:
                    segment_id = seg.id
                    break
            
            expr = TemporalExpression(
                id=f"tex_{expr_counter:04d}",
                original_text=match.group(),
                type=expr_type,
                normalized_value=None,  # Relative expressions don't have absolute value
                anchor_type=anchor_type,
                start_char=start,
                end_char=end,
                segment_id=segment_id,
                confidence=0.75,
            )
            expressions.append(expr)
            expr_counter += 1
    
    # =========================================================================
    # Sort by position in text
    # =========================================================================
    
    expressions.sort(key=lambda e: e.start_char)
    
    # Store results
    ctx.temporal_expressions = expressions
    
    # Log summary
    by_type = {}
    for e in expressions:
        t = e.type.value
        by_type[t] = by_type.get(t, 0) + 1
    
    log.info(
        "temporal_expressions_extracted",
        pass_name=PASS_NAME,
        channel="TEMPORAL",
        total=len(expressions),
        by_type=by_type,
    )
    
    ctx.add_trace(
        PASS_NAME,
        "expressions_extracted",
        after=f"{len(expressions)} temporal expressions ({by_type})",
    )
    
    return ctx
