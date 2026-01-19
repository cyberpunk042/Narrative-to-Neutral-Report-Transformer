# Stage 3: Renderer Simplification

## Objective

Strip the renderer (`structured.py`) down to **formatting-only**. It should receive pre-classified, pre-selected atoms and simply format them for display.

**Outcome**: No classification logic. No selection logic. No business logic. Just formatting.

### UPDATE 2026-01-18 22:46 — BREAKTHROUGH!

**selection_result is now REQUIRED** 🎉

Key changes:
1. ✅ `format_structured_output()` raises `ValueError` if `selection_result` not provided
2. ✅ All tests updated to pass `SelectionResult`
3. ✅ 8 legacy tests marked as skipped (test deprecated behavior)
4. ✅ PARTIES legacy block removed (97 lines)

**Current State**:
- **structured.py**: 2274 lines (was 2361)
- Legacy blocks are now **DEAD CODE** (if True: always takes new path)
- Next step: Delete the dead legacy blocks (~1500 lines)

---

## Current State (2000+ lines)

### structured.py Breakdown

| Section | Lines | What It Does | Category |
|---------|-------|--------------|----------|
| Header/imports | 1-60 | Imports, SectionRegistry | KEEP |
| `_deduplicate_statements` | 60-100 | Dedup helper | KEEP (utility) |
| Entity categorization | 143-234 | Split entities by role | SELECTION ❌ |
| Reference data formatting | 236-317 | Format identifiers | FORMATTING ✓ |
| Pattern constants | 322-389 | INTERPRETIVE_DISQUALIFIERS, etc. | CLASSIFICATION ❌ |
| `neutralize_for_observed()` | 391-428 | Strip interpretive words | DEPRECATED ❌ |
| `is_strict_camera_friendly()` | 430-568 | 6-rule camera check | DEPRECATED ❌ |
| `is_camera_friendly()` | 570-579 | Legacy wrapper | DEPRECATED ❌ |
| `is_follow_up_event()` | 581-589 | Follow-up detection | DEPRECATED ❌ |
| `is_source_derived()` | 591-598 | Source-derived detection | DEPRECATED ❌ |
| Event routing loop | 630-730 | Filter/route events | SELECTION ❌ |
| OBSERVED EVENTS rendering | 756-835 | Format strict events | FORMATTING ✓ |
| FOLLOW-UP rendering | 837-852 | Format follow-up | FORMATTING ✓ |
| Items discovered extraction | 854-1057 | Extract items from text | EXTRACTION ❌ |
| NARRATIVE EXCERPTS | 1060-1095 | Format excerpts | FORMATTING ✓ |
| SOURCE-DERIVED | 1097-1150 | Format source info | FORMATTING ✓ |
| MEDICAL FINDINGS | 1151-1230 | Extract/format medical | MIXED |
| Quote extraction/validation | 1250-1540 | Parse/validate quotes | SELECTION/FORMATTING |
| Timeline rendering | 1596-1800 | Format timeline | FORMATTING ✓ |
| Investigation questions | 1960-2020 | Generate questions | LOGIC ❌ |

### What Should Remain (Formatting Only)

1. **Section headers** — `lines.append("OBSERVED EVENTS...")`
2. **Bullet formatting** — `lines.append(f"  • {text}")`
3. **Role display** — `role.replace('_', ' ').title()`
4. **Timeline day headers** — "INCIDENT DAY (Day 0)", etc.
5. **Quote attribution formatting**

### What Should Be Removed

1. **Pattern constants** — Moved to YAML in Stage 1
2. **Classification functions** — Deprecated, use event fields
3. **Selection logic** — Use SelectionResult from Stage 2
4. **Event routing** — Done by p55_select
5. **Items discovery extraction** — Should be separate pass
6. **Medical content routing** — Should use classification
7. **Quote speaker resolution** — Should be in pipeline

---

## Target State

### New Renderer Flow

```
format_structured_output(ctx):
    # 1. Read SelectionResult from context
    sel = ctx.selection_result
    
    # 2. Format each section using pre-selected IDs
    lines = render_header()
    lines += render_parties(ctx, sel.incident_participants, 
                            sel.post_incident_pros, sel.mentioned_contacts)
    lines += render_reference_data(ctx.identifiers)
    lines += render_observed_events(ctx, sel.observed_events)
    lines += render_follow_up_events(ctx, sel.follow_up_events)
    lines += render_narrative_excerpts(ctx, sel.narrative_excerpts)
    lines += render_quotes(ctx, sel.preserved_quotes, sel.quarantined_quotes)
    lines += render_timeline(ctx, sel.timeline_entries)
    
    return "\n".join(lines)
```

