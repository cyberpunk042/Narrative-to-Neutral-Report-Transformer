# STAGE 1 AUDIT: Classification Layer Unification

**Document**: `.agent/milestones/stage_1_classification.md`
**Audit Date**: 2026-01-19

---

## Stage 1 Objective (from document)

> Move ALL classification logic from the renderer and scattered passes into a unified classification layer in the pipeline.

---

## COMPLETE V1 CLASSIFICATION LOGIC INVENTORY

Extracted from `structured_py_git_version.py` (2019 lines):

### PATTERN ARRAYS (8 total)

| # | Name | Lines | Count | Purpose | Migrated? |
|---|------|-------|-------|---------|-----------|
| 1 | `INTERPRETIVE_DISQUALIFIERS` | 339-355 | 45 words | Disqualify from camera-friendly | ⚠️ Partial in camera_friendly.yaml |
| 2 | `FOLLOW_UP_PATTERNS` | 359-363 | 8 patterns | Detect post-incident actions | ✅ In camera_friendly.yaml |
| 3 | `SOURCE_DERIVED_PATTERNS` | 367-373 | 12 patterns | Detect research/conclusions | ✅ In camera_friendly.yaml |
| 4 | `INTERPRETIVE_STRIP_WORDS` | 376-389 | 31 words | Neutralize text | ⚠️ Partial in neutralization.yaml |
| 5 | `CONJUNCTION_STARTS` | 445-448 | 12 words | Fragment detection | ✅ In camera_friendly.yaml |
| 6 | `VERB_STARTS` | 461-469 | 28 words | Verb-first fragment detection | ⚠️ Partial in camera_friendly.yaml |
| 7 | `PRONOUN_STARTS` | 523-527 | 17 words | Pronoun detection | ⚠️ Only basic check in p35 |
| 8 | `INTERPRETIVE_BLOCKERS` | 543-547 | 15 words | Block interpretive content | ✅ In camera_friendly.yaml |

### CLASSIFICATION FUNCTIONS (7 total)

| # | Function | Lines | Purpose | Migrated? |
|---|----------|-------|---------|-----------|
| 1 | `neutralize_for_observed()` | 391-422 | Strip interpretive words | ⚠️ Partial - apply_strip_rules exists |
| 2 | `is_strict_camera_friendly()` | 424-553 | 6-rule camera-friendly check | ✅ p35 has all 6 rules (verified 2026-01-19) |
| 3 | `is_camera_friendly()` | 555-562 | Legacy wrapper | ✅ Deprecated |
| 4 | `is_follow_up_event()` | 564-567 | Detect follow-up | ✅ In p35 via YAML |
| 5 | `is_source_derived()` | 569-572 | Detect source-derived | ✅ In p35 via YAML |
| 6 | `_is_medical_provider_content()` | 1125-1134 | Route medical content | ❌ NOT MIGRATED |
| 7 | `_deduplicate_statements()` | 60-100 | Remove duplicates | ❌ NOT MIGRATED |

### SECTION-SPECIFIC CLASSIFICATION LOGIC (11 blocks)

| # | Section | Lines | Classification Logic | Migrated? |
|---|---------|-------|---------------------|-----------|
| 1 | PARTIES | 143-234 | Role categorization (INCIDENT_ROLES, POST_INCIDENT_ROLES, BARE_ROLE_LABELS) | ❌ NOT MIGRATED |
| 2 | REFERENCE DATA | 236-316 | Officer badge linking, location categorization | ❌ NOT MIGRATED |
| 3 | OBSERVED EVENTS | 614-728 | V8.2 epistemic type filtering (OBSERVABLE_EPISTEMIC_TYPES) | ❌ NOT MIGRATED |
| 4 | ITEMS DISCOVERED | 828-1031 | Complex item parsing (DISCOVERY_PATTERNS, CONTRABAND_TERMS, etc.) | ❌ ENTIRE SECTION MISSING |
| 5 | SOURCE-DERIVED | 1077-1116 | Provenance status validation | ❌ NOT MIGRATED |
| 6 | SELF-REPORTED | 1118-1197 | Medical content routing | ❌ NOT MIGRATED |
| 7 | QUOTES | 1284-1494 | Speaker resolution (SPEECH_VERBS, NOT_SPEAKERS, name_patterns) | ❌ NOT MIGRATED |
| 8 | EVENT VALIDATION | 1496-1567 | Hard invariant checks | ❌ NOT MIGRATED |
| 9 | TIMELINE | 1569-1932 | Pronoun resolution, neutralization, fragment filtering | ❌ NOT MIGRATED |
| 10 | INVESTIGATION QUESTIONS | 1934-1994 | Question generation from gaps | ❌ NOT MIGRATED |
| 11 | CONTEXT SUMMARY | 736-803 | Opening context construction | ❌ NOT MIGRATED |

