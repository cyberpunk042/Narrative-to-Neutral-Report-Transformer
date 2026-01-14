# Infrastructure Gaps v3 - Grammar & Transformation Bugs

**Date**: 2026-01-14  
**Status**: 🔍 INVESTIGATION COMPLETE  
**Priority**: Critical (Breaks output quality)
**Total Bugs**: 16 identified, categorized into 8 root causes

---

## Bug Summary

| # | Bug | Severity | Root Cause | Fix Complexity |
|---|-----|----------|------------|----------------|
| 1 | Verb tense lost | 🔴 Critical | Replace doesn't preserve conjugation | Medium |
| 2 | Double 'against' | 🔴 Critical | Replacement contains word in context | Low |
| 3 | Word corruption (`use of forcerce`) | 🔴 Critical | Double rule match overlapping | Medium |
| 4 | Word truncation (`cers`) | 🔴 Critical | Token group merging malfunction | Medium |
| 5 | Missing space (`criminalconduct`) | 🟠 Severe | Adjacent replacements concatenate | Low |
| 6 | Missing 'at' (`speaking dismissively me`) | 🟠 Severe | Replacement incomplete | Low |
| 7 | Article mismatch (`a alleged`) | 🟠 Severe | No article adjustment pass | Low |
| 8 | Narrator action transformed | 🟡 Moderate | No first-person exclusion | Medium |
| 9 | Sentence boundary (`causey 15th`) | 🔴 Critical | Replacement overlaps sentence | Medium |
| 10 | Simile leaves orphan word | 🟡 Moderate | `like a criminal` → `criminal` | Low |
| 11 | Infinitive form broken | 🟡 Moderate | `to terrorize` → `to affecting` | Low |
| 12 | Double removal (`very  `) | 🟡 Moderate | Multiple certainty words | Low |

---

## Detailed Analysis

### Bug 1: Verb Tense Lost

**Example:**
```
IN:  "I screamed in pain"
OUT: "I speaking loudly in pain"  ❌
```

**Root Cause:** The `verb_screaming` rule replaces `screamed/screaming` with static text `speaking loudly`.

**Current Rule:**
```yaml
- id: verb_screaming
  patterns: ["screaming", "screamed"]
  action: replace
  replacement: "speaking loudly"  # Loses tense!
```

**Fix Options:**
1. **Split by tense**: `screamed` → `spoke loudly`, `screaming` → `speaking loudly`
2. **Use reframe with template**: `{past_form} loudly` where past_form is computed
3. **Remove rule**: Keep loaded verbs as factual

---

### Bug 2: Double 'against'

**Example:**
```
IN:  "slammed me against the car"
OUT: "moved forcefully against me against the car"  ❌
```

**Root Cause:** The replacement `moved forcefully against` already contains `against`, creating "against ... against".

**Current Rule:**
```yaml
- id: verb_slammed
  patterns: ["slammed"]
  action: replace
  replacement: "moved forcefully against"  # Contains 'against'!
```

**Fix:** Change replacement to not include context words:
```yaml
replacement: "pushed forcefully"  # Or "moved"
```

---

### Bug 3: Word Corruption (`use of forcerce`)

**Example:**
```
IN:  "police brutality incident"
OUT: "police use of forcerce incident"  ❌
```

**Root Cause:** Two rules match overlapping text:
- `le_police_brutality`: "police brutality" → "police use of force"
- `le_brutality`: "brutality" → "use of force"

The second rule matches WITHIN the replacement of the first!

**Evidence:**
```
RULES: ['le_police_brutality', 'le_brutality']  # Both fired!
```

**Fix:** The `le_brutality` rule should NOT fire when `le_police_brutality` already matched. Need **consumed span tracking** for replacements too.

---

### Bug 4: Word Truncation (`protect cers`)

**Example:**
```
IN:  "protect violent cops"
OUT: "protect cers"  ❌
```

**Root Cause:** Token group merging malfunctioning:
```
RULES: ['le_violent_cop', 'le_violent_cop', 'le_violent_modifier', 'le_cop_plural']
```

Multiple overlapping rules are merging incorrectly, leaving `cers`.

**Analysis:**
1. `le_violent_cop` matches "violent cop" → "officer" (fires twice?)
2. `le_violent_modifier` matches "violent" → remove
3. `le_cop_plural` matches "cops" → "officers"

The token group merge is taking partial matches.

**Fix:** Need to debug the token group merging logic in `apply_rules_with_context`.

---

### Bug 5: Missing Space (`alleged criminalconduct`)

**Example:**
```
IN:  "criminal behavior"
OUT: "alleged criminalconduct"  ❌
```

**Root Cause:** Two adjacent replacements:
- `legal_criminal_behavior`: "criminal behavior" → "alleged conduct"
- `legal_criminal_noun`: "criminal" → "alleged criminal"

Both fire and outputs concatenate.

**Fix:** Same as Bug 3 - need span consumption to prevent double-matching.

---

### Bug 6: Missing 'at' (`speaking dismissively me`)

**Example:**
```
IN:  "mocking me"
OUT: "speaking dismissively me"  ❌ (should be "speaking dismissively at me")
```

**Root Cause:** Simple rule error - replacement is incomplete.

**Fix:**
```yaml
- id: intent_mocking
  patterns: ["mocking", "taunting", "ridiculing"]
  action: replace
  replacement: "speaking dismissively at"  # Add 'at'
```

