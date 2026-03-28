# p51 — Contradiction Detection Pass

**Spec version:** 1.0  
**Author:** architect agent  
**Date:** 2026-03-28  
**Status:** Draft — awaiting lead approval before implementation  
**Milestone:** [Milestone 3 — Intelligence & Edge Cases](../milestones/milestone3.md)

---

## 1. Purpose

The contradiction detection pass (`p51_detect_contradictions`) identifies pairs of statements in the IR that are logically, temporally, or positionally incompatible with one another.

NNRT's goal is to transform narrative text into a neutral report without losing factual fidelity. Contradictions within a narrative are significant forensic signals — they may indicate:

- Unreliable narration (memory gaps, fabrication)
- Physical impossibility (sequential events that cannot both be true)
- Timeline inconsistency (two events asserted at the same time)
- Positional conflict (actor asserted in two places simultaneously)

This pass **does not resolve or discard** conflicting statements. It flags them for human review and enriches the IR with structured `ContradictionRecord` objects that downstream passes and renderers can act on.

---

## 2. Position in Pipeline

```
p00_normalize
p10_segment
p20_tag_spans
p22_classify_statements
p25_annotate_context
p26_decompose
p27_classify_atomic
p27b_attribute_statements
p27_epistemic_tag
p28_link_provenance
p30_extract_identifiers
p32_extract_entities
p33_resolve_text_coref
p34_extract_events
p35_classify_events
p36_resolve_quotes
p38_extract_items
p40_build_ir
p42_coreference
p43_resolve_actors
p44a_temporal_expressions
p44b_temporal_relations
p44c_timeline_ordering
p44d_timeline_gaps
p46_group_statements
p48_classify_evidence
p50_policy
p51_detect_contradictions   ← THIS PASS (NEW)
p55_select
p60_augment_ir
p70_render
p72_safety_scrub
p75_cleanup_punctuation
p80_package
p90_render_structured
```

**Why after p50?** Policy decisions from p50 may suppress or flag content that would otherwise trigger false contradiction signals. Running p51 after p50 ensures the contradiction engine operates on the post-policy IR and respects any already-flagged content.

**Why before p55?** The selection pass (p55) uses quality scores to select events for output. ContradictionRecords must be present before selection so that contradicted events can be deprioritized or flagged in the final output.

---

## 3. Inputs

All inputs are read from `TransformContext`. This pass reads but does not mutate any existing field.

| Field | Type | Source Pass | Notes |
|-------|------|-------------|-------|
| `ctx.atomic_statements` | `list[AtomicStatement]` | p26_decompose | Primary source: each statement is a candidate for contradiction |
| `ctx.statement_groups` | `list[StatementGroup]` | p46_group_statements | Used to scope cross-group contradiction checks |
| `ctx.timeline` | `list[TimelineEntry]` | p44a–p44d | Used for temporal contradiction detection |
| `ctx.temporal_expressions` | `list[TemporalExpression]` | p44a | Normalized times for temporal comparison |
| `ctx.temporal_relationships` | `list[TemporalRelationship]` | p44b | Existing Allen relations to augment (not replace) |
| `ctx.entities` | `list[Entity]` | p32_extract_entities | Actor identity for positional contradictions |
| `ctx.policy_decisions` | `list[PolicyDecision]` | p50_policy | Skip statements whose segments are already refused/suppressed |
| `ctx.evidence_classifications` | `list[EvidenceClassification]` | p48_classify_evidence | Reliability weights and existing `contradicting_ids` hints |

---

## 4. Output

### 4.1 New IR Collection

This pass appends one new field to `TransformContext`:

```python
ctx.contradictions: list[ContradictionRecord]
```

`ContradictionRecord` must also be added to `TransformResult` and `schema_v0_1.py`.

### 4.2 ContradictionRecord Schema