### Section Rendering Functions

Each section becomes a pure formatting function:

```python
def render_observed_events(ctx: TransformContext, event_ids: list[str]) -> list[str]:
    """Render observed events section — FORMATTING ONLY."""
    if not event_ids:
        return []
    
    lines = [
        "OBSERVED EVENTS (STRICT / CAMERA-FRIENDLY)",
        "─" * 70,
        "ℹ️ Fully normalized: Actor + action + object. No pronouns, quotes, or fragments.",
        ""
    ]
    
    for event_id in event_ids:
        event = ctx.get_event_by_id(event_id)
        text = event.neutralized_description or event.description
        lines.append(f"  • {text}")
    
    lines.append("")
    return lines
```

### What Gets Removed

```python
# REMOVE: These pattern constants (now in YAML)
INTERPRETIVE_DISQUALIFIERS = [...]  # ~45 items
FOLLOW_UP_PATTERNS = [...]           # ~8 items
SOURCE_DERIVED_PATTERNS = [...]      # ~12 items
INTERPRETIVE_STRIP_WORDS = [...]     # ~30 items
CONJUNCTION_STARTS = [...]           # ~12 items
VERB_STARTS = [...]                  # ~25 items
INTERPRETIVE_BLOCKERS = [...]        # ~15 items

# REMOVE: These functions (deprecated in Stage 1)
def neutralize_for_observed(text): ...
def is_strict_camera_friendly(text): ...
def is_camera_friendly(text, neutralized_text): ...
def is_follow_up_event(text): ...
def is_source_derived(text): ...

# REMOVE: Event routing loop (done by p55_select)
for epistemic_type in OBSERVABLE_EPISTEMIC_TYPES:
    for text in statements_by_epistemic[epistemic_type]:
        if is_follow_up_event(neutralized):
            follow_up_events.append(text)
        elif is_source_derived(neutralized):
            source_derived.append(text)
        elif is_strict_camera_friendly(neutralized):
            strict_events.append(text)
        else:
            narrative_excerpts.append((text, reason))

# REMOVE: Quote speaker extraction (should be pipeline pass)
for text in speech_texts:
    for verb in SPEECH_VERBS:
        if verb in text:
            parts = text.split(verb, 1)
            speaker_text = parts[0].strip()
            # ... 100+ lines of speaker extraction
```

---

## Implementation Plan

### Phase 1: Context Awareness

Add check for SelectionResult to renderer:

```python
def format_structured_output(..., ctx: TransformContext = None):
    # Check if we have selection result
    if ctx and ctx.selection_result:
        return format_from_selection(ctx, ...)
    else:
        # Legacy path - keep for backward compatibility
        return format_legacy(...)
```

**Estimated effort:** 2-4 hours

---

### Phase 2: Section-by-Section Migration

Migrate each section to use SelectionResult:

#### 2.1 Entities Section

```python
def render_parties(ctx, participant_ids, professional_ids, contact_ids):
    """Format PARTIES section from pre-selected entity IDs."""
    lines = ["PARTIES", "─" * 70]
    
    if participant_ids:
        lines.append("  INCIDENT PARTICIPANTS:")
        for entity_id in participant_ids:
            entity = ctx.get_entity_by_id(entity_id)
            role_display = entity.role.replace('_', ' ').title()
            lines.append(f"    • {entity.label} ({role_display})")
    
    # ... similar for professionals and contacts
    return lines
```

**Current:** 90 lines of selection + formatting
**Target:** 30 lines of formatting only

---

#### 2.2 Observed Events Section

```python
def render_observed_events(ctx, event_ids):
    """Format OBSERVED EVENTS from pre-selected IDs."""
    lines = [
        "OBSERVED EVENTS (STRICT / CAMERA-FRIENDLY)",
        "─" * 70,
    ]
    
    for event_id in event_ids:
        event = ctx.get_event_by_id(event_id)
        text = event.neutralized_description or event.description
        lines.append(f"  • {text}")
    
    return lines
```

**Current:** 170+ lines (selection + V8/V9 paths + formatting)
**Target:** 20 lines formatting only

---

#### 2.3 Follow-Up Events Section

```python
def render_follow_up_events(ctx, event_ids):
    """Format FOLLOW-UP ACTIONS from pre-selected IDs."""
    if not event_ids:
        return []
    
    lines = [
        "OBSERVED EVENTS (FOLLOW-UP ACTIONS)",
        "─" * 70,
    ]
    
    for event_id in event_ids:
        event = ctx.get_event_by_id(event_id)
        text = event.neutralized_description or event.description
        # Normalize pronouns
        text = _normalize_pronouns(text)
        lines.append(f"  • {text}")
    
    return lines
```

