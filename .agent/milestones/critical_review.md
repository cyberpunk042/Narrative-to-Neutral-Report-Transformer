# Architecture Refactor — Critical Review

## Review Date: 2026-01-18

This document provides a critical analysis of the complete stage progression to ensure:
1. Each stage is complete and well-defined
2. Stages link together fluidly
3. No gaps or inconsistencies exist
4. Dependencies are correctly mapped

---

## Stage Flow Analysis

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA FLOW                                       │
└─────────────────────────────────────────────────────────────────────────────┘

INPUT: Raw Narrative
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 0: ATOM SCHEMA ✅                                                     │
│  ────────────────────                                                        │
│  What: Add classification fields to atoms                                   │
│  Output: Empty fields on atoms (Event, Entity, SpeechAct, TimelineEntry)   │
│                                                                              │
│  Fields Added:                                                               │
│  • Event: is_camera_friendly, is_fragment, is_follow_up, contains_quote,   │
│           contains_interpretive, neutralized_description, quality_score    │
│  • Entity: is_valid_actor, is_named, gender, domain_role                   │
│  • SpeechAct: speaker_resolved, is_quarantined                             │
│  • TimelineEntry: has_unresolved_pronouns, display_quality                 │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 1: CLASSIFICATION ✅                                                  │
│  ─────────────────────────                                                   │
│  What: Populate atom classification fields using rules                      │
│  Pass: p35_classify_events                                                   │
│  Input: Atoms with empty classification fields                              │
│  Output: Atoms with filled classification fields                            │
│                                                                              │
│  Fields Populated:                                                           │
│  • Event: ALL classification fields (via PolicyEngine rules)               │
│  • Entity: NOT YET (future work)                                           │
│  • SpeechAct: NOT YET (future work)                                        │
│  • TimelineEntry: NOT YET (future work)                                    │
│                                                                              │
│  Gap: Only Events are classified. Entity/SpeechAct/Timeline need           │
│       their own classification passes.                                       │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 2: SELECTION 📋 PLANNED                                               │
│  ───────────────────────────                                                 │
│  What: Choose which atoms go to which output sections                       │
│  Pass: p55_select                                                            │
│  Input: Atoms with classification                                           │
│  Output: SelectionResult with lists of IDs per section                      │
│                                                                              │
│  Produces:                                                                   │
│  • observed_events, follow_up_events, narrative_excerpts                   │
│  • incident_participants, post_incident_pros, mentioned_contacts           │
│  • preserved_quotes, quarantined_quotes                                     │
│  • timeline_entries, excluded_timeline                                      │
│                                                                              │
│  Dependency: Requires Stage 1 (classification on atoms)                    │
│  Question: Entity/SpeechAct selection will use role/participation,         │
│            not Stage 1 classification. Is this OK or should we             │
│            add entity/quote classification first?                           │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 3: RENDERER SIMPLIFICATION 🔒 BLOCKED                                 │
│  ────────────────────────────────────────                                    │
│  What: Strip renderer to formatting-only                                    │
│  Input: SelectionResult + classified atoms                                  │
│  Output: Formatted text (report)                                            │
│                                                                              │
│  Removes from structured.py:                                                │
│  • is_strict_camera_friendly() — deprecated in Stage 1                     │
│  • neutralize_for_observed() — deprecated in Stage 1                       │
│  • Entity categorization logic — moved to Stage 2                          │
│  • Quote validation logic — moved to Stage 2                               │
│  • Timeline filtering logic — moved to Stage 2                             │
│                                                                              │
│  Dependency: Requires Stage 2 (selection infrastructure)                    │
│  Target: ~500-800 lines instead of ~2000                                   │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 6: RECOMPOSITION 🔒 BLOCKED                                           │
│  ─────────────────────────────────                                           │
│  What: Create flowing narrative from atoms                                  │
│  Input: SelectionResult + classified atoms (in RECOMPOSITION mode)         │
│  Output: Recomposed neutral narrative                                       │
│                                                                              │
│  Dependency: Requires Stage 3 (simplified renderer as template)             │
│  Dependency: Requires Stage 2 with RECOMPOSITION mode                       │
└─────────────────────────────────────────────────────────────────────────────┘

