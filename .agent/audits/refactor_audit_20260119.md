# COMPLETE REFACTORING AUDIT — 2026-01-19

## Executive Summary

**The v2 refactoring was fundamentally broken.** 

I created a "clean" `structured_v2.py` (492 lines) that was supposed to replace the working `structured.py` (2018 lines), assuming all logic was handled upstream by the new architecture. **It wasn't.**

The result: v2 produced 186 lines / 17KB of output vs v1's 401 lines / 31KB. Nearly half the content was missing because the logic that generates it was never migrated.

---

## PART 1: COMPLETE SECTION INVENTORY

### All Sections in v1 (git version structured.py)

| # | Section Name | Lines | Renders From | Present in v2? |
|---|--------------|-------|--------------|----------------|
| 1 | HEADER (═══ NEUTRALIZED REPORT ═══) | 137-141 | Static | ✅ Yes |
| 2 | **PARTIES** | 143-234 | `entities` + categorization | ⚠️ Simplified |
| 3 | **REFERENCE DATA** | 236-316 | `identifiers` + `entities` | ⚠️ Simplified |
| 4 | ACCOUNT SUMMARY HEADER | 317-321 | Static | ✅ Yes |
| 5 | **OBSERVED EVENTS (STRICT)** | 729-809 | events/statements + `is_strict_camera_friendly()` | ⚠️ Missing logic |
| 6 | **OBSERVED EVENTS (FOLLOW-UP)** | 811-826 | statements + `is_follow_up_event()` | ⚠️ Missing logic |
| 7 | **ITEMS DISCOVERED** | 828-1031 | Complex regex parsing of statements | ❌ MISSING |
| 8 | **NARRATIVE EXCERPTS (UNNORMALIZED)** | 1033-1069 | Failed camera-friendly checks | ⚠️ Missing logic |
| 9 | **SOURCE-DERIVED INFORMATION** | 1071-1116 | statements + `is_source_derived()` | ⚠️ Missing logic |
| 10 | **SELF-REPORTED STATE (ACUTE)** | 1139-1149 | `state_acute` epistemic | ✅ Yes |
| 11 | **SELF-REPORTED INJURY (Physical)** | 1151-1161 | `state_injury` epistemic | ✅ Yes |
| 12 | **SELF-REPORTED STATE (Psychological)** | 1163-1173 | `state_psychological` epistemic | ❌ MISSING |
| 13 | **SELF-REPORTED IMPACT (Socioeconomic)** | 1175-1185 | `state_socioeconomic` epistemic | ❌ MISSING |
| 14 | **SELF-REPORTED STATE (General)** | 1187-1197 | `self_report` epistemic | ❌ MISSING |
| 15 | **LEGAL ALLEGATIONS** | 1199-1207 | `legal_claim` epistemic | ❌ MISSING |
| 16 | **REPORTER CHARACTERIZATIONS** | 1209-1218 | `characterization` epistemic | ✅ Yes |
| 17 | **REPORTER INFERENCES** | 1220-1229 | `inference` epistemic | ❌ MISSING |
| 18 | **REPORTER INTERPRETATIONS** (legacy) | 1231-1237 | `interpretation` epistemic | ❌ MISSING |
| 19 | **CONTESTED ALLEGATIONS** | 1239-1248 | `conspiracy_claim` epistemic | ❌ MISSING |
| 20 | **MEDICAL FINDINGS** | 1250-1272 | `medical_finding` + routed content | ❌ MISSING |
| 21 | **ADMINISTRATIVE ACTIONS** | 1274-1282 | `admin_action` epistemic | ❌ MISSING |
| 22 | **PRESERVED QUOTES (SPEAKER RESOLVED)** | 1284-1468 | Complex speaker extraction | ⚠️ Missing logic |
| 23 | **QUOTES (SPEAKER UNRESOLVED)** | 1470-1494 | Quarantined quotes | ❌ MISSING |
| 24 | **EVENTS (ACTOR UNRESOLVED)** | 1496-1567 | Event validation/quarantine | ❌ MISSING |
| 25 | **RECONSTRUCTED TIMELINE** | 1569-1932 | timeline + pronoun resolution | ⚠️ Missing logic |
| 26 | **INVESTIGATION QUESTIONS** | 1934-1994 | `generate_all_questions()` | ❌ MISSING |
| 27 | **RAW NEUTRALIZED NARRATIVE** | 1996-2005 | `rendered_text` | ✅ Yes |
| 28 | FOOTER | 2007-2018 | Static | ✅ Yes |

