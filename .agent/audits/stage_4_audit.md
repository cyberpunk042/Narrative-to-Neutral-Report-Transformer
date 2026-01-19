# STAGE 4 AUDIT: Rule System Unification

**Audit Date**: 2026-01-19
**Reference**: V1 structured.py (structured_py_git_version.py, 2019 lines)
**Milestone**: `.agent/milestones/stage_4_rules.md`

---

## Stage 4 Objective (from milestone document)

> Unify all rule types under the Policy Engine. Consolidate duplicated patterns scattered across Python files into YAML configurations.

---

## PART 1: COMPLETE V1 PATTERN INVENTORY

### All Pattern Constants in V1 structured.py

| Line | Constant Name | Count | Purpose |
|------|---------------|-------|---------|
| 151-167 | `INCIDENT_ROLES` | 6 | Entity role categorization |
| 157-159 | `POST_INCIDENT_ROLES` | 3 | Entity role categorization |
| 163-167 | `BARE_ROLE_LABELS` | 14 | Entity filtering |
| 339-355 | `INTERPRETIVE_DISQUALIFIERS` | 35 | Camera-friendly disqualifiers |
| 359-363 | `FOLLOW_UP_PATTERNS` | 8 | Follow-up event detection |
| 367-373 | `SOURCE_DERIVED_PATTERNS` | 13 | Source-derived detection |
| 376-389 | `INTERPRETIVE_STRIP_WORDS` | 24 | Neutralization words |
| 445-448 | `CONJUNCTION_STARTS` | 12 | Camera-friendly validation |
| 461-469 | `VERB_STARTS` | 24 | Camera-friendly validation |
| 504-511 | `START_ACTOR_PATTERNS` | 3 (regex) | Camera-friendly validation |
| 523-527 | `PRONOUN_STARTS` | 15 | Camera-friendly validation |
| 543-547 | `INTERPRETIVE_BLOCKERS` | 15 | Camera-friendly validation |
| 628-633 | `OBSERVABLE_EPISTEMIC_TYPES` | 4 | Event selection |
| 835-839 | `DISCOVERY_PATTERNS` | 3 (regex) | Items extraction |
| 843-848 | `CONTRABAND_TERMS` | 13 | Items classification |
| 851-854 | `VAGUE_SUBSTANCE_TERMS` | 7 | Items classification |
| 856-859 | `WEAPON_TERMS` | 12 | Items classification |
| 861-865 | `PERSONAL_EFFECTS` | 15 | Items classification |
| 867-870 | `WORK_ITEMS` | 8 | Items classification |
| 1316-1321 | `SPEECH_VERBS` | 16 | Quote speaker extraction |
| 1339-1343 | `NOT_SPEAKERS` | 15 | Quote speaker validation |
| 1346-1357 | `name_patterns` | 10 (regex) | Quote speaker extraction |
| 1382-1391 | `first_person_patterns` | 8 | Quote speaker extraction |
| 1642-1646 | `fragment_starters` | 14 | Timeline filtering |
| 1719-1733 | `SKIP_PATTERNS` | 25 (regex) | Timeline neutralization |
| 1745-1756 | `NEUTRALIZE_PATTERNS` | 10 (regex) | Timeline neutralization |
| 1824-1830 | `bad_endings` | 11 | Timeline truncation |
| 1829-1830 | `incomplete_markers` | 10 | Timeline truncation |

**TOTAL: 29 pattern lists with ~335 individual patterns**

### All Functions with Inline Logic in V1

| Line | Function | Purpose |
|------|----------|---------|
| 60-100 | `_deduplicate_statements()` | Statement deduplication |
| 391-422 | `neutralize_for_observed()` | Text neutralization |
| 424-553 | `is_strict_camera_friendly()` | Camera-friendly validation (129 lines) |
| 555-562 | `is_camera_friendly()` | Camera-friendly wrapper |
| 564-567 | `is_follow_up_event()` | Follow-up detection |
| 569-572 | `is_source_derived()` | Source-derived detection |
| 591-598 | `clean_statement()` | Statement cleanup |
| 1125-1134 | `_is_medical_provider_content()` | Medical content routing |

**TOTAL: 8 functions with ~200+ lines of logic**

---

## PART 2: WHAT WAS MIGRATED TO YAML (Stage 4 Claims)

### YAML Files Created

| File | Rules | Source |
|------|-------|--------|
| `_context/force_context.yaml` | 8 | p25_annotate_context.py |
| `_context/injury_context.yaml` | 9 | p25_annotate_context.py |
| `_context/timeline_context.yaml` | 9 | p25_annotate_context.py |
| `_context/charge_context.yaml` | 6 | p25_annotate_context.py |
| `_extraction/entity_roles.yaml` | 11 | p32_extract_entities.py |
| `_grouping/statement_groups.yaml` | 24 | p46_group_statements.py |
| **TOTAL** | **67** | |