```python
class ContradictionRecord(BaseModel):
    """A detected conflict between two statements in the IR."""

    id: str = Field(..., description="Unique record identifier (uuid4 prefixed 'cont-')")

    # The two conflicting statements
    statement_a_id: str = Field(..., description="ID of first atomic statement")
    statement_b_id: str = Field(..., description="ID of second atomic statement")

    # Classification
    contradiction_type: ContradictionType = Field(
        ...,
        description="Category of contradiction"
    )

    # Severity
    severity: ContradictionSeverity = Field(
        ...,
        description="How serious the conflict is"
    )

    # Confidence
    confidence: float = Field(
        ...,
        ge=0.0, le=1.0,
        description="Confidence that this is a genuine contradiction (not noise)"
    )

    # Human-readable summary
    description: str = Field(
        ...,
        description="One-sentence plain-language description of the conflict"
    )

    # Evidence
    detection_method: str = Field(
        ...,
        description="Which sub-detector produced this: 'temporal', 'physical', 'positional', 'logical'"
    )
    evidence_text_a: Optional[str] = Field(
        None,
        description="Relevant text excerpt from statement A"
    )
    evidence_text_b: Optional[str] = Field(
        None,
        description="Relevant text excerpt from statement B"
    )

    # Impact on downstream passes
    affects_timeline: bool = Field(
        False,
        description="Whether this contradiction invalidates timeline ordering"
    )
    affects_actor: Optional[str] = Field(
        None,
        description="Entity ID whose account is contradicted (if applicable)"
    )
```

### 4.3 New Enums (add to `nnrt/ir/enums.py`)

```python
class ContradictionType(str, Enum):
    """Category of detected contradiction."""
    TEMPORAL    = "temporal"     # Two events placed at the same time
    PHYSICAL    = "physical"     # Physical impossibility (restrained → punched)
    POSITIONAL  = "positional"   # Actor in two places simultaneously
    LOGICAL     = "logical"      # Direct logical negation ("never touched" → "after I shoved")
    TESTIMONIAL = "testimonial"  # One account contradicts another person's account


class ContradictionSeverity(str, Enum):
    """How serious the conflict is."""
    HIGH    = "high"    # Almost certainly a contradiction; warrants review
    MEDIUM  = "medium"  # Likely contradiction; may be phrasing ambiguity
    LOW     = "low"     # Possible inconsistency; may be metaphor or imprecision
```

### 4.4 New Diagnostic Code

Add to `DiagnosticLevel` usage (no enum change needed):

```
code: "CONTRADICTION_DETECTED"
level: WARNING
message: "Statements {a_id} and {b_id} appear to contradict each other ({type})"
affected_ids: [statement_a_id, statement_b_id]
source: "p51_detect_contradictions"
```

---

## 5. Algorithm Design

The pass is structured as a coordinator that runs four typed sub-detectors in sequence. Each sub-detector produces `ContradictionRecord` candidates; the coordinator deduplicates and scores them.

```
detect_contradictions(ctx)
├── _run_temporal_detector(ctx)       → list[ContradictionRecord]
├── _run_physical_detector(ctx)       → list[ContradictionRecord]
├── _run_positional_detector(ctx)     → list[ContradictionRecord]
├── _run_logical_detector(ctx)        → list[ContradictionRecord]
└── _deduplicate_and_score(candidates) → list[ContradictionRecord]
```

### 5.1 Temporal Detector

**Goal:** Find two statements that assert incompatible times for the same actor or event.

**Algorithm:**
1. Collect all `TimelineEntry` objects that have a `normalized_time` and an associated `statement_id`.
2. Group entries by `day_offset`.
3. Within each day, find pairs where:
   - Both entries have the same `normalized_time` (±5 min tolerance)
   - The entries are linked to the **same entity** (via actor reference)
   - The entries describe **mutually exclusive locations or states**
4. For each such pair, emit a `ContradictionRecord(type=TEMPORAL, severity=HIGH)`.

**Example:**
> "At 3:00 PM I was at home." / "At 3:00 PM I was arrested at the corner of Main St."

**False-positive guard:** If both entries have `time_confidence < 0.4`, downgrade severity to MEDIUM.

### 5.2 Physical Detector

**Goal:** Find sequential statements where a physical state in B is impossible given a physical state in A.

**Algorithm:**
1. Build an ordered list of `atomic_statements` by their linked `TimelineEntry.sequence_order`.
2. Apply a **physical state machine** per actor:
   - State transitions are one-way: e.g., `HANDCUFFED → UNABLE_TO_STRIKE`
   - Incompatible states trigger a contradiction
