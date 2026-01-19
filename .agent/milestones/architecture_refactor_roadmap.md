# NNRT Architecture Refactoring — Master Roadmap

## Overview

This document provides a high-level roadmap for the architectural refactoring of NNRT. Each stage is a substantial body of work that warrants its own detailed planning document.

**Goal**: Transform NNRT from a monolithic design where layers are mixed, to a clean layered architecture that enables multiple output modes including future narrative recomposition.

---

## The Target Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        INPUT: Narrative                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                LAYER 1: DECOMPOSITION                           │
│  Break narrative into atomic pieces (statements, entities,      │
│  events, timeline entries, quotes)                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                LAYER 2: CLASSIFICATION                          │
│  Tag every atom with semantic metadata (epistemic type,         │
│  camera-friendly, validity, domain-specific tags)               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                LAYER 3: SELECTION                               │
│  Choose which atoms to include based on output mode             │
│  (strict, full, recomposition, etc.)                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                LAYER 4: RENDERING                               │
│  Format selected atoms into output (report, JSON, narrative)    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        OUTPUT: Multiple Modes                    │
│  • Neutralized Report (current)                                 │
│  • Recomposed Narrative (future)                                │
│  • Machine-Readable (JSON/API)                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Stage Breakdown

### Stage 0: Foundation — Atom Schema Enhancement ✅ COMPLETE
**Document**: `.agent/milestones/stage_0_atom_schema.md`

Enhance the IR schema so that all classification metadata has a home on the atoms themselves. Classification should be computed in the pipeline and stored, not computed at render-time.

**Scope**:
- Review all atom types (AtomicStatement, Entity, Event, TimelineEntry, SpeechAct) ✅
- Identify fields that are currently computed at render-time ✅
- Add missing classification fields to IR schema ✅
- Create migration plan for populating new fields ✅
- **Populate Entity classification fields in p32** ✅ (2026-01-18)
- **Populate SpeechAct classification fields in p40** ✅ (2026-01-18)
- **Populate TimelineEntry classification fields in p44** ✅ (2026-01-18)

**Completed 2026-01-18**: 
- Added 40+ classification fields across Event, Entity, SpeechAct, TimelineEntry, and StatementGroup atoms
- **All atom types now have classification field population**:
  - Entity: is_valid_actor, is_named, gender, domain_role (in p32_extract_entities)
  - SpeechAct: speaker_resolved, is_quarantined, etc. (in p40_build_ir)
  - TimelineEntry: pronouns_resolved, display_quality (in p44_timeline)
  - Event: is_camera_friendly, is_fragment, etc. (in p35_classify_events)

---

### Stage 1: Classification Layer Unification ✅ COMPLETE
**Document**: `.agent/milestones/stage_1_classification.md`

Move all classification logic from the renderer and scattered passes into a unified classification layer in the pipeline. Extend the Policy Engine to support classification rules alongside transformation rules.

**Scope**:
- Inventory all classification logic currently in renderer ✅
- Inventory all classification patterns in pipeline passes ✅
- Design extended PolicyEngine with classification rule type ✅
- Migrate classification logic to pipeline passes ✅
- Store classification results on atoms ✅

**Completed 2026-01-18**:
- Extended RuleAction with CLASSIFY, DISQUALIFY, DETECT, STRIP
- Created p35_classify_events pass using PolicyEngine rules
- Created _classification/camera_friendly.yaml and neutralization.yaml
- Event generator now uses pre-computed is_camera_friendly
- Renderer functions marked DEPRECATED (V8 fallback retained)

---

### Stage 2: Selection Layer Creation
**Document**: `.agent/milestones/stage_2_selection.md` ✅ COMPLETE

Create a new Selection layer that sits between Classification and Rendering. This layer chooses which atoms to include in output based on the selected output mode.

