# NNRT — Intermediate Representation Specification v0.1

## Purpose

This document defines the **Intermediate Representation (IR)** for NNRT.

The IR is the **source of truth** for all transformations. Text output is a rendering of the IR.

---

## Design Principles

1. **Minimal** — Only include fields justified by failure cases
2. **Typed** — All fields have explicit types
3. **Versioned** — IR schema is versioned; breaking changes require version bump
4. **Incomplete by default** — Missing data is explicit, never inferred
5. **Never invents facts** — IR captures what was detected, not what was assumed

---

## Core Rule

> The IR captures **semantic structure without judgment**.

If a field implies judgment, intent, or truth-determination, it does not belong in the IR.

---

## Top-Level Structure

```python
@dataclass
class TransformResult:
    """The complete output of an NNRT transformation."""
    
    version: str                    # IR schema version (e.g., "0.1.0")
    request_id: str                 # Unique identifier for this transformation
    timestamp: datetime             # When transformation occurred
    
    # Core IR
    segments: list[Segment]         # Segmented input
    spans: list[SemanticSpan]       # Tagged semantic spans
    entities: list[Entity]          # Detected entities (roles, not identities)
    events: list[Event]             # Extracted events
    speech_acts: list[SpeechAct]    # Detected speech acts
    
    # Metadata
    uncertainty: list[UncertaintyMarker]  # Explicit uncertainty markers
    policy_decisions: list[PolicyDecision]  # What policy rules applied
    trace: list[TraceEntry]         # Transformation trace
    diagnostics: list[Diagnostic]   # Warnings, errors, info
    
    # Output
    rendered_text: str | None       # Final rendered output (if successful)
    status: TransformStatus         # success, partial, refused
```

---

## Segment

A **segment** is a contiguous chunk of the input text, typically a sentence or clause.

```python
@dataclass
class Segment:
    """A contiguous chunk of input text."""
    
    id: str                         # Unique segment identifier
    text: str                       # Original text
    start_char: int                 # Character offset in original input
    end_char: int                   # Character offset end
    source_line: int | None         # Line number if available
```

---

## Semantic Span

A **span** is a tagged region within a segment.

```python
@dataclass
class SemanticSpan:
    """A tagged region within a segment."""
    
    id: str                         # Unique span identifier
    segment_id: str                 # Parent segment
    start_char: int                 # Offset within segment
    end_char: int                   # Offset end
    text: str                       # Span text
    label: SpanLabel                # Semantic label (enum)
    confidence: float               # Model confidence (0.0-1.0)
    source: str                     # Which pass/model produced this
```

### SpanLabel Enum

```python
class SpanLabel(Enum):
    """Semantic labels for spans."""
    
    # Factual content
    OBSERVATION = "observation"     # Direct sensory observation
    ACTION = "action"               # Observable action
    STATEMENT = "statement"         # Direct quote or reported speech
    
    # Interpretive content (flagged, not removed)
    INTERPRETATION = "interpretation"  # Reporter's interpretation
    INFERENCE = "inference"         # Implied meaning
    EMOTIONAL = "emotional"         # Emotional language
    
    # Structural
    TEMPORAL = "temporal"           # Time reference
    SPATIAL = "spatial"             # Location reference
    REFERENCE = "reference"         # Reference to prior event
    
    # Problematic (require attention)
    LEGAL_CONCLUSION = "legal_conclusion"  # Legal judgment language
    INTENT_ATTRIBUTION = "intent_attribution"  # Attributing motive
    INFLAMMATORY = "inflammatory"   # Charged/inflammatory phrasing
    
    # Uncertain
    AMBIGUOUS = "ambiguous"         # Cannot classify with confidence
    UNKNOWN = "unknown"             # Unrecognized
```

---

## Entity

An **entity** is a detected actor or object in the narrative. Entities capture **roles**, not **identities**.

```python
@dataclass
class Entity:
    """A detected actor or object in the narrative."""
    
    id: str                         # Unique entity identifier
    role: EntityRole                # Role enum
    mentions: list[str]             # Span IDs that reference this entity
    
    # Metadata (optional, may be empty)
    extracted_identifiers: list[ExtractedIdentifier] | None
```

### EntityRole Enum

```python
class EntityRole(Enum):
    """Roles entities can play in a narrative."""
    
    REPORTER = "reporter"           # The person providing the narrative
    SUBJECT = "subject"             # Primary subject of the narrative
    WITNESS = "witness"             # Third-party observer
    AUTHORITY = "authority"         # Authority figure
    INSTITUTION = "institution"     # Organization/institution
    OBJECT = "object"               # Physical object
    UNKNOWN = "unknown"             # Role unclear
```

### ExtractedIdentifier

Identifiers are **extracted but not asserted**. They are optional metadata, not part of the narrative output.

```python
@dataclass
class ExtractedIdentifier:
    """An identifier extracted from text."""
    
    id: str
    type: IdentifierType            # badge_number, name, employee_id, etc.
    value: str                      # The extracted value
    span_id: str                    # Source span
    confidence: float               # Extraction confidence
```

---

## Event

An **event** is a discrete occurrence extracted from the narrative.

