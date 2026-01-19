# Stage 2: Selection Layer Creation

## Objective

Create a dedicated **Selection layer** that sits between Classification and Rendering. This layer determines **which atoms to include** in output and **which section** each atom belongs to, based on output mode configuration.

**Outcome**: Selection decisions are made ONCE in the pipeline and stored. The renderer receives pre-filtered, pre-routed atoms and simply formats them.

---

## Current State

### Selection Logic Currently in Renderer

The renderer (`structured.py`) currently performs ALL selection decisions at render-time, scattered across ~2000 lines:

#### 1. Entity Selection (lines 144-234)

```python
# Current: Selection logic mixed with rendering
INCIDENT_ROLES = {'reporter', 'subject_officer', 'supervisor', ...}
POST_INCIDENT_ROLES = {'medical_provider', 'legal_counsel', ...}
BARE_ROLE_LABELS = {'partner', 'passenger', 'suspect', ...}  # Excluded

for e in entities:
    if label.lower() in BARE_ROLE_LABELS:
        continue  # SELECTION: Exclude bare labels
    
    if participation == 'incident':
        incident_participants.append(...)  # ROUTING: To section 1
    elif participation == 'post_incident':
        post_incident_pros.append(...)     # ROUTING: To section 2
    else:
        mentioned_contacts.append(...)     # ROUTING: To section 3
```

**Selection Decisions:**
- Include/exclude based on role and label
- Route to: INCIDENT PARTICIPANTS, POST-INCIDENT PROFESSIONALS, or MENTIONED CONTACTS

#### 2. Event Selection (lines 638-730)

```python
# Current: Complex selection loop
OBSERVABLE_EPISTEMIC_TYPES = ['direct_event', 'characterization', ...]

for epistemic_type in OBSERVABLE_EPISTEMIC_TYPES:
    for text in statements_by_epistemic[epistemic_type]:
        if text in seen_in_strict:
            continue  # SELECTION: Skip duplicates
        
        neutralized = neutralize_for_observed(text)
        
        if is_follow_up_event(neutralized):
            follow_up_events.append(...)   # ROUTING: To FOLLOW-UP section
            continue
        
        if is_source_derived(neutralized):
            source_derived.append(...)      # ROUTING: To SOURCE-DERIVED section
            continue
        
        passed, reason = is_strict_camera_friendly(neutralized)
        
        if passed:
            strict_events.append(...)       # ROUTING: To OBSERVED EVENTS
        else:
            narrative_excerpts.append(...)  # ROUTING: To NARRATIVE EXCERPTS
```

**Selection Decisions:**
- Filter by epistemic type
- Skip duplicates
- Route by camera-friendliness, follow-up status, source-derived status

#### 3. Quote Selection (lines 1316-1540)

```python
# Current: Quote validation and routing
SPEECH_VERBS = ['said', 'told', 'asked', 'whispered', ...]

for text in speech_texts:
    # Extract speaker from text
    if check_quote_has_speaker(quote).passes:
        validated_quotes.append(...)     # ROUTING: To PRESERVED QUOTES
    else:
        quarantined_quotes.append(...)   # ROUTING: To QUARANTINE
```

**Selection Decisions:**
- Include only quotes with resolved speakers
- Route to: PRESERVED QUOTES or QUARANTINE

#### 4. Timeline Selection (lines 1598-1800)

```python
# Current: Timeline entry filtering
for entry in timeline:
    description = getattr(entry, 'description', None)
    
    # Skip fragments
    if description.startswith(('And ', 'But ', 'When ', ...)):
        continue  # SELECTION: Exclude fragments
    
    # Skip pronoun starts without resolution
    if re.match(r'^(He|She|They)\s', description):
        # Attempt resolution...
        if not resolved:
            continue  # SELECTION: Exclude unresolved pronouns
```

**Selection Decisions:**
- Exclude fragment entries
- Exclude entries with unresolved pronouns

---

## Target State

### New Selection Pass

```
Pipeline Order:
  ...
  p43_resolve_actors     (existing)
  p44_timeline           (existing)
  ...
  p50_policy             (existing - text transformation)
  
  p55_select             (NEW - selection decisions)
  
  p70_render             (existing - formatting only)
  ...
```

### Selection Result Stored on Context

