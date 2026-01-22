# V2 Quality Improvement Plan
## Date: 2026-01-21

This plan addresses two high-impact improvements:
1. **Missing Events in OBSERVED EVENTS (STRICT)** - False negatives
2. **RAW NARRATIVE Grammar Quality** - Broken sentence structure

---

# PART 1: Missing Events in OBSERVED EVENTS (STRICT)

## Problem Statement
Currently extracting 14 events, but 5+ camera-friendly events with named actors are being missed.

## Gap Analysis

| # | Missing Event | Source Text | Root Cause |
|---|--------------|-------------|------------|
| 1 | Officer Jenkins **twisted** Reporter's arm | "grabbed my left arm...and **twisted** it behind my back" | Compound actions not parsed |
| 2 | Officer Jenkins **whispered** to Reporter | "Officer Jenkins **whispered** menacingly in my ear" | Contains modifier "menacingly" |
| 3 | Officer Rodriguez **tried to grab** phone | "ran over...and **tried to grab** his phone" | Compound actions not parsed |
| 4 | Officer Jenkins **laughed** at Reporter | "Officer Jenkins just **laughed** in my face" | Unknown - should be extractable |
| 5 | Officers **approached** with hands on weapons | "they both **approached** me with their hands" | Pronoun "they" not resolved |

## Investigation Plan

### Step 1: Trace Event Extraction Pipeline
**Files to examine:**
- `nnrt/passes/p30_extract_events.py` - Primary event extraction
- `nnrt/passes/p35_classify_events.py` - Event classification (camera-friendly check)
- `nnrt/render/event_generator.py` - Event sentence generation

**Questions to answer:**
1. Are these events being extracted at all? (Check ctx.events after p30)
2. Are they being classified as camera-friendly? (Check p35)
3. Are they being filtered in selection? (Check p55)

### Step 2: Check Compound Action Parsing
For "grabbed and twisted", "ran over and tried to grab":
- Is the parser splitting on "and" to extract multiple actions?
- Or treating "grabbed and twisted" as a single event?

### Step 3: Check Modifier Stripping
For "whispered menacingly":
- Is "menacingly" causing the event to be classified as interpretive?
- Can we strip adverbs like "menacingly" before classification?

### Step 4: Check Pronoun Resolution
For "they both approached":
- Does p30 extract this as an event?
- Does pronoun resolution in p28 resolve "they" to "Officers Jenkins and Rodriguez"?

## Implementation Steps

### 1.1 Add Compound Action Splitting
**File:** `nnrt/passes/p30_extract_events.py`
**Change:** When extracting verb phrases, split on " and " to create multiple events
```python
# Current: "grabbed my arm and twisted it" -> 1 event
# Target:  "grabbed my arm and twisted it" -> 2 events
#   Event 1: "grabbed my arm"
#   Event 2: "twisted it" (resolve "it" to "arm")
```

### 1.2 Strip Interpretive Adverbs Before Classification
**File:** `nnrt/passes/p35_classify_events.py`
**Change:** Remove adverbs like "menacingly", "brutally", "deliberately" before camera-friendly check
```python
INTERPRETIVE_ADVERBS = ['menacingly', 'brutally', 'deliberately', 'aggressively', 'violently']
# "whispered menacingly" -> "whispered" (camera-friendly)
```

### 1.3 Add "laughed" to Observable Verbs
**File:** `nnrt/render/event_generator.py` or policy rules
**Change:** Ensure "laughed" is recognized as observable/camera-friendly verb

### 1.4 Improve Pronoun Resolution for Groups
**File:** `nnrt/passes/p28_resolve_pronouns.py`
**Change:** Resolve "they both" to plural named actors when context is clear

## Expected Outcome
- Increase from 14 → 19+ events in OBSERVED EVENTS (STRICT)
- New events:
  - "Officer Jenkins twisted Reporter's arm behind Reporter's back."
  - "Officer Jenkins whispered to Reporter."
  - "Officer Rodriguez tried to grab Marcus's phone."
  - "Officer Jenkins laughed at Reporter."
  - "Officers Jenkins and Rodriguez approached Reporter."

---

# PART 2: RAW NARRATIVE Grammar Quality

## Problem Statement
The neutralized RAW NARRATIVE has broken sentence structure.

## Gap Analysis

| # | Current (Broken) | Expected (Fixed) | Root Cause |
|---|-----------------|------------------|------------|
| 1 | "he -- reporter infers intent to cause harm -- maximum damage" | "he -- reporter infers intent -- inflict maximum damage" | Verb removed by scrub |
| 2 | "-- reporter concludes -- I was and they had no" | "-- reporter concludes Reporter was innocent and they had no" | Pronoun+words stripped |
| 3 | "appeared to grab his phone" | "tried to grab his phone" | Over-neutralization |
| 4 | "spoke loudly in pain" | "cried out in pain" | Awkward replacement |