```python
@dataclass
class Event:
    """A discrete occurrence in the narrative."""
    
    id: str                         # Unique event identifier
    type: EventType                 # Event type enum
    description: str                # Neutral description
    
    # Evidence
    source_spans: list[str]         # Span IDs that support this event
    confidence: float               # Extraction confidence
    
    # Relationships
    actor_id: str | None            # Entity performing action (if any)
    target_id: str | None           # Entity receiving action (if any)
    temporal_marker: str | None     # Time reference (if any)
    
    # Flags
    is_uncertain: bool              # Explicitly uncertain
    requires_context: bool          # References external context
```

### EventType Enum

```python
class EventType(Enum):
    """Types of events that can be extracted."""
    
    ACTION = "action"               # Physical action
    VERBAL = "verbal"               # Speech/command
    MOVEMENT = "movement"           # Physical movement
    OBSERVATION = "observation"     # Something observed
    STATE_CHANGE = "state_change"   # Change in condition
    UNKNOWN = "unknown"             # Cannot classify
```

---

## Speech Act

A **speech act** captures direct or reported speech.

```python
@dataclass
class SpeechAct:
    """Direct or reported speech in the narrative."""
    
    id: str                         # Unique identifier
    type: SpeechActType             # Type of speech act
    speaker_id: str | None          # Entity who spoke (if known)
    content: str                    # What was said
    is_direct_quote: bool           # True if quoted directly
    source_span_id: str             # Source span
    confidence: float               # Extraction confidence
```

### SpeechActType Enum

```python
class SpeechActType(Enum):
    """Types of speech acts."""
    
    STATEMENT = "statement"         # Declarative statement
    COMMAND = "command"             # Directive/order
    QUESTION = "question"           # Interrogative
    THREAT = "threat"               # Threatening language (flagged)
    UNKNOWN = "unknown"             # Cannot classify
```

---

## Uncertainty Marker

Uncertainty must be **explicit**, never collapsed.

```python
@dataclass
class UncertaintyMarker:
    """Explicit marker of uncertainty in the IR."""
    
    id: str
    type: UncertaintyType           # Type of uncertainty
    description: str                # What is uncertain
    affected_ids: list[str]         # IDs of affected IR elements
    source: str                     # What caused the uncertainty
```

### UncertaintyType Enum

```python
class UncertaintyType(Enum):
    """Types of uncertainty."""
    
    AMBIGUOUS_REFERENCE = "ambiguous_reference"  # Unclear what is referenced
    MISSING_CONTEXT = "missing_context"          # Needs external context
    LOW_CONFIDENCE = "low_confidence"            # Model unsure
    CONTRADICTORY = "contradictory"              # Conflicting information
    INCOMPLETE = "incomplete"                    # Information missing
```

---

## Policy Decision

Every policy rule application is recorded.

```python
@dataclass
class PolicyDecision:
    """A policy rule that was applied."""
    
    id: str
    rule_id: str                    # Which rule fired
    action: PolicyAction            # What action was taken
    reason: str                     # Why
    affected_ids: list[str]         # What IR elements were affected
```

### PolicyAction Enum

```python
class PolicyAction(Enum):
    """Actions a policy rule can take."""
    
    ACCEPT = "accept"               # Accept as-is
    FLAG = "flag"                   # Flag for attention
    TRANSFORM = "transform"         # Transform content
    STRIP = "strip"                 # Remove from output
    REFUSE = "refuse"               # Refuse entire input
    WARN = "warn"                   # Add warning
```

---

## Trace Entry

Every transformation is traced.

```python
@dataclass
class TraceEntry:
    """A single transformation trace entry."""
    
    id: str
    timestamp: datetime
    pass_name: str                  # Which pass
    action: str                     # What happened
    before: str | None              # State before (if applicable)
    after: str | None               # State after (if applicable)
    affected_ids: list[str]         # What was affected
```

---

## Diagnostic

Warnings, errors, and info messages.

```python
@dataclass
class Diagnostic:
    """A diagnostic message."""
    
    id: str
    level: DiagnosticLevel          # error, warning, info
    code: str                       # Diagnostic code
    message: str                    # Human-readable message
    source: str                     # What produced this
    affected_ids: list[str]         # Related IR elements
```

---

## Transform Status

```python
class TransformStatus(Enum):
    """Overall transformation status."""
    
    SUCCESS = "success"             # Full transformation completed
    PARTIAL = "partial"             # Partial output (some refused)
    REFUSED = "refused"             # Entire input refused
    ERROR = "error"                 # Technical error occurred
```

---

## Versioning

The IR is versioned using semantic versioning:

- **Major** — Breaking changes to structure
- **Minor** — New optional fields
- **Patch** — Documentation/clarification only

Current version: **0.1.0**

---

## Validation Requirements

Every IR instance must pass:

1. **Schema validation** — All required fields present, correct types
2. **Referential integrity** — All ID references resolve
3. **Confidence bounds** — All confidence values in [0.0, 1.0]
4. **No empty required lists** — segments must have at least one entry
5. **Trace completeness** — Every pass must produce at least one trace entry

---

## What the IR Does NOT Contain

The IR explicitly does **not** include:

- Truth assertions
- Intent determination
- Credibility scores
- Guilt/innocence
- Legal conclusions
- Reconciled contradictions
- "Best guess" interpretations

If any of these appear in the IR, the design is wrong.

---

## Closing Note

The IR is the contract between all pipeline stages.

If a pass cannot express its output in IR terms, the IR must be extended (with justification) — or the pass is out of scope.