```python
@dataclass
class SelectionResult:
    """Which atoms are selected for which output sections."""
    
    # === Event Selections ===
    observed_events: list[str]        # Event IDs for OBSERVED EVENTS (STRICT)
    follow_up_events: list[str]       # Event IDs for FOLLOW-UP ACTIONS
    source_derived_events: list[str]  # Event IDs for SOURCE-DERIVED
    narrative_excerpts: list[tuple[str, str]]  # (Event ID, reason) for EXCERPTS
    excluded_events: list[str]        # Event IDs excluded entirely
    
    # === Quote Selections ===
    preserved_quotes: list[str]       # SpeechAct IDs with resolved speakers
    quarantined_quotes: list[tuple[str, str]]  # (SpeechAct ID, reason)
    
    # === Entity Selections ===
    incident_participants: list[str]  # Entity IDs for incident section
    post_incident_pros: list[str]     # Entity IDs for professionals section
    mentioned_contacts: list[str]     # Entity IDs for mentioned section
    excluded_entities: list[str]      # Entity IDs excluded entirely
    
    # === Timeline Selections ===
    timeline_entries: list[str]       # TimelineEntry IDs to include
    excluded_timeline: list[tuple[str, str]]  # (Entry ID, reason) excluded
    
    # === Metadata ===
    mode: str                         # Which selection mode was used
    stats: dict                       # Counts for logging/debugging
```

### Selection Modes

```python
class SelectionMode(str, Enum):
    """Output mode determines selection criteria."""
    
    STRICT = "strict"
    # Only camera-friendly events with high confidence
    # Resolved entities and quotes only
    # Current default mode
    
    FULL = "full"
    # All events with classification data
    # All entities
    # All quotes (resolved and unresolved)
    # For debugging/analysis
    
    TIMELINE = "timeline"
    # Focus on timeline entries
    # Events ordered by time
    # For chronology-focused output
    
    EVENTS_ONLY = "events_only"
    # Just the event list
    # No quotes, no entities
    # For event extraction analysis
    
    RECOMPOSITION = "recomposition"
    # All atoms for narrative reconstruction
    # Preserves order and relationships
    # For future Stage 6
```

### Selection Logic

```python
# p55_select.py

def select(ctx: TransformContext, mode: SelectionMode = SelectionMode.STRICT) -> TransformContext:
    """
    Select which atoms to include based on mode.
    
    Uses PRE-COMPUTED classification fields from Stage 1:
    - event.is_camera_friendly
    - event.is_follow_up
    - event.is_fragment
    - event.contains_quote
    - entity.is_valid_actor
    - entity.is_named
    - speechact.speaker_resolved
    - timeline_entry.has_unresolved_pronouns
    """
    result = SelectionResult(mode=mode.value, ...)
    
    # === Event Selection ===
    for event in ctx.events:
        if mode == SelectionMode.STRICT:
            # Use pre-computed classification from p35
            if event.is_camera_friendly and event.camera_friendly_confidence >= 0.7:
                if event.is_follow_up:
                    result.follow_up_events.append(event.id)
                else:
                    result.observed_events.append(event.id)
            elif not event.is_camera_friendly:
                result.narrative_excerpts.append((event.id, event.camera_friendly_reason))
        
        elif mode == SelectionMode.FULL:
            result.observed_events.append(event.id)  # Include all
        
        # ... other modes
    
    # === Entity Selection ===
    for entity in ctx.entities:
        if mode == SelectionMode.STRICT:
            # Use pre-computed or derive from role
            if is_bare_role_label(entity.label):
                result.excluded_entities.append(entity.id)
            elif get_participation(entity) == 'incident':
                result.incident_participants.append(entity.id)
            elif get_participation(entity) == 'post_incident':
                result.post_incident_pros.append(entity.id)
            else:
                result.mentioned_contacts.append(entity.id)
    
    # === Quote Selection ===
    for quote in ctx.speech_acts:
        if mode == SelectionMode.STRICT:
            if quote.speaker_resolved:
                result.preserved_quotes.append(quote.id)
            else:
                result.quarantined_quotes.append((quote.id, "speaker_unresolved"))
    
    # === Timeline Selection ===
    for entry in ctx.timeline_entries:
        if mode in (SelectionMode.STRICT, SelectionMode.TIMELINE):
            if entry.has_unresolved_pronouns:
                result.excluded_timeline.append((entry.id, "unresolved_pronouns"))
            else:
                result.timeline_entries.append(entry.id)
    
    # Store result on context
    ctx.selection_result = result
    
    return ctx
```

### Renderer Reads Selection Result

```python
# In p70_render.py or structured.py

def render_observed_events(ctx: TransformContext) -> list[str]:
    """Render events - NO selection logic here."""
    lines = []
    
    # Just render what was selected
    for event_id in ctx.selection_result.observed_events:
        event = ctx.get_event_by_id(event_id)
        text = event.neutralized_description or event.description
        lines.append(f"  • {text}")
    
    return lines

def render_entities(ctx: TransformContext) -> list[str]:
    """Render entities - NO categorization logic here."""
    lines = []
    
    # Just render what was selected into each category
    if ctx.selection_result.incident_participants:
        lines.append("  INCIDENT PARTICIPANTS:")
        for entity_id in ctx.selection_result.incident_participants:
            entity = ctx.get_entity_by_id(entity_id)
            lines.append(f"    • {entity.label} ({entity.role})")
    
    # ... etc
    return lines
```

