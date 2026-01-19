# V1 vs V2 Output Analysis — Comprehensive Gap Report

**Date**: 2026-01-19
**Purpose**: Honest, complete analysis of all differences between V1 (reliable) and V2 (current) output

---

## EXECUTIVE SUMMARY

| Metric | V1 | V2 | Verdict |
|--------|---|---|---------|
| Total Lines | 405 | 191 | ❌ V2 60% SHORTER |
| Well-formed sections | ~25 | ~18 | ❌ MISSING SECTIONS |
| Neutralized prose quality | Good | Poor | ❌ REGRESSION |
| Camera-friendly events | Good | Broken | ❌ SEVERE REGRESSION |

**Overall Assessment**: V2 is a significant **regression** from V1. Multiple critical issues need resolution before V2 can replace V1.

---

## SECTION-BY-SECTION ANALYSIS

### 1. REFERENCE DATA
**V1** (9 lines, structured):
```
INCIDENT DATETIME:
  Date: January 15th, 2026
  Time: 11:30 PM

INCIDENT LOCATION: Main Street and Oak Avenue
SECONDARY LOCATIONS:
  • the Riverside Cafe
  • St. Mary's Hospital

OFFICER IDENTIFICATION:
  • Sergeant Williams (Badge #2103)
  • Officer Jenkins (Badge #4821)
  • Officer Rodriguez (Badge #5539)
```

**V2** (5 lines, flat):
```
Date: January 15th, 2026
Time: 11:30 PM
Location: Main Street and Oak Avenue, the Riverside Cafe, St. Mary's Hospital
Badge Number: 4821, 5539, 2103
Name: Jenkins, Sarah Mitchell, Marcus Johnson, Patricia Chen...
```

**Issues**:
- ❌ Lost "INCIDENT DATETIME" section header
- ❌ Lost "INCIDENT LOCATION" vs "SECONDARY LOCATIONS" distinction
- ❌ Lost "OFFICER IDENTIFICATION" section with names linked to badges
- ❌ "ACCOUNT SUMMARY" section header completely removed
- 🔧 **Fix Required**: Restore structured formatting in structured_v2.py

---

### 2. OBSERVED EVENTS (CRITICAL REGRESSION)

**V1** (17 events, all clean):
```
• Officer Jenkins jumped out of the car.
• Reporter froze in place.
• Officer Jenkins grabbed Reporter's left arm.
• Officer Rodriguez searched through Reporter's pockets.
• Officers slammed Reporter against their patrol car.
```

**V2** (11 events, BROKEN):
```
• when the , cops attacked me 15th, 2026 at around 11:30 PM...
• It all started when I was innocently walking home...
• Officer Jenkins, badge number 4821, jumped out of the car and immediately started screaming at me
• Officer Jenkins grabbed my left arm ed it behind my back  ← TRUNCATION BUG
```

**Issues**:
- ❌ **CRITICAL**: "when the , cops attacked me" — un-neutralized, missing word, comma error
- ❌ **CRITICAL**: "It all started when I" — NOT camera-friendly, first-person narrator perspective
- ❌ **CRITICAL**: "innocently walking" — subjective word NOT neutralized
- ❌ **CRITICAL**: " ed it behind my back" — MID-WORD TRUNCATION, word mangled
- ❌ **CRITICAL**: "screaming at me" — un-neutralized (V1 says "started speaking loudly")
- ❌ **CRITICAL**: Events include first-person pronouns ("my", "me") — should be "Reporter"
- ❌ Context blurb removed that V1 had
- 📊 V1 Count: 17 events, V2 Count: 11 events (35% fewer)

**Root Cause**: `p35_classify_events.py` is_camera_friendly logic is allowing un-neutralized events through.

---

### 3. FOLLOW-UP ACTIONS SECTION
**V1**: Present with 2 entries
**V2**: **COMPLETELY MISSING**
🔧 **Fix Required**: Restore follow-up events rendering in structured_v2.py

---

### 4. ITEMS DISCOVERED
**V1** (well-formatted):
```
PERSONAL EFFECTS:
  • phone
  • wallet
```

**V2** (CORRUPT):
```
PERSONAL EFFECTS:
• phone
• wallet
• said "sure you did   ← QUOTE FRAGMENT LEAKED IN
...
OTHER ITEMS:
• that's what they all say  ← QUOTE FRAGMENT LEAKED IN
```

**Issues**:
- ❌ **CRITICAL**: Quote fragments leaked into ITEMS section
- ❌ "OTHER ITEMS" category created with garbage data
- ❌ "FOLLOW-UP QUESTION" section removed from V1
🔧 **Root Cause**: p38_extract_items is misclassifying quote fragments as items

