# NNRT v2 Implementation Roadmap
## From Lexical Neutralizer to Structural Decomposer

**Status**: Planning
**Created**: 2026-01-14
**Target**: Pre-Alpha → Alpha

---

## Vision

Transform NNRT from a "cautious paraphrase engine" to a "structural decomposition engine" that:

1. **Decomposes** narratives into atomic statements
2. **Classifies** each statement by type (observation/claim/interpretation)
3. **Tracks provenance** (interpretations link to source observations)
4. **Outputs structure first**, prose only as derived view

---

## Current State (v1)

```
Input → [Segment] → [Tag] → [Policy] → [Render] → Softened Prose
                                            ↑
                                    Information loss happens here
```

### What v1 Does Well ✅
- Quote-aware segmentation
- Entity/identifier extraction
- Policy rule matching
- Overlapping rule resolution
- Lexical neutralization

### What v1 Lacks ❌
- Statement type classification
- Observation/interpretation separation
- Provenance tracking
- Structured output format

---

## Target State (v2)

```
Input → [Segment] → [Tag] → [Decompose] → [Classify] → [Link] → Structured Output
                                                           ↓
                                              [Optional: Render Prose]
```

---

## Implementation Phases

### Phase 0: Foundation (DONE ✅)
- [x] Quote-aware segmentation
- [x] Policy decision observability (`--raw` flag)
- [x] Stress test infrastructure
- [x] Output schema design (v0.1)
- [x] Gold standard example

**Deliverable**: Can observe what pipeline extracts before rewriting

---

### Phase 1: Statement Decomposition
**Goal**: Break segments into atomic statements

**Tasks**:
- [ ] Create `p25_decompose.py` pass
- [ ] Implement clause boundary detection
- [ ] Split compound sentences into atomic statements
- [ ] Preserve span mapping to original text
- [ ] Update IR schema for atomic statements

**Example**:
```
Input segment:
"Officer Jenkins grabbed my arm and twisted it behind my back."

Decomposed:
- "Officer Jenkins grabbed reporter's arm"
- "Officer Jenkins twisted reporter's arm behind reporter's back"
```

**Testing**:
- [ ] Unit tests for decomposition
- [ ] Validate no content loss
- [ ] Maintain original span references

**Estimated Effort**: Medium

---

### Phase 2: Statement Classification
**Goal**: Assign type to each statement

**Tasks**:
- [ ] Create `p30_classify_statements.py` pass (enhance existing)
- [ ] Implement classification rules:
  - Physical actions → `observation`
  - Direct quotes → `reported_speech`
  - Internal states → `claim`
  - Intent words (deliberately, wanted to, etc.) → `interpretation`
  - Medical/legal documents → `medical_record` / `document`
- [ ] Add confidence scoring
- [ ] Flag ambiguous cases for review

**Classification Signals**:
| Signal | Type |
|--------|------|
| Physical verbs (grab, push, move) | observation |
| Quote markers | reported_speech |
| Pain/fear/feeling words | claim |
| "deliberately", "intentionally", "wanted to" | interpretation |
| "believed", "thought", "assumed" | interpretation |
| Medical terminology + source | medical_record |

**Testing**:
- [ ] Classification accuracy tests
- [ ] Edge case handling
- [ ] Confidence calibration

**Estimated Effort**: High

---

### Phase 3: Provenance Linking
**Goal**: Connect interpretations to their source observations

**Tasks**:
- [ ] Create `p35_link_provenance.py` pass
- [ ] Build statement dependency graph
- [ ] Implement `derived_from` links
- [ ] Detect circular dependencies
- [ ] Handle multi-source interpretations

**Example**:
```yaml
stmt_004:  # "Reporter believes force was excessive"
  derived_from: [stmt_001, stmt_003]
  # ↑ Links to "grabbed arm" and "force applied"
```

**Testing**:
- [ ] Provenance graph validation
- [ ] No orphan interpretations
- [ ] Link accuracy tests

**Estimated Effort**: Medium

---

### Phase 4: Structured Output
**Goal**: New output format as primary

**Tasks**:
- [ ] Implement `StructuredOutput` model (from schema v0.1)
- [ ] Create `--format structured` output
- [ ] Add statement filtering CLI options
- [ ] Create structured output renderer
- [ ] Deprecate prose as primary output

