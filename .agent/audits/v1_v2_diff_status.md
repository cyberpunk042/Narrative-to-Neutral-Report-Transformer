# V1 vs V2 Diff Status Report
Generated: 2026-01-19 16:50

## Executive Summary

| Category | V1 | V2 Current | Status |
|----------|----|----|--------|
| Structure Match | ✅ | ⚠️ Partial | 70% |
| Content Quality | ✅ | ❌ Poor | 30% |
| Formatting | ✅ | ⚠️ Broken | 50% |
| Newline Preservation | ✅ | ❌ Broken | 20% |

---

## ✅ FIXED Issues (This Session)

### 1. REFERENCE DATA Structure
- **V1**: Had structured sub-sections (INCIDENT DATETIME, SECONDARY LOCATIONS, OFFICER IDENTIFICATION)
- **V2 Before**: Flat key-value pairs
- **V2 After**: ✅ Now matches V1 structure

### 2. ACCOUNT SUMMARY Header
- **V1**: Present with `═══ ACCOUNT SUMMARY ═══` divider
- **V2 Before**: Missing
- **V2 After**: ✅ Added

### 3. Phrasal Verb Conjugation
- **V1**: "ran over", "came out"
- **V2 Before**: "run overred", "come outed"
- **V2 After**: ✅ Fixed with phrasal verb handling

### 4. Leading Whitespace (Partial)
- **V1**: 2-4 space indentation preserved
- **V2 Before**: Stripped to 0 spaces
- **V2 After**: ⚠️ Now 1-2 spaces (p75 still reducing)

---

## ❌ REMAINING Issues

### CRITICAL: Newlines Being Stripped Within Sections

**Symptom**: Bullets within sections are all merged onto 1-3 lines instead of separate lines.

**Example - OBSERVED EVENTS**:
```
V1 (Correct):
  • Officer Jenkins jumped out of the car.
  • Reporter froze in place.
  • Officer Jenkins grabbed Reporter's left arm.

V2 (Broken):
ℹ️ 11 camera-friendly events identified. ℹ️ Fully normalized... • the cops attacked Reporter. • It all started. • Reporter walked...
```

**Affected Sections**:
- OBSERVED EVENTS (all bullets on 1-2 lines)
- SELF-REPORTED STATE sections
- LEGAL ALLEGATIONS
- PRESERVED QUOTES
- REPORTER INFERENCES
- CONTESTED ALLEGATIONS

**Root Cause Investigation**:
- `structured_v2.py` correctly appends each bullet as separate line
- `p72_safety_scrub._clean_artifacts()` preserves newlines (tested ✅)
- `p75_cleanup_punctuation` preserves newlines (tested ✅)
- Something ELSE is joining lines — possibly in the data itself?

---

### 2. Title Not Centered

**V1**: 
```
                        NEUTRALIZED REPORT
```
(~24 spaces of centering)

**V2**:
```
 NEUTRALIZED REPORT
```
(Only 1 space)

---

### 3. Indentation Reduced

| Element | V1 | V2 |
|---------|----|----|
| Sub-headers | 2 spaces | 1 space |
| Bullet points | 4 spaces | 2 spaces |
| Nested content | 4-6 spaces | 2-4 spaces |

**Root Cause**: `p75_cleanup_punctuation` line 39-40:
```python
text = re.sub(r'  +', ' ', text)
```
This collapses 2+ spaces to 1 space globally, including indentation.

---

### 4. OFFICER IDENTIFICATION Missing Officer Names

**V1**:
```
  OFFICER IDENTIFICATION:
    • Sergeant Williams (Badge #2103)
    • Officer Jenkins (Badge #4821)
    • Officer Rodriguez (Badge #5539)
```

**V2**:
```
  OFFICER IDENTIFICATION:
  • Badge #4821
  • Badge #5539
  • Badge #2103
```

---

### 5. Event Content Quality

**V1 Events** (complete sentences):
```
• Officer Jenkins jumped out of the car.
• Reporter froze in place.
• Officer Jenkins grabbed Reporter's left arm.
• Officer Rodriguez searched through Reporter's pockets.
```

**V2 Events** (fragments, wrong actors):
```
• the cops attacked Reporter.
• It all started.
• Reporter walked.
• partner got.
• Officer Jenkins grabbed Reporter's left arm.
```

**Issues**:
- Fragments like "It all started.", "partner got."
- Wrong actor resolution "the cops" instead of specific officer
- First-person pronouns still present in some events
- One event is full V1 verbatim text (newlines stripped)

---

### 6. Missing Sections

**V1 Has, V2 Missing**:
- SOURCE-DERIVED INFORMATION
- EVENTS (ACTOR UNRESOLVED) with validation stats
- INVESTIGATION QUESTIONS section
- Timeline legend and stats

---

### 7. Section Order Differences

Some sections appear in different order or have different groupings.

---

## Recommended Next Steps (Priority Order)

1. **FIX NEWLINE STRIPPING** (Critical)
   - Root cause: Unknown — need to debug actual render output before cleanup
   - Impact: Affects readability of entire document

2. **FIX INDENTATION REDUCTION**
   - Modify `p75_cleanup_punctuation` to preserve leading whitespace
   - Change: Line-by-line processing instead of global regex

3. **IMPROVE EVENT QUALITY**
   - Review p34_extract_events for better actor/verb/target extraction
   - Ensure neutralized_description is properly constructed

4. **ADD MISSING SECTIONS**
   - SOURCE-DERIVED INFORMATION
   - EVENTS (ACTOR UNRESOLVED)
   - INVESTIGATION QUESTIONS

5. **FIX OFFICER IDENTIFICATION**
   - Link badge numbers to officer names in _render_reference_data

---

## Files Modified This Session

| File | Changes |
|------|---------|
| `nnrt/passes/p35_classify_events.py` | Added `_conjugate_past_tense()` with phrasal verb support; rewrote Step 3 to construct neutralized_description from resolved components |
| `nnrt/passes/p72_safety_scrub.py` | Removed global double-space replacement; preserved leading whitespace in line-by-line processing |
| `nnrt/render/structured_v2.py` | Rewrote `_render_reference_data()` for V1-style structure; added ACCOUNT SUMMARY header |

---

## Testing Commands

```bash
# Run stress test
cd /home/jfortin/Narrative-to-Neutral-Report-Transformer
python3 scripts/stress_test.py --input tests/fixtures/stress_test_narrative.txt

# Debug intermediate output
python3 -c "
from nnrt.passes.p72_safety_scrub import _clean_artifacts
# Test with sample text
"
```