### Already Existed (Pre-Stage 4)

| File | Rules | Source |
|------|-------|--------|
| `_classification/camera_friendly.yaml` | ? | structured.py (partial) |
| `_classification/neutralization.yaml` | ? | structured.py (partial) |
| `_categories/inflammatory_language.yaml` | ? | Various |
| `_categories/intent_attribution.yaml` | ? | Various |
| `_categories/legal_conclusions.yaml` | ? | Various |
| `_categories/loaded_verbs.yaml` | ? | Various |
| `_categories/manner_adverbs.yaml` | ? | Various |

---

## PART 3: V1 PATTERNS NOT MIGRATED

### Camera-Friendly Validation (V1 lines 424-553)

| Pattern List | V1 Location | Migrated? | Target YAML |
|--------------|-------------|-----------|-------------|
| `CONJUNCTION_STARTS` | line 445 | ❌ | Should be in camera_friendly.yaml |
| `VERB_STARTS` | line 461 | ❌ | Should be in camera_friendly.yaml |
| `START_ACTOR_PATTERNS` | line 504 | ❌ | Should be in camera_friendly.yaml |
| `PRONOUN_STARTS` | line 523 | ❌ | Should be in camera_friendly.yaml |
| `INTERPRETIVE_BLOCKERS` | line 543 | ❌ | Should be in camera_friendly.yaml |
| **is_strict_camera_friendly()** | line 424 | ❌ | Should be in p35_classify_events |

### Entity Categorization (V1 lines 151-167)

| Pattern List | V1 Location | Migrated? | Target YAML |
|--------------|-------------|-----------|-------------|
| `INCIDENT_ROLES` | line 151 | ❌ | Should be in entity_roles.yaml |
| `POST_INCIDENT_ROLES` | line 157 | ❌ | Should be in entity_roles.yaml |
| `BARE_ROLE_LABELS` | line 163 | ❌ | Should be in entity_roles.yaml |

### Items Discovery (V1 lines 828-960)

| Pattern List | V1 Location | Migrated? | Target YAML |
|--------------|-------------|-----------|-------------|
| `DISCOVERY_PATTERNS` | line 835 | ❌ | Should be in _extraction/items.yaml |
| `CONTRABAND_TERMS` | line 843 | ❌ | Should be in _extraction/items.yaml |
| `VAGUE_SUBSTANCE_TERMS` | line 851 | ❌ | Should be in _extraction/items.yaml |
| `WEAPON_TERMS` | line 856 | ❌ | Should be in _extraction/items.yaml |
| `PERSONAL_EFFECTS` | line 861 | ❌ | Should be in _extraction/items.yaml |
| `WORK_ITEMS` | line 867 | ❌ | Should be in _extraction/items.yaml |

### Quote Speaker Extraction (V1 lines 1284-1494)

| Pattern List | V1 Location | Migrated? | Target YAML |
|--------------|-------------|-----------|-------------|
| `SPEECH_VERBS` | line 1316 | ❌ | Should be in _extraction/quotes.yaml |
| `NOT_SPEAKERS` | line 1339 | ❌ | Should be in _extraction/quotes.yaml |
| `name_patterns` | line 1346 | ❌ | Should be in _extraction/quotes.yaml |
| `first_person_patterns` | line 1382 | ❌ | Should be in _extraction/quotes.yaml |

### Timeline Processing (V1 lines 1569-1932)

| Pattern List | V1 Location | Migrated? | Target YAML |
|--------------|-------------|-----------|-------------|
| `fragment_starters` | line 1642 | ❌ | Should be in _classification/timeline.yaml |
| `SKIP_PATTERNS` | line 1719 | ❌ | Should be in _classification/timeline.yaml |
| `NEUTRALIZE_PATTERNS` | line 1745 | ❌ | Should be in _classification/neutralization.yaml |
| `bad_endings` | line 1824 | ❌ | Should be in _classification/timeline.yaml |
| `incomplete_markers` | line 1829 | ❌ | Should be in _classification/timeline.yaml |

### Event Classification (V1 lines 339-389)

| Pattern List | V1 Location | Migrated? | Target YAML |
|--------------|-------------|-----------|-------------|
| `INTERPRETIVE_DISQUALIFIERS` | line 339 | ⚠️ PARTIAL | camera_friendly.yaml (check coverage) |
| `FOLLOW_UP_PATTERNS` | line 359 | ❌ | Should be in camera_friendly.yaml |
| `SOURCE_DERIVED_PATTERNS` | line 367 | ❌ | Should be in camera_friendly.yaml |
| `INTERPRETIVE_STRIP_WORDS` | line 376 | ⚠️ PARTIAL | neutralization.yaml (check coverage) |

---

## PART 4: MIGRATION COVERAGE ANALYSIS

### Pattern Migration Summary