**Completed**:
- ✅ `SelectionMode` enum (STRICT, FULL, TIMELINE, EVENTS_ONLY, RECOMPOSITION)
- ✅ `SelectionResult` dataclass with event/entity/quote/timeline routing
- ✅ `p55_select` pass wired into pipeline after evaluate_policy
- ✅ TransformContext.selection_result + helper methods
- ✅ CLI mode configuration: `--mode strict|full|timeline|events|recompose`
- ✅ Unit tests: tests/test_selection.py (24 tests)
- ✅ All 602 tests pass

**Deferred to Stage 3**:
- [ ] Renderer reads from SelectionResult instead of inline logic

**Key Design Decisions**:
- Selection stores IDs, not copies (atoms remain in original lists)
- Renderer fallback to inline logic during migration
- STRICT mode = current behavior (camera-friendly only)

---

### Stage 3: Renderer Simplification
**Document**: `.agent/milestones/stage_3_renderer.md` ✅ CORE COMPLETE

Strip the renderer down to **formatting-only**. It should receive pre-classified, pre-selected atoms and simply format them for display. No classification. No selection. No business logic.

**Completed**:
1. ✅ All 7 sections have SelectionResult paths
2. ✅ `p90_render_structured` pass created
3. ✅ `structured_only` pipeline uses new pass
4. ✅ Deprecated code marked with comments
5. ✅ All 602 tests pass
6. ✅ `format_structured_output` accepts `selection_result` directly (2026-01-18)
7. ✅ Web server updated to use `build_selection_from_result()` (2026-01-18)
8. ✅ `nnrt/selection/utils.py` created with helper function
9. ✅ All legacy blocks marked DEPRECATED with TODO comments

**Remaining (optional cleanup)**:
- Remove legacy code blocks (~1500 lines) once confident in new path
- Reduce structured.py from ~2365 to ~800 lines (estimated)

**Architecture**:
```
Pipeline: ... → p55_select → ... → p90_render_structured → ...
                   ↓                       ↓
            SelectionResult    →    format_structured_output(selection_result=sr)
                                           ↓
                                   Uses new path if selection_result provided
```

**Web Server Path**:
```
TransformResult → build_selection_from_result() → SelectionResult → format_structured_output()
```

---

### Stage 4: Rule System Unification
**Document**: `.agent/milestones/stage_4_rules.md` ✅ CORE COMPLETE

Unify all rule types under the Policy Engine. Consolidate duplicated patterns scattered across Python files into YAML configurations.

**Complete**:
- ✅ Schema extension (Phase 1)
- ✅ PolicyEngine action handlers (Phase 2)
- ✅ **67 rules in YAML** (Phase 3)
- ✅ p25_annotate_context using YAML rules
- ✅ p46_group_statements using YAML rules
- ✅ Legacy patterns marked DEPRECATED

**YAML Files**:
- `_context/`: 32 rules (force, injury, timeline, charge)
- `_extraction/`: 11 rules (entity roles)
- `_grouping/`: 24 rules (statement groups)

**Optional Remaining**:
- p32_extract_entities migration
- Schema validation

---

### Stage 5: Domain System Completion
**Document**: `.agent/milestones/stage_5_domains.md` ✅ PHASE 4 COMPLETE

Complete the domain system so that each domain is a self-contained configuration with vocabulary, extraction patterns, classification rules, and transformation rules. Enable clean domain composition.

**Completed**:
1. ✅ Phase 1: Domain Schema
   - `nnrt/domain/schema.py` - Pydantic models
   - `nnrt/domain/loader.py` - Load, cache, merge
2. ✅ Phase 2: Migrate Existing Rules
   - `nnrt/domain/configs/base.yaml` - Universal rules (37 transformations)
   - Migrated rules from `_categories/` files
3. ✅ Phase 3: Domain Composition
   - `law_enforcement.yaml` extends `base`
   - 50 rules (37 base + 13 domain-specific)
4. ✅ Phase 4: Integration
   - `nnrt/domain/integration.py` - Bridge to PolicyEngine
   - Domain→PolicyRuleset conversion working

