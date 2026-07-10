# NNRT Architectural Gap Analysis
## Date: 2026-01-14
## Status: 🔴 CRITICAL — Requires Architectural Rethink

---

## Executive Summary

NNRT v1 successfully performs **lexical neutralization** (softening inflammatory language) but fails at **structural decomposition** (separating observation from interpretation).

The current output is a **cautious paraphrase**, not a **neutral representation**.

This is not a bug — it's a paradigm error in the core design.

---

## The Core Promise (What NNRT Should Do)

NNRT must:
1. **Extract structure** — Break narrative into atomic statements
2. **Separate layers** — Observation / Claim / Interpretation / Uncertainty
3. **Make ambiguity explicit** — Don't resolve it, mark it
4. **Preserve provenance** — Link interpretations to their source observations
5. **Enable reviewer clarity** — Reviewer must be able to answer:
   - What was observed?
   - What is claimed?
   - What is inferred?
   - What is unknown?

---

## What NNRT v1 Actually Does

1. **Rewrites prose linearly** — Preserves narrative flow
2. **Swaps insults for hedges** — "brutal" → (removed), "wanted to" → "appeared to"
3. **Keeps accusations embedded in prose** — Still reads as accusation
4. **Smuggles judgment through hedging language** — "appeared", "described as", "suggests"
5. **Produces emotionally legible output** — Should feel boring, clinical, flat

**Verdict**: Cosmetic neutralization, not structural normalization.

---

## Specific Failures Identified

### 1. Massive Overuse of "Appeared / Described / Suggests"

Examples from stress test output:
- "appeared to be looking for trouble"
- "described as excessive force"  
- "suggests there's a large disputed process"
- "appeared they were discussing how to cover up"

**Problem**: This launders inference through hedging verbs. The interpretation is still presented inline as fact-adjacent prose, just softened.

**Correct Behavior**:
```
Observation: Officer twisted arm behind back.
Claim: Reporter states force was excessive.
Interpretation: Reporter believes intent was to cause harm.
```

### 2. Illegal Intent/Mental State Inference

Even hedged, these are intent attributions:
- "appeared to be looking for trouble"
- "appeared to enjoy my suffering"
- "was a threat that they would fabricate charges"

**NNRT must not infer intent** — only label that the reporter is inferring intent.

### 3. Failure to Separate Observation vs Interpretation

**Input**: "Officer Jenkins deliberately grabbed my left arm with excessive force"

**Current Output**: "grabbed my left arm with described as excessive force"

**Correct Output**:
```
Observation: Officer Jenkins grabbed reporter's left arm and twisted it behind back.
Claim: Reporter states force caused pain.
Interpretation: Reporter believes force was excessive.
```

### 4. Introduction of New Semantic Artifacts

NNRT invented new content:
- "large disputed process" (not in input)
- "internal review and disputed process" (not in input)
- "known offender" (not in input)

**NNRT must not introduce new semantic content.**

### 5. Syntactic Degradation

Trust-killing errors:
- "grabbed my left arm with described as excessive force"
- "making physical contact with an person"
- Inconsistent tense
- Sentence fragments

---

## Architectural Gap Analysis

### Current Pipeline (v1)

```
Input Narrative
    ↓
[Segmentation] → Sentences
    ↓
[Span Tagging] → Identify entities, quotes, etc.
    ↓
[Policy Evaluation] → Match rules, create transformations
    ↓
[Rendering] → Apply transformations to prose
    ↓
Output: Softened Prose ← WRONG OUTPUT TYPE
```

### Required Pipeline (v2)

```
Input Narrative
    ↓
[Segmentation] → Sentences (quote-aware) ✅ Done
    ↓
[Decomposition] → Atomic statements ← NEW PASS
    ↓
[Classification] → Type each statement ← NEW PASS
    │   - observation
    │   - claim
    │   - interpretation
    │   - reported_speech
    │   - unknown
    ↓
[Entity/Provenance Linking] → Connect statements ← NEW PASS
    ↓
[Structured IR] → Statement graph with metadata
    ↓
[Optional: Prose Rendering] → Only if requested, always secondary
    ↓
Output: Structured Statements + (optional) Derived Prose
```

### Key Insight: Information Loss

Current pipeline loses critical information:
- **Classification data** (observation vs interpretation) — never extracted
- **Provenance** (which interpretation comes from which observation) — never tracked
- **Confidence levels** — never computed
- **Source attribution** — partially tracked but not exposed

We need observability into the pipeline to debug this. A `--debug` flag should expose the IR at each stage.

---

## Open Questions

1. **Where does classification data live?**
   - In the rendered output? (verbose)
   - In metadata only? (hidden from default view)
   - In structured IR? (requires schema change)

2. **What is the primary output format?**
   - Structured statements (JSON/YAML)?
   - Prose with inline markers?
   - Separate layers (prose + metadata)?

3. **How do we handle ambiguity?**
   - Mark it explicitly?
   - Split into multiple possible interpretations?
   - Flag for human review?

4. **How do we test structural correctness?**
   - Current tests check string presence/absence
   - Need tests that verify statement classification
   - Need tests that verify provenance links

---

## Proposed Next Steps

### Phase 1: Design (Before Any Code)
- [ ] Define NNRT output schema formally
- [ ] Create manual "gold standard" decomposition of stress test paragraph
- [ ] Define invariants that must hold (testable properties)
- [ ] Design debug/observability mode

### Phase 2: Infrastructure  
- [ ] Add `--debug` flag to expose IR at each stage
- [ ] Create statement classification pass
- [ ] Create provenance linking pass
- [ ] Update IR schema to support structured statements

### Phase 3: Implementation
- [ ] Implement decomposition pass
- [ ] Implement classification pass
- [ ] Update rendering to be optional/secondary
- [ ] Create new stress tests for structural correctness

### Phase 4: Validation
- [ ] Manual review of stress test output
- [ ] Adversarial tests that current system would fail
- [ ] Reviewer clarity test (can reviewer distinguish observation/claim/interpretation?)

---

## What We Fixed Today (Still Valid)

The following fixes are still valuable and should be preserved:

1. ✅ **Quote-aware segmentation** — Multi-sentence quotes now stay together
2. ✅ **Overlapping rule consumption** — No more word corruption
3. ✅ **Verb tense preservation** — "screamed" → "spoke loudly" (past tense correct)
4. ✅ **Article agreement** — "a alleged" → "an alleged"
5. ✅ **Double verb fix** — "was clearly looking" no longer becomes "was appeared"

These are valid improvements to the lexical layer. The problem is that lexical improvement alone is insufficient.

---

## Key Realization

> NNRT is supposed to break the story apart, not retell it politely.

The tool isn't bad. It's incomplete. We've built a good lexical transformer. We haven't built a structural decomposer yet.

The next phase is about **decomposition**, not **rewriting**.

---

## References

- `stress_tests/cases/02_mega_law_enforcement.yaml` — Full stress test
- `docs/analysis/infrastructure_gaps_v3.md` — Previous gap analysis (lexical level)
- This document — Architectural gap analysis (structural level)
