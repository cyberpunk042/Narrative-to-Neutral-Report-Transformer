# NNRT Quality Analysis — Pipeline Issues

**Date**: 2026-01-15
**Status**: Active Investigation

---

## Executive Summary

The NNRT pipeline is producing incorrect results in several critical areas:

| Issue | Severity | Root Cause | Affected Pass |
|-------|----------|------------|---------------|
| Wrong OBSERVATION classification | **HIGH** | Missing sensory patterns | p22, p27 |
| Pronouns as locations | **HIGH** | NER false positives | p30 |
| Fragmented events | **MEDIUM** | Missing context | p34 |
| Entity role confusion | **MEDIUM** | Weak role inference | p32 |
| No statement grouping | **HIGH** | Missing aggregation | NEW |

---

## Issue 1: OBSERVATION Classification (Critical)

### Problem
Almost nothing is classified as OBSERVATION. The user's example has only 1 observation:
```
• I couldn't hear what they were saying
```

But the input contains many first-person witness statements:
- "I was absolutely terrified"
- "I was so scared I froze in place"
- "I screamed in pain"
- "I asked him politely"

### Root Cause
**`p22_classify_statements.py` and `p27_classify_atomic.py`** only recognize OBSERVATION when:
1. First-person subject ("I", "we"), AND
2. Sensory verb (saw, heard, felt, noticed)

But many witness statements use OTHER patterns:
- "I was [emotional state]" — experiential
- "I asked/said/screamed" — speech acts
- "I froze/ran/moved" — physical reactions

### Current Logic (p22)
```python
OBSERVATION_PATTERNS = [
    r"\bI\s+saw\b",
    r"\bI\s+heard\b",
    r"\bI\s+felt\b",
    # ... only sensory verbs
]
```

### Fix Required
Expand OBSERVATION to include:
1. **Experiential states**: "I was [adjective]" (terrified, scared, exhausted)
2. **Physical reactions**: "I froze", "I jumped", "I fell"
3. **Speech acts**: "I said", "I asked", "I yelled", "I screamed"
4. **Involuntary responses**: "I was crying", "I was shaking"

---

## Issue 2: Pronouns Classified as Locations (Critical)

### Problem
```
Location: January, around, corner, Main Street, Oak Avenue, Riverside, me, their, me, Riverside, me, his, Marcus
```

**"me", "their", "his", "Marcus"** are being classified as locations.

### Root Cause
**`p30_extract_identifiers.py`** uses spaCy NER which has known issues:
1. Mis-classifies pronouns as locations in certain constructions
2. No post-processing filter for common pronouns
3. No stopword list for entities

### Current Code (p30)
```python
type_map = {
    "PERSON": IdentifierType.NAME,
    "GPE": IdentifierType.LOCATION,  # Geopolitical entity
    "LOC": IdentifierType.LOCATION,  # Non-GPE locations
    "FAC": IdentifierType.LOCATION,  # Facilities
}

for ent in doc.ents:
    if ent.label_ in type_map:
        results.append(...)  # NO validation!
```

### Fix Required
1. **Stopword filter**: Skip common pronouns (me, him, her, them, their, his, her, my, your)
2. **Minimum length**: Reject 1-2 character "locations"
3. **POS validation**: Verify entity is actually NOUN/PROPN, not PRON
4. **Context check**: Reject if preceded by preposition indicating not-location

---

## Issue 3: Entity Role Confusion (High)

### Problem
```
AGENT:    4821, 5539, 2103, Sergeant Williams, Officers Jenkins, Officer...
WITNESS:  Jenkins, Sarah Mitchell, Marcus Johnson, Patricia Chen...
```

**Officer Jenkins** appears as both AGENT and WITNESS (impossible).
Badge numbers are classified as separate agents.

### Root Cause
**`p32_extract_entities.py`** has weak role inference:
1. Badge numbers extracted as entities instead of linking to person
2. Duplicate detection not working across different mention forms
3. Role inference too simplistic

### Fix Required
1. **Link badge numbers to people**: "Officer Jenkins, badge number 4821" → Jenkins has badge 4821
2. **Canonical entity merging**: Jenkins = Officer Jenkins = 4821
3. **Stronger role heuristics**:
   - "Officer X" → AUTHORITY
   - "my neighbor X" → WITNESS
   - "I was treated by Dr. X" → AUTHORITY (medical)

