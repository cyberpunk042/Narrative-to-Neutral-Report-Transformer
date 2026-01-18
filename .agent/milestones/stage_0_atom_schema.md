# Stage 0: Atom Schema Enhancement

## Objective

Enhance the IR schema so that all classification metadata has a permanent home on the atoms themselves. Classification results should be computed in the pipeline and stored on atoms, NOT computed at render-time.

**Outcome**: Every atom carries its own classification state. The renderer can simply check `atom.is_camera_friendly` instead of calling a function to compute it.

---

## Current State

### Atom Types in NNRT

| Type | Location | Status |
|------|----------|--------|
| `AtomicStatement` | `p26_decompose.py` | dataclass, comprehensive |
| `Entity` | `ir/schema_v0_1.py` | Pydantic, partial |
| `Event` | `ir/schema_v0_1.py` | Pydantic, minimal |
| `TimelineEntry` | `ir/schema_v0_1.py` | Pydantic, comprehensive |
| `SpeechAct` | `ir/schema_v0_1.py` | Pydantic, partial |
| `ExtractedAction` | `enhanced_event_extractor.py` | dataclass, temporary |

### What AtomicStatement Already Has (Good)

```python
@dataclass
class AtomicStatement:
    # Core identity
    id: str
    text: str
    segment_id: str
    span_start: int
    span_end: int
    
    # Epistemic classification
    source: str                    # reporter, witness, medical, etc.
    epistemic_type: str            # direct_event, self_report, interpretation, etc.
    polarity: str                  # asserted, denied, uncertain
    evidence_source: str           # direct_observation, self_report, etc.
    
    # Provenance
    source_type: str
    source_entity_id: Optional[str]
    provenance_status: str         # verified, cited, missing, etc.
    
    # Attribution
    attributed_text: Optional[str]
    is_aberrated: bool
    aberration_reason: Optional[str]
    
    # Resolution
    actor_resolved_text: Optional[str]
```

This is already quite rich. The AtomicStatement is in good shape.

### What Event Is Missing

```python
class Event(BaseModel):
    id: str
    type: EventType
    description: str
    
    # Has actor/target linking
    actor_id: Optional[str]
    target_id: Optional[str]
    actor_label: Optional[str]
    action_verb: Optional[str]
    
    # Flags (basic)
    is_uncertain: bool
    requires_context: bool
    
    # MISSING:
    # - is_camera_friendly: bool
    # - camera_friendly_reason: Optional[str]
    # - is_follow_up: bool
    # - is_fragment: bool
    # - contains_quote: bool
    # - neutralized_description: Optional[str]
    # - actor_resolved: bool
    # - quality_score: float
```

### What Is Computed at Render-Time (Problem)

In `structured.py`, this function runs for EVERY event at render time:

```python
def is_strict_camera_friendly(text: str) -> tuple[bool, str]:
    """
    Checks:
    - Rule 1: No conjunction starts
    - Rule 2: No embedded quotes  
    - Rule 3: No verb-first fragments
    - Rule 4: Must have named actor
    - Rule 5: Pronoun starts need named actor
    - Rule 6: No interpretive content
    """
```

This should be pre-computed in the pipeline and stored as:
- `Event.is_camera_friendly: bool`
- `Event.camera_friendly_reason: Optional[str]`

Similarly, `neutralize_for_observed(text)` computes a stripped version at render-time:
- Should be stored as `Event.neutralized_description: Optional[str]`

---

## Target State

### Enhanced Event Schema

