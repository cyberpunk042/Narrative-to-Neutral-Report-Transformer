# NNRT — V5 Blocking Issues (Road to Alpha)

## Status: ✅ COMPLETE
## Created: 2026-01-16
## Completed: 2026-01-16
## Target: Pre-Alpha → Alpha

---

## Executive Summary

NNRT v0.3 has strong structural foundations but fails key invariants required for
a "neutral" label to be honest. This document tracked the 5 blocking issues that
must be resolved before Alpha.

**ALL 5 ISSUES RESOLVED** ✅

**Updated Rating:**
- As debugging/engine trace: **8/10** → **9/10**
- As neutral report someone could rely on: **4/10** → **7/10**

### Stress Test Validation ✅

The extreme stress test narrative (~7,000 characters) was successfully processed:
- **37 safety scrubs applied**
- ✅ All legal allegations properly attributed
- ✅ All intent/threat perceptions flagged
- ✅ All conspiracy language removed or flagged
- ✅ All invective neutralized
- ✅ Patterns enhanced to handle edge cases (plural forms, names, etc.)

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
- `legal_claim_direct`: "This was excessive force"
- `legal_claim_admin`: "IA found conduct within policy"
- `legal_claim_causation`: "PTSD directly caused by..."
- `legal_claim_attorney`: "Attorney says this is the clearest case..."

**Exit Criteria**:
- [x] Each sub-type has distinct label in output ✅ IMPLEMENTED
- [x] No mixing of admin outcomes with legal allegations ✅ IMPLEMENTED

**Status**: ✅ IMPLEMENTED (2026-01-16)
- Split `LEGAL_CLAIM_PATTERNS` into 4 sub-categories in `p27_epistemic_tag.py`
- New patterns: `LEGAL_CLAIM_DIRECT_PATTERNS`, `LEGAL_CLAIM_ADMIN_PATTERNS`, 
  `LEGAL_CLAIM_CAUSATION_PATTERNS`, `LEGAL_CLAIM_ATTORNEY_PATTERNS`
- Updated `_classify_epistemic()` to return sub-types
- 21 tests added in `test_p27_legal_taxonomy.py`

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
- [x] Medical provider observations have correct epistemic_type ✅ IMPLEMENTED
- [x] Evidence source reflects the actual source (document, not self) ✅ IMPLEMENTED

**Status**: ✅ IMPLEMENTED (2026-01-16)
- Massively expanded `MEDICAL_FINDING_PATTERNS` (20+ patterns)
- Moved medical finding check BEFORE self-report checks in `_classify_epistemic()`
- Added flexible patterns for "She/He documented/noted/found [words] injuries/bruises"
- 12 tests added in `test_p27_medical_finding.py`

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
- [x] Quotes contain ONLY the quoted speech ✅ IMPLEMENTED
- [x] Trailing characterizations become separate INFERENCE statements ✅ IMPLEMENTED

**Status**: ✅ IMPLEMENTED (2026-01-16)
- Added `QUOTE_TRAILING_PATTERN` in `p43_resolve_actors.py`
- Pattern matches: `'"...' which was clearly`, `', which`, `obviously`, etc.
- Quote part preserved, interpretation split into new statement
- New statement has `epistemic_type="inference"` and flag `"split_from_quote"`

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
    ✅ #3 Medical provider finding vs self-report — DONE
    ✅ #4 Quote + interpretation separation — DONE

P2: TAXONOMY CLARITY (bucket purity)
    ✅ #2 Split "legal allegations" into sublabels — DONE
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

### Phase 3: Provenance Fixes ✅ COMPLETE

1. ✅ Fixed medical finding classification in `p27_epistemic_tag.py`
2. ✅ Enhanced quote extraction to strip trailing characterization

### Phase 4: Taxonomy Refinement ✅ COMPLETE

1. ✅ Split legal bucket into 4 sub-categories
2. ✅ Added 21 tests for legal taxonomy

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

### Issue #2: Legal Taxonomy — `tests/passes/test_p27_legal_taxonomy.py` (21 tests)
- `TestLegalClaimDirect` (5 tests)
- `TestLegalClaimAdmin` (5 tests)
- `TestLegalClaimCausation` (4 tests)
- `TestLegalClaimAttorney` (4 tests)
- `TestLegalTaxonomyDistinction` (3 tests)

### Issue #3: Medical Finding — `tests/passes/test_p27_medical_finding.py` (12 tests)
- `TestMedicalProviderFinding` (7 tests)
- `TestSelfReportInjuryNotOverridden` (3 tests)
- `TestMedicalVsSelfDistinction` (2 tests)

### Issue #5: Attribution Enforcement — `tests/passes/test_p72_safety_scrub.py` (20 tests)
- `TestLegalAttributionEnforcement` (6 tests)
- `TestIntentAttributionEnforcement` (4 tests)
- `TestConspiracyRemoval` (3 tests)
- `TestInvectiveRemoval` (3 tests)
- `TestNoFalsePositives` (2 tests)
- `TestDiagnosticTracking` (2 tests)

---

*Document created: 2026-01-16*
*Last updated: 2026-01-16*
*Status: ✅ ALL V5 BLOCKING ISSUES COMPLETE*
*Total tests added: 71 tests across 4 test files*

