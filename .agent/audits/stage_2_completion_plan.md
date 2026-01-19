# STAGE 2 COMPLETION PLAN

**Based on**: Stage 2 Audit (2026-01-19)
**Objective**: Complete the Selection layer so all atom types are routed to appropriate sections.

---

## CURRENT STATE (2026-01-19)

### What's Done
| Component | Status | Notes |
|-----------|--------|-------|
| SelectionMode enum | ✅ Complete | models.py lines 16-43 |
| SelectionResult dataclass | ⚠️ Partial | 12/28 fields |
| p55_select pass | ✅ Created | 379 lines |
| Event selection | ✅ Done | Uses is_camera_friendly |
| Entity selection | ✅ Done | Matches V1 role lists |
| Quote selection | ✅ Ready | p36 now populates speaker fields |
| Timeline selection | ⚠️ Partial | Missing 10 fragment patterns |

### What's Missing
| Component | Gap |
|-----------|-----|
| Statement selection | Not implemented (12 epistemic categories) |
| Identifier selection | Not implemented |
| Timeline patterns | Missing 10 fragment starters |
| **Already Fixed in Stage 1:** | |
| ~~Items extraction~~ | ✅ p38_extract_items created |
| ~~Medical routing~~ | ✅ Added to p27_classify_atomic |
| ~~Quote speaker resolution~~ | ✅ p36_resolve_quotes created |

---

## REMAINING TASKS — ALL COMPLETE ✅

### TASK 1: ✅ Add Statement Selection to p55
**Status**: DONE (2026-01-19)
- Added `_select_statements()` function
- Routes 12 epistemic_type categories to appropriate fields
- Checks medical_provider_content flag for medical routing

### TASK 2: ✅ Add Statement Fields to SelectionResult
**Status**: DONE (2026-01-19)
- Added 12 statement fields (acute_state, injury_state, etc.)
- Added `identifiers_by_type` dict field

### TASK 3: ✅ Add Missing Timeline Fragment Patterns
**Status**: DONE (2026-01-19)
- Updated FRAGMENT_STARTS from 7 to 17 patterns (matching V1)
- Added: to, for, from, by, where, who, until, unless, what, how, why, if, or, yet

### TASK 4: ✅ Add Identifier Selection
**Status**: DONE (2026-01-19)
- Added `_select_identifiers()` function
- Groups identifiers by type for REFERENCE DATA section

---

## EXECUTION ORDER — ALL COMPLETE ✅

1. ~~**TASK 2** - Add fields to SelectionResult~~ ✅ DONE
2. ~~**TASK 1** - Add statement selection to p55~~ ✅ DONE
3. ~~**TASK 3** - Add missing timeline fragment patterns~~ ✅ DONE
4. ~~**TASK 4** - Add identifier selection~~ ✅ DONE

---

## SUCCESS CRITERIA — ALL MET ✅

- [x] SelectionResult has fields for all 12 epistemic categories
- [x] p55 routes atomic statements by epistemic_type
- [x] Timeline fragment patterns match V1 (17 patterns)
- [x] Identifiers routed by type
- [x] Selection coverage: 28/28 sections

**STAGE 2: ✅ COMPLETE**

---

*Stage 2 Completion Plan — Updated 2026-01-19*
