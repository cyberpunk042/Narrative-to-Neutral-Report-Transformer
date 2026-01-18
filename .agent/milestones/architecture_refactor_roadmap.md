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

### Stage 0: Foundation — Atom Schema Enhancement
**Document**: `.agent/milestones/stage_0_atom_schema.md`

Enhance the IR schema so that all classification metadata has a home on the atoms themselves. Classification should be computed in the pipeline and stored, not computed at render-time.

**Scope**:
- Review all atom types (AtomicStatement, Entity, Event, TimelineEntry, SpeechAct)
- Identify fields that are currently computed at render-time
- Add missing classification fields to IR schema
- Create migration plan for populating new fields

---

### Stage 1: Classification Layer Unification
**Document**: `.agent/milestones/stage_1_classification.md`

Move all classification logic from the renderer and scattered passes into a unified classification layer in the pipeline. Extend the Policy Engine to support classification rules alongside transformation rules.

**Scope**:
- Inventory all classification logic currently in renderer
- Inventory all classification patterns in pipeline passes (p27, p32, p48, etc.)
- Design extended PolicyEngine with classification rule type
- Migrate classification logic to pipeline passes
- Store classification results on atoms

---

### Stage 2: Selection Layer Creation
**Document**: `.agent/milestones/stage_2_selection.md`

Create a new Selection layer that sits between Classification and Rendering. This layer chooses which atoms to include in output based on the selected output mode.

**Scope**:
- Define output modes (strict, full, events-only, timeline-only, recomposition)
- Design selection predicates for each mode
- Create selection pass or component
- Move selection logic from renderer to this layer

---

### Stage 3: Renderer Simplification
**Document**: `.agent/milestones/stage_3_renderer.md`

Strip the renderer down to formatting-only. It should receive pre-classified, pre-selected atoms and simply format them for display. No classification. No selection. No business logic.

**Scope**:
- Remove classification logic from structured.py
- Remove selection logic from structured.py
- Keep only formatting/display logic
- Create multiple renderer modes (report, JSON, etc.)
- Target: ~500 lines instead of ~2000

---

### Stage 4: Rule System Unification
**Document**: `.agent/milestones/stage_4_rules.md`

Unify all rule types under the Policy Engine. Consolidate duplicated patterns. Define a single schema for all rules (transformation, classification, validation, extraction).

**Scope**:
- Extend PolicyEngine with new rule types
- Define unified rule schema
- Migrate scattered patterns to YAML configs
- Consolidate duplicates between files
- Create rule composition system

---

### Stage 5: Domain System Completion
**Document**: `.agent/milestones/stage_5_domains.md`

Complete the domain system so that each domain is a self-contained configuration with vocabulary, extraction patterns, classification rules, and transformation rules. Enable clean domain composition.

**Scope**:
- Design complete domain schema
- Extend law_enforcement.yaml with full vocabulary
- Create domain composition mechanism
- Add domain auto-detection (future)
- Template for adding new domains

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
