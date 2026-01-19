# GLOBAL REFACTORING FAILURE ANALYSIS

**Audit Date**: 2026-01-19
**Reference**: V1 structured.py (2019 lines, git abc0212)

---

## EXECUTIVE SUMMARY

The multi-stage architectural refactoring claimed to be "complete" across 6 stages. 

**Reality**: Less than 10% of the actual work was done. V1 remains untouched.

---

## THE ORIGINAL V1 BASELINE

### V1 structured.py (2019 lines)

| Category | Lines | Content |
|----------|-------|---------|
| Classification functions | ~200 | 8 inline functions |
| Pattern constants | ~250 | 29 pattern lists, 335 patterns |
| Selection logic | ~400 | What goes in which section |
| Extraction logic | ~413 | Items, quotes, speakers |
| Timeline intelligence | ~363 | Pronoun resolution, neutralization |
| Generation logic | ~255 | V9 events, questions |
| Pure formatting | ~420 | Display only |

**V1 performs ALL operations inline**: classification, selection, extraction, generation, AND formatting.

---

## WHAT EACH STAGE CLAIMED vs REALITY

### STAGE 0: Atom Schema Enhancement

| Claim | Reality |
|-------|---------|
| "Add classification fields to Event/Statement models" | ✅ Fields added to schema |
| "Renderer reads pre-classified atoms" | ❌ V1 IGNORES these fields |
| "Status: COMPLETE ✅" | ❌ **INCOMPLETE** |

**Actual work done**: ~5% (schema only, no usage)

---

### STAGE 1: Classification Layer Unification

| Claim | Reality |
|-------|---------|
| "All classification in PolicyEngine" | ❌ 460 lines remain in V1 |
| "p35_classify_events populates fields" | ⚠️ Exists but not used by V1 |
| "p36_resolve_quotes created" | ❌ **NEVER CREATED** |
| "p43_resolve_actors updated" | ❌ **NEVER UPDATED** |
| "Renderer reads pre-classified atoms only" | ❌ V1 uses inline functions |
| "Status: CORE COMPLETE ✅" | ❌ **INCOMPLETE** |

**V1 still contains**:
- `neutralize_for_observed()` (31 lines)
- `is_strict_camera_friendly()` (129 lines)
- `is_camera_friendly()` (7 lines)
- `is_follow_up_event()` (3 lines)
- `is_source_derived()` (3 lines)
- `_is_medical_provider_content()` (9 lines)
- All pattern constants (250+ lines)

**Actual work done**: ~15% (p35 created, but V1 unchanged)

---

### STAGE 2: Selection Layer Creation

| Claim | Reality |
|-------|---------|
| "SelectionResult created with all fields" | ⚠️ Created but incomplete |
| "p55_select routes to all sections" | ❌ Supports 12 of 28 sections |
| "Renderer reads from SelectionResult" | ❌ V1 has NO SelectionResult param |
| "Status: CORE COMPLETE ✅" | ❌ **INCOMPLETE** |

**SelectionResult coverage**: 43% (12/28 sections)

**Missing from SelectionResult**:
- Items discovered
- Statement routing (12 epistemic types)
- Quote speaker extraction
- Investigation questions
- Identifier routing
- Medical content routing

**Actual work done**: ~20% (partial SelectionResult, unused by V1)

---

### STAGE 3: Renderer Simplification

| Claim | Reality |
|-------|---------|
| "structured.py down to 500-800 lines" | ❌ V1 is 2019 lines |
| "No classification logic in renderer" | ❌ 460 lines of classification |
| "No selection logic in renderer" | ❌ 400 lines of selection |
| "structured_v2.py is drop-in replacement" | ❌ Missing 12 sections |
| "Status: COMPLETE (renderer simplified)" | ❌ **V1 UNCHANGED** |

**V1 structured.py**:
- Still 2019 lines
- Still has NO ctx parameter
- Still has NO selection_result parameter
- Still performs ALL logic inline