3. Physical state rules (pattern-based, extensible via YAML):
   | State A | Impossible State B |
   |---------|-------------------|
   | `HANDCUFFED` | `PUNCHED`, `GRABBED`, `PUSHED` (as actor) |
   | `UNCONSCIOUS` | `SAID`, `RAN`, `WALKED` |
   | `PINNED_TO_GROUND` | `REACHED_FOR`, `MOVED_TOWARD` (as actor) |
4. Emit `ContradictionRecord(type=PHYSICAL, severity=HIGH)` for each violation.

**Example:**
> "He was handcuffed and on the ground." / "He then grabbed the officer's weapon."

### 5.3 Positional Detector

**Goal:** Find two statements placing the same actor in two incompatible locations at the same time.

**Algorithm:**
1. Extract location mentions from `SemanticSpan` (label `LOCATION`) linked to each statement.
2. Find pairs of statements that:
   - Reference the same actor (via `entity_id`)
   - Have matching or overlapping normalized times
   - Reference distinct named locations
3. Emit `ContradictionRecord(type=POSITIONAL, severity=MEDIUM)`.

**Note:** Severity is MEDIUM by default because location mentions are often imprecise or metaphorical.

### 5.4 Logical Detector

**Goal:** Detect direct negation patterns between statements.

**Algorithm:**
1. For each atomic statement pair `(A, B)` within the same `StatementGroup` or adjacent groups:
2. Check for negation inversion patterns:
   - A contains `"never X"` / `"did not X"` and B contains the same verb `X` with the same actor
   - A contains a universal qualifier (`"always"`, `"never"`) and B presents a counter-instance
3. Use the actor's `entity_id` to ensure the same actor is referenced.
4. Emit `ContradictionRecord(type=LOGICAL, severity=HIGH)`.

**Example:**
> "I never touched him." / "After I shoved him, he fell."

**Complexity note:** This detector should only compare statements within a window of ±10 statements to bound quadratic complexity. For large narratives, chunk by `StatementGroup`.

### 5.5 Deduplication and Scoring

```python
def _deduplicate_and_score(candidates: list[ContradictionRecord]) -> list[ContradictionRecord]:
    """Merge duplicate pairs; promote severity if multiple detectors agree."""
    ...
```

- Two records are **duplicate** if they share the same `(statement_a_id, statement_b_id)` pair (order-independent).
- If two detectors flag the same pair: promote severity by one level (LOW→MEDIUM, MEDIUM→HIGH) and take the higher confidence score.
- Discard records where `confidence < 0.3` to suppress noise.

---

## 6. Integration in `__init__.py`

Add to `nnrt/passes/__init__.py`:

```python
from nnrt.passes.p51_detect_contradictions import detect_contradictions
```

Add to the default pipeline in `nnrt/core/engine.py` (or pipeline config) after `evaluate_policy`:

```python
evaluate_policy,
detect_contradictions,   # p51
select,                  # p55
```

---

## 7. Pass Signature

```python
# nnrt/passes/p51_detect_contradictions.py

from nnrt.core.context import TransformContext

PASS_NAME = "p51_detect_contradictions"


def detect_contradictions(ctx: TransformContext) -> TransformContext:
    """
    Detect contradictions between statements in the IR.

    Reads: atomic_statements, statement_groups, timeline, temporal_expressions,
           entities, policy_decisions, evidence_classifications
    Writes: ctx.contradictions (new field), ctx.diagnostics (appends)

    Does NOT modify existing IR fields.
    Returns: ctx with contradictions populated
    """
    ...
```

`TransformContext` must be extended:

```python
# In nnrt/core/context.py, add to TransformContext:
contradictions: list["ContradictionRecord"] = field(default_factory=list)
```

And in `TransformResult` (schema_v0_1.py):

```python
contradictions: list[ContradictionRecord] = Field(
    default_factory=list,
    description="Detected conflicts between IR statements"
)
```

---

## 8. Performance Constraints