---

## Implementation Plan

### Step 1: Define Selection Models

**File:** `nnrt/selection/models.py`

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

class SelectionMode(str, Enum):
    STRICT = "strict"
    FULL = "full"
    TIMELINE = "timeline"
    EVENTS_ONLY = "events_only"
    RECOMPOSITION = "recomposition"

@dataclass
class SelectionResult:
    mode: str
    
    # Event selections
    observed_events: list[str] = field(default_factory=list)
    follow_up_events: list[str] = field(default_factory=list)
    source_derived_events: list[str] = field(default_factory=list)
    narrative_excerpts: list[tuple[str, str]] = field(default_factory=list)
    excluded_events: list[str] = field(default_factory=list)
    
    # Quote selections
    preserved_quotes: list[str] = field(default_factory=list)
    quarantined_quotes: list[tuple[str, str]] = field(default_factory=list)
    
    # Entity selections
    incident_participants: list[str] = field(default_factory=list)
    post_incident_pros: list[str] = field(default_factory=list)
    mentioned_contacts: list[str] = field(default_factory=list)
    excluded_entities: list[str] = field(default_factory=list)
    
    # Timeline selections
    timeline_entries: list[str] = field(default_factory=list)
    excluded_timeline: list[tuple[str, str]] = field(default_factory=list)
    
    # Stats
    stats: dict = field(default_factory=dict)
```

**Estimated effort:** 1-2 hours

---

### Step 2: Add SelectionResult to TransformContext

**File:** `nnrt/core/context.py`

```python
class TransformContext:
    # ... existing fields ...
    
    # V7 / Stage 2: Selection result
    selection_result: Optional[SelectionResult] = None
    
    def get_event_by_id(self, event_id: str) -> Optional[Event]:
        """Get event by ID for rendering."""
        for event in self.events:
            if event.id == event_id:
                return event
        return None
    
    # Similar for entities, quotes, timeline
```

**Estimated effort:** 1 hour

---

### Step 3: Create Selection Pass

**File:** `nnrt/passes/p55_select.py`

Core selection logic:
1. Event selection using pre-computed `is_camera_friendly`, `is_follow_up`, etc.
2. Entity selection using role and participation
3. Quote selection using `speaker_resolved`
4. Timeline selection using resolution status

**Estimated effort:** 4-6 hours

---

### Step 4: Wire Selection Pass into Pipeline

**File:** `nnrt/cli/main.py`

```python
from nnrt.passes.p55_select import select

def setup_default_pipeline(engine):
    # ... existing passes ...
    
    engine.register_pass("select", select)  # Add after policy, before render
```

**Estimated effort:** 30 minutes

---

### Step 5: Update Renderer to Read SelectionResult

**File:** `nnrt/render/structured.py`

Phase 1: Add optional path that reads from `SelectionResult`
Phase 2: Remove inline selection logic once Phase 1 is proven

```python
def format_structured_output(...):
    # Check if selection was done
    if ctx and hasattr(ctx, 'selection_result') and ctx.selection_result:
        # Use pre-computed selections
        return render_from_selection(ctx)
    else:
        # Fall back to inline selection (legacy)
        return render_legacy(...)
```

**Estimated effort:** 8-12 hours

---

### Step 6: Add Mode Configuration

**File:** `nnrt/cli/main.py`

```python
@click.option('--mode', type=click.Choice(['strict', 'full', 'timeline', 'events', 'recompose']), 
              default='strict', help='Output mode')
def transform(input_text, mode):
    request = TransformRequest(text=input_text, selection_mode=mode)
    # ...
```

**Estimated effort:** 1-2 hours

---

## Testing Strategy

### Unit Tests for Selection Pass

```python
# tests/test_selection.py

def test_strict_mode_only_camera_friendly():
    """STRICT mode includes only camera-friendly events in observed_events."""
    events = [
        Event(id="e1", is_camera_friendly=True, camera_friendly_confidence=0.9),
        Event(id="e2", is_camera_friendly=False, camera_friendly_reason="conjunction_start"),
        Event(id="e3", is_camera_friendly=True, is_follow_up=True),
    ]
    result = select_events(events, mode=SelectionMode.STRICT)
    
    assert "e1" in result.observed_events
    assert "e2" not in result.observed_events
    assert ("e2", "conjunction_start") in result.narrative_excerpts
    assert "e3" in result.follow_up_events

def test_full_mode_includes_all():
    """FULL mode includes all events with classification."""
    events = [...]
    result = select_events(events, mode=SelectionMode.FULL)
    
    assert len(result.observed_events) == len(events)
    assert len(result.excluded_events) == 0