| Category | V1 Patterns | Migrated | Not Migrated | Coverage |
|----------|-------------|----------|--------------|----------|
| Context Detection (p25) | ~40 | ~32 (in YAML) | ~8 | 80% |
| Statement Grouping (p46) | ~60 | ~24 (in YAML) | ~36 | 40% |
| Entity Roles (p32) | ~30 | ~11 (in YAML) | ~19 | 37% |
| Camera-Friendly (structured.py) | ~100 | ~0 | ~100 | **0%** |
| Items Discovery (structured.py) | ~50 | 0 | ~50 | **0%** |
| Quote Extraction (structured.py) | ~50 | 0 | ~50 | **0%** |
| Timeline Processing (structured.py) | ~70 | 0 | ~70 | **0%** |
| **TOTAL** | **~400** | **~67** | **~333** | **17%** |

---

## PART 5: FUNCTIONS NOT MIGRATED

Stage 4 was supposed to migrate patterns to YAML and have passes use PolicyEngine. However, V1's inline functions were NEVER extracted to passes:

| Function | V1 Lines | Should Move To | Status |
|----------|----------|----------------|--------|
| `neutralize_for_observed()` | 391-422 | p35 or helper module | ❌ NOT DONE |
| `is_strict_camera_friendly()` | 424-553 | p35_classify_events | ❌ NOT DONE |
| `is_camera_friendly()` | 555-562 | p35 (wrapper) | ❌ NOT DONE |
| `is_follow_up_event()` | 564-567 | p35_classify_events | ❌ NOT DONE |
| `is_source_derived()` | 569-572 | p35_classify_events | ❌ NOT DONE |
| `_is_medical_provider_content()` | 1125-1134 | p37 or p35 | ❌ NOT DONE |
| Quote speaker extraction | 1284-1408 | p36_resolve_quotes | ❌ PASS NEVER CREATED |
| Timeline pronoun resolution | 1650-1697 | p43_resolve_actors | ❌ NOT DONE |
| Timeline neutralization | 1715-1759 | p43 or p55 | ❌ NOT DONE |
| Items extraction | 903-957 | New extraction pass | ❌ NOT DONE |

---

## PART 6: WHAT STAGE 4 ACTUALLY DID

### ✅ Completed

1. Extended PolicyEngine with CONTEXT, GROUP, EXTRACT actions
2. Created 67 YAML rules for context/grouping/extraction
3. Updated p25_annotate_context to use PolicyEngine
4. Updated p46_group_statements to use PolicyEngine  
5. Marked Python patterns as DEPRECATED (but kept as fallback)

### ❌ NOT Done

1. **structured.py patterns NOT migrated** (335 patterns remain inline)
2. **structured.py functions NOT extracted** (8 functions, ~200 lines)
3. **Items extraction patterns NOT migrated** (6 lists, ~50 patterns)
4. **Quote extraction patterns NOT migrated** (4 lists, ~50 patterns)
5. **Timeline patterns NOT migrated** (5 lists, ~70 patterns)
6. **Camera-friendly validation NOT migrated** (5 lists, ~70 patterns)
7. **Entity role patterns NOT fully migrated** (3 lists, ~23 patterns)

---

## STAGE 4 VERDICT

### Status: ❌ **INCOMPLETE**

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| V1 patterns identified | ~400 | ~400 | ✅ |
| Patterns migrated to YAML | ~400 | ~67 | ❌ 17% |
| structured.py patterns migrated | ALL | 0 | ❌ 0% |
| structured.py functions extracted | ALL | 0 | ❌ 0% |
| Total YAML rule coverage | 100% | 17% | ❌ |

### Critical Finding

**Stage 4 only addressed patterns in p25 and p46.** It completely ignored:
- All patterns in structured.py (335 patterns)
- All inline functions in structured.py (8 functions)
- Items discovery logic (203 lines)
- Quote speaker extraction logic (210 lines)
- Timeline processing logic (363 lines)

The milestone document claimed Stage 4 would unify "all rule types" but only addresses ~17% of the actual patterns in V1.

---

## REMEDIATION REQUIRED

To complete Stage 4 properly:

1. **Create `_extraction/items.yaml`** - Migrate 6 item classification lists
2. **Create `_extraction/quotes.yaml`** - Migrate quote speaker patterns
3. **Create `_classification/timeline.yaml`** - Migrate timeline filtering patterns
4. **Extend `_classification/camera_friendly.yaml`** - Add ALL patterns from is_strict_camera_friendly()
5. **Extend `_classification/neutralization.yaml`** - Add ALL patterns from INTERPRETIVE_STRIP_WORDS
6. **Extend `_extraction/entity_roles.yaml`** - Add INCIDENT_ROLES, POST_INCIDENT_ROLES, BARE_ROLE_LABELS
7. **Extract functions to passes** - Move all inline functions from structured.py to appropriate passes

---

*Stage 4 Audit — 2026-01-19*