### Summary: 
- **✅ Present and correct:** 5 sections
- **⚠️ Present but missing critical logic:** 7 sections  
- **❌ Completely missing:** 11 sections

---

## PART 2: MISSING CLASSIFICATION FUNCTIONS

These functions exist ONLY in structured.py and were NEVER migrated to passes:

### 1. `is_strict_camera_friendly(text)` → Lines 424-553

**Purpose:** Determines if an event can appear in OBSERVED EVENTS section.

**Rules implemented:**
1. Rule 1 (lines 445-450): No conjunction starts (`but`, `and`, `when`, `which`, etc.)
2. Rule 2 (lines 452-456): No embedded quotes (`"`, `"`, `"`)
3. Rule 3 (lines 458-471): No verb-first fragments (`twisted`, `grabbed`, etc.)
4. Rule 4 (lines 473-516): Must have NAMED ACTOR anywhere (title patterns, proper nouns)
5. Rule 5 (lines 518-534): Pronoun starts OK only if named actor exists
6. Rule 6 (lines 540-550): No interpretive/legal content

**What p35_classify_events does instead:**
- Defaults `is_camera_friendly = True` (WRONG - should default False)
- Calls `engine.apply_classification_rules()` which only checks YAML patterns
- YAML has Rules 1, 2, 3, 6 but is MISSING Rules 4 and 5 (named actor requirement)
- The pronoun check (lines 102-115 of p35) only checks `event.actor_label`, not the full pattern matching

**Result:** New pass classifies 49 events as camera-friendly vs v1's 17.

### 2. `neutralize_for_observed(text)` → Lines 391-422

**Purpose:** Strips interpretive words while keeping factual core.

**Implementation:**
- Uses `INTERPRETIVE_STRIP_WORDS` list (lines 376-388)
- Regex-based word removal
- Fixes article agreement after stripping
- Cleans trailing punctuation artifacts

**What p35 does:** Calls `engine.apply_strip_rules()` which may have different patterns.

**Status:** Needs verification that YAML patterns match the hardcoded list.

### 3. `is_follow_up_event(text)` → Lines 564-567

**Purpose:** Identifies post-incident follow-up actions.

**Patterns checked:**
```python
FOLLOW_UP_PATTERNS = [
    'went to the emergency', 'went to the hospital', 'filed a complaint',
    'filed a formal', 'the next day', 'afterward', 'afterwards',
    'detective', 'took my statement',
]
```

**What p35 does:** Similar patterns in YAML but needs verification.

### 4. `is_source_derived(text)` → Lines 569-572

**Purpose:** Identifies research/comparison/conclusion content.

**Patterns checked:**
```python
SOURCE_DERIVED_PATTERNS = [
    'later found', 'later learned', 'found out', 'turned out',
    'found that', 'researched', 'so-called',
    'at least', 'other citizens', 'complaints against',
    'received a letter', 'three months later',
    'investigated', 'pursuing legal', 'my attorney',
]
```

**What p35 does:** Similar patterns in YAML but needs verification.

### 5. `_is_medical_provider_content(text)` → Lines 1125-1134

**Purpose:** Routes medical provider content to MEDICAL_FINDINGS section.

**Implementation:**
```python
providers = ['dr.', 'dr ', 'doctor', 'nurse', 'emt', 'paramedic', 'physician', 'therapist']
medical_verbs = ['documented', 'diagnosed', 'noted', 'observed', 'confirmed', 'stated that my injuries']
return has_provider and has_verb
```

**Status:** NOT migrated at all. v2 doesn't have this routing.

---

## PART 3: MISSING COMPLEX LOGIC BLOCKS

### 1. ITEMS DISCOVERED Parsing → Lines 828-1031 (203 lines!)

This entire section is missing from v2. It includes:

**Discovery Patterns:**
```python
DISCOVERY_PATTERNS = [
    r'(?:he|she|they|officer|rodriguez|jenkins)\s+found\s+(.+?)(?:\.|$)',
    r'(?:he|she|they)\s+(?:took|seized|grabbed|confiscated)\s+(.+?)(?:\.|$)',
    r'(?:searched|searching).+?(?:found|discovered)\s+(.+?)(?:\.|$)',
]
```