def test_quote_selection_speaker_resolved():
    """Only quotes with resolved speakers go to preserved_quotes."""
    quotes = [
        SpeechAct(id="q1", speaker_resolved=True),
        SpeechAct(id="q2", speaker_resolved=False),
    ]
    result = select_quotes(quotes, mode=SelectionMode.STRICT)
    
    assert "q1" in result.preserved_quotes
    assert ("q2", "speaker_unresolved") in result.quarantined_quotes
```

### Integration Tests

```python
def test_rendered_output_matches_selection():
    """Renderer uses SelectionResult correctly."""
    ctx = transform("...")
    
    # Check selection populated
    assert ctx.selection_result is not None
    
    # Check rendered output matches selection
    rendered = render(ctx)
    for event_id in ctx.selection_result.observed_events:
        event = ctx.get_event_by_id(event_id)
        assert event.description in rendered or event.neutralized_description in rendered
```

### Golden Case Tests

```python
def test_golden_output_unchanged():
    """Ensure Stage 2 doesn't change golden case outputs."""
    for case in load_golden_cases():
        result = transform(case.input)
        assert result.rendered_text == case.expected_output
```

---

## Migration Strategy

### Phase 1: Parallel Path (Safe)

1. Implement p55_select pass
2. Add SelectionResult to context
3. Keep renderer's inline selection logic
4. Add new render path that reads SelectionResult
5. Compare outputs between old and new paths
6. Log discrepancies

### Phase 2: Switch (When Proven)

1. Make new path the default
2. Keep old path as fallback
3. Monitor for regressions

### Phase 3: Cleanup (After Stabilization)

1. Remove inline selection logic from renderer
2. Remove fallback path
3. Renderer becomes ~800 lines (formatting only)

---

## Rollback Plan

1. **p55_select is additive** — Can be disabled without breaking anything
2. **SelectionResult is optional** — Renderer falls back to inline logic
3. **Mode defaults to STRICT** — Same behavior as current system
4. **All changes are backward compatible** — Tests must pass before and after

---

## Done Criteria

- [x] `SelectionMode` enum created ✅ (2026-01-18)
- [x] `SelectionResult` dataclass created ✅ (2026-01-18)
- [x] `TransformContext.selection_result` added ✅ (2026-01-18)
- [x] Helper methods added: get_event_by_id, get_entity_by_id, etc. ✅
- [x] `p55_select` pass implemented ✅ (2026-01-18):
  - [x] Event selection (observed, follow-up, source-derived, excerpts)
  - [x] Entity selection (participants, professionals, mentioned)
  - [x] Quote selection (preserved, quarantined)
  - [x] Timeline selection (included, excluded)
- [x] Pass wired into pipeline after p50_policy ✅ (2026-01-18)
- [ ] Renderer has optional path using SelectionResult (Stage 3)
- [x] Mode configurable via CLI ✅ (2026-01-18)
  - `--mode strict|full|timeline|events|recompose`
  - Mode passed through request.metadata to p55_select
- [x] Unit tests for each selection type ✅ (2026-01-18)
  - tests/test_selection.py: 24 tests covering mode parsing, event/entity/quote selection
- [x] Integration tests for full pipeline ✅ (2026-01-18)
- [x] All 602 tests pass ✅ (2026-01-18)
- [x] Golden case outputs unchanged ✅ (2026-01-18)

---

## Dependencies

**Blocked by**: Stage 1 (Classification Layer) - needs classified atoms ✅ COMPLETE

**Blocks**:
- Stage 3 (Renderer Simplification) - needs selection out of renderer
- Stage 6 (Recomposition Mode) - needs selection infrastructure

---

## Estimated Effort

| Task | Hours |
|------|-------|
| SelectionResult models | 1-2 |
| TransformContext updates | 1 |
| p55_select pass | 4-6 |
| Pipeline wiring | 0.5 |
| Renderer integration | 8-12 |
| Mode configuration | 1-2 |
| Unit tests | 4-6 |
| Integration tests | 2-4 |
| Documentation | 1-2 |
| **Total** | **22-36 hours** |

Estimated calendar time: **1-2 weeks** (with other work)

---

## Open Questions

1. **Where to store SelectionResult?**
   - Option A: On TransformContext (proposed)
   - Option B: Separate return value from select pass
   - Option C: New SelectionContext parallel to TransformContext

2. **Should selection be reversible?**
   - Current plan: Selection IDs stored, atoms not modified
   - Alternative: Move excluded atoms to separate lists

3. **Mode configuration source?**
   - CLI flag (proposed)
   - Request parameter
   - Config file
   - Environment variable

4. **How to handle items discovered section?**
   - Currently extracted at render-time from event descriptions
   - Should this be a separate extraction pass?

---

*Stage 2 Document — 2026-01-18*