---

### 5. SOURCE-DERIVED INFORMATION
**V1**: Present with 6 claims + provenance tracking
**V2**: **COMPLETELY MISSING**
🔧 **Fix Required**: Restore this section in structured_v2.py

---

### 6. SELF-REPORTED SECTIONS

**V1 format** (clean, prefixed):
```
SELF-REPORTED STATE (ACUTE - During Incident)
• Reporter reports: I was absolutely terrified in complete shock.
```

**V2 format** (inconsistent, missing prefix):
```
SELF-REPORTED STATE (ACUTE)
• I was absolutely terrified in complete shock.
• I was so scared I froze in place.
• I froze in place  ← DUPLICATE
```

**Issues**:
- ⚠️ V2 missing "- During Incident" qualifier in header
- ⚠️ V2 missing "Reporter reports:" prefix
- ❌ V2 has duplicate entries
- ⚠️ V1 section named "SELF-REPORTED INJURY (Physical)", V2 is "SELF-REPORTED STATE (INJURY)"

---

### 7. REPORTER CHARACTERIZATIONS

**V1** (8 entries, well formatted):
```
REPORTER CHARACTERIZATIONS (Subjective Language)
  • Opinion: when the brutal, psychotic cops viciously attacked me...
```

**V2** (8 entries, missing "Opinion:" prefix):
```
REPORTER DESCRIPTIONS (CHARACTERIZATIONS)
  • when the brutal, psychotic cops viciously attacked me...
```

**Issues**:
- ⚠️ Section renamed from "CHARACTERIZATIONS" to "DESCRIPTIONS"
- ⚠️ Missing "Opinion:" prefix
- Minor: Different section title styling

---

### 8. CONTESTED ALLEGATIONS

**V1** (13 entries, well formatted):
```
CONTESTED ALLEGATIONS (unverifiable)
  ⚠️ Unverified: The police department refuses to release...
```

**V2** (14 entries, corrupt):
```
CONTESTED ALLEGATIONS
  • I later found out that her call was mysteriously "lost" in the system, which proves there's a going on.
    ← TRUNCATED, "massive cover-up" removed but sentence left broken
```

**Issues**:
- ❌ **CRITICAL**: Broken sentences - words removed but sentences not reconstructed
- ❌ "which proves there's a going on" — missing word "massive cover-up"
- ⚠️ Missing "⚠️ Unverified:" prefix

---

### 9. MEDICAL FINDINGS

**V1** (1 entry, clean):
```
• She documented bruises on both wrists, a sprained left shoulder...
```

**V2** (3 entries, messy):
```
• was treated by Dr. Amanda Foster  ← SENTENCE FRAGMENT
• She documented bruises...
• My therapist, Dr. Michael Thompson, has diagnosed me with Post-Traumatic Stress Disorder directly caused by this -- reporter characterizes conduct as ity -- incident.
    ← "ity" is broken word, should be "brutality"
```

**Issues**:
- ❌ "was treated by" fragment doesn't start with actor
- ❌ **CRITICAL**: "-- reporter characterizes conduct as ity --" — word "brutal" removed mid-word, leaving "ity"

---

### 10. PRESERVED QUOTES

**V1** (6 quotes, well attributed):
```
• Officer Jenkins said: You should have just cooperated...
• Reporter said: I just got off work...
• Rodriguez said: You better delete that video...
```

**V2** (9 quotes, COMPLETELY BROKEN):
```
• He yelled: STOP RIGHT THERE! DON'T YOU DARE MOVE!  ← "He" not resolved
• they say: Sure you did, that's what they all say.  ← "they say" WTF
• him saying: You better delete that video...  ← "him saying" WTF
```

**Issues**:
- ❌ **CRITICAL**: Speaker resolution completely broken
- ❌ V1 had "Officer Jenkins said:", V2 has "He yelled:"
- ❌ V1 had "Reporter said:", V2 has weird garbage attributions
- ❌ Missing "Officer Jenkins said: You should have just cooperated..." quote entirely

---

### 11. EVENTS (ACTOR UNRESOLVED)
**V1**: Present with 10 examples + validation stats
**V2**: **COMPLETELY MISSING**
🔧 **Fix Required**: Restore this section

---

### 12. RECONSTRUCTED TIMELINE

**V1** (well formatted, ~50 events visible):
```
┌─── INCIDENT DAY (Day 0) ───
│  ○ Officer Jenkins yelled
│  ○ Reporter froze in place
│  ○ Reporter asked him politely...
│  ⟳ [then] Officer Jenkins was fishing through Reporter's belongings
```