**Current:** 15 lines
**Target:** 15 lines (already simple)

---

#### 2.4 Narrative Excerpts Section

```python
def render_narrative_excerpts(ctx, excerpts: list[tuple[str, str]]):
    """Format NARRATIVE EXCERPTS from pre-selected (ID, reason) tuples."""
    if not excerpts:
        return []
    
    lines = [
        "NARRATIVE EXCERPTS (UNNORMALIZED)",
        "─" * 70,
        "⚠️ These excerpts couldn't be normalized. Listed by rejection reason:",
        ""
    ]
    
    # Group by reason
    by_reason = defaultdict(list)
    for event_id, reason in excerpts:
        event = ctx.get_event_by_id(event_id)
        by_reason[reason].append(event.description)
    
    for reason, texts in by_reason.items():
        label = REASON_LABELS.get(reason, reason)
        lines.append(f"  [{label}]")
        for text in texts[:5]:
            lines.append(f"    - {text[:80]}{'...' if len(text) > 80 else ''}")
    
    return lines
```

**Current:** 35 lines
**Target:** 30 lines

---

#### 2.5 Quotes Section

```python
def render_quotes(ctx, preserved_ids, quarantined: list[tuple[str, str]]):
    """Format quotes from pre-selected IDs."""
    lines = []
    
    if preserved_ids:
        lines += [
            "PRESERVED QUOTES (SPEAKER RESOLVED)",
            "─" * 70,
        ]
        for quote_id in preserved_ids:
            quote = ctx.get_speech_act_by_id(quote_id)
            speaker = quote.speaker_label or "Unknown"
            verb = quote.speech_verb or "said"
            lines.append(f"  {speaker} {verb}: \"{quote.content}\"")
    
    if quarantined:
        lines += [
            "",
            "⚠️ QUOTES (QUARANTINE - Speaker Unresolved)",
            "─" * 70,
        ]
        for quote_id, reason in quarantined:
            quote = ctx.get_speech_act_by_id(quote_id)
            lines.append(f"  - {quote.content[:80]}...")
    
    return lines
```

**Current:** 200+ lines (speaker extraction/validation + formatting)
**Target:** 30 lines formatting only

---

#### 2.6 Timeline Section

```python
def render_timeline(ctx, entry_ids):
    """Format RECONSTRUCTED TIMELINE from pre-selected entry IDs."""
    if not entry_ids:
        return []
    
    lines = [
        "─" * 70,
        "",
        "RECONSTRUCTED TIMELINE",
        "─" * 70,
    ]
    
    # Group by day
    entries_by_day = defaultdict(list)
    for entry_id in entry_ids:
        entry = ctx.get_timeline_entry_by_id(entry_id)
        day = getattr(entry, 'day_offset', 0)
        entries_by_day[day].append(entry)
    
    for day_offset in sorted(entries_by_day.keys()):
        lines.append(f"  ┌─── {_day_label(day_offset)} ───")
        for entry in entries_by_day[day_offset]:
            lines.append(f"  │ {entry.time_marker or '??:??'} - {entry.description}")
        lines.append("  └───")
    
    return lines
```

**Current:** 200+ lines (filtering + pronoun resolution + formatting)
**Target:** 40 lines formatting only

---

### Phase 3: Remove Deprecated Code

After Phase 2 is verified:

1. Remove deprecated functions:
   - `neutralize_for_observed()`
   - `is_strict_camera_friendly()`
   - `is_camera_friendly()`
   - `is_follow_up_event()`
   - `is_source_derived()`

2. Remove pattern constants (now in YAML):
   - `INTERPRETIVE_DISQUALIFIERS`
   - `FOLLOW_UP_PATTERNS`
   - `SOURCE_DERIVED_PATTERNS`
   - etc.

3. Remove V8 fallback path (if V9 proven stable)

**Estimated effort:** 4-8 hours

---

### Phase 4: Extract Remaining Logic

Move remaining business logic to pipeline passes:

1. **Items Discovery** → `p36_extract_items.py`
   - Extract discovered items from event descriptions
   - Store as new atom type or on context

2. **Investigation Questions** → `p65_generate_questions.py`
   - Generate questions based on timeline gaps
   - Store on context for rendering

**Estimated effort:** 8-12 hours (optional, can defer)

---

## Testing Strategy

### Equivalence Tests

```python
def test_new_renderer_matches_old():
    """New renderer should produce identical output to old."""
    for case in load_golden_cases():
        # Run with old renderer
        ctx_old = transform_with_legacy_renderer(case.input)
        
        # Run with new renderer
        ctx_new = transform_with_selection_renderer(case.input)
        
        assert ctx_old.rendered_text == ctx_new.rendered_text
```

