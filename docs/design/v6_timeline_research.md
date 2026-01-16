# V6 Timeline Reconstruction — Research & Redesign

## Status: ✅ IMPLEMENTED (2026-01-16)
## Created: 2026-01-16

> **See [/docs/v6_features.md](../v6_features.md) for usage documentation.**
> **See [/examples/](../../examples/) for example scripts.**

---

## 1. Research Summary

### Key Findings from Academic Literature

#### 1.1 Temporal Information Extraction (TIE) Pipeline

Based on current NLP research, a proper timeline reconstruction requires these **distinct stages**:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    TEMPORAL INFORMATION EXTRACTION                       │
├─────────────────┬─────────────────┬─────────────────┬───────────────────┤
│  Stage 1        │  Stage 2        │  Stage 3        │  Stage 4          │
│  EVENT          │  TEMPORAL       │  TEMPORAL       │  TIMELINE         │
│  IDENTIFICATION │  EXPRESSION     │  RELATION       │  GENERATION       │
│                 │  RECOGNITION    │  EXTRACTION     │                   │
├─────────────────┼─────────────────┼─────────────────┼───────────────────┤
│ What happened?  │ When markers?   │ How do events   │ Final ordering    │
│ Who did what?   │ Normalize to    │ relate in time? │ with gaps and     │
│                 │ TIMEX3 format   │ (Allen's logic) │ confidence        │
└─────────────────┴─────────────────┴─────────────────┴───────────────────┘
```

#### 1.2 Allen's Interval Algebra — 13 Temporal Relations

Allen (1983) defined 13 exhaustive relations between time intervals:

| Relation | Inverse | Description | Example |
|----------|---------|-------------|---------|
| BEFORE | AFTER | A ends before B starts | A ──── B ──── |
| MEETS | MET_BY | A ends exactly when B starts | A ────≡B ──── |
| OVERLAPS | OVERLAPPED_BY | A starts first, ends during B | A ────╲B ──── |
| STARTS | STARTED_BY | A and B start together, A ends first | A ──╲B ────── |
| DURING | CONTAINS | A is entirely within B | ─ A ─ B ──── |
| FINISHES | FINISHED_BY | A starts after B, end together | ─ A ──╱B ──── |
| EQUALS | EQUALS | A and B have identical intervals | A ≡≡≡≡ B ≡≡≡≡ |

**Key Insight**: Current implementation only tracks `before_entry_ids` and `after_entry_ids`, missing the richer relation types.

#### 1.3 TimeML TIMEX3 Standard

Temporal expressions should be normalized to:
- **DATE**: `2026-01-10`
- **TIME**: `T23:30:00`
- **DURATION**: `PT20M` (20 minutes)
- **SET**: Recurring times

**Current Gap**: Our implementation stores raw strings like "11:30 PM" — not normalized.

#### 1.4 LLM Limitations in Temporal Reasoning

2024 research (TRAM benchmark) shows:
- LLMs struggle with temporal reasoning
- Best LLMs still fall "significantly short of human performance"
- Hybrid approaches (rules + embeddings) work better

**Implication**: Don't rely solely on LLM; use structured rules.

---

## 2. Current Implementation Analysis

### What Exists (p44_timeline.py)

```python
# Current Strengths:
✓ Uses existing TIME/DATE identifiers from p30
✓ Detects relative patterns: then, after, later, before, during
✓ Builds TimelineEntry objects
✓ Computes sequence_order
✓ Has before/after linking

# Current Weaknesses:
✗ Associates time to event by character position (fragile)
✗ No time normalization (stores "11:30 PM" not ISO format)
✗ Single-day assumption (no day_offset tracking)
✗ No gap detection between events
✗ Only BEFORE/AFTER relations (not full Allen's 13)
✗ No statement-to-timeline linking (events only)
✗ No confidence propagation for uncertain placements
✗ No rendered output (timeline not displayed to user)
```

### Test Coverage (test_p44_timeline.py)

- 9 test cases
- Covers: absolute times, relative markers, sequence ordering, edge cases
- **Missing**: multi-day narratives, gap detection, confidence scoring

---

## 3. Redesigned Timeline System

### 3.1 New Data Model

```python
class TemporalExpression(BaseModel):
    """Normalized temporal expression following TIMEX3-like standard."""
    
    id: str
    original_text: str                    # "11:30 PM", "the next day"
    type: TemporalExpressionType         # DATE, TIME, DURATION, RELATIVE
    
    # Normalized values (ISO-like)
    normalized_value: Optional[str]       # "T23:30:00" or "2026-01-10"
    
    # For relative expressions
    anchor_type: Optional[AnchorType]     # DOCUMENT_TIME, PREVIOUS_EVENT, EXPLICIT
    anchor_reference: Optional[str]       # What this is relative to
    
    # Position in text
    start_char: int
    end_char: int
    segment_id: str
    
    confidence: float


class TemporalRelation(BaseModel):
    """Allen-style temporal relation between two temporal entities."""
    
    id: str
    source_id: str         # Event/statement ID
    target_id: str         # Event/statement ID
    
    relation: AllenRelation  # BEFORE, AFTER, MEETS, OVERLAPS, DURING, etc.
    
    # Evidence for this relation
    evidence_type: RelationEvidence  # EXPLICIT_MARKER, IMPLICIT_ORDER, INFERRED
    evidence_text: Optional[str]     # The marker that indicated this
    
    confidence: float


class TimelineEntry(BaseModel):
    """A positioned element in the reconstructed timeline."""
    
    id: str
    
    # What this entry represents (expanded)
    event_id: Optional[str]
    statement_id: Optional[str]       # NEW: Can link to atomic statements
    
    # Temporal information (enhanced)
    day_offset: int = 0               # NEW: 0=incident day, 1=next day, etc.
    time_expression_id: Optional[str] # Link to TemporalExpression
    
    # Normalized time (NEW)
    normalized_time: Optional[str]    # ISO format: "T23:30:00"
    normalized_date: Optional[str]    # ISO format: "2026-01-10"
    
    # For relative/inferred times
    estimated_minutes_from_start: Optional[int]  # NEW: Estimated offset
    
    # Ordering
    sequence_order: int
    
    # Gap detection (NEW)
    gap_before: Optional[TimeGap]
    
    # Confidence and source
    placement_confidence: float
    time_source: TimeSource           # EXPLICIT, RELATIVE, INFERRED
    
    # Relations to other entries (enhanced)
    temporal_relations: list[str]     # TemporalRelation IDs


class TimeGap(BaseModel):
    """A detected gap in the timeline that may need investigation."""
    
    id: str
    
    # Position
    after_entry_id: str
    before_entry_id: str
    
    # Gap characteristics
    gap_type: TimeGapType             # EXPLAINED, UNEXPLAINED, UNCERTAIN
    estimated_duration_minutes: Optional[int]
    
    # For explained gaps
    explanation_text: Optional[str]   # "20 minutes later", "the next day"
    
    # Investigation flag
    requires_investigation: bool
    suggested_question: Optional[str] # For question generation


class AllenRelation(str, Enum):
    """Allen's 13 temporal interval relations."""
    
    BEFORE = "before"
    AFTER = "after"
    MEETS = "meets"
    MET_BY = "met_by"
    OVERLAPS = "overlaps"
    OVERLAPPED_BY = "overlapped_by"
    STARTS = "starts"
    STARTED_BY = "started_by"
    DURING = "during"
    CONTAINS = "contains"
    FINISHES = "finishes"
    FINISHED_BY = "finished_by"
    EQUALS = "equals"
    
    # Uncertainty
    UNKNOWN = "unknown"
```

### 3.2 New Pipeline Architecture

Replace single `p44_timeline` with modular stages:

```
┌────────────────────────────────────────────────────────────────────────────┐
│                          TIMELINE RECONSTRUCTION                            │
├───────────────┬───────────────┬───────────────┬───────────────────────────┤
│ p44a_tempo_   │ p44b_tempo_   │ p44c_timeline │ p44d_timeline_            │
│ expressions   │ relations     │ ordering      │ gaps                      │
├───────────────┼───────────────┼───────────────┼───────────────────────────┤
│ • Extract     │ • Find        │ • Build       │ • Detect gaps             │
│   temporal    │   temporal    │   ordered     │ • Classify as             │
│   expressions │   relations   │   timeline    │   explained/unexplained   │
│ • Normalize   │ • Apply       │ • Assign      │ • Generate                │
│   to TIMEX3   │   Allen's     │   sequence    │   investigation           │
│ • Link to     │   algebra     │   numbers     │   questions               │
│   statements  │               │               │                           │
└───────────────┴───────────────┴───────────────┴───────────────────────────┘
```

### 3.3 Multi-Day Handling

```
Algorithm:
1. Establish DAY_ZERO:
   - If explicit date in narrative → use as anchor
   - Otherwise → "incident day" (day_offset = 0)

2. Detect day transitions:
   - "the next day", "the following morning" → increment day_offset
   - "three days later" → day_offset += 3
   - New explicit date → calculate offset from DAY_ZERO

3. Build day-segmented timeline:
   DAY 0: [event1, event2, event3]
   DAY 1: [event4, event5]
   DAY N: [event6]

4. Handle cross-day time comparisons correctly:
   - 11:30 PM Day 0 happens BEFORE 9:00 AM Day 1
   - 3:00 AM Day 1 happens BEFORE 11:30 PM Day 0 (next day scenario)
```

### 3.4 Gap Detection Algorithm

```
For each pair of consecutive timeline entries (A, B):

1. CALCULATE GAP:
   if A.normalized_time and B.normalized_time and same_day:
     gap_minutes = time_diff(A, B)
   else if B.estimated_minutes_from_start:
     gap_minutes = B.estimated_minutes - A.estimated_minutes
   else:
     gap_minutes = UNKNOWN

2. CLASSIFY GAP:
   if gap_minutes == UNKNOWN:
     gap_type = UNCERTAIN
   else if B has relative_time marker ("20 minutes later"):
     gap_type = EXPLAINED
     explanation = B.relative_time
   else if gap_minutes > THRESHOLD (e.g., 10 minutes):
     gap_type = UNEXPLAINED
     
3. FLAG FOR INVESTIGATION:
   if gap_type == UNEXPLAINED and gap_minutes > 5:
     requires_investigation = True
     suggested_question = f"What happened during the ~{gap_minutes} minutes between {A.description} and {B.description}?"
```

### 3.5 Rendering Timeline in Output

New section in structured report:

```
══════════════════════════════════════════════════════════════════════════════
                          RECONSTRUCTED TIMELINE
══════════════════════════════════════════════════════════════════════════════

Note: Timeline reconstructed from narrative with confidence levels shown.
      ⚠️ marks unexplained gaps or low-confidence placements.

────────────────────────────────────────────────────────────────────────────
 DAY 1: Wednesday, January 10, 2026
────────────────────────────────────────────────────────────────────────────

  11:30 PM │ Reporter was walking on Cedar Street
           │ Source: Explicit time "At 11:30 PM"
           │ Confidence: 95%
           │
  ~11:32   │ Officers Jenkins and Rodriguez approached Reporter
           │ Source: Inferred from sequence
           │ Confidence: 70%
           │
           ├─ ⚠️ GAP: ~5 minutes unaccounted
           │
  ~11:37   │ Reporter was grabbed by Officer Jenkins
           │ Source: Relative "then grabbed"
           │ Confidence: 80%
           │
  11:47 PM │ Bystander Patricia Chen began recording
           │ Source: Explicit time "At 11:47 PM"
           │ Confidence: 95%

────────────────────────────────────────────────────────────────────────────
 DAY 2: Thursday, January 11, 2026
────────────────────────────────────────────────────────────────────────────

  Morning  │ Reporter went to emergency room
           │ Source: Relative "The next day I went to the ER"
           │ Confidence: 60%
           │
           ├─ ⚠️ GAP: Duration of ER visit not specified
           │
  Unspec.  │ Reporter filed formal complaint
           │ Source: Relative "after that"
           │ Confidence: 50%

────────────────────────────────────────────────────────────────────────────
 STATUS SUMMARY
────────────────────────────────────────────────────────────────────────────
  
  Total Events: 6
  With Explicit Time: 2 (33%)
  With Relative Time: 3 (50%)
  Inferred Only: 1 (17%)
  
  Unexplained Gaps: 2
  Low-Confidence Placements: 2

══════════════════════════════════════════════════════════════════════════════
```

---

## 4. Implementation Plan

### Phase 1: Foundation (3-4 hours)

| Task | Description | Effort |
|------|-------------|--------|
| 1.1 | Define new enums in `enums.py` | 0.5h |
| 1.2 | Add TemporalExpression model to schema | 0.5h |
| 1.3 | Add TemporalRelation model to schema | 0.5h |
| 1.4 | Enhance TimelineEntry model | 0.5h |
| 1.5 | Add TimeGap model | 0.5h |
| 1.6 | Add AllenRelation enum | 0.5h |

### Phase 2: Temporal Expression Extraction (3 hours)

| Task | Description | Effort |
|------|-------------|--------|
| 2.1 | Create p44a_temporal_expressions.py | 1h |
| 2.2 | Implement TIMEX3-style normalization | 1h |
| 2.3 | Link expressions to statements/events | 0.5h |
| 2.4 | Tests | 0.5h |

### Phase 3: Relation Extraction (2 hours)

| Task | Description | Effort |
|------|-------------|--------|
| 3.1 | Create p44b_temporal_relations.py | 1h |
| 3.2 | Map text markers to Allen relations | 0.5h |
| 3.3 | Tests | 0.5h |

### Phase 4: Timeline Ordering (2 hours)

| Task | Description | Effort |
|------|-------------|--------|
| 4.1 | Rewrite p44c_timeline_ordering.py | 1h |
| 4.2 | Implement multi-day handling | 0.5h |
| 4.3 | Tests | 0.5h |

### Phase 5: Gap Detection (2 hours)

| Task | Description | Effort |
|------|-------------|--------|
| 5.1 | Create p44d_timeline_gaps.py | 1h |
| 5.2 | Implement investigation flagging | 0.5h |
| 5.3 | Tests | 0.5h |

### Phase 6: Rendering (2 hours)

| Task | Description | Effort |
|------|-------------|--------|
| 6.1 | Add timeline section to structured.py | 1h |
| 6.2 | Format with day breaks, gaps, confidence | 0.5h |
| 6.3 | Tests | 0.5h |

### Total: ~14 hours

---

## 5. Test Cases (TDD)

### Temporal Expression Tests
```python
def test_normalizes_time_to_iso():
    """'11:30 PM' → 'T23:30:00'"""

def test_normalizes_date_to_iso():
    """'January 10th, 2026' → '2026-01-10'"""

def test_extracts_relative_markers():
    """'the next day', '20 minutes later' extracted"""
```

### Multi-Day Tests
```python
def test_multi_day_narrative():
    """Incident on Day 1, ER on Day 2, complaint on Day 3"""

def test_cross_midnight_ordering():
    """11:30 PM → 3:00 AM correctly ordered across midnight"""
```

### Gap Detection Tests
```python
def test_detects_unexplained_gap():
    """20 minute gap without marker → flagged"""

def test_explained_gap_not_flagged():
    """'20 minutes later' → gap explained, not flagged"""
```

### Allen Relation Tests
```python
def test_during_relation():
    """'while he was holding me' → DURING relation"""

def test_meets_relation():
    """'as soon as' → MEETS relation"""
```

---

## 6. Decision Points

### Question 1: Keep or Replace p44_timeline.py?

**Option A**: Incrementally enhance
- Pro: Less disruptive
- Con: Carries forward architectural debt

**Option B**: Replace with modular passes ✓
- Pro: Clean architecture, easier to test
- Con: More initial work

**Recommendation**: Option B — clean slate with proper separation of concerns.

### Question 2: Use timexy library for temporal expressions?

**Option A**: Use timexy (spaCy component)
- Pro: Battle-tested TIMEX3 normalization
- Con: Another dependency

**Option B**: Build custom extractor
- Pro: Full control, no dependency
- Con: More work to implement

**Recommendation**: Start with Option B (custom), evaluate timexy for enhancement later.

### Question 3: Allen's 13 relations or simplified set?

**Option A**: Full 13 relations
- Pro: Complete, academically correct
- Con: May be overkill for narratives

**Option B**: Simplified 7 relations (BEFORE, AFTER, MEETS, DURING, OVERLAPS, EQUALS, UNKNOWN)
- Pro: Covers most narrative needs
- Con: May miss edge cases

**Recommendation**: Option B for now, extensible to full 13 later.

---

## 7. Next Steps

1. **Review this analysis** — Does this approach make sense?
2. **Approve scope** — 14 hours estimated
3. **Begin Phase 1** — Foundation models
4. **Iterate** — Test-driven development for each phase
