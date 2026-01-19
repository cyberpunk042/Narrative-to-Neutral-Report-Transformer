# V1 vs V2 Comprehensive Gap Analysis
Generated: 2026-01-19 17:22

## Critical Issues (Blocking Quality)

### 1. OFFICER IDENTIFICATION - Missing Names
**V1:**
```
  OFFICER IDENTIFICATION:
    • Sergeant Williams (Badge #2103)
    • Officer Jenkins (Badge #4821)
    • Officer Rodriguez (Badge #5539)
```

**V2:**
```
 OFFICER IDENTIFICATION:
 • Badge #4821
 • Badge #5539
 • Badge #2103
```

**Issue:** V2 only shows badge numbers, not linked to officer names.
**File:** `nnrt/render/structured_v2.py` in `_render_reference_data()`

---

### 2. OBSERVED EVENTS - Missing Context Header
**V1:**
```
ℹ️ Context: Reporter encountered Officer Jenkins and Officer Rodriguez on 
January 15th, 2026 at approximately 11:30 PM near Main Street and Oak Avenue. 
Reporter reports feeling frightened during this encounter.
```

**V2:** Missing entirely - just shows count and normalization note.

---

### 3. OBSERVED EVENTS - Poor Event Quality
**V1 (17 high-quality events):**
```
  • Officer Jenkins jumped out of the car.
  • Reporter froze in place.
  • Officer Jenkins grabbed Reporter's left arm.
  • Officer Rodriguez searched through Reporter's pockets.
  • Officers slammed Reporter against their patrol car.
  ...
```

**V2 (11 poor-quality events):**
```
 • the cops attacked Reporter.          <- "cops" is informal, not specific
 • It all started.                      <- Fragment, meaningless
 • Reporter walked.                     <- Incomplete
 • Officer Rodriguez jumped.            <- Missing object
 • partner got.                         <- Fragment, bare role
 • They then slammed me...              <- First person, unresolved "They"
```

**Issues:**
- Fragments admitted as camera-friendly
- First-person pronouns not replaced
- Bare roles like "partner" not filtered
- 17 → 11 events (6 lost)

---

### 4. OBSERVED EVENTS (FOLLOW-UP ACTIONS) - Missing Section
**V1:**
```
OBSERVED EVENTS (FOLLOW-UP ACTIONS)
──────────────────────────────────────────────────────────────────────
  • Reporter went to the emergency room at St. Mary's Hospital immediately after.
  • Detective Sarah Monroe took Reporter's statement
```

**V2:** Section entirely missing.

---

### 5. SOURCE-DERIVED INFORMATION - Missing Section
**V1:**
```
SOURCE-DERIVED INFORMATION
──────────────────────────────────────────────────────────────────────
  ⚠️ The following claims require external provenance verification:

  [1] CLAIM: The so-called "robbery suspect"...
      Source: Reporter
      Status: Self-Attested
  ...
```

**V2:** Section entirely missing.

---

### 6. ITEMS DISCOVERED - Wrong Items
**V1:**
```
  PERSONAL EFFECTS:
    • phone
    • wallet
```

**V2:**
```
 PERSONAL EFFECTS:
 • wallet
 • said "sure you did     <- This is a QUOTE FRAGMENT, not an item!
 • phone
```

**Issue:** Quote fragments being classified as items.

---

### 7. NARRATIVE EXCERPTS - Missing Categorization
**V1:** Has proper categorization:
```
  [Fragment (conjunction start)]
    - While my face was pressed...
  [Contains quote (see QUOTES section)]
    - He started recording...
  [Pronoun start (actor unresolved)]
    - He found my wallet...
```

**V2:** Just shows rejection reason codes without proper grouping/formatting.

---

## Formatting Issues

### 8. Indentation Inconsistent
**V1:** Uses 2-4 space indentation consistently
**V2:** Uses 1-2 space indentation inconsistently

### 9. Title Not Centered
**V1:** `                        NEUTRALIZED REPORT`
**V2:** ` NEUTRALIZED REPORT`

### 10. ACCOUNT SUMMARY Header Not Centered
**V1:** `                         ACCOUNT SUMMARY`  
**V2:** ` ACCOUNT SUMMARY`

---

## Missing Sections in V2

1. OBSERVED EVENTS (FOLLOW-UP ACTIONS)
2. SOURCE-DERIVED INFORMATION
3. EVENTS (ACTOR UNRESOLVED) with validation stats
4. INVESTIGATION QUESTIONS
5. Timeline legend and stats

---

## Files to Investigate

| Issue | Primary File | Secondary |
|-------|--------------|-----------|
| Officer names missing | `structured_v2.py` | `p55_select.py` |
| Context header missing | `structured_v2.py` | - |
| Event quality | `p35_classify_events.py` | `p34_extract_events.py` |
| Follow-up missing | `structured_v2.py` | `p55_select.py` |
| Source-derived missing | `structured_v2.py` | `p55_select.py` |
| Items wrong | `p38_extract_items.py` | - |
| Indentation | `p75_cleanup_punctuation.py` | `structured_v2.py` |
| Title centering | `p75_cleanup_punctuation.py` | `p72_safety_scrub.py` |

---

## Priority Order for Fixes

1. **Event Quality** - Core value proposition
   - Filter fragments, bare roles
   - Replace first-person pronouns
   - Add targets to incomplete events

2. **Missing Sections** - Structural completeness
   - Add FOLLOW-UP ACTIONS
   - Add SOURCE-DERIVED INFORMATION

3. **Officer Names** - Data quality
   - Link badges to names in REFERENCE DATA

4. **Context Header** - UX
   - Add incident context summary

5. **Formatting** - Polish
   - Fix indentation
   - Fix centering