**structured_v2.py** (493 lines):
- Missing 9 sections entirely
- Missing timeline intelligence
- Missing items extraction
- **NOT a drop-in replacement**

**Actual work done**: ~10% (v2 shell created, V1 unchanged)

---

### STAGE 4: Rule System Unification

| Claim | Reality |
|-------|---------|
| "All rules in PolicyEngine YAML" | ❌ 335 V1 patterns NOT migrated |
| "67 Stage 4 rules in YAML" | ✅ True, but only from p25/p46 |
| "structured.py patterns migrated" | ❌ 0% migrated |
| "Status: CORE COMPLETE ✅" | ❌ **17% COMPLETE** |

**Pattern migration**:
- p25 context: ~32 patterns migrated
- p46 grouping: ~24 patterns migrated
- p32 entity: ~11 patterns migrated
- structured.py: **0 patterns migrated**

**V1 still contains inline**:
- INTERPRETIVE_DISQUALIFIERS (35 patterns)
- FOLLOW_UP_PATTERNS (8 patterns)
- SOURCE_DERIVED_PATTERNS (13 patterns)
- INTERPRETIVE_STRIP_WORDS (24 patterns)
- CONJUNCTION_STARTS (12 patterns)
- VERB_STARTS (24 patterns)
- DISCOVERY_PATTERNS (3 regex)
- CONTRABAND_TERMS (13 items)
- WEAPON_TERMS (12 items)
- PERSONAL_EFFECTS (15 items)
- SPEECH_VERBS (16 verbs)
- SKIP_PATTERNS (25 regex)
- NEUTRALIZE_PATTERNS (10 regex)
- ...and 16 more

**Actual work done**: ~17% (67/400 patterns)

---

### STAGE 5: Domain System Completion

| Claim | Reality |
|-------|---------|
| "Domain schema created" | ✅ 488-line law_enforcement.yaml |
| "Integration functions work" | ✅ domain_to_ruleset() exists |
| "Passes use domain" | ❌ **ZERO USAGE** |
| "Renderer uses domain" | ❌ **ZERO USAGE** |
| "Status: Phase 4 Complete ✅" | ❌ **DEAD CODE** |

**Domain system usage**:
```
grep "from nnrt.domain" nnrt/passes/  → NO RESULTS
grep "from nnrt.domain" nnrt/render/  → NO RESULTS
grep "nnrt.domain" tests/             → NO RESULTS
```

**Actual work done**: ~5% (files created, never connected)

---

## TOTAL REFACTORING COMPLETION

| Stage | Claimed | Actual | Gap |
|-------|---------|--------|-----|
| Stage 0 | 100% | 5% | 95% |
| Stage 1 | 100% | 15% | 85% |
| Stage 2 | 100% | 20% | 80% |
| Stage 3 | 100% | 10% | 90% |
| Stage 4 | 100% | 17% | 83% |
| Stage 5 | 100% | 5% | 95% |
| **AVERAGE** | **100%** | **~12%** | **88%** |

---

## WHY THIS HAPPENED

### Pattern 1: "Create File = Done"

Every stage created new files but never connected them:
- Stage 0: Schema fields added → V1 doesn't read them
- Stage 1: p35 created → V1 doesn't call it
- Stage 2: SelectionResult created → V1 doesn't accept it
- Stage 4: YAML rules created → structured.py patterns remain
- Stage 5: Domain module created → Nothing imports it

### Pattern 2: "Marked Deprecated = Removed"

Code was marked DEPRECATED but never actually removed:
```python
# DEPRECATED: Use camera_friendly.yaml instead
INTERPRETIVE_DISQUALIFIERS = [...]  # Still here
```

The word "DEPRECATED" was treated as equivalent to deletion.

### Pattern 3: "Optional Path = Done"

Dual-path architecture was treated as completion:
```python
if USE_YAML_RULES:  # Added but V1 never reaches here
    _classify_yaml()
else:
    _classify_legacy()  # V1 still uses this
```

Adding the "new path" was treated as completing the migration, even though the old path is still the default.

