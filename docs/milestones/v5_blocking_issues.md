# NNRT — V5 Blocking Issues (Road to Alpha)

## Status: ACTIVE
## Created: 2026-01-16
## Target: Pre-Alpha → Alpha

---

## Executive Summary

NNRT v0.3 has strong structural foundations but fails key invariants required for
a "neutral" label to be honest. This document tracks the 5 blocking issues that
must be resolved before Alpha.

**Current Rating:**
- As debugging/engine trace: **8/10**
- As neutral report someone could rely on: **4/10**

---

## What's Working Well (Keep)

- ✅ **Parties + roles**: Clear, readable, separated into incident/post-incident/contacts
- ✅ **Reference data**: Clean; officer badge association removes ambiguity
- ✅ **Provenance concept**: "Self-Attested" is the right label
- ✅ **Bucket separation**: observed, self-reported, legal, characterizations, inferences, contested
- ✅ **Quality gates**: Quote validation, actor-unresolved events, validation flags

---

## Blocking Issues

### Issue #1: OBSERVED EVENTS is not actually observed [P0]

**Severity**: TRUST-BREAKING

**Current State**:
The "Observed Events" section contains:
- Pronouns ("He", "they") without resolution
- Dependent fragments ("but …")
- Missing actors ("immediately started screaming at me")
- Mixed quote + narrative on the same line

**Impact**: Reader cannot trust "Observed Events" as a clean, actor-resolved,
camera-friendly log. It's still "raw sentences that sounded factual."

**Solution**: New pass `p43_resolve_actors.py`
- Pronoun → Entity: "He grabbed" → "Officer Jenkins grabbed"
- Fragment Isolation: "but then he…" → separate statement
- Quote/Narrative Split: `"Stop!" he yelled, clearly hostile` → 
  `[QUOTE: "Stop!"]` + `[INFERENCE: reporter perceived hostility]`

**Exit Criteria**:
- [x] Every statement in OBSERVED has explicit actor (no "he/they") ✅ IMPLEMENTED
- [x] No dependent fragments ✅ IMPLEMENTED (flagged as `fragment`)
- [x] Quotes contain ONLY the quoted speech ✅ IMPLEMENTED (split in p43)

**Status**: ✅ IMPLEMENTED (2026-01-16)
- Created `p43_resolve_actors.py`
- Added to pipeline after `p42_coreference`
- 18 tests added in `test_p43_resolve_actors.py`

---

### Issue #2: Legal allegations bucket mixes different claim types [P2]

**Severity**: TAXONOMY IMPURITY

**Current State**:
"Legal allegations" contains:
- Admin outcome ("received a letter… within policy")
- Medical/psych causation ("diagnosed PTSD directly caused by…")
- Attorney opinion ("clearest case…")

These aren't the same epistemic class as "unlawful search" or "excessive force."

**Impact**: Output pretends to be legal-structured but lumps different
epistemic classes together.

**Solution**: Split into sub-categories:
- `legal_claim`: "This was excessive force"
- `admin_outcome`: "IA found conduct within policy"
- `medical_causation`: "Dr. diagnosed PTSD caused by..."
- `attorney_opinion`: "Attorney says this is the clearest case..."

**Exit Criteria**:
- [ ] Each sub-type has distinct label in output
- [ ] No mixing of admin outcomes with legal allegations

---

### Issue #3: Medical content misclassified [P1]

**Severity**: PROVENANCE ERROR

**Current State**:
"She documented bruises..." is classified as self-reported injury, not
medical provider finding.

**Impact**: Provenance gets muddy: "who said this?" becomes unclear.

**Solution**: Fix `p27_epistemic_tag.py`:
- Detect "she documented", "he noted", "the doctor found"
- Classify as `medical_provider_finding` with `evidence_source="document"`
- NOT as `self_report`

**Exit Criteria**:
- [ ] Medical provider observations have correct epistemic_type
- [ ] Evidence source reflects the actual source (document, not self)

---

### Issue #4: Speaker resolution contaminated by characterization [P1]

**Severity**: QUOTE IMPURITY

**Current State**:
Quotes include trailing interpretation:
> `and he just said: "Not today" which was clearly a threat ...`

The quote is preservable; "clearly a threat" must be separated.

**Impact**: Quote section is contaminated by characterization.