**V2** (messy, un-neutralized):
```
┌─── INCIDENT DAY (Day 0) ───
│ [around 11:30 PM] It all started when I was innocently walking...
│ when the cops attacked me for absolutely no reason...
│ The officer behind the wheel was clearly looking for trouble
```

**Issues**:
- ❌ **CRITICAL**: V2 timeline uses un-neutralized text
- ❌ "when the cops attacked me" — not neutral
- ❌ "innocently walking" — not neutral  
- ❌ "clearly looking for trouble" — not neutral
- ❌ V1 uses "Reporter", V2 uses "I" and "me"
- ⚠️ Legend section removed from V2

---

### 13. INVESTIGATION QUESTIONS
**V1**: Present with 7 questions, priority markers
**V2**: **COMPLETELY MISSING**
🔧 **Fix Required**: Restore this section

---

### 14. RAW NEUTRALIZED NARRATIVE (CRITICAL REGRESSION)

**V1 excerpt**:
```
I was frightened and in shock when the officers made physical contact with me...
```

**V2 excerpt**:
```
I was terrified and in complete shock when the cops made physical contact with me...
The officer cop behind the wheel appeared to be looking for trouble.
```

**Issues**:
- ❌ **CRITICAL**: V1 "frightened" → V2 "terrified" (not neutralized)
- ❌ **CRITICAL**: V1 "officers" → V2 "cops" (not neutralized)
- ❌ **CRITICAL**: "The officer cop behind the wheel" — double word, grammar broken
- ❌ **CRITICAL**: V2 narrative is on a single line (newlines stripped in render)
- ❌ Many neutralization transforms not applied

---

## ROOT CAUSES

### 1. Prose Renderer Regression (p70_render)
The prose neutralization is WORSE in V2. Words like "cops", "terrified", "innocently" are passing through where V1 properly transformed them.

**Affected Files**: `nnrt/passes/p70_render.py`, policy transform patterns

### 2. Structured V2 Renderer Missing Sections
structured_v2.py is not rendering several sections that V1 had:
- FOLLOW-UP ACTIONS
- SOURCE-DERIVED INFORMATION
- EVENTS (ACTOR UNRESOLVED)
- INVESTIGATION QUESTIONS

**Affected Files**: `nnrt/render/structured_v2.py`

### 3. Camera-Friendly Classification Broken
Events that are NOT camera-friendly are being marked as camera-friendly:
- First-person narrative ("It all started when I...")
- Subjective descriptors ("innocently walking")
- Characterizations ("cops attacked me")

**Affected Files**: `nnrt/passes/p35_classify_events.py`

### 4. Quote Speaker Resolution Broken
V1 correctly resolved "He" to "Officer Jenkins", V2 leaves it as "He" or produces garbage like "they say:".

**Affected Files**: `nnrt/passes/p36_resolve_quotes.py`

### 5. Word Truncation Bug
Words are being cut mid-word, leaving broken fragments:
- "brutal" → "ity" 
- "twisted" → " ed "
- "massive cover-up" → "a going on"

**Affected Files**: Likely in neutralization transform patterns (regex issues)

### 6. Items Extraction Pollution
Quote fragments are leaking into the ITEMS section.

**Affected Files**: `nnrt/passes/p38_extract_items.py`

---

## PRIORITY FIX LIST

| Priority | Issue | Affected Pass | Severity |
|----------|-------|---------------|----------|
| P0 | Prose neutralization regression | p70_render | CRITICAL |
| P0 | Camera-friendly events broken | p35_classify_events | CRITICAL |
| P0 | Word truncation bug | Transform patterns | CRITICAL |
| P1 | Quote speaker resolution | p36_resolve_quotes | HIGH |
| P1 | Missing sections in structured_v2 | structured_v2.py | HIGH |
| P2 | Items extraction pollution | p38_extract_items | MEDIUM |
| P2 | Timeline un-neutralized | Timeline builder | MEDIUM |
| P3 | Section formatting | structured_v2.py | LOW |

---

## IMMEDIATE ACTION REQUIRED

Before V2 can ship, we need to:

1. **Identify why p70_render neutralization regressed** — Compare the transform patterns being applied in V1 vs V2 runs
2. **Fix camera-friendly classification** — Tighten is_camera_friendly to reject first-person and characterizations
3. **Find the word truncation bug** — Likely a regex substitution issue
4. **Restore missing sections in structured_v2.py**

---

*Generated 2026-01-19 — Honest gap analysis*