## Investigation Plan

### Step 1: Trace Neutralization Pipeline
**Files to examine:**
- `nnrt/passes/p60_apply_policy.py` - Policy rule application
- `nnrt/passes/p72_safety_scrub.py` - Final scrubbing
- Policy rules in `nnrt/policy/rulesets/`

**Questions to answer:**
1. What rule is creating "-- reporter infers intent to cause harm --" and removing the verb?
2. Why is "I was completely innocent" becoming "I was and"?
3. What's causing "appeared to" instead of "tried to"?

### Step 2: Check Deletion vs Replacement
Many issues come from REMOVING text rather than REPLACING it:
- When we remove "wanted to hurt me", we need to leave something grammatical
- Current: "because he wanted to hurt me" → "because he -- reporter infers intent --"
- Need: "because he -- reporter infers intent to cause harm --"

### Step 3: Check Pronoun Replacement in Narrative
- "I was completely innocent" should become "Reporter was completely innocent"
- Not just strip "completely innocent" and leave "I was and"

## Implementation Steps

### 2.1 Fix Intent Attribution to Preserve Grammar
**File:** `nnrt/passes/p72_safety_scrub.py` or policy rules
**Change:** When attributing intent phrases, preserve the verb structure
```python
# Current pattern: "wanted to hurt" → "-- reporter infers intent --"
# Fixed pattern:   "wanted to hurt" → "-- reporter infers intent to harm --"
```

### 2.2 Fix "completely innocent" Replacement
**File:** Policy rules or `p72_safety_scrub.py`
**Change:** Replace entire phrase, not partial
```python
# Current: "I was completely innocent" → "I was and"
# Fixed:   "I was completely innocent" → "-- reporter claims innocence --"
# Or:      "I was completely innocent" → "Reporter was not charged"
```

### 2.3 Review "appeared to" Pattern
**File:** Policy rules
**Question:** Is "tried to X" being replaced with "appeared to X"?
**Fix:** Keep "tried to" as it's factual (Reporter is stating they tried)

### 2.4 Fix "spoke loudly" Pattern
**File:** Policy rules
**Change:** "screamed" → "cried out" not "spoke loudly"
```python
# Current: "screamed" → "spoke loudly"
# Better:  "screamed" → "cried out" or just "said loudly"
```

### 2.5 Add Post-Processing Grammar Check
**New pass or enhancement to p75:**
- Detect patterns like "noun + and + nothing"
- Detect "because he + attribution + nothing" 
- Fix incomplete sentences

## Expected Outcome
- RAW NARRATIVE reads as proper English
- No orphaned words after attributions
- Verbs preserved in attributed phrases
- Natural-sounding replacements

---

# Execution Order

## Phase 1: Event Extraction (Estimated: 2-3 hours)
1. [ ] Investigate p30_extract_events.py - understand current compound handling
2. [ ] Investigate p35_classify_events.py - check why whispered/laughed rejected
3. [ ] Implement compound action splitting
4. [ ] Implement interpretive adverb stripping
5. [ ] Test: Verify 5 new events extracted
6. [ ] Run stress test

## Phase 2: Grammar Quality (Estimated: 2-3 hours)
1. [ ] Investigate p72_safety_scrub.py - trace "wanted to hurt" → broken output
2. [ ] Investigate policy rules - find "completely innocent" handling
3. [ ] Fix intent attribution patterns
4. [ ] Fix innocence claim patterns
5. [ ] Fix "appeared to" vs "tried to"
6. [ ] Add grammar post-processing
7. [ ] Test: Verify RAW NARRATIVE reads properly
8. [ ] Run stress test

## Verification Criteria

### For Event Extraction:
- [ ] "Officer Jenkins twisted Reporter's arm" appears in OBSERVED EVENTS
- [ ] "Officer Jenkins whispered to Reporter" appears in OBSERVED EVENTS
- [ ] "Officer Rodriguez tried to grab phone" appears in OBSERVED EVENTS
- [ ] "Officer Jenkins laughed" appears in OBSERVED EVENTS
- [ ] Stress test still passes

### For Grammar:
- [ ] No instances of "-- attribution -- (nothing)"
- [ ] No "he -- X -- maximum damage" broken sentences
- [ ] No "I was and they" fragments
- [ ] RAW NARRATIVE reads as coherent English

