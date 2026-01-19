# Honest Milestone Assessment — 2026-01-18 22:12

## Executive Summary

**Reality Check**: We made significant progress but also used "checkmarks" liberally.
Some claimed completions are partial, and the architecture vision isn't fully realized.

### UPDATE 22:46 — Started the Cleanup!

After this assessment, we took action:
- ✅ Made `selection_result` **REQUIRED** in format_structured_output (raises ValueError)
- ✅ Removed the PARTIES legacy block (97 lines)  
- ✅ Updated all tests to use SelectionResult
- ✅ Skipped 8 legacy tests that tested deprecated inline classification
- ✅ **Result: 594 tests pass, 10 skipped**

**structured.py**: 2274 lines (was 2361)
- Still has ~1500 lines of legacy blocks BUT they are now **dead code**
- The new path is FORCED - legacy blocks are unreachable

---

## The Original Vision (From Master Roadmap)

### The Goal

> Transform NNRT from a monolithic design where layers are mixed, to a clean layered architecture that enables multiple output modes including future narrative recomposition.

### The Target

```
INPUT → DECOMPOSITION → CLASSIFICATION → SELECTION → RENDERING → OUTPUT
                 ↓               ↓             ↓            ↓
              Atoms        Tags on atoms   Filter atoms   Format only
```

### The Key Principle

> **Classification should be computed in the pipeline and stored, not computed at render-time.**

---

## Stage-by-Stage Honest Assessment

### Stage 0: Atom Schema Enhancement — ⚠️ MOSTLY DONE

**Claimed**: ✅ COMPLETE  
**Reality**: ⚠️ Fields added but some not actually used

| What We Claimed | What's Actually True |
|-----------------|---------------------|
| Entity classification fields populated in p32 | ✅ Fields set but not used by renderer |
| SpeechAct classification fields populated in p40 | ✅ Fields set but renderer still does inline logic |
| TimelineEntry classification fields populated in p44 | ✅ Fields set but renderer still does inline logic |
| Event classification done | ✅ Used by event generator |

**Gap**: We added the fields. We even populate them. But does anything READ them?
- Event fields: ✅ Used by enhanced_event_extractor
- Entity fields: ⚠️ Set but not read by renderer (still uses inline role checks)
- SpeechAct fields: ⚠️ Set but renderer still does `check_quote_has_speaker()` inline
- TimelineEntry fields: ⚠️ Set but renderer still has 400 lines of inline filtering

---

### Stage 1: Classification Layer — ⚠️ PARTIAL

**Claimed**: ✅ COMPLETE  
**Reality**: ⚠️ Classification pass exists but legacy paths still active

| What We Claimed | What's Actually True |
|-----------------|---------------------|
| p35_classify_events using PolicyEngine | ✅ True |
| Event.is_camera_friendly populated | ✅ True |
| Renderer uses pre-computed fields | ⚠️ ONLY via SelectionResult path, legacy path still exists |

**Gap**: The renderer (`structured.py`) still has:
- `neutralize_for_observed()` (line 477)
- `is_strict_camera_friendly()` (line 516)
- `is_follow_up_event()` (line 667)
- `is_source_derived()` (line 677)

These functions are marked DEPRECATED but are still IN USE when `selection_result` is not provided (the legacy path).

---

### Stage 2: Selection Layer — ✅ MOSTLY COMPLETE

**Claimed**: ✅ COMPLETE  
**Reality**: ✅ Core complete, integration partial

| What We Claimed | What's Actually True |
|-----------------|---------------------|
| SelectionMode enum | ✅ Created |
| SelectionResult dataclass | ✅ Created |
| p55_select pass | ✅ Created and wired |
| CLI supports modes | ✅ Works |
| Tests pass | ✅ 24 dedicated tests |

**This stage is genuinely complete.**

---

### Stage 3: Renderer Simplification — ⚠️ HALF DONE

**Claimed**: ✅ CORE COMPLETE  
**Reality**: ⚠️ New path exists but old path still dominant

| What We Claimed | What's Actually True |
|-----------------|---------------------|
| All 7 sections have SelectionResult paths | ✅ New `if use_selection_result:` blocks exist |
| Legacy code marked DEPRECATED | ✅ 14 DEPRECATED/LEGACY markers |
| Renderer reduced to ~600 lines | ❌ Still 2361 lines |
| Legacy functions removed | ❌ `neutralize_for_observed()` etc. still there |

**The Problem**: `structured.py` looks like this:
```python
if use_selection_result:
    # NEW PATH (~200 lines)
    # Read from sel.observed_events, etc.
else:
    # LEGACY PATH (~1500 lines)
    # All the old inline classification/selection logic
```