OUTPUT: Neutralized Report / Recomposed Narrative
```

---

## Parallel Track Analysis

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 4: RULE SYSTEM UNIFICATION 📋 CAN START                              │
│  ──────────────────────────────────────────                                  │
│  What: Unify all rule types under PolicyEngine                             │
│                                                                              │
│  Currently have rule types:                                                 │
│  • REMOVE, REPLACE, REFRAME — text transformation ✅                        │
│  • CLASSIFY, DISQUALIFY, DETECT, STRIP — classification ✅ Stage 1         │
│  • FLAG, REFUSE, PRESERVE — special actions ✅                              │
│                                                                              │
│  What's missing:                                                             │
│  • EXTRACT — extraction patterns (currently scattered in NLP code)         │
│  • VALIDATE — validation rules (currently separate schema)                 │
│                                                                              │
│  Goal: Single rule schema for ALL operations                               │
│  Dependency: Only Stage 1 (uses classification rule types)                 │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 5: DOMAIN SYSTEM 📋 CAN START (after Stage 4)                        │
│  ─────────────────────────────────────────────                               │
│  What: Complete domain configuration system                                │
│                                                                              │
│  Each domain (law_enforcement, medical, etc.) has:                         │
│  • vocabulary.yaml — domain-specific terms                                 │
│  • extraction.yaml — entity/event patterns                                 │
│  • classification.yaml — classification rules                              │
│  • transformation.yaml — neutralization rules                              │
│                                                                              │
│  Goal: Add new domain = just add YAML files                                │
│  Dependency: Stage 4 (unified rule system)                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Critical Gaps Identified

### Gap 1: Entity Classification Not Connected

**Issue**: Stage 1 only classifies Events. Entity has classification fields but no pass populates them.

**Current State**:
```python
# Entity fields exist (Stage 0)
entity.is_valid_actor = True  # Default
entity.is_named = False       # Default
entity.gender = None          # Default

# No pass sets these!
```

**Impact on Stage 2**:
- Entity selection in p55_select uses `role` and `participation` (from Entity schema)
- Does NOT use Stage 1 classification fields
- Inconsistent: Events use classification, Entities use role

**Options**:
1. **Accept inconsistency** — Entity selection uses role, Events use classification
2. **Add p33_classify_entities** — Before Stage 2, populate Entity classification fields
3. **Defer** — Classification fields exist, populate them later

**Recommendation**: Option 1 for now. Entity selection by role is sufficient. Add p33 later.

---

### Gap 2: SpeechAct Classification Not Connected

**Issue**: SpeechAct has `speaker_resolved` field but no pass populates it.

**Current State**:
```python
# SpeechAct fields exist (Stage 0)
speechact.speaker_resolved = False       # Default
speechact.speaker_resolution_confidence = 0.0
speechact.is_quarantined = False         # Default

# No pass sets these!
```

**Impact on Stage 2**:
- Quote selection uses `speaker_resolved` field
- But no pass populates it!
- Renderer currently does speaker resolution inline

**Options**:
1. **Move speaker resolution to p36_resolve_quotes** — Before Stage 2
2. **Stage 2 derives from quote content** — Check if quote has speaker at selection time
3. **Keep in renderer temporarily** — Renderer still does resolution, sets field

**Recommendation**: Option 2 for now. p55_select can check if quote has speaker_label set (already exists on SpeechAct). Add p36 later.

---

### Gap 3: Timeline Classification Not Connected

**Issue**: TimelineEntry has `has_unresolved_pronouns` but no pass populates it.

**Current State**:
```python
# TimelineEntry fields exist (Stage 0)
timeline_entry.has_unresolved_pronouns = False  # Default
timeline_entry.display_quality = "normal"       # Default

# No pass sets these!
```

**Impact on Stage 2**:
- Timeline selection uses `has_unresolved_pronouns`
- No pass populates it
- Renderer currently checks pronouns inline

**Options**:
1. **Extend p43_resolve_actors** — Check timeline entries for pronouns
2. **Stage 2 derives inline** — Check pronouns at selection time
3. **Defer** — Use all timeline entries, filter later

**Recommendation**: Option 2 for now. p55_select can check for pronoun patterns.

---

### Gap 4: "Items Discovered" Section

**Issue**: The ITEMS DISCOVERED section is extracted at render-time from event descriptions.

**Current State**:
```python
# In structured.py, lines 854-1057
# Patterns extracted from event descriptions:
DISCOVERY_PATTERNS = [r'found\s+(.+)', r'seized\s+(.+)', ...]
CONTRABAND_TERMS = {'cocaine', 'heroin', ...}
WEAPON_TERMS = {'gun', 'knife', ...}
```

**Impact on Stage 2**:
- Not a selection from existing atoms
- Extraction of NEW data at render time
- Doesn't fit SelectionResult model

**Options**:
1. **Create new atom type** — DiscoveredItem, populate in extraction pass
2. **Create extraction pass** — p36_extract_items, stores on context
3. **Keep in renderer** — It's formatting logic, not selection

**Recommendation**: Option 3 for Stage 2. Items extraction is specific to law enforcement domain. Can move to Stage 5 (domain system).

---

### Gap 5: Source-Derived Events

**Issue**: Stage 2 SelectionResult has `source_derived_events` but Stage 1 doesn't classify this.

**Current State**:
```python
# Stage 1 classification doesn't have:
event.is_source_derived = ???  # Field doesn't exist!

# Stage 2 expects:
result.source_derived_events = [...]  # But how to know?
```

**Impact on Stage 2**:
- Can't select source-derived events without classification
- Need to add field to Event schema

**Options**:
1. **Add is_source_derived to Event** — Stage 0/1 enhancement
2. **Remove from SelectionResult** — Don't have this distinction
3. **Derive at selection time** — Use SOURCE_DERIVED_PATTERNS

**Recommendation**: Option 3 for now. p55_select can check patterns inline. Add field later.

---

## Stage Dependency Corrections

### Current (In Roadmap)
```
Stage 0 → Stage 1 → Stage 2 → Stage 3 → Stage 6
              ↓
           Stage 4 → Stage 5