**Remaining (optional)**:
- Phase 5: Documentation & domain template command

---

### Stage 6: Recomposition Mode
**Document**: `.agent/milestones/stage_6_recomposition.md`

Create the recomposition renderer that reconstructs classified atoms into a flowing neutral narrative. The current report format remains as one option.

**Scope**:
- Design recomposed narrative format
- Create recomposition renderer
- Ensure original neutralization mode preserved
- Test both modes produce equivalent semantic content

---

## Dependencies Between Stages

```
Stage 0 (Atom Schema)
    │
    ▼
Stage 1 (Classification) ───► Stage 4 (Rules)
    │                              │
    ▼                              ▼
Stage 2 (Selection)         Stage 5 (Domains)
    │
    ▼
Stage 3 (Renderer) ───────────────┐
                                  │
                                  ▼
                           Stage 6 (Recomposition)
```

**Critical Path**: 0 → 1 → 2 → 3

**Independent Track**: 4 → 5 (can happen in parallel after Stage 1)

**Final**: 6 (requires 3)

---

## Preservation Commitment

Throughout all stages:
- The current output format ("Neutralized Report") must be preserved
- Tests must ensure no regression in output quality
- Each stage should be independently deployable

---

## Trust & Verification Philosophy

**CRITICAL PRINCIPLE**: We must NOT assume existing tools or implementations are complete or correct.

### Known Limitations

| Component | Known Gaps |
|-----------|-----------|
| **spaCy NER** | Misses entities, wrong boundaries, title confusion ("Officers" → "Officer") |
| **spaCy Dependencies** | Edge cases in complex sentences, nested clauses |
| **Pronoun Resolution** | Context-dependent, often needs domain hints |
| **Event Extraction** | Fragment extraction, phrasal verbs, missed targets |
| **Timeline Ordering** | Relative time ambiguity, multi-day confusion |

### Design Implications

**1. Confidence Scores Are Not Optional**

Every classification field should have an associated confidence:
```python
is_camera_friendly: bool = False
camera_friendly_confidence: float = 0.0  # How sure are we?
```

**2. Fallback Behavior Required**

When a tool fails or returns low confidence:
- Don't silently accept bad output
- Have explicit fallback paths
- Log/trace the degradation

**3. Multiple Verification Sources**

Don't trust one signal:
```
Entity detected by spaCy? Check.
But also: Does it match title patterns? Check.
And: Is it referenced elsewhere? Check.
Combined confidence = weighted average
```

**4. "Unknown" Is a Valid State**

Better to say "I don't know" than to guess wrong:
```python
# Bad: Default to True (optimistic assumption)
is_camera_friendly: bool = True

# Good: Default to unknown, require explicit classification
camera_friendly_status: Literal["yes", "no", "unknown"] = "unknown"
```

**5. Audit Trail for Debugging**

When something is wrong, we need to trace WHY:
```python
camera_friendly_reason: Optional[str] = None  # Why yes or no
camera_friendly_source: Optional[str] = None  # Which pass decided
```

### Stage-Specific Considerations

Each stage document MUST include:
- **Known Limitations** section for relevant components
- **Fallback Behavior** for when primary approach fails
- **Confidence Handling** for uncertain outputs
- **Verification Tests** that probe edge cases, not just happy path

---

## Stage Document Template

Each stage document should include:

1. **Objective** - What this stage accomplishes
2. **Current State** - How things work today
3. **Target State** - How things should work after
4. **Inventory** - Specific items to migrate/change
5. **Design** - Technical approach
6. **Implementation Plan** - Step-by-step tasks
7. **Testing Strategy** - How to verify correctness
8. **Rollback Plan** - How to revert if needed
9. **Done Criteria** - When is this stage complete

---

## Next Steps

1. Create the milestones directory: `.agent/milestones/`
2. Start with Stage 0 document (foundation)
3. Expand each stage document as we approach it
4. Track progress in this master document

---

*Master Roadmap — 2026-01-18*