### ITEMS DISCOVERED CLASSIFICATION (lines 828-1031)

**Never migrated. 200+ lines of complex extraction:**

| Pattern Set | Lines | Count | Purpose |
|-------------|-------|-------|---------|
| `DISCOVERY_PATTERNS` | 835-839 | 3 regexes | Detect item discovery |
| `CONTRABAND_TERMS` | 843-848 | 16 terms | Specific illegal substances |
| `VAGUE_SUBSTANCE_TERMS` | 851-854 | 9 terms | Ambiguous substance references |
| `WEAPON_TERMS` | 856-859 | 12 terms | Weapon detection |
| `PERSONAL_EFFECTS` | 861-865 | 14 terms | Personal item detection |
| `WORK_ITEMS` | 867-870 | 9 terms | Work-related item detection |

**Output categories:**
- personal_effects, work_items, valuables, contraband, unspecified_substances, weapons, other

### QUOTE SPEAKER EXTRACTION (lines 1315-1410)

**Never migrated. 95 lines of complex extraction:**

| Pattern Set | Lines | Purpose |
|-------------|-------|---------|
| `SPEECH_VERBS` | 1316-1321 | 18 verbs: said, yelled, shouted, asked, told, screamed, whispered, replied, answered, explained, stated, mentioned, demanded, threatened, warned, muttered, exclaimed |
| `NOT_SPEAKERS` | 1339-1343 | 17 words to exclude: phone, face, me, him, her, them, us, it, ear, car, head, arm, hand, back, porch, saying, and, just, then, also, immediately |
| `name_patterns` | 1346-1357 | 10 regex patterns for extracting speaker names |
| `first_person_patterns` | 1382-1391 | 8 patterns for "I tried to explain" etc. |

### TIMELINE PRONOUN RESOLUTION (lines 1650-1697)

**Never migrated. 47 lines of hardcoded context-based resolution:**

```python
# Hardcoded name mappings (test-case specific):
if 'searched' in desc_lower:
    full_desc = 'Officer Rodriguez' + full_desc[2:]
if 'recording' in desc_lower or 'neighbor' in desc_lower:
    full_desc = 'Marcus Johnson' + full_desc[2:]
if '911' in desc_lower or 'porch' in desc_lower:
    full_desc = 'Patricia Chen' + full_desc[3:]
```

### TIMELINE NEUTRALIZATION (lines 1715-1759)

**Never migrated. 44 lines of neutralization patterns:**

| Pattern Set | Lines | Count | Purpose |
|-------------|-------|-------|---------|
| `SKIP_PATTERNS` | 1719-1733 | 28 regexes | Skip entries with subjective language |
| `NEUTRALIZE_PATTERNS` | 1745-1756 | 10 pairs | Replace phrases with neutral alternatives |
| First-person normalization | 1761-1778 | 16 patterns | I→Reporter, my→Reporter's, etc. |

### TIMELINE FRAGMENT FILTERING (lines 1637-1702)

| Pattern | Lines | Purpose |
|---------|-------|---------|
| `fragment_starters` | 1642-1646 | 14 prepositions to skip |
| Conjunction skip | 1701-1702 | but, or, yet |
| Short description skip | 1638-1639 | <15 chars |
| Bad endings skip | 1824-1826 | a, an, the, of, etc. |
| Incomplete markers | 1829-1833 | Add "..." to incomplete entries |

---

## WHAT WAS ACTUALLY MIGRATED (VERIFIED)

### Policy Engine Extensions ✅

**models.py lines 20-25:**
- CLASSIFY, DISQUALIFY, DETECT, STRIP actions exist

**engine.py:**
- `apply_classification_rules()` (lines 650-713)
- `apply_strip_rules()` (lines 715-760)

### camera_friendly.yaml (292 lines) ✅

