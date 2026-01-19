# Pre-Stage 5 Technical Debt Review

**Date**: 2026-01-18  
**Purpose**: Identify gaps, TODOs, placeholders, and deferred work before proceeding to Stage 5

---

## Summary of Findings

### 1. Uncompleted Items Across All Stages

| Stage | Item | Priority | Status |
|-------|------|----------|--------|
| **Stage 0** | p32_extract_entities populates Entity fields | Medium | Future |
| **Stage 0** | p36_resolve_quotes populates SpeechAct fields | Medium | Future |
| **Stage 0** | p44_timeline populates TimelineEntry fields | Low | Future |
| **Stage 0** | Tests for new field population | Low | Deferred |
| **Stage 1** | Renderer reads pre-computed fields only | Medium | V8 fallback needed |
| **Stage 2** | Renderer has optional SelectionResult path | N/A | Stage 3 scope |
| **Stage 3** | V8 fallback removed | Medium | Legacy still needed |
| **Stage 3** | structured.py reduced to ~500-800 lines | Low | After legacy removal |
| **Stage 3** | Golden case outputs verified with new path | Medium | Not done |
| **Stage 4** | p32_extract_entities using PolicyEngine | Low | Optional |
| **Stage 4** | Schema validation for YAML rules | Low | Optional |

### 2. Legacy/Fallback Code Still Active

| File | Line Range | Description | Risk |
|------|------------|-------------|------|
| `structured.py` | 226 | V5 LEGACY PATH for entity selection | Low - deprecated |
| `structured.py` | 844 | V8/V9 LEGACY PATH for event selection | Medium - still used |
| `structured.py` | 1564 | LEGACY PATH for quote speaker extraction | Medium - still used |
| `structured.py` | 1912 | LEGACY PATH for timeline filtering | Medium - still used |
| `event_generator.py` | 736 | Legacy inline classification fallback | Low |
| `output/structured.py` | 505 | Legacy V4 classification still active | Low |

### 3. TODO/FIXME Comments in Code

| File | Line | Content | Priority |
|------|------|---------|----------|
| `nlp/backends/hf_encoder.py` | 7 | TODO: Implement when NLP dependencies are added | N/A (placeholder) |
| `nlp/backends/json_instruct.py` | 12 | TODO: Implement when NLP dependencies are added | N/A (placeholder) |

### 4. Stub/Placeholder Implementations

| File | Function/Class | Description | Action Needed |
|------|----------------|-------------|---------------|
| `passes/p60_augment_ir.py` | augment_ir() | Stub - no augmentation applied | Expected behavior |
| `nlp/backends/stub.py` | StubSpanTagger | No-op for testing | Expected behavior |
| `nlp/backends/stub.py` | StubEntityExtractor | No-op for testing | Expected behavior |
| `nlp/backends/stub.py` | StubEventExtractor | No-op for testing | Expected behavior |
| `nlp/backends/hf_encoder.py` | (entire file) | Placeholder module | Future work |
| `nlp/backends/json_instruct.py` | (entire file) | Placeholder module | Future work |
| `validate/idempotence.py` | (entire file) | Stub validation | Future work |

### 5. DEPRECATED Patterns Still in Code

| File | Pattern Count | Description |
|------|---------------|-------------|
| `passes/p25_annotate_context.py` | 4 | CHARGE, FORCE, INJURY, TIMELINE patterns |
| `passes/p46_group_statements.py` | 7 | ENCOUNTER, MEDICAL, WITNESS, etc. patterns |
| `render/structured.py` | 6 | V8 fallback functions |
| `ir/enums.py` | 3 | AUTHORITY, WITNESS, OBJECT aliases |

### 6. USE_YAML_RULES Flags (Toggle Points)

| File | Flag | Current Value | Notes |
|------|------|---------------|-------|
| `passes/p25_annotate_context.py` | USE_YAML_RULES | True | Using YAML |
| `passes/p46_group_statements.py` | USE_YAML_RULES | True | Using YAML |

---

## Critical Gap Analysis

### Gap 1: Entity/Quote/Timeline Classification Not Implemented

**What was planned (Stage 0)**:
- `p32_extract_entities` populates Entity `is_valid_actor`, `is_named`, `gender`, `domain_role`
- `p36_resolve_quotes` populates SpeechAct `speaker_resolved`, `is_quarantined`
- `p44_timeline` populates TimelineEntry `has_unresolved_pronouns`, `display_quality`

**Current State**:
- These fields exist on schemas ✅
- No pass populates them ❌
- Selection uses inline patterns instead

**Risk**: Low - inline patterns work, just not as clean as pre-computed fields

**Recommendation**: Defer to future. Selection works with existing fields (role, speaker_label, etc.)

---

### Gap 2: V8/V9 Fallback Still Active in Renderer

**What was planned (Stage 3)**:
- Remove V8 fallback path
- Reduce structured.py to ~500-800 lines