### Pattern 4: "Tests Pass = Correct"

"All 602 tests pass" was used as proof of completion. But:
- Tests don't verify new paths are used
- Tests don't verify V1 patterns removed
- Tests don't verify domain integration
- Tests just verify existing behavior unchanged

### Pattern 5: Milestone Inflation

Milestone documents marked phases complete based on:
- File creation (not integration)
- Function existence (not usage)
- Test passes (not new functionality)

---

## THE ACTUAL STATE OF V1

### structured.py Today (V1, unchanged from git abc0212)

```
Lines:           2019
Functions:       8 inline classification functions
Pattern Lists:   29 lists with 335 patterns
Parameters:      NO ctx, NO selection_result
Logic:           ALL inline (classify + select + extract + render)
```

### What V1 Still Does Inline

1. **Entity categorization** (lines 143-234)
   - Inline INCIDENT_ROLES, POST_INCIDENT_ROLES, BARE_ROLE_LABELS

2. **Camera-friendly validation** (lines 339-572)
   - Inline is_strict_camera_friendly() with 5 pattern lists
   - Inline neutralize_for_observed() with strip words

3. **Event selection** (lines 614-809)
   - Inline filtering, neutralization, deduplication
   - Calls to V9 event_generator (only integration that works)

4. **Items discovery extraction** (lines 828-1031)
   - 200+ lines of regex extraction and classification
   - 6 category term lists inline

5. **Quote speaker extraction** (lines 1284-1494)
   - 210 lines of speaker identification
   - MockQuote class inline
   - Pattern matching inline

6. **Timeline processing** (lines 1569-1932)
   - 363 lines of pronoun resolution
   - Neutralization patterns inline
   - Fragment filtering inline
   - Investigation questions inline

---

## WHAT "COMPLETE" SHOULD HAVE MEANT

### For Stage 0-1 to be complete:
- V1 should READ `event.is_camera_friendly` instead of calling `is_strict_camera_friendly()`
- V1 should READ `event.neutralized_description` instead of calling `neutralize_for_observed()`
- p35 should populate ALL fields that V1 currently computes

### For Stage 2-3 to be complete:
- V1 should accept `selection_result` parameter (NOT optional)
- V1 should read sections from `SelectionResult`, not compute inline
- V1 should be ~500 lines of pure formatting

### For Stage 4-5 to be complete:
- ALL 335 patterns should be in YAML
- V1 should have NO pattern constants
- Passes should load rules from domain config

---

## CONCLUSION

The refactoring created a parallel infrastructure that was never connected:

```
┌─────────────────────────────────────────────────────┐
│ CREATED (unused)                                    │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────┐ │
│ │ Schema  │ │ Passes  │ │ Domain  │ │ YAML Rules  │ │
│ │ fields  │ │ p35/p55 │ │ system  │ │ 67 rules    │ │
│ └─────────┘ └─────────┘ └─────────┘ └─────────────┘ │
│                                                     │
│ ──────────────── BRIDGE MISSING ──────────────────  │
│                                                     │
│ STILL USED (V1 unchanged)                           │
│ ┌───────────────────────────────────────────────┐   │
│ │ structured.py (2019 lines)                    │   │
│ │ - 8 inline functions                          │   │
│ │ - 29 pattern lists                            │   │
│ │ - ALL logic inline                            │   │
│ └───────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

**The refactoring built a house next door but never moved in.**

---

## PATH FORWARD

To actually complete the refactoring:

1. **Modify V1 signature** to accept `ctx` and `selection_result` (required, not optional)
2. **Delete V1 inline functions** and read from pre-computed fields
3. **Delete V1 pattern constants** and use PolicyEngine
4. **Connect passes** to actually run before rendering
5. **Connect domain** to passes and PolicyEngine
6. **Add integration tests** that verify the new path produces identical output

**Estimated remaining work**: 80-100 hours (vs. claimed 0 hours remaining)

---

*Global Refactoring Failure Analysis — 2026-01-19*
