# V2 Improvement Opportunities - Deep Analysis
Generated: 2026-01-19 18:40

## 🔴 HIGH IMPACT ISSUES

### 1. RAW NARRATIVE - Incomplete Neutralization
**Location**: Lines 529+
**Problem**: Several characterizations still present:
- "terrified" (should be "frightened")
- "the cops" (should be "officers")
- "cop behind the wheel" (should be "officer behind the wheel")
- "slammed" (could be "pushed against")

**Example**:
```
V2: "I was terrified and in complete shock when the cops made physical contact"
V1: "I was frightened and in shock when the officers made physical contact"
```

**Fix**: Update `p70_neutralize_text.py` patterns

---

### 2. PRESERVED QUOTES - Missing V1 Quotes
**Location**: Lines 322-331
**Problem**: Some key V1 quotes are missing:
- "You should have just cooperated, now you're going to pay for wasting our time." (Jenkins whisper)
- "I just got off work at the Riverside Cafe!" (Reporter explanation)
- "You're hurting me! Please stop!" (in resolved section)
- "Hey! What are you doing to him?" (Marcus Johnson)
- "There's been a misunderstanding. You can go." (Sgt Williams)

**These are in UNRESOLVED but should be in RESOLVED**

**Fix**: Improve quote speaker detection in `p42_extract_speech_acts.py`

---

### 3. QUOTES (SPEAKER UNRESOLVED) - Should Be Resolvable
**Location**: Lines 333-346
**Problem**: These quotes CAN be attributed from context:
- "You're hurting me!" → **Reporter** (obvious from "I screamed")
- "Hey! What are you doing to him?" → **Marcus Johnson** (he spoke)
- "There's been a misunderstanding" → **Sergeant Williams** (he came over and said)
- "Sure you did, that's what they all say" → **Officer Jenkins** (he laughed and said)

**Fix**: Improve context-based speaker resolution

---

## 🟠 MEDIUM IMPACT ISSUES

### 4. CHARACTERIZATIONS Section - Truncated Entries
**Location**: Lines 268-279
**Problem**: Some entries are truncated/malformed:
```
• Officer Jenkins is a known individual with history with a history of ity complaints
• jumped out of the car like a.   (incomplete)
```

**Fix**: Clean up truncation in `p70_neutralize_text.py`

---

### 5. CONTESTED ALLEGATIONS - Malformed Entries
**Location**: Lines 294-311
**Problem**: Several malformed entries:
```
• there's a going on.  (missing word "cover-up")
• ,these officers will continue to  (leading comma)
```

**Fix**: Clean up extraction in relevant pass

---

### 6. SELF-REPORTED STATE (GENERAL) - Fragment Entries
**Location**: Lines 239-247
**Problem**: Some entries are fragments:
```
• shaking their heads.  (fragment - no actor)
```

**Fix**: Filter out fragments in rendering

---

### 7. MEDICAL FINDINGS - Truncated "ity" Word
**Location**: Line 320
**Problem**:
```
• caused by this -- reporter characterizes conduct as ity -- incident.
```
Should be "brutality" but got truncated

**Fix**: Pattern issue in neutralization

---

## 🟡 LOW IMPACT ISSUES

### 8. Section Title Alignment
| V1 | V2 |
|----|----| 
| SELF-REPORTED STATE (ACUTE - During Incident) | SELF-REPORTED STATE (ACUTE) |
| SELF-REPORTED INJURY (Physical) | SELF-REPORTED STATE (INJURY) |
| REPORTER CHARACTERIZATIONS (Subjective Language) | REPORTER DESCRIPTIONS (CHARACTERIZATIONS) |

### 9. ITEMS - "my shift" Possessive
**Location**: Line 80
```
• work apron that still had some cash tips from my shift
```
Should be "Reporter's shift" for full neutralization

---

## PRIORITY ORDER

1. **QUOTES resolution** (HIGH) - Move unresolved quotes to resolved using context
2. **RAW NARRATIVE neutralization** (HIGH) - Fix "terrified", "cops", "slammed"
3. **Truncation/malformed text** (MEDIUM) - Fix "ity", "going on", fragments
4. **Section titles** (LOW) - Match V1 naming

---

## FILES TO MODIFY

| Issue | Primary File |
|-------|-------------|
| Quote speaker resolution | `nnrt/passes/p42_extract_speech_acts.py` |
| RAW NARRATIVE neutralization | `nnrt/passes/p70_neutralize_text.py` |
| Truncation issues | `nnrt/passes/p70_neutralize_text.py` |
| Section titles | `nnrt/render/structured_v2.py` |
