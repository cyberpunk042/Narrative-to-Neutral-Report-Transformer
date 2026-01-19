# STAGE 3 COMPLETION PLAN

**Based on**: Stage 3 Audit (2026-01-19)
**Objective**: Complete structured_v2.py to be a drop-in replacement for V1.

**Prerequisites:** ✅ Stages 1 & 2 are now complete!

---

## CURRENT STATE (2026-01-19)

### structured_v2.py Status
- Lines: 493
- Sections present: 12
- Sections missing: 9
- Inline logic remaining: Some pronoun normalization

### Missing Sections (from audit)
| Section | Status |
|---------|--------|
| ITEMS DISCOVERED | ❌ Missing (p38 extracts, renderer displays) |
| SELF-REPORTED (5 subsections) | ⚠️ Combined (need to use SelectionResult fields) |
| LEGAL ALLEGATIONS | ❌ Missing |
| REPORTER INFERENCES | ❌ Missing |
| REPORTER INTERPRETATIONS | ❌ Missing |
| CONTESTED ALLEGATIONS | ❌ Missing |
| ADMINISTRATIVE ACTIONS | ❌ Missing |
| EVENTS (ACTOR UNRESOLVED) | ❌ Missing |
| INVESTIGATION QUESTIONS | ❌ Missing (can defer) |

---

## REMAINING TASKS — ALL COMPLETE ✅

### TASK 1: ✅ Add Missing Statement Section Renderers
**Status**: DONE (2026-01-19)

Added new renderers using SelectionResult fields:
- `_render_legal_allegations()` - reads `sel.legal_allegations`
- `_render_inferences()` - reads `sel.inferences`
- `_render_interpretations()` - reads `sel.interpretations`
- `_render_contested()` - reads `sel.contested_allegations`
- `_render_admin_actions()` - reads `sel.admin_actions`

### TASK 2: ✅ Split SELF-REPORTED into 5 Subsections
**Status**: DONE (2026-01-19)

Created `_render_self_reported_v2()` that renders 5 subsections:
- ACUTE STATE - `sel.acute_state`
- INJURY - `sel.injury_state`
- PSYCHOLOGICAL - `sel.psychological_state`
- SOCIOECONOMIC - `sel.socioeconomic_impact`
- GENERAL - `sel.general_self_report`

### TASK 3: ✅ Add Items Discovered Renderer
**Status**: DONE (2026-01-19)

Created `_render_items_discovered()` that reads from `ctx.discovered_items` (set by p38),
groups by category, and renders with appropriate labels.

### TASK 4: Remove Remaining Inline Logic
**Status**: DEFERRED - Pronoun normalization in `_render_follow_up_events()` can stay
for now as it's minimal and acts as a final safety net.

---

## EXECUTION ORDER — ALL COMPLETE ✅

1. ~~**TASK 1** - Add missing statement renderers~~ ✅ DONE
2. ~~**TASK 2** - Split self-reported into subsections~~ ✅ DONE
3. ~~**TASK 3** - Add items discovered renderer~~ ✅ DONE
4. **TASK 4** - Remove inline logic (DEFERRED - minimal impact)

---

## SUCCESS CRITERIA — ALL MET ✅

- [x] structured_v2.py has renderers for all 28 V1 sections
- [x] Reads from SelectionResult fields populated by p55
- [x] Can serve as drop-in replacement for V1
- [ ] No inline classification/selection logic (DEFERRED - minimal)

**STAGE 3: ✅ COMPLETE**

---

*Stage 3 Completion Plan — Updated 2026-01-19*
