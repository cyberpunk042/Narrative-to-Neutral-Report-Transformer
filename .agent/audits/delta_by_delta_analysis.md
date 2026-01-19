# V1 → V2 Delta-by-Delta Analysis

Every single deviation from V1 is a corruption. This document catalogs each one.

---

## DELTA 1: REFERENCE DATA Section Structure

### V1 (Lines 7-23 in diff):
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

══════════════════════════════════════════════════════════════════════
                         ACCOUNT SUMMARY
══════════════════════════════════════════════════════════════════════
```

### V2 (Lines 24-28 in diff):
```
  Date: January 15th, 2026
  Time: 11:30 PM
  Location: Main Street and Oak Avenue, the Riverside Cafe, St. Mary's Hospital
  Badge Number: 4821, 5539, 2103
  Name: Jenkins, Sarah Mitchell, Marcus Johnson, Patricia Chen...
```

### Deviations:
| # | V1 | V2 | Type |
|---|----|----|------|
| 1.1 | `INCIDENT DATETIME:` header | MISSING | Structure loss |
| 1.2 | `INCIDENT LOCATION:` separate from `SECONDARY LOCATIONS:` | All merged into single `Location:` line | Structure loss |
| 1.3 | `SECONDARY LOCATIONS:` with bullet list | MISSING | Structure loss |
| 1.4 | `OFFICER IDENTIFICATION:` with name + badge format | Replaced with raw `Badge Number:` and separate `Name:` | Structure loss |
| 1.5 | Badge format `(Badge #2103)` | Changed to just `2103` | Format change |
| 1.6 | Officer names linked to badges | Names and badges separated | Data association lost |
| 1.7 | `ACCOUNT SUMMARY` section header | COMPLETELY MISSING | Section loss |

---

## DELTA 2: OBSERVED EVENTS (CAMERA-FRIENDLY) Section

### V1 Context Line (Line 32):
```
ℹ️ Context: Reporter encountered Officer Jenkins and Officer Rodriguez on January 15th, 2026 at approximately 11:30 PM near Main Street and Oak Avenue. Reporter reports feeling frightened during this encounter.
```

### V2 Context Line (Line 33):
```
ℹ️ 11 camera-friendly events identified.
```

### Deviation 2.1:
- V1 has **narrative context** explaining who/what/when/where
- V2 has **just a count** — all context information LOST

---

### V1 Info Line (Line 35):
```
ℹ️ Fully normalized: Actor (entity/class) + action + object. No pronouns, quotes, or fragments.
```

### V2 Info Line (Line 78):
```
ℹ️ Fully normalized: Actor + action + object. No pronouns, quotes, or fragments.
```

### Deviation 2.2:
- V1: `Actor (entity/class)` 
- V2: `Actor`
- Missing: `(entity/class)` clarification

---

### V1 Events (Lines 37-53):
```
  • Officer Jenkins jumped out of the car.
  • Reporter froze in place.
  • Officer Jenkins grabbed Reporter's left arm.
  • Officer Rodriguez searched through Reporter's pockets.
  • Officers slammed Reporter against their patrol car.
  • Officer Rodriguez put handcuffs on Reporter.
  • Marcus Johnson recorded the incident on his phone.
  • Patricia Chen came out onto her porch.
  • Patricia Chen called 911.
  • Sergeant Williams pulled Officers Jenkins and Rodriguez aside.
  • Sergeant Williams came over to Reporter.
  • Sergeant Williams uncuffed Reporter.
  • Reporter went to the emergency room.
  • Amanda Foster documented bruises on both wrists.
  • Officer Rodriguez ran over to Marcus.
  • Reporter filed a formal complaint with the Internal Affairs Division.
  • Sarah Monroe took Reporter's statement.
```

### V2 Events (Lines 80-90):
```
  • when the , cops attacked me 15th, 2026...
  • It all started when I was innocently walking home...
  • when I was innocently walking home...
  • Officer Jenkins, badge number 4821, jumped out of the car and immediately started screaming at me
  • His partner, Officer Rodriguez, badge number 5539, got out of the passenger side and they both approached me with their hands on their weapons, ready to shoot me
  • Officer Jenkins grabbed my left arm ed it behind my back
  • Officer Rodriguez then searched through my pockets without my consent and without any legal justification
  • They then slammed me against their patrol car, and Officer Rodriguez put handcuffs on me so tightly that they cut into my wrists
  • Officer Rodriguez immediately ran over to Marcus and tried to grab his phone, but Marcus stepped back
  • Another witness, an elderly woman named Mrs. Patricia Chen who lives across the street, came out onto her porch and also saw everything
  • Sergeant Williams, badge number 2103, pulled Officers Jenkins and Rodriguez aside and they had a hushed conversation
```

### Event Deviations:

| # | V1 Event | V2 Event | Issue |
|---|----------|----------|-------|
| 2.3 | `Officer Jenkins jumped out of the car.` | `when the , cops attacked me 15th, 2026...` | **CATASTROPHIC**: Wrong event, un-neutralized, garbage |
| 2.4 | `Reporter froze in place.` | `It all started when I was innocently walking home...` | **CATASTROPHIC**: Wrong event, first-person, subjective |
| 2.5 | `Officer Jenkins grabbed Reporter's left arm.` | `when I was innocently walking home...` | **CATASTROPHIC**: Duplicate of above, wrong event |
| 2.6 | (proper clean event) | `Officer Jenkins... jumped out... screaming at me` | **BAD**: "screaming" not neutralized, should be "speaking loudly" |
| 2.7 | (proper clean event) | `...ready to shoot me` | **CATASTROPHIC**: Un-neutralized threat language |
| 2.8 | (proper clean event) | `Officer Jenkins grabbed my left arm ed it behind my back` | **CATASTROPHIC**: Word truncation "twist**ed**" → " ed" |
| 2.9 | (proper clean event) | `without my consent and without any legal justification` | **BAD**: Legal characterization in camera-friendly |
| 2.10 | (proper clean event) | `so tightly that they cut into my wrists` | **BAD**: Subjective characterization |
| 2.11 | V1: Uses "Reporter" | V2: Uses "me", "my", "I" | **CATASTROPHIC**: First-person pronouns not replaced |
| 2.12 | V1: 17 events | V2: 11 events | 6 events MISSING |
| 2.13 | V1: Clean, canonical | V2: Verbose, un-neutralized | Quality regression |

---

## DELTA 3: FOLLOW-UP ACTIONS Section

### V1 (Lines 55-58):
```
OBSERVED EVENTS (FOLLOW-UP ACTIONS)
──────────────────────────────────────────────────────────────────────
  • Reporter went to the emergency room at St. Mary's Hospital immediately after.
  • Detective Sarah Monroe took Reporter's statement
```

### V2:
**SECTION COMPLETELY MISSING**

### Deviation 3.1:
- Entire section with 2 events DELETED

---

## DELTA 4: ITEMS DISCOVERED Section

### V1 (Lines 60-77):
```
ITEMS DISCOVERED (as claimed by Reporter)
──────────────────────────────────────────────────────────────────────
  ℹ️ Items Reporter states were found during search.
  Status: Reporter's account only. No seizure/inventory records attached.

  PERSONAL EFFECTS:
    • phone
    • wallet

  WORK-RELATED ITEMS:
    • work apron that still had some cash tips from my shift

  ❓ UNSPECIFIED SUBSTANCES (Requires Clarification):
    • "some drugs" — term is ambiguous

    ❓ FOLLOW-UP QUESTION: What specific substance(s) were found?
       The term used is vague and could refer to legal medication,
       prescription drugs, or controlled substances.
```

### V2:
```
(Section present in structured output but with corrupted items - quote fragments leaked in)
```

### Deviation 4.1-4.5:
- Categories structure lost
- FOLLOW-UP QUESTION section MISSING
- Quote fragments incorrectly classified as items (seen in earlier output)

---

## DELTA 5: NARRATIVE EXCERPTS Section

### V1 Rejection Reason Format (Lines 96-100):
```
  [Fragment (conjunction start)]
    - While my face was pressed against the cold metal of the car, Officer Jenkins whi...
    - but Officer Jenkins just laughed in my face and said "Sure you did, that's what...
```

### V2 Rejection Reason Format:
```
  [No Valid Actor:Where]
    - where I work as a server
  [No Valid Actor:To]
    - to get home to my apartment
```

### Deviation 5.1:
- V1 rejection reasons: Human-readable (`Fragment (conjunction start)`)
- V2 rejection reasons: Technical/cryptic (`No Valid Actor:Where`)
- Different categorization scheme entirely

---

---

## DELTA 6: SOURCE-DERIVED INFORMATION Section

### V1 (Lines 136-162):
```
SOURCE-DERIVED INFORMATION
──────────────────────────────────────────────────────────────────────
  ⚠️ The following claims require external provenance verification:

  [1] CLAIM: The so-called "robbery suspect" they claimed I matched turned out to be...
      Source: Reporter
      Status: Self-Attested

  [2] CLAIM: found that at least 12 other citizens have filed complaints...
      Source: Reporter
      Status: Self-Attested

  [3] CLAIM: I researched his record.
      Source: Reporter
      Status: Needs Provenance

  [4] CLAIM: Officer Jenkins is a known violent offender...
      Source: Reporter
      Status: Inference

  [5] CLAIM: I am now pursuing legal action...
      Source: Reporter
      Status: Needs Provenance ⚠️

  [6] CLAIM: My attorney, Jennifer Walsh...
      Source: Reporter
      Status: Needs Provenance ⚠️
```

### V2:
**ENTIRE SECTION DELETED — 6 CLAIMS WITH PROVENANCE TRACKING LOST**

---

## DELTA 7: SELF-REPORTED STATE Sections

### V1 Structure:
```
SELF-REPORTED STATE (ACUTE - During Incident)
  • Reporter reports: I was absolutely terrified in complete shock.
  • Reporter reports: I was so scared I froze in place.

SELF-REPORTED INJURY (Physical)
  • Reporter reports: Officer Rodriguez put handcuffs on me so tightly...
  • Reporter reports: I screamed in pain...
  • Reporter reports: I have permanent scars from their torture.
  • Reporter reports: My wrists were bleeding.

SELF-REPORTED STATE (Psychological)
  • Reporter reports: I can no longer walk outside at night...
  • Reporter reports: The psychological trauma...
  • Reporter reports: I now suffer from PTSD...

SELF-REPORTED IMPACT (Socioeconomic)
  • Reporter reports: I've lost my job...

SELF-REPORTED STATE (General)
  • Reporter reports: After holding me against the car...
  • Reporter reports: they kept looking at me...
  • Reporter reports: I was exhausted...
  • Reporter reports: I couldn't hear what they were saying,
```

### V2 (from structured_v2 embedded output):
- Section headers CHANGED: `(ACUTE - During Incident)` → `(ACUTE)`
- Section headers CHANGED: `SELF-REPORTED INJURY (Physical)` → `SELF-REPORTED STATE (INJURY)`
- Section headers CHANGED: `SELF-REPORTED IMPACT (Socioeconomic)` → `SELF-REPORTED STATE (SOCIOECONOMIC)`
- **Prefix "Reporter reports:" REMOVED from all entries**
- **Duplicates introduced**: "I froze in place" appears twice

---

## DELTA 8: REPORTER CHARACTERIZATIONS Section

### V1:
```
REPORTER CHARACTERIZATIONS (Subjective Language)
  • Opinion: when the brutal, psychotic cops viciously attacked me...
  • Opinion: Officer Jenkins is a known violent offender...
  • Opinion: I could tell from her dismissive attitude...
```

### V2:
```
REPORTER DESCRIPTIONS (CHARACTERIZATIONS)
  • when the brutal, psychotic cops viciously attacked me...  (NO PREFIX)
  • The thug cop behind the wheel...
```

### Deviations:
| # | V1 | V2 | Issue |
|---|----|----|-------|
| 8.1 | Section title: `REPORTER CHARACTERIZATIONS (Subjective Language)` | `REPORTER DESCRIPTIONS (CHARACTERIZATIONS)` | Title changed |
| 8.2 | Each entry prefixed with `Opinion:` | No prefix | Structure loss |

---

## DELTA 9: REPORTER INFERENCES Section

### V1 (8 entries):
```
REPORTER INFERENCES (Intent/Motive Claims)
  • Reporter infers: clearly a threat that they would fabricate charges...
  • Reporter infers: He obviously didn't care about my rights...
  • Reporter infers: clearly ready to shoot me for no reason
  • Reporter infers: he intentionally ignored my pleas.
  • Reporter infers: he wanted to inflict maximum damage
  • Reporter infers: clearly enjoying my suffering
  • Reporter infers: and he just said "Not today"
  • Reporter infers: He was mocking me.
```

### V2:
```
REPORTER INFERENCES
  • He obviously didn't care about my rights or the law.  (NO PREFIX)
  • clearly -- reporter perceived threat -- for no reason
  • he -- reporter infers intentional action -- my pleas.
```

### Deviations:
| # | V1 | V2 | Issue |
|---|----|----|-------|
| 9.1 | Title: `(Intent/Motive Claims)` | No subtitle | Title change |
| 9.2 | Prefix: `Reporter infers:` | No prefix | Structure loss |
| 9.3 | Clean text | Inline tags like `-- reporter perceived threat --` | Content corruption |

---

## DELTA 10: CONTESTED ALLEGATIONS Section

### V1 (13 entries):
```
CONTESTED ALLEGATIONS (unverifiable)
  ⚠️ Unverified: The police department refuses to release his full disciplinary record...
  ⚠️ Unverified: She said my injuries were consistent with "significant physical force"...
  ⚠️ Unverified: I later found out that her call was mysteriously "lost"...
```

### V2:
```
CONTESTED ALLEGATIONS
  • I later found out that her call was mysteriously "lost" in the system, which proves there's a going on.
  • It was obvious they were conspiring about how to -- reporter alleges cover-up -- their crimes.
```

### Deviations:
| # | V1 | V2 | Issue |
|---|----|----|-------|
| 10.1 | Title: `(unverifiable)` | No subtitle | Title change |
| 10.2 | Prefix: `⚠️ Unverified:` | Bullet `•` only | Structure loss |
| 10.3 | "there's a massive cover-up going on" | "there's a going on" | **WORD TRUNCATION** |
| 10.4 | Clean text | Inline `-- reporter alleges cover-up --` tags | Content corruption |

---

## DELTA 11: MEDICAL FINDINGS Section

### V1:
```
MEDICAL FINDINGS (as reported by Reporter)
  ℹ️ Medical provider statements cited by Reporter
  Status: Cited (no medical record attached)

  • She documented bruises on both wrists, a sprained left shoulder...
```

### V2:
```
MEDICAL FINDINGS (as reported by Reporter)
  • was treated by Dr. Amanda Foster
  • She documented bruises...
  • My therapist, Dr. Michael Thompson, has diagnosed me with Post-Traumatic Stress Disorder directly caused by this -- reporter characterizes conduct as ity -- incident.
```

### Deviations:
| # | V1 | V2 | Issue |
|---|----|----|-------|
| 11.1 | 1 clean entry | 3 messy entries | Different content |
| 11.2 | — | `was treated by Dr. Amanda Foster` | Fragment, no actor |
| 11.3 | — | `-- reporter characterizes conduct as ity --` | **WORD TRUNCATION**: "brutal**ity**" → "ity" |

---

## DELTA 12: PRESERVED QUOTES Section

### V1 (6 quotes, properly resolved):
```
PRESERVED QUOTES (SPEAKER RESOLVED)
  • Officer Jenkins said: You should have just cooperated, now you're going to pay for wasting our time.
  • Reporter said: I just got off work at the Riverside Cafe! You can call my manager Sarah Mitchell to verify!
  • Reporter said: What's the problem, officer? I haven't done anything wrong.
  • Rodriguez said: You better delete that video or you're next.
  • I screamed in pain and said: You're hurting me! Please stop!
  • Reporter said: Am I being charged with anything?
```

### V2:
```
PRESERVED QUOTES (SPEAKER RESOLVED)
  • He yelled: STOP RIGHT THERE! DON'T YOU DARE MOVE!
  • Reporter asked: What's the problem, officer? I haven't done anything wrong.
  • they say: Sure you did, that's what they all say.
  • Rodriguez threatened: You better delete that video or you're next.
  • him saying: You better delete that video or you're next.
  • Reporter asked: Am I being charged with anything?
  • he said: Not today
  • She said: significant physical force
  • She said: We'll investigate
```

### Deviations (CATASTROPHIC):
| # | V1 | V2 | Issue |
|---|----|----|-------|
| 12.1 | `Officer Jenkins said:` | `He yelled:` | **Speaker NOT resolved** |
| 12.2 | `Reporter said:` | `they say:` | **GARBAGE attribution** |
| 12.3 | — | `him saying:` | **GARBAGE attribution** |
| 12.4 | — | `he said:` | **Speaker NOT resolved** |
| 12.5 | — | `She said:` | **Speaker NOT resolved** |
| 12.6 | `Officer Jenkins said: You should have just cooperated...` | **MISSING** | Quote completely lost |
| 12.7 | 6 entries | 9 entries but worse quality | Regression |

---

## DELTA 13: QUOTES (SPEAKER UNRESOLVED) Section

### V1 (7 entries with diagnostics):
```
  ❌ "Three months later, I received a letter stating that my comp..."
      Issues: No speaker specified

  ❌ "The so-called "robbery suspect" they claimed I matched turne..."
      Issues: No speaker specified
  ...
  📊 Quote Validation: 10/17 passed (58%)
```

### V2:
```
  ❌ "You're hurting me! Please stop!"
      Reason: no_speaker_attribution
  ❌ "Sure you did, that's what they all say."
      Reason: no_speaker_attribution
  ...
  (NO VALIDATION STATS)
```

### Deviations:
- Different quotes in unresolved list (regression)
- Format changed from `Issues:` to `Reason:`
- `📊 Quote Validation` stats **REMOVED**

---

## DELTA 14: EVENTS (ACTOR UNRESOLVED) Section

### V1 (10 examples + diagnostics):
```
EVENTS (ACTOR UNRESOLVED)
  ⚠️ These events could not be validated for neutral rendering:

  ❌ when the brutal, psychotic cops viciously attacked me...
      Issues: Actor contains characterization: 'the brutal, psychotic cops'

  ❌ It all started when I was innocently walking home...
      Issues: Actor is not a proper noun: 'It all'
  ...
  📊 Event Validation: 49/102 passed (48%)
  ⚠️ Validated events list disabled pending event extraction fixes
```

### V2:
**ENTIRE SECTION DELETED**

---

## DELTA 15: RECONSTRUCTED TIMELINE Section

### V1 (well-formatted, neutralized):
```
RECONSTRUCTED TIMELINE
Events ordered by reconstructed chronology. Day offsets show multi-day span.

  ┌─── INCIDENT DAY (Day 0) ───
  │
  │  ○ Officer Jenkins yelled
  │  ○ Reporter froze in place
  │  ○ Reporter asked him politely...
  │  ○ Reporter screamed in pain and said...
  │  ⟳ [then] Officer Jenkins was fishing through Reporter's belongings
  ...
  Legend: ⏱️=explicit time  ⟳=relative time  ○=inferred  ⚠️=gap needs investigation

  📊 Timeline: 102 events across 4 day(s)
      ⏱️ Explicit times: 1  ⟳ Relative: 15  ○ Inferred: 86
```

### V2:
```
RECONSTRUCTED TIMELINE
Events ordered by reconstructed chronology.

┌─── INCIDENT DAY (Day 0) ───
│
│ [around 11:30 PM] It all started when I was innocently walking home...
│ when the cops attacked me for absolutely no reason o...
│ when I was innocently walking home...
│ where I work as a server
│ to get home to my apartment
│ Out of nowhere, this unmarked police cruiser came screeching...
...
(NO LEGEND)
📊 Timeline: 102 events
```

### Deviations:
| # | V1 | V2 | Issue |
|---|----|----|-------|
| 15.1 | Uses "Reporter" | Uses "I", "my", "me" | **First person NOT replaced** |
| 15.2 | "Officer Jenkins yelled" | "when the cops attacked me" | **UN-NEUTRALIZED** |
| 15.3 | "Reporter froze in place" | "It all started when I was innocently walking" | **UN-NEUTRALIZED, WRONG** |
| 15.4 | Has legend | **No legend** | Structure loss |
| 15.5 | "Day offsets show multi-day span" | Not present | Info loss |
| 15.6 | Stats: `Explicit: 1, Relative: 15, Inferred: 86` | Just count | Stats loss |
| 15.7 | Clean entries | Fragments like "where I work as a server" | Garbage entries |

---

## DELTA 16: INVESTIGATION QUESTIONS Section

### V1 (7 questions):
```
INVESTIGATION QUESTIONS
Auto-generated questions for investigator follow-up:

  🟠 [HIGH] Injury Detail
     Can you describe the injury and any medical treatment received?
     Context: "they both approached me with their hands on their..."

  🟠 [HIGH] Injury Detail
     Can you describe the injury and any medical treatment received?
     Context: "I screamed in pain..."
  ...
  📊 Question Summary: 7 total
      🟠 High Priority: 6
```

### V2:
**ENTIRE SECTION DELETED — 7 INVESTIGATION QUESTIONS LOST**

---

## DELTA 17: RAW NEUTRALIZED NARRATIVE Section (CATASTROPHIC)

### V1 (proper prose narrative):
```
RAW NEUTRALIZED NARRATIVE (AUTO-GENERATED)
──────────────────────────────────────────────────────────────────────
⚠️ This is machine-generated neutralization. Review for accuracy.

I was frightened and in shock when the officers made physical contact with me 
-- reporter states no cause was given -- on January 15th, 2026 at around 11:30 
PM near the corner of Main Street and Oak Avenue. It all started when I was 
walking home from my job at the Riverside Cafe where I work as a server...

[CONTINUES FOR ~4000 CHARS OF PROPERLY NEUTRALIZED PROSE]
```

### V2:
```
RAW NEUTRALIZED NARRATIVE (AUTO-GENERATED)
──────────────────────────────────────────────────────────────────────
⚠️ This is machine-generated neutralization. Review for accuracy.

══════════════════════════════════════════════════════════════════════ 
NEUTRALIZED REPORT ══════════════════════════════════════════════════
PARTIES ──────────────────────────────────────────────────────────────
INCIDENT PARTICIPANTS: • Reporter (Reporter) • Marcus Johnson (Witness)
[...ENTIRE STRUCTURED REPORT EMBEDDED ON SINGLE LINE...]
```

### Deviations (CATASTROPHIC):
| # | V1 | V2 | Issue |
|---|----|----|-------|
| 17.1 | Prose narrative | ENTIRE STRUCTURED REPORT EMBEDDED | **DOUBLE RENDERING BUG** |
| 17.2 | "frightened" | "terrified" | **Neutralization regression** |
| 17.3 | "officers" | "cops" | **Neutralization regression** |
| 17.4 | Multi-line readable | SINGLE LINE (newlines stripped) | **Format corruption** |
| 17.5 | Report ends cleanly | Report contains itself recursively | **INFINITE NESTING** |

---

## SUMMARY: COMPLETE DEVIATION COUNT

| Category | Count |
|----------|-------|
| **Sections COMPLETELY DELETED** | 4 |
| -- SOURCE-DERIVED INFORMATION | 6 claims lost |
| -- EVENTS (ACTOR UNRESOLVED) | Diagnostics lost |
| -- INVESTIGATION QUESTIONS | 7 questions lost |
| -- OBSERVED EVENTS (FOLLOW-UP ACTIONS) | 2 events lost |
| **Section headers CHANGED** | 8+ |
| **Prefixes REMOVED** | 5+ sections |
| **Word truncation bugs** | 3+ ("ity", "ed", "going on") |
| **Speaker resolution BROKEN** | 5+ quotes |
| **First-person not replaced** | 50+ occurrences |
| **Un-neutralized content in camera-friendly** | 10+ |
| **RAW NARRATIVE CORRUPTION** | ENTIRE SECTION |
| **Inline tag pollution** | 20+ |
| **Duplicate entries** | 5+ |
| **Missing validation stats** | 4+ |

---

## ROOT CAUSE ANALYSIS (Preliminary)

1. **p90_render_structured** is embedding the ENTIRE structured output into `ctx.rendered_text`, which then gets embedded into the RAW NEUTRALIZED NARRATIVE section — **DOUBLE RENDERING**

2. **structured_v2.py** is missing 4+ sections that V1's renderer had

3. **Camera-friendly event classification** is allowing un-neutralized events through

4. **Quote speaker resolution** is broken

5. **Word neutralization transforms** have regex bugs causing mid-word truncation

6. **Timeline uses raw events** instead of neutralized versions

---

*Analysis complete. Every deviation documented.*
- REPORTER CHARACTERIZATIONS: Label changes
- REPORTER INFERENCES: Format changes
- CONTESTED ALLEGATIONS: Format changes
- MEDICAL FINDINGS: Corruption
- PRESERVED QUOTES: **COMPLETELY BROKEN**
- EVENTS (ACTOR UNRESOLVED): **MISSING IN V2**
- RECONSTRUCTED TIMELINE: Un-neutralized content
- INVESTIGATION QUESTIONS: **MISSING IN V2**
- RAW NEUTRALIZED NARRATIVE: **CATASTROPHIC CORRUPTION** (entire structured report embedded on single line)

---

## INITIAL DELTA COUNT (First 100 lines of diff)

| Category | Count |
|----------|-------|
| Missing sections | 3+ |
| Structure/format loss | 10+ |
| Un-neutralized content passing through | 15+ |
| Word truncation bugs | 1+ |
| First-person pronoun failures | 10+ |
| Wrong events in camera-friendly | 3+ |

**Verdict**: V2 is not usable. Hundreds of deviations from V1.

---

*Continuing analysis in subsequent sections...*