---

## Issue 4: Event Fragmentation (Medium)

### Problem
```
• brutal attacked me
• YOU DARE
• you doing What
• You cooperated
```

Events are fragmented, losing subject-verb-object context.

### Root Cause
**`p34_extract_events.py`** extracts verb-based events but:
1. Doesn't capture full SVO triples
2. Quote content bleeding into events
3. No sentence boundary respect

### Fix Required
1. **SVO extraction**: Capture subject + verb + object together
2. **Quote boundary**: Don't extract events from quoted speech
3. **Context window**: Include surrounding words for clarity

---

## Issue 5: No Statement Grouping (Critical/New Feature)

### Problem
User correctly identified: "maybe we need something more advanced and even need to be able to group"

The output shows 80+ individual statements with no logical grouping. A human reader would group them into:

1. **Encounter narrative** (what happened chronologically)
2. **Documented injuries** (medical evidence)
3. **Witnesses and their statements**
4. **Official actions** (filing complaint, IA investigation)
5. **Emotional/psychological impact**

### Current State
No grouping logic exists. Each atomic statement stands alone.

### Fix Required
Implement **semantic clustering** for atomic statements:
1. **Timeline grouping**: Group by temporal indicators
2. **Topic clustering**: Group by semantic similarity
3. **Actor-based grouping**: Group by who is involved
4. **Evidence type grouping**: Physical evidence vs testimony vs official records

---

## Issue 6: Date/Time Identifier Noise

### Problem
```
Date: January 15th, 2026, today, The next day, Three months later, 40s, 28-year-old, PTSD
```

**PTSD**, **40s**, **28-year-old** are not dates.

### Root Cause
Regex patterns and NER are over-matching.

### Fix Required
1. **Validate date formats** more strictly
2. **Reject age patterns**: "XX-year-old" is not a date
3. **Medical/diagnostic terms**: "PTSD" is not a date

---

## Proposed Architecture Improvements

### Tier 1: Quick Fixes (Hours)
1. ✅ Add pronoun stoplist to `p30_extract_identifiers`
2. ✅ Expand OBSERVATION patterns in `p22/p27`
3. ✅ Filter age patterns from DATE

### Tier 2: Medium Fixes (Days)
1. Link badge numbers to person entities
2. Improve event SVO extraction
3. Add quote boundary detection to event extraction

### Tier 3: New Features (Week+)
1. **Statement Grouping System**
   - Semantic clustering pass (new p29_group_statements?)
   - Timeline extraction and ordering
   - Evidence classification
   
2. **Improved Entity Resolution**
   - Coreference resolution within narrative
   - Canonical entity merging
   - Role inference from full context

---

## Test Input for Validation

Use this standard input for testing fixes:

```
I was absolutely terrified and in complete shock when the brutal, psychotic cops 
viciously attacked me for absolutely no reason on January 15th, 2026 at around 
11:30 PM near the corner of Main Street and Oak Avenue.

It all started when I was innocently walking home from my job at the Riverside 
Cafe where I work as a server. I was exhausted after pulling a double shift 
and just wanted to get home to my apartment. Out of nowhere, this unmarked 
police cruiser came screeching up beside me with its lights flashing aggressively.

Officer Jenkins, badge number 4821, jumped out of the car like a maniac and 
immediately started screaming at me. He yelled "STOP RIGHT THERE! DON'T YOU 
DARE MOVE!" I was so scared I froze in place. I asked him politely "What's 
the problem, officer? I haven't done anything wrong."
```

Expected outcomes after fixes:
- **OBSERVATIONS**: "I was terrified", "I was scared", "I froze", "I asked"
- **LOCATIONS**: Main Street, Oak Avenue, Riverside Cafe (NOT me, their, his)
- **ENTITIES**: Reporter (role=REPORTER), Officer Jenkins (role=AUTHORITY, badge=4821)
- **EVENTS**: "Officer Jenkins jumped out of car", "Officer Jenkins yelled at Reporter"

---

## Next Steps

1. **Prioritize** fixes by impact and effort
2. **Implement** Tier 1 quick fixes first
3. **Run** test suite after each fix
4. **Design** statement grouping architecture

---

*Document created: 2026-01-15*
*Owner: NNRT Dev Team*