---

### Bug 7: Article Mismatch (`a alleged criminal`)

**Example:**
```
IN:  "not a criminal"
OUT: "not a alleged criminal"  ❌ (should be "an alleged")
```

**Root Cause:** No post-processing to fix "a" → "an" before vowels.

**Fix:** Add to `p75_cleanup_punctuation.py`:
```python
# Fix article before vowels
text = re.sub(r'\ba\s+([aeiouAEIOU])', r'an \1', text)
```

---

### Bug 8: Narrator Action Transformed

**Example:**
```
IN:  "I tried to explain"
OUT: "I appeared to explain"  ❌ (narrator's own action)
```

**Root Cause:** `intent_tried_to` doesn't check if subject is "I".

**Fix Options:**
1. Add `exempt_preceding: ["I", "we"]` to intent rules
2. Add context condition for first-person

---

### Bug 9: Sentence Boundary Corruption (`causey 15th`)

**Example:**
```
IN:  "for absolutely no reason on January 15th"
OUT: "without stated causey 15th"  ❌
```

**Root Cause:** Two rules match with overlap:
- `le_no_reason`: "for absolutely no reason" → "without stated cause"
- `cert_absolutely`: "absolutely" → (remove)

The removal of "absolutely" corrupts "cause on" → "causey".

**Analysis:** The "absolutely" inside "no reason" phrase is being removed AFTER the phrase replacement, corrupting the result.

**Fix:** When a phrase rule matches, the words inside should be protected from further word-level rules.

---

### Bug 10: Simile Leaves Orphan Word

**Example:**
```
IN:  "belongings like a criminal"
OUT: "belongings criminal"  ❌
```

**Root Cause:** 
1. `simile_criminal` removes "like a criminal"
2. But wait - there's no "like a criminal" pattern!
3. Actually `legal_criminal_noun` also fires

**Analysis:**
```
RULES: ['simile_criminal', 'legal_criminal_noun']
```

The simile removes "like a" but leaves "criminal", then `legal_criminal_noun` tries to transform it but something goes wrong.

**Fix:** The simile patterns need to include the target word: `like a criminal` → remove entirely.

---

### Bug 11: Infinitive Form Broken

**Example:**
```
IN:  "will continue to terrorize"
OUT: "will continue to affecting"  ❌
```

**Root Cause:** `terrorize` (infinitive) → `affecting` (gerund). Wrong verb form.

**Fix:** Need tense-aware replacement:
```yaml
- id: inflam_terrorize
  patterns: ["terrorize"]
  action: replace
  replacement: "affect"  # Not "affecting"!
```

And for gerund:
```yaml
- id: inflam_terrorizing
  patterns: ["terrorizing"]
  action: replace
  replacement: "affecting"
```

---

## Priority Matrix

| Priority | Bugs | Description |
|----------|------|-------------|
| P0 | 3, 4, 9 | Double-match corruption - Breaks output badly |
| P1 | 1, 2, 11 | Verb form issues - Grammar broken |
| P2 | 5, 6, 7 | Missing text/articles - Awkward output |
| P3 | 8, 10 | Context sensitivity - Incorrect transforms |

---

## Root Cause Categories

### Category A: Overlapping Rule Matches (Bugs 3, 4, 5, 9, 10)
- **Problem**: Multiple rules fire on same/overlapping text
- **Solution**: When a rule matches, mark those characters as CONSUMED for subsequent rules
- **Affect**: Prevents word-level rules from corrupting phrase-level replacements

### Category B: Verb Form Preservation (Bugs 1, 11)
- **Problem**: Static replacements lose verb conjugation
- **Solution**: Either split rules by tense, or implement tense-aware replacement
- **Complexity**: Medium

### Category C: Replacement Content Issues (Bugs 2, 6)
- **Problem**: Replacement text is wrong or incomplete
- **Solution**: Simple YAML fixes
- **Complexity**: Low

### Category D: Post-Processing Gaps (Bug 7)
- **Problem**: Article agreement not fixed
- **Solution**: Add to cleanup pass
- **Complexity**: Low

### Category E: Context Sensitivity (Bug 8)
- **Problem**: Narrator's own actions transformed
- **Solution**: Add first-person exemption
- **Complexity**: Medium

---

## Recommended Fix Order

### Phase 1: Critical Infrastructure (1-2 hours)
1. Fix overlapping rule consumption (Category A)
2. This will fix bugs 3, 4, 5, 9, 10 automatically

### Phase 2: YAML Fixes (30 min)
3. Fix `verb_slammed` replacement (Bug 2)
4. Fix `intent_mocking` replacement (Bug 6)
5. Split verb rules by tense (Bugs 1, 11)

### Phase 3: Post-Processing (30 min)
6. Add article correction to cleanup pass (Bug 7)

### Phase 4: Context Sensitivity (1 hour)
7. Add first-person exemption mechanism (Bug 8)

---

## Files to Modify

| File | Changes |
|------|---------|
| `nnrt/policy/engine.py` | Fix span consumption for replacements |
| `nnrt/policy/rulesets/_categories/loaded_verbs.yaml` | Split by tense |
| `nnrt/policy/rulesets/_categories/intent_attribution.yaml` | Fix mocking |
| `nnrt/policy/rulesets/_categories/inflammatory_language.yaml` | Fix terrorize |
| `nnrt/passes/p75_cleanup_punctuation.py` | Add article fix |