| Rule ID | Migrates |
|---------|----------|
| cf_conjunction_start | CONJUNCTION_STARTS ✅ |
| cf_verb_start | VERB_STARTS (partial - 10 verbs, V1 has 28) |
| cf_embedded_quote | Quote check ✅ |
| cf_follow_up_* | FOLLOW_UP_PATTERNS ✅ |
| cf_source_derived_* | SOURCE_DERIVED_PATTERNS ✅ |
| cf_interpretive_* | Some INTERPRETIVE_DISQUALIFIERS ✅ |

### neutralization.yaml (168 lines) ✅

| Rule ID | Migrates |
|---------|----------|
| neut_adverb_* | brutally, viciously, savagely, aggressively, menacingly, deliberately, intentionally, obviously, clearly, absolutely, completely, totally, definitely, certainly |
| neut_adjective_* | brutal, vicious, savage, psychotic, horrifying, horrific, terrifying, shocking, excessive, menacing, manic, innocent |
| neut_phrase_* | like a maniac, like a criminal, for no reason, with excessive force, without provocation |

---

## WHAT WAS NOT MIGRATED (DETAILED)

### 1. Named Actor Detection (Rules 4 & 5) — ✅ VERIFIED COMPLETE (2026-01-19)

**V1 (lines 473-538):**
```python
# Pattern 1: Title + Name
title_pattern = r'\b(Officer|Sergeant|Detective|...)\s+[A-Z][a-z]+'
if re.search(title_pattern, text):
    has_named_actor = True

# Pattern 2: Two-word proper nouns
proper_noun_pattern = r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b'
if re.search(proper_noun_pattern, text):
    has_named_actor = True

# START_ACTOR_PATTERNS (3 patterns)
if first_word in PRONOUN_STARTS:
    if not has_named_actor:
        return (False, f"pronoun_start:{first_word}")
```

**p35 (lines 99-178) — NOW COMPLETE:**
```python
# Pattern 1: Title + Name (line 114)
title_pattern = r'\b(Officer|Sergeant|Detective|Captain|Lieutenant|Deputy|Dr\.?|Mr\.?|Mrs\.?|Ms\.?)\s+[A-Z][a-z]+'

# Pattern 2: Two-word proper nouns (lines 121-129)
proper_noun_pattern = r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b'

# START_ACTOR_PATTERNS (lines 133-140)
# Rule 5: Pronoun handling (lines 153-178)
```

**Test Results:** All 7 test cases pass ✅

### 2. VERB_STARTS Array — ✅ VERIFIED COMPLETE (2026-01-19)

**V1 (lines 461-469) — 28 verbs:**
```
twisted, grabbed, pushed, slammed, found, tried, stepped, saw, also, put, cut, screamed,
yelled, shouted, told, called, ran, walked, went, came, left, arrived, started, began,
stopped, continued, happened, witnessed, watched, heard, felt, noticed, realized, screeching, immediately
```

**camera_friendly.yaml cf_verb_start (line 46) — ALL 35 verbs included ✅:**
```
twisted|grabbed|pushed|slammed|found|tried|stepped|saw|also|put|cut|screamed|
yelled|shouted|told|called|ran|walked|went|came|left|arrived|started|began|
stopped|continued|happened|witnessed|watched|heard|felt|noticed|realized|screeching|immediately
```

### 3. INTERPRETIVE_STRIP_WORDS — INCOMPLETE

**V1 (lines 376-389) — 31 items:**
```
innocently, distressingly, horrifyingly, terrifyingly, distressing, manic, maniacal,
like a maniac, like a criminal, for no reason, for absolutely no reason, without any reason,
with excessive force, without provocation
```

**neutralization.yaml — missing:**
- innocently
- distressingly
- horrifyingly
- terrifyingly
- distressing
- maniacal

### 4. Medical Content Routing — NOT MIGRATED

**V1 (lines 1125-1134):**
```python
providers = ['dr.', 'dr ', 'doctor', 'nurse', 'emt', 'paramedic', 'physician', 'therapist']
medical_verbs = ['documented', 'diagnosed', 'noted', 'observed', 'confirmed', 'stated that my injuries']
return has_provider and has_verb
```

Routes content from SELF-REPORTED STATE to MEDICAL FINDINGS. Not in p35 or any YAML.

### 5. ITEMS DISCOVERED Extraction — NOT MIGRATED

