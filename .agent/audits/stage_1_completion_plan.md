# STAGE 1 COMPLETION PLAN

**Based on**: Stage 1 Audit (Updated 2026-01-19)
**Objective**: Make renderer read pre-computed classification fields from atoms instead of computing inline.

---

## VERIFIED CURRENT STATE (2026-01-19)

### Classification Layer
| Component | Status | Notes |
|-----------|--------|-------|
| p35_classify_events | ✅ Complete | All 6 V1 rules, tested |
| camera_friendly.yaml | ✅ Complete | All 35 verbs, all patterns |
| neutralization.yaml | ✅ Complete | All words migrated (6 added 2026-01-19) |
| p36_resolve_quotes | ✅ Complete | Created 2026-01-19 |
| p38_extract_items | ✅ Complete | Created 2026-01-19 |
| p44_timeline updates | ✅ Complete | V1 neutralization migrated |

### Renderer Integration (After TASK 1 Complete)
| Metric | Current | Target |
|--------|---------|--------|
| Reads `event.is_camera_friendly` | ✅ | ✅ |
| Reads `event.neutralized_description` | ✅ | ✅ |
| Has inline `is_strict_camera_friendly()` in V2 | ✅ NONE | ❌ |
| Has inline `neutralize_for_observed()` in V2 | ✅ NONE | ❌ |

---

## REMAINING TASKS

### TASK 1: ✅ COMPLETE - p90 Now Uses structured_v2
**Priority**: HIGHEST (enables entire Stage 1 goal)
**Status**: ✅ DONE (2026-01-19)

**Changes made:**
- Updated `p90_render_structured.py` to use `structured_v2.format_structured_output_v2`
- When `ctx.selection_result` is populated (from p55_select):
  - Uses V2 renderer that reads pre-computed fields
  - Reads `event.is_camera_friendly`, `event.neutralized_description`
  - Reads `event.is_follow_up`, `event.is_source_derived`
  - Reads `speech_act.speaker_resolved`, `speech_act.is_quarantined`
  - Reads `entry.resolved_description`, `entry.display_quality`
- Fallback to V1 renderer when no SelectionResult (legacy compatibility)

**No inline classification functions** in the new path.

---

### TASK 2: ✅ COMPLETE - Added Missing 6 Words to neutralization.yaml
**Priority**: Low (minor gap)
**Status**: ✅ DONE (2026-01-19)

**Added words:**
- ✅ `innocently` → neut_adverb_emotional
- ✅ `distressingly` → neut_adverb_emotional
- ✅ `horrifyingly` → neut_adverb_emotional
- ✅ `terrifyingly` → neut_adverb_emotional
- ✅ `distressing` → neut_adjective_extreme
- ✅ `maniacal` → neut_adjective_extreme

---

### TASK 3: ✅ COMPLETE - Created p36_resolve_quotes Pass
**Priority**: Medium (for QUOTES section)
**Status**: ✅ DONE (2026-01-19)

**Created file**: `nnrt/passes/p36_resolve_quotes.py`

**Migrated V1 logic (lines 1315-1410):**
- ✅ SPEECH_VERBS (17 verbs)
- ✅ NOT_SPEAKERS (17 exclusion words)
- ✅ NAME_PATTERNS (11 regex patterns)
- ✅ FIRST_PERSON_PATTERNS (8 patterns)
- ✅ Entity context matching (new enhancement)

**Sets SpeechAct fields:**
- `speaker_resolved`, `speaker_label`, `speaker_resolution_method`
- `speaker_validation`, `speaker_resolution_confidence`
- `is_quarantined`, `quarantine_reason`

---

### TASK 4: ✅ COMPLETE - Created p38_extract_items Pass
**Priority**: Medium (for ITEMS DISCOVERED section)
**Status**: ✅ DONE (2026-01-19)

**Created file**: `nnrt/passes/p38_extract_items.py`

**Migrated V1 logic (lines 828-1031):**
- ✅ DISCOVERY_PATTERNS (3 regexes)
- ✅ CONTRABAND_TERMS (16 terms)
- ✅ VAGUE_SUBSTANCE_TERMS (9 terms)
- ✅ WEAPON_TERMS (12 terms)
- ✅ PERSONAL_EFFECTS (14 terms)
- ✅ WORK_ITEMS (9 terms)
- ✅ ItemDiscovered dataclass with categories

---

### TASK 5: ✅ COMPLETE - Updated p44_timeline with V1 Neutralization
**Priority**: Medium (for TIMELINE section)
**Status**: ✅ DONE (2026-01-19)

**Updated file**: `nnrt/passes/p44_timeline.py`

**Migrated V1 logic (lines 1715-1778):**
- ✅ SKIP_PATTERNS (28 patterns for subjective language)
- ✅ NEUTRALIZE_PATTERNS (10 replacement pairs)
- ✅ FIRST_PERSON_REPLACEMENTS (I/me/my → Reporter)
- ✅ _neutralize_timeline_text() helper function
- ✅ Updated TimelineEntry creation to use neutralization

---

### TASK 6: ✅ COMPLETE - Added Medical Content Routing
**Priority**: Low (for correct section routing)
**Status**: ✅ DONE (2026-01-19)

**Updated file**: `nnrt/passes/p27_classify_atomic.py`

**Migrated V1 logic (lines 1125-1134):**
- ✅ MEDICAL_PROVIDERS (10 terms)
- ✅ MEDICAL_VERBS (10 verbs)
- ✅ _is_medical_provider_content() function
- ✅ Routes medical content with "medical_provider_content" flag

---

## EXECUTION ORDER — ALL COMPLETE ✅

1. ~~**TASK 1** - Update p90 to use structured_v2~~ ✅ DONE
2. ~~**TASK 2** - Add missing neutralization words~~ ✅ DONE
3. ~~**TASK 3** - Create p36_resolve_quotes~~ ✅ DONE
4. ~~**TASK 4** - Create p38_extract_items~~ ✅ DONE
5. ~~**TASK 5** - Update p44_timeline~~ ✅ DONE
6. ~~**TASK 6** - Add medical routing~~ ✅ DONE

---

## SUCCESS CRITERIA — ALL MET ✅

- [x] structured_v2.py reads `event.is_camera_friendly` instead of calling inline function
- [x] structured_v2.py reads `event.neutralized_description` instead of computing
- [x] structured_v2.py reads `speech_act.speaker_resolved` for quotes
- [x] structured_v2.py reads `entry.resolved_description` for timeline
- [x] No inline classification functions in V2 renderer
- [x] All V1 classification logic migrated to passes

**STAGE 1: ✅ COMPLETE**

---

## RISK ASSESSMENT

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Output differs from V1 | High | High | Create comparison tests before changes |
| Missing edge cases in p35 | Medium | Medium | Expand test suite with V1 golden cases |
| Timeline resolution breaks | Medium | High | Keep V1 fallback until verified |

---

*Stage 1 Completion Plan — 2026-01-19*