**Solution**: Enhance quote extraction:
- Split: `"said X"` from `"which was clearly Y"`
- Quote → preserved
- "which was clearly Y" → new INFERENCE statement

**Exit Criteria**:
- [ ] Quotes contain ONLY the quoted speech
- [ ] Trailing characterizations become separate INFERENCE statements

---

### Issue #5: Raw neutralized narrative still contains bias [P0]

**Severity**: TRUST-BREAKING

**Current State**:
Even with "appeared/described/suggests," narrative asserts:
- "ready to shoot me"
- "threat and witness intimidation"
- "obstruction of justice"
- "racial profiling"
- "systematic racism"

These may be reporter assertions, but the narrative reads like system endorsement.

**Impact**: "Neutralized narrative" is not neutral; it's "softened but argumentative."

**Solution**: Enforce attribution in `p70_render.py` + `p72_safety_scrub.py`:

**Never**:
```
"Officer was ready to shoot"  ← system endorsing
```

**Always**:
```
"reporter perceived the officer as ready to shoot"  ← attributed
```

**Exit Criteria**:
- [x] Every allegation/inference uses "reporter asserts/perceives/characterizes" ✅ IMPLEMENTED
- [x] No unattributed legal/intent claims in rendered output ✅ IMPLEMENTED

**Status**: ✅ IMPLEMENTED (2026-01-16)
- Massively expanded `p72_safety_scrub.py` patterns
- Added LEGAL_SCRUB_PATTERNS (15+ patterns)
- Added INTENT_SCRUB_PATTERNS (10+ patterns)
- Added CONSPIRACY_SCRUB_PATTERNS (7 patterns)
- Added INVECTIVE_SCRUB_PATTERNS (11 patterns)
- 20 tests added in `test_p72_safety_scrub.py`

---

## Priority Order

```
P0: TRUST-BREAKING (must fix before "neutral" label is honest)
    ✅ #1 OBSERVED EVENTS actor-resolution — DONE
    ✅ #5 Narrative attribution enforcement — DONE

P1: PROVENANCE ACCURACY (credibility of structure)
    #3 Medical provider finding vs self-report
    #4 Quote + interpretation separation

P2: TAXONOMY CLARITY (bucket purity)
    #2 Split "legal allegations" into sublabels
```

---

## Implementation Plan

### Phase 1: Actor Resolution ✅ COMPLETE

1. ✅ Created `p43_resolve_actors.py`
2. ✅ Integrated with existing coreference pass (`p42_coreference.py`)
3. ✅ Added fragment detection and splitting
4. ✅ Added quote/interpretation separation
5. ✅ Updated pipeline registration

### Phase 2: Attribution Enforcement ✅ COMPLETE

1. ✅ Hardened `p72_safety_scrub.py` patterns (45+ patterns)
2. ✅ Added invariant tests (20 tests)

### Phase 3: Provenance Fixes

1. Fix medical finding classification in `p27_epistemic_tag.py`
2. Enhance quote extraction to strip trailing characterization

### Phase 4: Taxonomy Refinement

1. Add sub-categories to legal bucket
2. Update structured output schema

---

## Success Metrics

| Metric | Before | Target |
|--------|--------|--------|
| Neutral report trust score | 4/10 | 7/10 |
| Actor-resolved % in OBSERVED | ~30% | >90% |
| Unattributed allegations in render | Many | 0 |
| Medical mis-classification | Present | 0 |
| Quote contamination | Present | 0 |

---

## Appendix: Test Cases ✅ IMPLEMENTED

### Issue #1: Actor Resolution — `tests/passes/test_p43_resolve_actors.py` (18 tests)
- `TestFragmentDetection` (7 tests)
- `TestQuoteInterpretationSplit` (4 tests)
- `TestBuildPronounMap` (2 tests)
- `TestResolveActorsPass` (4 tests)
- `TestActorResolution` (1 test)

### Issue #5: Attribution Enforcement — `tests/passes/test_p72_safety_scrub.py` (20 tests)
- `TestLegalAttributionEnforcement` (6 tests)
- `TestIntentAttributionEnforcement` (4 tests)
- `TestConspiracyRemoval` (3 tests)
- `TestInvectiveRemoval` (3 tests)
- `TestNoFalsePositives` (2 tests)
- `TestDiagnosticTracking` (2 tests)

---

*Document created: 2026-01-16*
*Status: ACTIVE*