**CLI**:
```bash
# New default: structured
nnrt transform input.txt --format structured

# Optional: old prose mode
nnrt transform input.txt --format prose

# Filter by type
nnrt transform input.txt --filter observations
nnrt transform input.txt --filter interpretations
```

**Testing**:
- [ ] Schema validation tests
- [ ] Round-trip tests (input → structured → matches expected)
- [ ] Reviewer usability testing

**Estimated Effort**: Medium

---

### Phase 5: Prose as Derived View
**Goal**: Prose rendering from structured statements (optional)

**Tasks**:
- [ ] Update render pass to work from statements
- [ ] Implement rendering modes:
  - `clinical`: Boring, flat, NNRT-compliant
  - `standard`: Current neutralized style (deprecated warning)
- [ ] Ensure prose is ALWAYS secondary
- [ ] Add "derived from structure" marker in prose output

**Output Example**:
```
=== STRUCTURED OUTPUT ===
[statements as yaml/json]

=== DERIVED PROSE (OPTIONAL) ===
⚠️ This prose is derived from the structured statements above.
   For authoritative output, use the structured format.

[rendered prose]
```

**Estimated Effort**: Low (reuse existing render)

---

### Phase 6: Validation & Testing
**Goal**: Ensure NNRT meets its promise

**Tasks**:
- [ ] Create adversarial test suite
- [ ] Implement "reviewer clarity test":
  - Can reviewer distinguish observation/claim/interpretation?
  - Can reviewer trace interpretations to source?
  - Does output feel "emotionally neutral"?
- [ ] Build regression test suite
- [ ] Document failure modes

**Adversarial Tests**:
- [ ] Intent smuggling (hedge words that still imply intent)
- [ ] Observation pollution (judgment in observation statements)
- [ ] Provenance gaps (unlinked interpretations)
- [ ] Classification errors (observation mislabeled as claim)

**Estimated Effort**: Medium

---

## Dependencies

```
Phase 0 ✅
    ↓
Phase 1 (Decompose)
    ↓
Phase 2 (Classify) ←── Can start some work in parallel
    ↓
Phase 3 (Link) ←── Requires Phase 2
    ↓
Phase 4 (Output) ←── Requires Phase 1-3
    ↓
Phase 5 (Prose) ←── Requires Phase 4
    ↓
Phase 6 (Validate) ←── Happens throughout
```

---

## Success Criteria

### Minimum Viable NNRT v2
- [ ] Every statement has a type
- [ ] Observations contain no judgment
- [ ] Interpretations explicitly flagged
- [ ] Provenance links present
- [ ] Structured output is default

### Full NNRT v2
- [ ] All minimum criteria
- [ ] Confidence scoring accurate
- [ ] Reviewer clarity test passes
- [ ] Adversarial tests pass
- [ ] <5% unknown classification rate
- [ ] <2% provenance gap rate

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Classification accuracy too low | High | Start with high-signal patterns, flag uncertain |
| Decomposition breaks sentence flow | Medium | Preserve original text spans for debugging |
| Provenance links incorrect | Medium | Conservative linking, flag uncertain |
| Performance regression | Low | Optimize after correctness |
| Scope creep | High | Strict phase boundaries, no feature additions |

---

## Timeline (Estimated)

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Decompose | 2-3 sessions | None |
| Phase 2: Classify | 3-4 sessions | Phase 1 |
| Phase 3: Link | 2 sessions | Phase 2 |
| Phase 4: Output | 2 sessions | Phase 1-3 |
| Phase 5: Prose | 1 session | Phase 4 |
| Phase 6: Validate | Ongoing | All |

**Total**: ~10-12 focused sessions

---

## Next Steps

1. **Review this roadmap** — Any phases missing? Priority changes?
2. **Start Phase 1** — Decomposition pass
3. **Create test cases** — Inputs with expected decomposed outputs

---

## Appendix: Key Decisions Made

1. **Prose is secondary** — Structured statements are THE output
2. **Confidence scoring** — Some classifications will be uncertain
3. **Provenance is required** — No orphan interpretations
4. **Flagging over hiding** — Unknown/ambiguous gets flagged, not hidden
5. **Backwards compatibility** — Old `--format text` still works (with warning)