**Item Categories:**
- `CONTRABAND_TERMS` (specific illegal substances)
- `VAGUE_SUBSTANCE_TERMS` (needs clarification)
- `WEAPON_TERMS`
- `PERSONAL_EFFECTS`
- `WORK_ITEMS`

**Output Structure:**
- PERSONAL EFFECTS
- WORK-RELATED ITEMS
- VALUABLES/CURRENCY
- ❓ UNSPECIFIED SUBSTANCES (with follow-up question)
- ⚠️ CONTROLLED SUBSTANCES / CONTRABAND
- ⚠️ WEAPONS
- OTHER ITEMS

### 2. Quote Speaker Extraction → Lines 1284-1494 (210 lines!)

**Speech Verbs (line 1316-1321):**
```python
SPEECH_VERBS = [
    ' said ', ' yelled ', ' shouted ', ' asked ', ' told ',
    ' screamed ', ' whispered ', ' replied ', ' answered ',
    ' explained ', ' stated ', ' mentioned ', ' demanded ',
    ' threatened ', ' warned ', ' muttered ', ' exclaimed ',
]
```

**Name Extraction Patterns (lines 1346-1357):**
```python
name_patterns = [
    r'(Officer\s+\w+)\s*$',
    r'(Sergeant\s+\w+)\s*$',
    r'(Detective\s+\w+)\s*$',
    r'(Dr\.\s+\w+)\s*$',
    r'(Mrs?\.\s+\w+(?:\s+\w+)?)\s*$',
    r'(Marcus\s+Johnson)\s*$',  # Known witness
    r'(Patricia\s+Chen)\s*$',
    r'(\w+\s+\w+)\s*$',  # Generic two-word name at end
    r'([Hh]e|[Ss]he|[Tt]hey)\s*$',  # Pronouns at end
]
```

**NOT_SPEAKERS filter (lines 1339-1343):**
```python
NOT_SPEAKERS = {
    'phone', 'face', 'me', 'him', 'her', 'them', 'us', 'it',
    'ear', 'car', 'head', 'arm', 'hand', 'back', 'porch',
    'saying', 'and', 'just', 'then', 'also', 'immediately',
}
```

### 3. Timeline Pronoun Resolution → Lines 1650-1697

**Context-based resolution:**
```python
if desc_lower.startswith('he '):
    if ('recording' in desc_lower and 'yelled' in desc_lower) or 'neighbor' in desc_lower:
        full_desc = 'Marcus Johnson' + full_desc[2:]
    elif 'uncuffed' in desc_lower or 'badge' in desc_lower or 'sergeant' in desc_lower:
        full_desc = 'Sergeant Williams' + full_desc[2:]
    elif 'searched' in desc_lower or 'handcuff' in desc_lower or 'found' in desc_lower:
        full_desc = 'Officer Rodriguez' + full_desc[2:]
    else:
        full_desc = 'Officer Jenkins' + full_desc[2:]
```

This is **hardcoded to the test narrative** but provides critical functionality.

### 4. Timeline Neutralization → Lines 1715-1741

**SKIP_PATTERNS (lines 1719-1733):**
```python
SKIP_PATTERNS = [
    r'\bthug\b', r'\bpsychotic\b', r'\bbrutal\b', r'\bmaniac\b',
    r'\bviolent\b', r'\bviciously\b', r'\baggressively\b',
    r'\bconspiring\b', r'\bcover.?up\b', r'\bcorrupt\b',
    r'\btorture\b', r'\bterrorize\b', r'\bterrorized\b',
    r'\binnocently\b', r'\bdeliberately\b', r'\bintentionally\b',
    r'\bwhich proves\b', r'\bclearly\b', r'\bobviously\b',
    r'\bassaulting\b', r'\battacked\b', r'\battack\b',
    r'\bcriminal behavior\b', r'\btheir crimes\b', r'\billegal\b',
    r'\bfabricated\b', r'\blie\b', r'\blied\b',
    r'\binnocent person\b', r'\binnocent citizen\b',
    r'\bwhitewash\b', r'\bracism\b', r'\bracist\b',
    r'\bknow they always\b', r'\bprotect their own\b',
]
```

