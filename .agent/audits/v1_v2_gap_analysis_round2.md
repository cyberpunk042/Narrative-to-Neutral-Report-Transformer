# V1 vs V2 Comprehensive Gap Analysis - Round 2
Generated: 2026-01-19 18:10

## SECTIONS COMPARISON

### V1 Only (Missing in V2):
1. **EVENTS (ACTOR UNRESOLVED)** - Shows events that failed validation with reasons
2. **INVESTIGATION QUESTIONS** - Auto-generated follow-up questions

### Section Title Differences:
| V1 Title | V2 Title | Notes |
|----------|----------|-------|
| SELF-REPORTED STATE (ACUTE - During Incident) | SELF-REPORTED STATE (ACUTE) | Minor difference |
| SELF-REPORTED INJURY (Physical) | SELF-REPORTED STATE (INJURY) | V2 uses STATE |
| SELF-REPORTED STATE (Psychological) | SELF-REPORTED STATE (PSYCHOLOGICAL) | Case difference |
| SELF-REPORTED IMPACT (Socioeconomic) | SELF-REPORTED STATE (SOCIOECONOMIC) | V1 uses IMPACT |
| REPORTER CHARACTERIZATIONS (Subjective Language) | REPORTER DESCRIPTIONS (CHARACTERIZATIONS) | Different wording |
| REPORTER INFERENCES (Intent/Motive Claims) | REPORTER INFERENCES | V1 has more detail |
| CONTESTED ALLEGATIONS (unverifiable) | CONTESTED ALLEGATIONS | V1 has clarifier |

---

## PRESERVED QUOTES ISSUES

### V1 (Better Quality):
```
• Officer Jenkins said: You should have just cooperated, now you're going to pay for wasting our time.
• Reporter said: I just got off work at the Riverside Cafe! You can call my manager Sarah Mitchell to verify!
• Reporter said: What's the problem, officer? I haven't done anything wrong.
• Rodriguez said: You better delete that video or you're next.
```

### V2 (Issues):
```
• He yelled: STOP RIGHT THERE! DON'T YOU DARE MOVE!         <- "He" not resolved to Officer Jenkins
• they say: Sure you did, that's what they all say.         <- "they" not resolved
• Rodriguez threatened: You better delete that video...     <- DUPLICATE
• him saying: You better delete that video...               <- DUPLICATE
• he said: Not today                                        <- "he" not resolved
• She said: significant physical force                      <- "She" not resolved to Dr. Foster
• She said: We'll investigate                               <- "She" not resolved to Detective Monroe
```

**Issues:**
1. Pronouns not resolved to named speakers
2. Duplicate quotes appearing
3. Missing key quotes that V1 has (Jenkins whisper)

---

## MISSING SECTIONS IN V2

### 1. EVENTS (ACTOR UNRESOLVED)
V1 shows events that failed validation with clear reasons:
```
❌ when the brutal, psychotic cops viciously attacked me...
    Issues: Actor contains characterization: 'the brutal, psychotic cops'
```

This provides transparency about what was filtered out.

### 2. INVESTIGATION QUESTIONS
V1 auto-generates follow-up questions:
```
🟠 [HIGH] Injury Detail
   Can you describe the injury and any medical treatment received?
   Context: "My wrists were bleeding."
```

Very useful for investigators.

---

## QUALITY DIFFERENCES

### PRESERVED QUOTES
| Aspect | V1 | V2 |
|--------|----|----|
| Speaker resolution | Named (Officer Jenkins) | Pronoun (He) |
| Duplicates | None | Multiple duplicates |
| Key quotes | Has Jenkins whisper | Missing |

### RAW NARRATIVE
| Aspect | V1 | V2 |
|--------|----|----|
| "brutally" | Neutralized | Still present |
| "slammed" | Changed to "pushed" | Still "slammed" |
| "this unmarked police cruiser" | "Out of nowhere, this..." | "this unmarked police cruiser" |

---

## PRIORITY FIX ORDER

### HIGH Priority:
1. **PRESERVED QUOTES pronoun resolution** - Resolve "He", "She", "they" to named speakers
2. **Remove duplicate quotes** - Same quote appearing multiple times

### MEDIUM Priority:
3. **Add EVENTS (ACTOR UNRESOLVED) section** - Show what was filtered and why
4. **Add INVESTIGATION QUESTIONS section** - Auto-generated follow-up

### LOW Priority:
5. **Section title alignment** - Match V1 naming conventions
6. **RAW NARRATIVE remaining characterizations** - "brutally", "slammed" should be neutralized

---

## FILES TO MODIFY

| Issue | File |
|-------|------|
| Quote pronoun resolution | `nnrt/render/structured_v2.py` - `_render_preserved_quotes` |
| Duplicate quotes | `nnrt/render/structured_v2.py` - `_render_preserved_quotes` |
| Actor unresolved section | `nnrt/render/structured_v2.py` - Add new function |
| Investigation questions | `nnrt/render/structured_v2.py` - Add new function |
