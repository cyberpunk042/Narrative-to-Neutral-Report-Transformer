# Stages 0 & 1 Review + Stage 2 Preparation

## Review Date: 2026-01-18

---

## Stage 0: Atom Schema Enhancement — Complete ✅

### What We Accomplished

| Area | Status | Details |
|------|--------|---------|
| **Event fields** | ✅ Complete | 17 new fields added (camera-friendly, fragment, follow-up, quote, interpretive, neutralization, actor resolution, quality) |
| **Entity fields** | ✅ Complete | 11 new fields (actor validity, naming, gender inference, domain role) |
| **SpeechAct fields** | ✅ Complete | 6 new fields (speaker resolution, quarantine) |
| **TimelineEntry fields** | ✅ Complete | 3 new fields (pronoun resolution, display quality) |
| **StatementGroup fields** | ✅ Complete | 2 new fields (quality score, display quality) |
| **Default values** | ✅ Complete | All fields have sensible defaults for backward compatibility |
| **Tests passing** | ✅ Complete | 578 tests pass |

### What Was NOT Done (Deferred)

| Item | Reason | Impact |
|------|--------|--------|
| Fields on Segment | Didn't identify need | May need for render selection |
| Fields on AtomicStatement | Already comprehensive | None |
| Validation fields | Deferred to Stage 4 | Can add later |

### Lessons Learned

1. **Default values are critical** — Every new field needs a sensible default to avoid breaking existing code
2. **Confidence + Reason + Source pattern** — This triple (value, confidence, source) is a good pattern for all classification fields
3. **Not all atoms need classification** — Segment and AtomicStatement were already well-structured

---

## Stage 1: Classification Layer Unification — Complete ✅

### What We Accomplished

| Area | Status | Details |
|------|--------|---------|
| **RuleAction enum** | ✅ Complete | Added CLASSIFY, DISQUALIFY, DETECT, STRIP |
| **ClassificationOutput** | ✅ Complete | Dataclass for rule output specification |
| **apply_classification_rules()** | ✅ Complete | Returns classification results |
| **apply_strip_rules()** | ✅ Complete | Neutralizes text |
| **_get_replacement()** | ✅ Fixed | Handles STRIP like REMOVE |
| **Span consumption** | ✅ Fixed | DETECT/CLASSIFY don't block REMOVE/REPLACE |
| **p35_classify_events** | ✅ Complete | Wired into pipeline after extract_events |
| **camera_friendly.yaml** | ✅ Complete | 12 rules (DISQUALIFY + DETECT) |
| **neutralization.yaml** | ✅ Complete | 10 STRIP rules |
| **Event generator** | ✅ Updated | Checks event.is_camera_friendly first |
| **Renderer functions** | ✅ Deprecated | Kept for V8 fallback, marked deprecated |

### What Was NOT Done (Deferred)

| Item | Reason | Impact |
|------|--------|--------|
| p54_neutralize pass | Integrated into p35 | Simpler design |
| Remove renderer functions | V8 fallback still needed | Technical debt |
| Migrate ALL patterns to YAML | Some patterns are semantic | Actor resolution check still inline |
| Entity classification pass | Out of scope | Stage 4 or separate work |
| SpeechAct classification pass | Out of scope | Stage 4 or separate work |
| TimelineEntry classification | Out of scope | Stage 4 or separate work |

### Lessons Learned

1. **Classification rules shouldn't consume spans** — DETECT/CLASSIFY rules read text but don't modify it; they shouldn't block transformation rules
2. **STRIP is just REMOVE for text** — No need for complex logic difference
3. **Not all classification is rule-based** — Actor resolution requires semantic context (checking if actor_label exists), not just pattern matching
4. **V8/V9 paths complicate migration** — The renderer has multiple paths; V9 (event-based) is cleaner and uses pre-computed fields, V8 (statement-based) still uses inline functions
5. **Neutralization integrated naturally** — Making p54 separate was overkill; neutralization fits naturally in p35

---

## Current Architecture State