200+ lines of complex extraction logic including:
- 3 discovery regex patterns
- 6 categorization term sets
- 7 output categories

No pass exists for this.

### 6. Quote Speaker Extraction — NOT MIGRATED

95 lines of complex extraction logic including:
- 18 speech verbs
- 17 speaker exclusion words
- 10 name extraction patterns
- 8 first-person patterns

No p36_resolve_quotes pass exists.

### 7. Timeline Processing — NOT MIGRATED

200+ lines including:
- Context-based pronoun resolution (47 lines)
- Entry neutralization (44 lines)
- Fragment filtering (65 lines)

p44_timeline does not have this logic.

### 8. Role Categorization — NOT MIGRATED

**V1 (lines 150-168):**
```python
INCIDENT_ROLES = {'reporter', 'subject_officer', 'supervisor', ...}
POST_INCIDENT_ROLES = {'medical_provider', 'legal_counsel', 'investigator'}
BARE_ROLE_LABELS = {'partner', 'passenger', 'suspect', 'manager', ...}
```

Not in any pass.

---

## QUANTITATIVE ASSESSMENT

### Lines of Classification Logic in V1: ~850 lines
```
PATTERN ARRAYS:        ~100 lines
FUNCTIONS (7):         ~180 lines  
ITEMS DISCOVERED:      ~200 lines
QUOTES:                ~95 lines
TIMELINE:              ~200 lines
PARTIES/REFERENCE:     ~75 lines
```

### Lines Migrated: ~350 lines (41%)
```
camera_friendly.yaml:   292 lines (but incomplete)
neutralization.yaml:    168 lines (but incomplete)
p35_classify_events:    157 lines (but wrong logic)
```

### Lines NOT Migrated: ~500 lines (59%)
- ITEMS DISCOVERED: 200 lines
- QUOTES: 95 lines
- TIMELINE: 200 lines (but hardcoded to test case)
- Medical routing, role categorization: ~50 lines

---

## STAGE 1 VERDICT (Updated 2026-01-19)

| Metric | Status |
|--------|--------|
| Policy Engine extended | ✅ Complete |
| p35 created | ✅ Complete with all 6 V1 rules |
| YAML rules created | ✅ Complete (VERB_STARTS has all 35) |
| Named actor rules (4 & 5) | ✅ Implemented in p35 (lines 99-178) |
| VERB_STARTS array | ✅ All 35 verbs migrated |
| STRIP_WORDS array | ⚠️ 25/31 migrated (81%) |
| p36_resolve_quotes | ❌ Not created |
| p44_timeline updates | ⚠️ Basic - missing V1 pronoun resolution |
| Medical routing | ❌ Not migrated |
| Items extraction | ❌ Not migrated |
| Renderer using pre-computed | ❌ Document admits "deferred" |

### Outcome Status: ⚠️ PARTIALLY COMPLETE

**What's Done:**
- ✅ p35 correctly classifies camera-friendly events (verified with tests)
- ✅ YAML rules for VERB_STARTS complete
- ✅ Classification fields populated

**What's NOT Done:**
- ❌ Renderer still uses inline functions (must read from fields)
- ❌ Quote speaker extraction (p36_resolve_quotes not created)
- ❌ Items discovered extraction (no pass exists)
- ❌ Medical content routing not migrated
- ❌ Timeline pronoun resolution logic not migrated

---

## REMEDIATION REQUIRED (Updated)

### ~~Priority 1: Fix Logic Discrepancies~~ ✅ DONE
1. ~~Add missing 18 verbs to VERB_STARTS in YAML~~ ✅ Already complete
2. ⚠️ Add missing 6 words to neutralization.yaml (minor)
3. ~~Implement named actor detection (Rules 4 & 5) in p35~~ ✅ Already complete

### Priority 2: Create Missing Passes
4. Create p36_resolve_quotes (95 lines of logic) ❌
5. Update p44_timeline with pronoun resolution (47 lines) ❌
6. Update p44_timeline with neutralization (44 lines) ❌

### Priority 3: Create New Extraction
7. Create items extraction pass (200 lines) ❌
8. Migrate medical content routing to classification ❌

### Priority 4: Update Renderer (CRITICAL)
9. Replace inline function calls with field reads ❌
10. Remove V8 fallback path ❌

---

*Stage 1 Audit — Updated 2026-01-19*