```python
class Event(BaseModel):
    """A discrete occurrence in the narrative."""
    
    # === EXISTING FIELDS ===
    id: str
    type: EventType
    description: str
    source_spans: list[str]
    confidence: float
    actor_id: Optional[str]
    target_id: Optional[str]
    temporal_marker: Optional[str]
    actor_label: Optional[str]
    action_verb: Optional[str]
    target_label: Optional[str]
    target_object: Optional[str]
    is_uncertain: bool
    requires_context: bool
    
    # === NEW: Classification Fields ===
    
    # Camera-friendly classification
    is_camera_friendly: bool = Field(
        False, 
        description="Whether this event is observable and can appear in OBSERVED EVENTS"
    )
    camera_friendly_reason: Optional[str] = Field(
        None,
        description="If not camera-friendly, why (e.g., 'conjunction_start:but', 'no_valid_actor')"
    )
    
    # Event category
    is_follow_up: bool = Field(
        False,
        description="Whether this is a post-incident follow-up action (filing report, etc.)"
    )
    is_fragment: bool = Field(
        False,
        description="Whether this is an incomplete/fragment event"
    )
    
    # Content flags
    contains_quote: bool = Field(
        False,
        description="Whether event description contains embedded quotes"
    )
    contains_interpretive: bool = Field(
        False,
        description="Whether event contains interpretive/legal language"
    )
    
    # Neutralization
    neutralized_description: Optional[str] = Field(
        None,
        description="Description with interpretive words stripped"
    )
    
    # Resolution status
    actor_resolved: bool = Field(
        False,
        description="Whether actor pronouns have been resolved to names"
    )
    
    # Quality assessment
    quality_score: float = Field(
        0.5,
        ge=0.0, le=1.0,
        description="Overall quality score for selection (0=low, 1=high)"
    )
```

### Enhanced Entity Schema

```python
class Entity(BaseModel):
    """A detected actor or object in the narrative."""
    
    # === EXISTING FIELDS ===
    id: str
    type: EntityType
    label: Optional[str]
    role: EntityRole
    mentions: list[str]
    extracted_identifiers: Optional[list[ExtractedIdentifier]]
    participation: Optional[Participation]
    badge_number: Optional[str]
    
    # === NEW: Classification Fields ===
    
    # Validation
    is_valid_actor: bool = Field(
        True,
        description="Whether this can serve as an actor in events (not 'it', 'this', etc.)"
    )
    is_named: bool = Field(
        False,
        description="Whether entity has a proper name (Officer Jenkins vs 'he')"
    )
    
    # Gender (for pronoun resolution)
    gender: Optional[str] = Field(
        None,
        description="Inferred gender: 'male', 'female', 'neutral', None=unknown"
    )
    
    # Domain classification
    domain_role: Optional[str] = Field(
        None,
        description="Domain-specific role (e.g., 'subject_officer', 'medical_provider')"
    )
```

### Enhanced SpeechAct Schema

```python
class SpeechAct(BaseModel):
    """Direct or reported speech in the narrative."""
    
    # === EXISTING FIELDS ===
    id: str
    type: SpeechActType
    speaker_id: Optional[str]
    content: str
    is_direct_quote: bool
    source_span_id: str
    confidence: float
    speaker_label: Optional[str]
    speech_verb: str
    is_nested: bool
    raw_text: Optional[str]
    
    # === NEW: Classification Fields ===
    
    # Resolution status
    speaker_resolved: bool = Field(
        False,
        description="Whether speaker has been resolved to a named entity"
    )
    speaker_validation: Optional[str] = Field(
        None,
        description="Validation status: 'valid', 'pronoun_only', 'unknown'"
    )
    
    # For quarantine decisions
    is_quarantined: bool = Field(
        False,
        description="Whether this quote is quarantined (unresolved speaker)"
    )
    quarantine_reason: Optional[str] = Field(
        None,
        description="Reason for quarantine if applicable"
    )
```

### Enhanced TimelineEntry Schema

The TimelineEntry is already fairly comprehensive. Add:

```python
class TimelineEntry(BaseModel):
    # ... existing fields ...
    
    # === NEW: Classification Fields ===
    
    # Pronoun resolution status
    pronouns_resolved: bool = Field(
        False,
        description="Whether pronouns in this entry have been resolved"
    )
    resolved_description: Optional[str] = Field(
        None,
        description="Description with pronouns replaced by names"
    )
    
    # Quality for selection
    display_quality: str = Field(
        "normal",
        description="Quality tier: 'high', 'normal', 'low', 'fragment'"
    )
```

---

## Migration Inventory

### Fields to Add