```

### Corrected (With Gaps Addressed)
```
Stage 0 (Schema)
    │
    ▼
Stage 1 (Event Classification) ─────────────────────┐
    │                                               │
    │  [FUTURE: Entity/Quote/Timeline Classification]
    │                                               │
    ▼                                               ▼
Stage 2 (Selection)                          Stage 4 (Rules)
    │                                               │
    ▼                                               ▼
Stage 3 (Renderer)                           Stage 5 (Domains)
    │
    ▼
Stage 6 (Recomposition)
```

**Key insight**: Stage 2 can proceed even without entity/quote/timeline classification. Selection logic will derive from existing fields (role, speaker_label, pronouns).

---

## Stage 2 Completeness Check

### Required Fields for Selection

| Selection | Field Needed | Source | Status |
|-----------|--------------|--------|--------|
| Event → OBSERVED | `is_camera_friendly` | Stage 1 | ✅ |
| Event → FOLLOW-UP | `is_follow_up` | Stage 1 | ✅ |
| Event → EXCERPTS | `camera_friendly_reason` | Stage 1 | ✅ |
| Entity → section | `role`, `participation` | Existing schema | ✅ |
| Entity → excluded | `label` (bare role check) | Inline pattern | ⚠️ Pattern-based |
| Quote → PRESERVED | `speaker_label` exists | Existing schema | ✅ |
| Quote → QUARANTINE | `speaker_label` missing | Existing schema | ✅ |
| Timeline → included | pronoun check | Inline pattern | ⚠️ Pattern-based |
| Timeline → excluded | conjunction check | Inline pattern | ⚠️ Pattern-based |

**Assessment**: Stage 2 can proceed. Some selections use inline patterns instead of pre-computed fields. This is acceptable for MVP.

---

## Recommendations

### 1. Proceed with Stage 2 As Planned ✅

The Stage 2 document is comprehensive. Gaps exist but are manageable:
- Entity selection uses role (existing field)
- Quote selection checks speaker_label (existing field)
- Timeline selection uses inline patterns (acceptable)

### 2. Add Missing Classification Later (Stage 1.5)

After Stage 2, before Stage 3, consider:
- **p33_classify_entities** — Populate is_valid_actor, is_named, gender, domain_role
- **p36_classify_quotes** — Populate speaker_resolved, speaker_resolution_confidence
- **Extend p44_timeline** — Populate has_unresolved_pronouns

This can be folded into Stage 4 (Rule System) if we define extraction rules for these.

### 3. Revise Stage 3 Dependencies

Stage 3 (Renderer Simplification) should explicitly require:
- Stage 2 complete (selection infrastructure)
- Renderer using SelectionResult (Phase 2 of Stage 2 migration)

### 4. Add is_source_derived to Event Schema

Small addition to Stage 0/1:
```python
# Event schema addition
is_source_derived: bool = Field(False, description="...")

# p35_classify_events addition
if is_source_derived_pattern(text):
    event.is_source_derived = True
```

---

## Final Validation Checklist

| Stage | Document | Dependencies Clear | Output Clear | Input Clear | Tests Clear |
|-------|----------|-------------------|--------------|-------------|-------------|
| 0 | ✅ Complete | ✅ None | ✅ Schema fields | ✅ N/A | ✅ 578 pass |
| 1 | ✅ Complete | ✅ Stage 0 | ✅ Classification | ✅ Empty fields | ✅ 578 pass |
| 2 | 📋 Ready | ✅ Stage 1 | ✅ SelectionResult | ✅ Classification | 📋 Defined |
| 3 | 📋 Planned | ✅ Stage 2 | ✅ Simplified renderer | ✅ SelectionResult | 📋 TBD |
| 4 | 📋 Outline | ✅ Stage 1 | 📋 Unified rules | 📋 Current rules | 📋 TBD |
| 5 | 📋 Outline | ✅ Stage 4 | 📋 Domain configs | 📋 Unified rules | 📋 TBD |
| 6 | 📋 Outline | ✅ Stage 3 | 📋 Narrative | ✅ SelectionResult | 📋 TBD |

---

## Action Items

### Before Starting Stage 2

1. ✅ Stage 2 document is complete
2. ⚠️ Consider adding `is_source_derived` to Event (minor enhancement)
3. ⚠️ Document inline pattern approach for entity/quote/timeline selection

### During Stage 2

1. Implement p55_select with inline patterns where classification fields don't exist
2. Track which selections use classification vs inline patterns
3. These inline patterns become candidates for Stage 1 extensions

### After Stage 2

1. Evaluate: Which inline patterns should become classification rules?
2. Plan Stage 1.5 or fold into Stage 4

---

*Critical Review — 2026-01-18*