```
┌─────────────────────────────────────────────────────────────────┐
│                        INPUT: Narrative                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                LAYER 1: DECOMPOSITION                           │
│  p25_segment, p26_decompose, p32_extract_entities,              │
│  p34_extract_events                                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                LAYER 2: CLASSIFICATION ✅ NEW                    │
│  p35_classify_events (uses PolicyEngine classification rules)   │
│  - is_camera_friendly, is_fragment, is_follow_up               │
│  - contains_quote, contains_interpretive                        │
│  - neutralized_description                                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                LAYER 3: SELECTION ❌ NOT YET                     │
│  (Currently done in renderer — needs extraction)               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                LAYER 4: RENDERING                               │
│  p70_render (still has V8 fallback classification)             │
│  event_generator (uses pre-computed classification ✅)          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        OUTPUT: Report                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Gaps to Address

### High Priority (Stage 2)

1. **Selection logic still in renderer** — `structured.py` has complex logic for:
   - Which events go to OBSERVED EVENTS vs FOLLOW-UP vs NARRATIVE EXCERPTS
   - Which quotes are included vs quarantined
   - Which entities are included
   - Section-specific filtering

2. **Output modes not supported** — Currently only one output mode (neutralized report)

### Medium Priority (Stage 3-4)

3. **Entity classification not wired** — Entity has classification fields but no pass populates them
4. **Quote speaker resolution not wired** — SpeechAct has resolution fields but no pass populates them
5. **Timeline classification not wired** — TimelineEntry has fields but no pass populates them

### Low Priority (Later)

6. **V8 fallback still active** — Can't remove until V9 is proven everywhere
7. **Renderer still 2000+ lines** — Needs Stage 3 simplification

---

## Stage 2: Selection Layer — Initial Scope

### Objective

Create a dedicated Selection layer that sits between Classification and Rendering. This layer chooses WHICH atoms to include in output based on configuration/output mode.

### What Selection Currently Does (in Renderer)

Looking at `structured.py`, selection logic includes:

1. **Event Selection** (lines 638-690):
   - Filter to OBSERVABLE_EPISTEMIC_TYPES
   - Skip duplicates
   - Neutralize text
   - Check is_follow_up → route to follow-up section
   - Check is_source_derived → route to source-derived section
   - Check is_camera_friendly → include or route to excerpts

2. **Quote Selection** (lines 1316-1400):
   - Check speaker_resolved
   - Quarantine if unknown speaker
   - Group by speaker

3. **Entity Selection** (lines 146-234):
   - Categorize as incident_participants, post_incident_professionals, mentioned_contacts
   - Filter by role

4. **Section Routing**:
   - Events → OBSERVED EVENTS, FOLLOW-UP, NARRATIVE EXCERPTS
   - Quotes → PRESERVED QUOTES, QUARANTINE
   - Entities → Different sections based on role

### Proposed Selection Pass

```python
# p55_select.py

class SelectionMode(str, Enum):
    STRICT = "strict"           # Only camera-friendly events
    FULL = "full"               # All events with classification
    EVENTS_ONLY = "events_only" # Just the event list
    TIMELINE = "timeline"       # Timeline focus
    RECOMPOSITION = "recomposition"  # For narrative recomposition

@dataclass
class SelectionResult:
    """Which atoms are selected for which output sections."""
    
    # Event selections
    observed_events: list[str]      # Event IDs for OBSERVED EVENTS
    follow_up_events: list[str]     # Event IDs for FOLLOW-UP
    narrative_excerpts: list[str]   # Event IDs for NARRATIVE EXCERPTS
    excluded_events: list[str]      # Event IDs excluded
    
    # Quote selections
    included_quotes: list[str]      # SpeechAct IDs to include
    quarantined_quotes: list[str]   # SpeechAct IDs quarantined
    
    # Entity selections
    incident_participants: list[str]
    professionals: list[str]
    mentioned: list[str]
    
    # Timeline selections
    timeline_entries: list[str]

def select(ctx: TransformContext, mode: SelectionMode = SelectionMode.STRICT) -> SelectionResult:
    """
    Select which atoms to include in output based on mode.
    
    Uses pre-computed classification from Stage 1.
    """
    result = SelectionResult(...)
    
    for event in ctx.events:
        if mode == SelectionMode.STRICT:
            if event.is_camera_friendly and event.camera_friendly_confidence >= 0.7:
                if event.is_follow_up:
                    result.follow_up_events.append(event.id)
                else:
                    result.observed_events.append(event.id)
            elif not event.is_camera_friendly:
                result.narrative_excerpts.append(event.id)
        # ... other modes
    
    return result
```

### Benefits

1. **Clear separation** — Selection logic is in one place, not scattered in renderer
2. **Multiple output modes** — Easy to add new modes
3. **Testable** — Can unit test selection without rendering
4. **Traceable** — SelectionResult shows exactly what was selected and why

### Open Questions for Stage 2

1. **Where to store SelectionResult?** — On context? Separate return value?
2. **How to handle quote/entity selection?** — Same pass or separate?
3. **Mode configuration** — CLI flag? Config file? Both?
4. **Backward compatibility** — Keep renderer working during migration?

---

## Updated Timeline

| Stage | Status | Est. Effort | Notes |
|-------|--------|-------------|-------|
| Stage 0 | ✅ Complete | ~6 hours | Done 2026-01-18 |
| Stage 1 | ✅ Complete | ~8 hours | Done 2026-01-18 |
| Stage 2 | 📋 Ready | 8-16 hours | Selection layer |
| Stage 3 | 🔒 Blocked | 16-24 hours | Requires Stage 2 |
| Stage 4 | 📋 Can parallel | 8-12 hours | Rule unification |
| Stage 5 | 📋 Can parallel | 8-12 hours | Domain completion |
| Stage 6 | 🔒 Blocked | 16-24 hours | Requires Stage 3 |

---

## Next Steps

1. **Create Stage 2 document** — `.agent/milestones/stage_2_selection.md`
2. **Inventory selection logic** — List all selection decisions in renderer
3. **Design SelectionResult** — What needs to be tracked
4. **Define output modes** — What modes do we need?
5. **Implement p55_select** — Core selection pass
6. **Update renderer** — Read from SelectionResult instead of computing

---

*Review Document — 2026-01-18*