| Atom Type | New Field | Type | Where Populated |
|-----------|-----------|------|-----------------|
| `Event` | `is_camera_friendly` | bool | New pass: `p35_classify_events` |
| `Event` | `camera_friendly_reason` | Optional[str] | New pass: `p35_classify_events` |
| `Event` | `is_follow_up` | bool | New pass: `p35_classify_events` |
| `Event` | `is_fragment` | bool | New pass: `p35_classify_events` |
| `Event` | `contains_quote` | bool | New pass: `p35_classify_events` |
| `Event` | `contains_interpretive` | bool | New pass: `p35_classify_events` |
| `Event` | `neutralized_description` | Optional[str] | New pass: `p54_neutralize` |
| `Event` | `actor_resolved` | bool | Existing pass: `p43_resolve_actors` |
| `Event` | `quality_score` | float | New pass: `p35_classify_events` |
| `Entity` | `is_valid_actor` | bool | Existing pass: `p32_extract_entities` |
| `Entity` | `is_named` | bool | Existing pass: `p32_extract_entities` |
| `Entity` | `gender` | Optional[str] | Existing pass: `p32_extract_entities` |
| `Entity` | `domain_role` | Optional[str] | Existing pass: `p32_extract_entities` |
| `SpeechAct` | `speaker_resolved` | bool | Existing logic in renderer |
| `SpeechAct` | `speaker_validation` | Optional[str] | Existing logic in renderer |
| `SpeechAct` | `is_quarantined` | bool | Existing logic in renderer |
| `SpeechAct` | `quarantine_reason` | Optional[str] | Existing logic in renderer |
| `TimelineEntry` | `pronouns_resolved` | bool | Existing logic in renderer |
| `TimelineEntry` | `resolved_description` | Optional[str] | Existing logic in renderer |
| `TimelineEntry` | `display_quality` | str | Existing logic in renderer |

### Existing Passes to Modify

| Pass | Modification |
|------|-------------|
| `p32_extract_entities` | Populate `is_valid_actor`, `is_named`, `gender`, `domain_role` |
| `p34_extract_events` | Initialize new Event fields with defaults |
| `p43_resolve_actors` | Set `actor_resolved` flag after resolving |

### New Passes to Create

| Pass | Purpose |
|------|---------|
| `p35_classify_events` | Apply camera-friendly rules, set classification fields |
| `p54_neutralize` | Apply neutralization rules, store neutralized text |

---

## Implementation Plan

### Step 1: Update IR Schema (schema_v0_1.py)

Add the new fields to `Event`, `Entity`, `SpeechAct` with defaults so existing code doesn't break.

```python
# In Event class, add:
is_camera_friendly: bool = Field(False, description="...")
camera_friendly_reason: Optional[str] = Field(None, description="...")
# etc.
```

### Step 2: Update AtomicStatement to Pydantic (Optional)

Currently `AtomicStatement` is a dataclass in `p26_decompose.py`. Consider:
- Moving to `ir/schema_v0_1.py` as Pydantic model
- Or keeping as dataclass but ensuring it's serializable

Decision: **Keep as dataclass for now** - it's internal to the pipeline and already comprehensive.

### Step 3: Modify Existing Passes

Update passes to populate the new fields where logic already exists:

- `p32_extract_entities.py`: Add `is_valid_actor`, `is_named`, `gender` population
- `p43_resolve_actors.py`: Set `actor_resolved = True` after resolution

### Step 4: Create Placeholder Pass (p35_classify_events)

Create skeleton pass that will be filled in Stage 1:

```python
# p35_classify_events.py
"""Pass 35 — Event Classification

Classifies events with camera-friendly status and other metadata.
Populated in Stage 1 of architecture refactor.
"""

def classify_events(ctx: TransformContext) -> TransformContext:
    """Placeholder - classification logic moved from renderer in Stage 1."""
    # For now, just initialize all fields to defaults
    for event in ctx.events:
        event.is_camera_friendly = False  # Will be properly computed in Stage 1
        event.quality_score = 0.5
    return ctx
```

### Step 5: Update Tests