| Constraint | Target |
|------------|--------|
| Pass wall-clock time | < 500 ms per narrative (all four detectors) |
| Pair comparison bound | O(n²) within group; O(n) across timeline |
| Max pairs evaluated | ≤ 10,000 per narrative (chunk large inputs) |
| Memory overhead | No new data structures larger than the statement list |

The logical detector's pairwise comparison is the only O(n²) component. It is bounded by the ±10-statement window and by `StatementGroup` chunking.

---

## 9. Test Strategy

### 9.1 Golden Tests

Create `tests/passes/test_p51_contradiction_detection.py` with the following golden cases:

#### Group A — Temporal Contradictions

| Test ID | Input A | Input B | Expected Type | Expected Severity |
|---------|---------|---------|---------------|-------------------|
| `gold_p51_t01` | "At 3pm I was at home." | "At 3pm he was arrested at the station." | TEMPORAL | HIGH |
| `gold_p51_t02` | "Around 3pm..." | "About 3pm..." | TEMPORAL | MEDIUM (low time_confidence) |

#### Group B — Physical Contradictions

| Test ID | Input A | Input B | Expected Type | Expected Severity |
|---------|---------|---------|---------------|-------------------|
| `gold_p51_p01` | "He was handcuffed on the ground." | "He then punched the officer." | PHYSICAL | HIGH |
| `gold_p51_p02` | "She was unconscious." | "She said 'let me go'." | PHYSICAL | HIGH |

#### Group C — Logical Contradictions

| Test ID | Input A | Input B | Expected Type | Expected Severity |
|---------|---------|---------|---------------|-------------------|
| `gold_p51_l01` | "I never touched him." | "After I shoved him, he fell." | LOGICAL | HIGH |
| `gold_p51_l02` | "He always complied." | "He refused the officer's command." | LOGICAL | MEDIUM |

#### Group D — Non-Contradiction (False Positive Guard)

| Test ID | Input | Expected Result |
|---------|-------|-----------------|
| `gold_p51_n01` | "He walked to the car. He then opened the door." | No contradiction |
| `gold_p51_n02` | "She approximately said 3pm." | No contradiction (single statement) |

### 9.2 Unit Tests

- Each sub-detector has its own unit tests with synthetic `TransformContext` fixtures.
- Test deduplication: same pair flagged by two detectors → single record, severity promoted.
- Test confidence threshold: records with `confidence < 0.3` are filtered out.

### 9.3 Integration Tests

- Run the full pipeline on `tests/fixtures/stress_test_narrative.txt` with at least one injected contradiction.
- Verify `TransformResult.contradictions` is non-empty and the appropriate diagnostic is present.
- Verify no existing passing tests are broken.

### 9.4 Hard Case Coverage

This pass directly addresses Milestone 3 hard cases:

| Hard Case Level | Case | Covered By |
|----------------|------|------------|
| 8 | Self-contradiction | Physical + Logical detector |
| 8 | Timeline inconsistency | Temporal detector |

---

## 10. Out of Scope (v1)

The following are intentionally deferred to a future version:

| Item | Reason |
|------|--------|
| Cross-document contradictions | Requires multi-document context (not in scope for single-narrative transform) |
| Speaker-attributed contradictions (TESTIMONIAL type) | Requires reliable speaker resolution across all SpeechActs; p36 resolution confidence not yet stable enough |
| ML-based contradiction scoring | Rule-based first; ML upgrade when golden test corpus is ≥ 50 labeled pairs |
| Contradiction resolution / arbitration | NNRT preserves all statements; resolution is a human decision |

---

## 11. Governance

Per NNRT project rule: **every new pass requires a backing spec before code may be written.**

This document satisfies that requirement for `p51_detect_contradictions`.

**Approval gate:** @lead must approve this spec before the implementation task is created or assigned.

---

## 12. References

- [Milestone 3 — Intelligence & Edge Cases](../milestones/milestone3.md)
- [IR Schema v0.1](../IR_SPEC_v0_1.md)
- [p48 Evidence Classification](../../nnrt/passes/p48_classify_evidence.py) — existing `contradicting_ids` field
- [p44b Temporal Relations](../../nnrt/passes/p44b_temporal_relations.py) — Allen temporal model
- [p50 Policy Pass](../../nnrt/passes/p50_policy.py) — upstream policy decisions
