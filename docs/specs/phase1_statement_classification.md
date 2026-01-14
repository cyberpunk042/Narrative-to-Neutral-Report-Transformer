# Phase 1: Statement Classification — Implementation Spec

## Overview

Classify each segment/statement into one of four types:
- **OBSERVATION** — Sensory experience, directly witnessed
- **CLAIM** — Asserted fact, not directly witnessed
- **INTERPRETATION** — Inference, opinion, or intent attribution
- **QUOTE** — Direct speech, preserved verbatim

---

## New Enum: StatementType

Location: `nnrt/ir/enums.py`

```python
class StatementType(str, Enum):
    """Classification of statement epistemic status."""
    
    OBSERVATION = "observation"     # "I saw him grab my arm"
    CLAIM = "claim"                 # "He punched me" (no explicit witness)
    INTERPRETATION = "interpretation"  # "He wanted to hurt me"
    QUOTE = "quote"                 # "'Get on the ground!' he said"
    UNKNOWN = "unknown"             # Unable to classify
```

---

## Schema Changes

Location: `nnrt/ir/schema_v0_1.py`

Add to `Segment` model:

```python
class Segment(BaseModel):
    # ... existing fields ...
    
    # NEW: Statement classification
    statement_type: StatementType = Field(
        default=StatementType.UNKNOWN,
        description="Epistemic status of this statement"
    )
    statement_confidence: float = Field(
        default=0.0,
        ge=0.0, le=1.0,
        description="Confidence in statement_type classification"
    )
```

---

## Classification Pass: p22_classify_statements.py

Location: `nnrt/passes/p22_classify_statements.py`

### Pipeline Position
```
p10_segment
p20_tag_spans
p22_classify_statements  ← NEW
p25_annotate_context
p30_extract_identifiers
```

### Classification Rules

#### OBSERVATION Patterns
```python
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
]
```

#### INTERPRETATION Patterns
```python
INTERPRETATION_PATTERNS = [
    r"\b(wanted\s+to|tried\s+to|meant\s+to)\b",
    r"\b(obviously|clearly|definitely|must\s+have)\b",
    r"\b(on\s+purpose|intentionally|deliberately)\b",
    r"\b(I\s+think|I\s+believe|I\s+feel\s+like)\b",
    r"\b(probably|maybe|might\s+have|could\s+have)\b",
    r"\b(seemed\s+like|looked\s+like|appeared\s+to)\b",
]
```

#### QUOTE Detection
Already handled by `SegmentContext.DIRECT_QUOTE` — leverage this.

#### CLAIM (Default)
If no OBSERVATION or INTERPRETATION patterns match, and not a QUOTE → CLAIM.

### Algorithm

```python
def classify_statements(ctx: TransformContext) -> TransformContext:
    for segment in ctx.segments:
        text = segment.text.lower()
        
        # Check if already marked as quote
        if SegmentContext.DIRECT_QUOTE.value in segment.contexts:
            segment.statement_type = StatementType.QUOTE
            segment.statement_confidence = 0.95
            continue
        
        # Check for observation
        if _matches_any(text, OBSERVATION_PATTERNS):
            segment.statement_type = StatementType.OBSERVATION
            segment.statement_confidence = 0.85
            continue
        
        # Check for interpretation
        if _matches_any(text, INTERPRETATION_PATTERNS):
            segment.statement_type = StatementType.INTERPRETATION
            segment.statement_confidence = 0.80
            continue
        
        # Default: claim (assertion without explicit witness)
        segment.statement_type = StatementType.CLAIM
        segment.statement_confidence = 0.70
    
    return ctx
```

---

## Edge Cases

### "He grabbed me" — CLAIM or OBSERVATION?
- If narrator is the actor/target → can be OBSERVATION
- We mark as CLAIM but with lower confidence
- Future: use actor extraction to improve

### "I saw him grab her" vs "He grabbed her"
- First is OBSERVATION (explicit witness)
- Second is CLAIM (no witness stated)

### Quotes with interpretation
> "He obviously wanted to scare me," I told them.

- The outer statement is QUOTE (report of own words)
- The inner content contains INTERPRETATION
- We classify the segment as QUOTE, note interpretation in spans

---

## Testing

Create `tests/test_classify_statements.py`:

```python
@pytest.mark.parametrize("input_text,expected_type", [
    ("I saw him grab my arm", StatementType.OBSERVATION),
    ("He punched me in the face", StatementType.CLAIM),
    ("He wanted to hurt me", StatementType.INTERPRETATION),
    ("'Get on the ground!' he screamed", StatementType.QUOTE),
    ("I believe he meant to intimidate me", StatementType.INTERPRETATION),
    ("I watched him put his hand on his gun", StatementType.OBSERVATION),
])
def test_classification(input_text, expected_type):
    ...
```

---

## Exit Criteria

- [ ] `StatementType` enum exists
- [ ] `segment.statement_type` field exists
- [ ] `p22_classify_statements` pass works
- [ ] Pipeline includes new pass
- [ ] 80%+ accuracy on test corpus
- [ ] All 40 existing tests still pass

---

## Estimated Time: 4-6 hours

| Task | Hours |
|------|-------|
| Enum + Schema changes | 0.5 |
| Classification pass | 2-3 |
| Edge case handling | 1-2 |
| Testing | 1 |
