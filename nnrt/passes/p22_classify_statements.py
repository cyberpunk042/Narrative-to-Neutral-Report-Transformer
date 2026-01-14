"""
Pass 22: Classify Statements

Classifies each segment as:
- OBSERVATION: Directly witnessed ("I saw him grab me")
- CLAIM: Asserted without explicit witness ("He grabbed me")
- INTERPRETATION: Inference/opinion ("He wanted to hurt me")
- QUOTE: Direct speech preserved verbatim

This enriches the IR with epistemic metadata for structured output.
"""

import re
from nnrt.core.context import TransformContext
from nnrt.ir.enums import SegmentContext, StatementType

PASS_NAME = "classify_statements"

# ============================================================================
# Classification Patterns
# ============================================================================

# OBSERVATION: Narrator explicitly witnessed
OBSERVATION_PATTERNS = [
    r"\bI\s+saw\b",
    r"\bI\s+heard\b",
    r"\bI\s+felt\b",
    r"\bI\s+watched\b",
    r"\bI\s+noticed\b",
    r"\bI\s+observed\b",
    r"\bI\s+looked\b",
    r"\bI\s+could\s+see\b",
    r"\bI\s+witnessed\b",
    r"\bI\s+smelled\b",
    r"\bI\s+tasted\b",
]

# INTERPRETATION: Inference, opinion, intent attribution
INTERPRETATION_PATTERNS = [
    # Intent attribution
    r"\b(wanted\s+to|tried\s+to|meant\s+to)\b",
    r"\b(was\s+trying\s+to|were\s+trying\s+to)\b",
    # Certainty markers (often interpretation)
    r"\b(obviously|clearly|definitely|certainly)\b",
    r"\b(must\s+have|had\s+to\s+have)\b",
    # Intent language
    r"\b(on\s+purpose|intentionally|deliberately)\b",
    # Opinion markers
    r"\b(I\s+think|I\s+believe|I\s+feel\s+like)\b",
    r"\b(in\s+my\s+opinion)\b",
    # Uncertainty (still interpretation)
    r"\b(probably|maybe|might\s+have|could\s+have)\b",
    r"\b(seemed\s+like|looked\s+like|appeared\s+to)\b",
]


def classify_statements(ctx: TransformContext) -> TransformContext:
    """
    Classify each segment by epistemic status.
    
    Priority:
    1. QUOTE - if segment is a direct quote
    2. OBSERVATION - if explicit witness language
    3. INTERPRETATION - if inference/opinion language
    4. CLAIM - default (assertion without explicit witness)
    """
    classified = 0
    
    for segment in ctx.segments:
        text = segment.text
        text_lower = text.lower()
        
        # Priority 1: Check if already marked as direct quote
        if SegmentContext.DIRECT_QUOTE.value in segment.contexts:
            segment.statement_type = StatementType.QUOTE
            segment.statement_confidence = 0.95
            classified += 1
            continue
        
        # Priority 2: Check for explicit observation
        if _matches_any(text_lower, OBSERVATION_PATTERNS):
            segment.statement_type = StatementType.OBSERVATION
            segment.statement_confidence = 0.85
            classified += 1
            continue
        
        # Priority 3: Check for interpretation
        if _matches_any(text_lower, INTERPRETATION_PATTERNS):
            segment.statement_type = StatementType.INTERPRETATION
            segment.statement_confidence = 0.80
            classified += 1
            continue
        
        # Default: CLAIM (assertion without explicit witness)
        segment.statement_type = StatementType.CLAIM
        segment.statement_confidence = 0.70
        classified += 1
    
    # Add trace
    ctx.add_trace(
        pass_name=PASS_NAME,
        action="classified",
        after=f"{classified} segments classified",
    )
    
    # Log summary
    type_counts = {}
    for seg in ctx.segments:
        t = seg.statement_type.value
        type_counts[t] = type_counts.get(t, 0) + 1
    
    ctx.add_trace(
        pass_name=PASS_NAME,
        action="summary",
        after=str(type_counts),
    )
    
    return ctx


def _matches_any(text: str, patterns: list[str]) -> bool:
    """Check if text matches any of the regex patterns."""
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False