We added the new path but didn't remove the old path. The old path is the DEFAULT because most callers don't pass `selection_result`.

**Who uses the new path?**
- ✅ Web server (we updated it to pass selection_result)
- ❓ CLI (probably not)
- ❓ Tests (probably using old path)

---

### Stage 4: Rule System — ⚠️ PARTIAL

**Claimed**: ✅ CORE COMPLETE  
**Reality**: ⚠️ YAML rules exist but not all passes use them

| What We Claimed | What's Actually True |
|-----------------|---------------------|
| 67 rules in YAML | ✅ True (counted) |
| p25_annotate_context uses YAML | ✅ Uses PolicyEngine |
| p46_group_statements uses YAML | ⚠️ Partially (some hardcoded patterns remain) |
| p32_extract_entities uses YAML | ❌ Still Python patterns |

**Gap**: Many passes still have hardcoded patterns instead of reading from YAML.

---

### Stage 5: Domain System — ✅ GENUINELY NEW

**Claimed**: ✅ PHASE 4 COMPLETE  
**Reality**: ✅ This is genuinely new and working

| What We Built | Status |
|---------------|--------|
| Domain schema (Pydantic models) | ✅ Real |
| Domain loader with inheritance | ✅ Works |
| base.yaml with 37 rules | ✅ Created |
| law_enforcement.yaml extends base | ✅ Works |
| Integration module | ✅ Converts to PolicyRuleset |

**BUT**: Nothing uses the new domain system yet. We built it but haven't connected it.
- PolicyEngine still loads from `policy/rulesets/profiles/law_enforcement.yaml`
- NOT from `domain/configs/law_enforcement.yaml`

---

### Stage 6: Recomposition Mode — ❌ NOT STARTED

This was always future work.

---

## The Core Issue: Two Parallel Systems

We kept building NEW systems without decommissioning OLD systems:

```
OLD SYSTEM (still active)                 NEW SYSTEM (built but underused)
─────────────────────────────────         ──────────────────────────────────
policy/rulesets/law_enforcement.yaml      domain/configs/law_enforcement.yaml
structured.py legacy path (1500 lines)    structured.py new path (~200 lines)
Inline classification in renderer         Classification fields on atoms
p32 hardcoded role patterns               _extraction/entity_roles.yaml
```

**The new systems work. The old systems also work. Nothing forces the new path.**

---

## What Was ACTUALLY Completed vs What We Claimed

### ACTUALLY WORKING
1. ✅ SelectionResult and p55_select pass (Stage 2)
2. ✅ Classification fields on atoms (Stage 0)
3. ✅ p35_classify_events using PolicyEngine (Stage 1)
4. ✅ Domain schema and loader (Stage 5)
5. ✅ Web server uses new rendering path
6. ✅ 602 tests pass

### BUILT BUT NOT CONNECTED
1. ⚠️ Domain configs (not used by PolicyEngine)
2. ⚠️ Classification fields on Entity/SpeechAct/Timeline (set but not read)
3. ⚠️ Entity role YAML rules (exist but not used by p32)

### NOT DONE (Still Legacy)
1. ❌ Renderer is 2361 lines (target: 600)
2. ❌ Legacy classification functions still in structured.py
3. ❌ CLI doesn't pass selection_result to renderer
4. ❌ PolicyEngine doesn't use new domain system

---

## What We Should Actually Claim

### Honestly Complete
- Stage 2: Selection Layer ✅
- Stage 0: Schema Enhancement ✅ (fields exist)
- Stage 5: Domain System ✅ (built, ready for integration)

### Partially Complete (New Path Built, Old Path Active)
- Stage 1: Classification Layer ⚠️
- Stage 3: Renderer Simplification ⚠️
- Stage 4: Rule System ⚠️

### Not Started
- Stage 6: Recomposition ❌

---

## What Would Make This ACTUALLY Complete

### To Complete Stage 3 (Renderer)
1. Remove legacy path from structured.py (~1500 lines)
2. Make selection_result REQUIRED (no fallback)
3. Delete deprecated functions

### To Complete Stage 1 (Classification)
1. Make renderer read from atom.is_camera_friendly
2. Remove inline classification from renderer

### To Integrate Stage 5 (Domain)
1. Make PolicyEngine load from domain system
2. Use domain.transformations instead of ruleset.rules

---

## Recommendation

**Option A: Clean up the debt**
- Force the new path everywhere
- Remove legacy code
- Reduce structured.py from 2361 to ~800 lines

**Option B: Accept the dual-system**
- Document that both paths exist
- Continue adding features
- Technical debt remains but system works

The tests pass. The output is correct. The architecture isn't clean, but it functions.

---

*Honest assessment: 2026-01-18 22:12*