- Add tests for new fields
- Ensure backward compatibility (old code that doesn't use new fields still works)

---

## Known Limitations & Trust Considerations

**CRITICAL**: We cannot blindly trust that fields are accurate just because they're set.

### spaCy Limitations Affecting This Stage

| What We Use | Known Gaps |
|-------------|-----------|
| Entity extraction | Misses names without titles, wrong boundaries on compounds |
| Dependency parsing | Fails on complex nested sentences |
| POS tagging | "Officer" detected as noun, not title in some contexts |
| Name detection | Generic first names often missed |

### Confidence Handling Requirements

For each new field, we need to decide:

| Field Pattern | When to Use |
|---------------|------------|
| `is_X: bool` | Only when binary is truly meaningful |
| `X_status: Literal["yes", "no", "unknown"]` | When uncertainty is common |
| `is_X: bool` + `X_confidence: float` | When we need the bool but also quality info |
| `X_reason: str` + `X_source: str` | For traceability |

### Revised Field Design

Based on this, update key fields:

```python
# Event - instead of just bool, include confidence and source
is_camera_friendly: bool = Field(False, description="...")
camera_friendly_confidence: float = Field(0.0, description="Confidence in classification")
camera_friendly_reason: Optional[str] = Field(None, description="Why classified this way")
camera_friendly_source: Optional[str] = Field(None, description="Which pass/rule decided")

# Entity - gender is uncertain, use tri-state
gender: Optional[Literal["male", "female", "neutral"]] = Field(
    None,  # None = unknown, not assumed
    description="Inferred gender, None if cannot determine"
)
is_named: bool = Field(False, description="Has proper name")
is_named_confidence: float = Field(0.0, description="How sure we are it's a real name")

# SpeechAct - speaker resolution is often uncertain
speaker_resolved: bool = Field(False, description="...")
speaker_resolution_confidence: float = Field(0.0, description="...")
speaker_resolution_method: Optional[str] = Field(None, description="How resolved: 'pattern', 'context', 'default'")
```

### Fallback Behavior

When upstream data is unreliable:

```python
def classify_event(event: Event, ctx: TransformContext) -> None:
    """Classify event with fallbacks."""
    
    # Primary: Check via established rules
    result = apply_camera_friendly_rules(event.description)
    
    if result.confidence >= 0.8:
        event.is_camera_friendly = result.passed
        event.camera_friendly_confidence = result.confidence
        event.camera_friendly_source = "rules"
    else:
        # Fallback: Conservative default
        event.is_camera_friendly = False
        event.camera_friendly_confidence = result.confidence
        event.camera_friendly_reason = "low_confidence_default"
        event.camera_friendly_source = "fallback"
```

### "Unknown" vs "False" Philosophy

```python
# WRONG: Assume positive when we don't know
event.is_camera_friendly = True  # Optimistic

# WRONG: Assume negative when we don't know
event.is_camera_friendly = False  # Pessimistic but unexplained

# RIGHT: Be explicit about uncertainty
event.is_camera_friendly = False
event.camera_friendly_confidence = 0.3  # Low confidence
event.camera_friendly_reason = "could_not_determine"
```

---

## Testing Strategy

### Backward Compatibility Tests

```python
def test_event_without_new_fields():
    """Events created without new fields should use defaults."""
    event = Event(
        id="e1",
        type=EventType.ACTION,
        description="Test",
        confidence=0.9,
    )
    assert event.is_camera_friendly == False  # Default
    assert event.camera_friendly_reason is None
```

### Field Population Tests

```python
def test_entity_classification():
    """Entity extraction should set classification fields."""
    ctx = process_narrative("Officer Jenkins grabbed the wallet.")
    officer = find_entity_by_label(ctx, "Officer Jenkins")
    
    assert officer.is_valid_actor == True
    assert officer.is_named == True
    assert officer.gender == "male"
```

---

## Rollback Plan

If issues arise:
1. All new fields have defaults - old code continues to work
2. New passes can be disabled in pipeline configuration
3. Renderer can fall back to computing values if atom fields are unset

---

## Done Criteria

- [ ] `Event` schema has all new classification fields
- [ ] `Entity` schema has validation/classification fields
- [ ] `SpeechAct` schema has resolution status fields
- [ ] `TimelineEntry` schema has quality/resolution fields
- [ ] All new fields have sensible defaults
- [ ] Existing passes modified to populate new fields where logic exists
- [ ] `p35_classify_events` pass exists (skeleton for Stage 1)
- [ ] Tests pass for backward compatibility
- [ ] Tests exist for new field population

---

## Dependencies

**Blocks**: Stage 1 (Classification Layer) - needs schema fields to write to

**Blocked by**: Nothing - this is the foundation

---

## Estimated Effort

- Schema changes: 2-4 hours
- Pass modifications: 4-8 hours  
- New pass skeleton: 1-2 hours
- Testing: 4-6 hours
- **Total: 2-3 days**

---

*Stage 0 Document — 2026-01-18*
