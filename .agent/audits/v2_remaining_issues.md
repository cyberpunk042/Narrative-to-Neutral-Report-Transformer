# V2 Updated Delta Analysis (Post-Fixes)

## Fixes Applied

1. ✅ **Double Rendering Bug** — Fixed by removing manual `format_structured_output_v2()` calls in `server.py` and `stress_test.py`
2. ✅ **Single-Line Output** — Fixed by preserving newlines in `p72_safety_scrub._clean_artifacts()`

---

## REMAINING ISSUES (Categorized by Severity)

### 🔴 CRITICAL — Output Quality Degradation

#### Issue #1: OBSERVED EVENTS (STRICT) - Complete Failure
V1 had 17 clean, normalized events like:
```
• Officer Jenkins jumped out of the car.
• Reporter froze in place.
• Officer Jenkins grabbed Reporter's left arm.
```

V2 has 11 events, most BROKEN:
```
• when the cops attacked me 15th, 2026 at around 11:30 PM...
• It all started when I was innocently walking home...
• Officer Jenkins grabbed my left arm ed it behind my back  <-- TRUNCATED WORD
```

**Problems:**
- First-person pronouns ("I", "me", "my") not replaced with "Reporter"
- Subjective language ("innocently", "attacked") not removed
- Word truncation: "twisted" → "ed"
- Non-camera-friendly content included

---

#### Issue #2: RAW NEUTRALIZED NARRATIVE — Still Broken
- Still on ONE LINE (disclaimer blended with content)
- Un-neutralized terms: "cops", "terrified" (V1: "officers", "frightened")
- Word issues: "The officer cop behind the wheel" (double word)
- First-person not neutralized to "Reporter"

---

#### Issue #3: ITEMS DISCOVERED — Quote Fragment Pollution
V2 has garbage items:
```
• said "sure you did
• that's what they all say
```

These are quote fragments, not items!

---

#### Issue #4: Word Truncation Bug
- `twisted` → `ed` (in "Officer Jenkins grabbed my left arm ed it behind my back")
- `brutality` → `ity` (in "[Interpretive Legal:ity]")

This is a regex truncation bug in the neutralization transforms.

---

### 🟠 HIGH — Missing Sections

#### Issue #5: MISSING SECTIONS in V2
| Section | V1 | V2 |
|---------|----|----|
| OBSERVED EVENTS (FOLLOW-UP ACTIONS) | ✅ | ❌ MISSING |
| SOURCE-DERIVED INFORMATION | ✅ | ❌ MISSING |
| EVENTS (ACTOR UNRESOLVED) | ✅ | ❌ MISSING |
| INVESTIGATION QUESTIONS | ✅ | ❌ MISSING |

---

### 🟡 MEDIUM — Formatting Issues

#### Issue #6: Lost Indentation
V1:
```
  INCIDENT PARTICIPANTS:
    • Reporter (Reporter)
    • Marcus Johnson (Witness)
```

V2:
```
INCIDENT PARTICIPANTS:
• Reporter (Reporter)
• Marcus Johnson (Witness)
```

All indentation (2-space and 4-space) is stripped.

---

#### Issue #7: Lost Sub-structure in REFERENCE DATA
V1:
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

V2:
```
Date: January 15th, 2026
Time: 11:30 PM
Location: Main Street and Oak Avenue, the Riverside Cafe, St. Mary's Hospital
Badge Number: 4821, 5539, 2103
Name: Jenkins, Sarah Mitchell, Marcus Johnson, Patricia Chen...
```

All sub-structure lost, merged into flat key-value pairs.

---

#### Issue #8: Section Headers Merged with Content
V2 has headers merged with content on same line:
```
ℹ️ 11 camera-friendly events identified. ℹ️ Fully normalized: Actor + action + object...
```
Should be separate lines.

---

#### Issue #9: Missing ACCOUNT SUMMARY Section Header
V1 had:
```
══════════════════════════════════════════════════════════════════════
                         ACCOUNT SUMMARY
══════════════════════════════════════════════════════════════════════
```

V2 is missing this entirely.

---

### 🟢 LOW — Minor Formatting

#### Issue #10: Section Title Changes
| V1 | V2 |
|----|----|
| REPORTER CHARACTERIZATIONS (Subjective Language) | REPORTER DESCRIPTIONS (CHARACTERIZATIONS) |
| SELF-REPORTED STATE (ACUTE - During Incident) | SELF-REPORTED STATE (ACUTE) |
| SELF-REPORTED INJURY (Physical) | SELF-REPORTED STATE (INJURY) |
| CONTESTED ALLEGATIONS (unverifiable) | CONTESTED ALLEGATIONS |
| REPORTER INFERENCES (Intent/Motive Claims) | REPORTER INFERENCES |

---

#### Issue #11: Different Quote Speaker Format
V1: `• Officer Jenkins said: You should have just cooperated...`
V2: `• He yelled: STOP RIGHT THERE!`

Speaker resolution failing — using pronouns instead of names.

---

#### Issue #12: Missing Legend in Timeline
V1 had:
```
Legend: ⏱️=explicit time  ⟳=relative time  ○=inferred  ⚠️=gap needs investigation
📊 Timeline: 102 events across 4 day(s)
    ⏱️ Explicit times: 1  ⟳ Relative: 15  ○ Inferred: 86
```

V2 just has:
```
📊 Timeline: 102 events
```

---

## ROOT CAUSES

| Issue | Root Cause | File(s) |
|-------|-----------|---------|
| First-person pronouns | Pronoun replacement not running | `p70_render.py` or `nnrt/policy/` |
| Word truncation | Regex pattern error | Neutralization transforms |
| Missing sections | Not implemented in structured_v2.py | `nnrt/render/structured_v2.py` |
| Lost indentation | Renderer not adding indentation | `nnrt/render/structured_v2.py` |
| Quote fragments in items | Items extraction bug | `nnrt/passes/p37_extract_items.py` |
| Speaker resolution | Resolution logic broken | `nnrt/passes/p36_resolve_quotes.py` |
| Header merging | Missing newlines | Likely still p72 or rendering |

---

## PRIORITY FIXES

1. **CRITICAL: Event extraction** — Events are fundamentally broken
2. **CRITICAL: First-person neutralization** — "I/me/my" → "Reporter"  
3. **CRITICAL: Word truncation** — Find and fix regex
4. **HIGH: Missing sections** — Implement in structured_v2.py
5. **HIGH: Items extraction** — Stop polluting with quote fragments
6. **MEDIUM: Indentation** — Restore 2-space/4-space formatting
7. **MEDIUM: RAW NARRATIVE** — Split disclaimer onto separate line

---

*Analysis updated: 2026-01-19 16:15*