**NEUTRALIZE_PATTERNS (lines 1745-1756):**
```python
NEUTRALIZE_PATTERNS = [
    (r'\blike a maniac\b', ''),
    (r'\blike a criminal\b', ''),
    (r'\bfor no reason\b', ''),
    (r'\bwithout any legal justification\b', ''),
    (r'\bwith excessive force\b', 'with force'),
    (r'\bbrutal(ly)?\b', ''),
    (r'\bvicious(ly)?\b', ''),
    (r'\bdeliberate(ly)?\b', ''),
    (r'\bhorrifying\b', ''),
    (r'\bterrified\b', 'frightened'),
]
```

---

## PART 4: MISSING SelectionResult FIELDS

The `SelectionResult` dataclass needs these additional fields to support all v1 sections:

```python
@dataclass
class SelectionResult:
    # Currently has:
    observed_events: List[str]
    follow_up_events: List[str]
    source_derived: List[str]
    narrative_excerpts: List[Tuple[str, str]]
    acute_state: List[str]
    injury_state: List[str]
    characterizations: List[str]
    preserved_quotes: List[str]
    events_requiring_review: List[str]
    timeline_entries: List[str]
    
    # MISSING - needs to be added:
    discovered_items: Dict[str, List[str]]  # categorized items
    psychological_state: List[str]
    socioeconomic_impact: List[str]
    general_self_report: List[str]
    legal_allegations: List[str]
    reporter_inferences: List[str]
    reporter_interpretations: List[str]  # legacy
    contested_allegations: List[str]
    medical_findings: List[str]
    administrative_actions: List[str]
    quarantined_quotes: List[Tuple[str, str]]  # (content, reason)
    events_actor_unresolved: List[Tuple[str, str]]  # (event, issues)
    investigation_questions: List[Dict]  # question objects
    time_gaps: List[Dict]  # gap objects
```

---

## PART 5: CORRECT REMEDIATION PATH

### Option A: Fix v2 by Migrating All Logic (WRONG)
This would make v2 grow to 2000+ lines, defeating the purpose of the refactoring.

### Option B: Keep v1, Incrementally Refactor (CORRECT)
1. **Don't replace structured.py.** It works.
2. Migrate logic piece by piece:
   - Move `is_strict_camera_friendly` verbatim to `nnrt/classification/camera_friendly.py`
   - Move item discovery to `nnrt/extraction/items.py`
   - Move quote speaker extraction to `nnrt/extraction/quotes.py`
   - Move timeline resolution to `nnrt/extraction/timeline.py`
3. Update structured.py to call these modules instead of inline functions
4. Verify output remains identical after each migration
5. Only after ALL logic is migrated, structured.py becomes thin wrapper

### Option C: The SelectionResult Must Be Complete First
Before ANY renderer can work, the selection layer must provide:
1. All 20+ section data buckets
2. All classification results
3. All extraction results

The p55_select pass must be massively expanded.

---

## PART 6: WHAT WAS ACTUALLY WRONG WITH THE REFACTORING APPROACH

### The Fundamental Error
The refactoring assumed a clean separation:
```
[Extraction] → [Classification] → [Selection] → [Rendering]
```

But structured.py does ALL FOUR in one monolithic function because:
1. Classification depends on context not available upstream
2. Selection depends on inline heuristics
3. Extraction (items, quotes, timeline) happens AT RENDER TIME

### The Correct Approach
1. **Extract to libraries first** — Don't change where logic runs, just where it's defined
2. **Test equivalence** — After each extraction, verify output is byte-identical
3. **Only then refactor data flow** — Once all logic is in libraries, refactor to call them from appropriate passes
4. **Never delete working code** — Keep the original renderer as the gold standard until new passes are proven

---

## CONCLUSION

The v2 renderer was created without understanding:
1. The full scope of what v1 does (28 sections, not 15)
2. The complex inline logic that can't just be "assumed upstream"
3. The fundamental architecture mismatch between ideal and actual

**Next Steps:**
1. Delete/archive structured_v2.py
2. Create proper architecture document showing actual data dependencies
3. Extract logic to libraries WITHOUT changing behavior
4. Add comprehensive diff tests
5. Only attempt architectural refactoring after libraries are proven equivalent