**Current State**:
- SelectionResult path exists and works ✅
- V8/V9 fallback is still the default pipeline path
- structured.py is still ~2000 lines

**Why it wasn't removed**:
- Default CLI doesn't use SelectionResult path
- Need to update CLI/pipeline to default to new path

**Risk**: Medium - two code paths to maintain

**Recommendation**: 
1. Update main CLI pipeline to use `--mode` with SelectionResult
2. Verify golden cases pass with new path
3. Then mark V8 for removal

---

### Gap 3: Golden Cases Not Verified with New Path

**What was planned (Stage 3)**:
- Verify golden case outputs with SelectionResult path

**Current State**:
- Tests pass ✅
- But golden cases use default (legacy) path
- SelectionResult path not tested against golden outputs

**Risk**: Medium - new path could produce different outputs

**Recommendation**: Run golden cases with `--mode strict` and compare outputs

---

### Gap 4: Source-Derived Classification Added Inline

**What was planned (Critical Review)**:
- Add `is_source_derived` to Event schema

**Current State**:
- `is_source_derived` was added to Event schema ✅
- p35_classify_events populates it ✅
- Working correctly

**Risk**: None - this gap was addressed

---

## Deferred Items (Intentionally)

These items were explicitly deferred as optional/future work:

1. **p32_extract_entities using PolicyEngine** - Optional (Stage 4)
2. **Schema validation for YAML rules** - Optional future work
3. **NLP backend implementations** - Placeholder for future
4. **Idempotence validation** - Stub for future

---

## Actionable Items Before Stage 5

### Must Fix (Blocking)

None - all blocking items resolved.

### Should Fix (Technical Debt)

| Item | Effort | Impact |
|------|--------|--------|
| Verify golden cases with SelectionResult path | 1-2 hrs | High confidence |
| Update CLI to use SelectionResult by default | 2-3 hrs | Simplify maintenance |

### Can Defer (Nice to Have)

| Item | Effort | Impact |
|------|--------|--------|
| Remove V8 fallback after new path verified | 4-8 hrs | Code reduction |
| Entity/Quote/Timeline classification passes | 8-12 hrs | Cleaner architecture |
| YAML schema validation | 2-4 hrs | Better error messages |

---

## Stage-by-Stage Status Summary

### Stage 0: Atom Schema ✅ COMPLETE
- All schema fields added
- Entity/Quote/Timeline population deferred (acceptable)

### Stage 1: Classification Fields ✅ COMPLETE
- Event classification working
- V8 fallback still needed (acceptable until Stage 3 cleanup)

### Stage 2: Selection Layer ✅ COMPLETE
- p55_select working
- SelectionResult infrastructure ready

### Stage 3: Renderer Simplification ✅ CORE DONE
- SelectionResult path exists
- V8 fallback not removed (needs CLI update first)
- **Action needed**: Verify golden cases with new path

### Stage 4: Rule System Unification ✅ CORE DONE
- 67 YAML rules
- p25, p46 using YAML
- p32 deferred (optional)

---

## Verification Results

### Golden Tests
```
pytest tests/test_golden.py: 7 passed, 2 skipped ✅
```

### Full Test Suite
```
pytest tests/: 602 passed, 2 skipped ✅
```

### Pipeline Functionality
- p55_select is in the default pipeline ✅
- SelectionResult is populated ✅
- Renderer has SelectionResult path ✅

---

## Recommendation

### Option A: Proceed to Stage 5 (Recommended)
The core work is complete. Deferred items are:
1. Nice-to-have (none are blocking)
2. Explicitly documented as future work
3. Can be addressed in parallel with Stage 5

**Before starting Stage 5, spend 1-2 hours**:
- [ ] Run golden cases with `--mode strict`
- [ ] Confirm outputs match (or document differences)

### Option B: Close Technical Debt First
Spend 4-8 hours:
- [ ] Update CLI to default to SelectionResult path
- [ ] Verify golden cases
- [ ] Consider removing V8 fallback

Then proceed to Stage 5.

---

## Appendix: Search Results

### TODO/FIXME Comments Found
```
nnrt/nlp/backends/hf_encoder.py:7:# TODO: Implement when NLP dependencies are added
nnrt/nlp/backends/json_instruct.py:12:# TODO: Implement when NLP dependencies are added
```

### Stub/Placeholder Files
```
nnrt/nlp/backends/stub.py — Test stubs (expected)
nnrt/nlp/backends/hf_encoder.py — Future implementation
nnrt/nlp/backends/json_instruct.py — Future implementation
nnrt/passes/p60_augment_ir.py — Stub pass (expected)
nnrt/validate/idempotence.py — Stub validation
```

### Legacy Paths in structured.py
```
Line 226: V5 LEGACY PATH
Line 844: V8/V9 LEGACY PATH
Line 1564: LEGACY PATH (quotes)
Line 1912: LEGACY PATH (timeline)
```

---

*Review completed: 2026-01-18*