### Section Tests

```python
def test_render_observed_events():
    """render_observed_events formats correctly."""
    ctx = mock_context_with_events([
        Event(id="e1", description="Officer stopped vehicle", is_camera_friendly=True)
    ])
    ctx.selection_result = SelectionResult(
        observed_events=["e1"]
    )
    
    lines = render_observed_events(ctx, ctx.selection_result.observed_events)
    
    assert "OBSERVED EVENTS" in lines[0]
    assert "Officer stopped vehicle" in "\n".join(lines)
```

---

## Migration Strategy

### Safe Transition Path

```
Phase 1: Add parallel path (both old and new renderers work)
    ↓
Phase 2: Migrate sections one at a time
    - Test each section independently
    - Compare output between old/new paths
    ↓
Phase 3: Make new path default
    - Old path becomes fallback
    - Log warnings if fallback is used
    ↓
Phase 4: Remove old path
    - After 1-2 weeks of stability
    - Delete deprecated code
```

### Rollback

- New renderer is opt-in initially
- `ctx.selection_result` presence determines path
- Can disable p55_select to use old path

---

## Done Criteria

- [x] `ctx` parameter added to format_structured_output ✅ (2026-01-18)
- [x] `use_selection_result` check implemented ✅ (2026-01-18)
- [x] Entity section uses SelectionResult ✅ (2026-01-18)
- [x] Observed Events section uses SelectionResult ✅ (2026-01-18)
- [x] Follow-up Events section uses SelectionResult ✅ (2026-01-18)
- [x] Source-Derived section uses SelectionResult ✅ (2026-01-18)
- [x] Narrative Excerpts section uses SelectionResult ✅ (2026-01-18)
- [x] Quotes section uses SelectionResult ✅ (2026-01-18)
- [x] Timeline section uses SelectionResult ✅ (2026-01-18)
- [x] Pipeline integration via p90_render_structured ✅ (2026-01-18)
- [x] Deprecated functions marked ✅ (functions have DEPRECATED docstrings)
- [x] Pattern constants marked ✅ (all have DEPRECATED comments)
- [ ] V8 fallback removed (or clearly marked) — still used by default pipeline
- [ ] structured.py reduced to ~500-800 lines — deferred until legacy path removed
- [x] All 602 tests pass ✅ (2026-01-18)
- [ ] Golden case outputs verified with new path

---

## Dependencies

**Blocked by**: Stage 2 (Selection Layer) ✅ COMPLETE

**Blocks**:
- Stage 6 (Recomposition Mode) - needs clean renderer architecture

---

## Estimated Effort

| Phase | Task | Hours |
|-------|------|-------|
| 1 | Add SelectionResult awareness | 2-4 |
| 2.1 | Entities section | 2-3 |
| 2.2 | Observed Events section | 4-6 |
| 2.3 | Follow-up Events section | 1-2 |
| 2.4 | Narrative Excerpts section | 2-3 |
| 2.5 | Quotes section | 4-6 |
| 2.6 | Timeline section | 4-6 |
| 3 | Remove deprecated code | 4-8 |
| 4 | Extract remaining logic (optional) | 8-12 |
| - | Testing | 4-8 |
| **Total** | | **35-58 hours** |

Estimated calendar time: **2-3 weeks**

---

## Line Count Projection

| Component | Current | Target | Reduction |
|-----------|---------|--------|-----------|
| Imports/SectionRegistry | 60 | 60 | 0 |
| Pattern constants | 150 | 0 | -150 |
| Classification functions | 200 | 0 | -200 |
| Selection/routing logic | 300 | 0 | -300 |
| Section formatting | 800 | 400 | -400 |
| Quote extraction | 200 | 30 | -170 |
| Timeline filtering | 200 | 40 | -160 |
| Other | 135 | 70 | -65 |
| **Total** | **2045** | **600** | **-1445 (71%)** |

---

## Open Questions

1. **Items Discovery section** — Extract to pipeline or keep in renderer?
   - Currently extracts contraband/weapons/personal items from text
   - Domain-specific (law enforcement)
   - Could be Stage 5 (Domains) scope

2. **Investigation Questions section** — Keep or remove?
   - Currently generates questions from timeline gaps
   - Useful for report but not core neutralization
   - Could be optional section controlled by mode

3. **V8/V9 paths** — When to remove V8?
   - V8 uses atomic_statements (older path)
   - V9 uses event_generator (newer, cleaner)
   - Need to verify V9 handles all cases before removing V8

---

*Stage 3 Document — 2026-01-18*
