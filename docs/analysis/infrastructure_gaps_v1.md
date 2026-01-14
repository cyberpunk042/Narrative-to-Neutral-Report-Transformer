# Infrastructure Gaps Analysis v1

**Date**: 2026-01-14  
**Status**: ✅ COMPLETED (All 5 Gaps)  
**Priority**: Pre-Alpha Blocker → Resolved

## Overview

Testing with complex narratives revealed five categories of infrastructure gaps. **All five** have been fixed with proper architectural solutions.

---

## Gap 1: Overlapping Rule Matches (Critical)

### Symptom
`"thug cop"` → `"officer officer"`

### Root Cause
Policy engine applies rules **independently** to each matched pattern:
- Rule `inflam_derogatory_officer`: `thug` → `officer` (priority 80)
- Rule `inflam_cop`: `cop` → `officer` (priority 60)

Both fire on adjacent words, creating double replacement.

### Required Infrastructure Change
**Option A: Span Consumption Model**
- When a rule matches, mark the character span as "consumed"
- Lower-priority rules skip consumed spans
- Requires tracking matched spans in policy evaluation

**Option B: Compound Phrase Priority**
- Add compound phrase rules with higher priority
- `"thug cop"` → `"officer"` (priority 100) fires FIRST
- Individual word rules don't fire on already-matched content

**Option C: Collision Detection Pass**
- New pass between policy evaluation and rendering
- Detects overlapping replacements and merges them
- More complex but more flexible

### Recommendation
**Option A** is cleanest - modify `p50_evaluate_policy.py` to track consumed spans.

---

## Gap 2: Context-Aware Intent Attribution (Critical)

### Symptom
`"just wanted to get home"` → `"just appeared to get home"`

### Root Cause
Rule `intent_wanted_to` replaces ALL instances of `"wanted to"`:
```yaml
patterns: ["wanted to", "meant to"]
replacement: "appeared to"
```

But `"wanted to [benign verb]"` is NOT intent attribution - it's describing the narrator's own desire.

### Required Infrastructure Change
**Option A: Negative Lookahead in Patterns**
- Extend pattern matching to support regex lookahead
- `"wanted to (?!go|get|leave|return|walk|run|sleep|eat)"`
- Requires pattern engine enhancement

**Option B: Exempt-Following-Words in Rule Definition**
```yaml
- id: intent_wanted_to
  match:
    patterns: ["wanted to"]
    exempt_when_followed_by: ["go", "get", "leave", "return", "home", "sleep", "eat"]
  action: replace
  replacement: "appeared to"
```
- Cleaner, more maintainable
- Requires YAML schema extension

**Option C: Semantic Role Check**
- Check if the subject of "wanted to" is the narrator (first-person)
- If so, preserve (describing own desires)
- Requires entity linking in policy evaluation

### Recommendation
**Option B** is most maintainable - extend rule schema to support `exempt_when_followed_by`.

---

## Gap 3: Post-Replacement Punctuation Cleanup (Medium)

### Symptom
`"the brutal, psychotic cops"` → `"the, psychotic cops"`

### Root Cause
Removing `"brutal"` leaves a dangling comma. No cleanup pass exists.

### Required Infrastructure Change
**New Pass: `p75_cleanup_punctuation.py`**

Run AFTER rendering, BEFORE packaging:
1. Fix double spaces: `"  "` → `" "`
2. Fix dangling commas: `", "` at word boundaries → proper spacing
3. Fix orphaned punctuation: `"., "` `", ,"` etc.
4. Fix sentence boundary issues

### Implementation Sketch
```python
def cleanup_punctuation(ctx: TransformContext) -> TransformContext:
    text = ctx.rendered_text
    
    # Double spaces
    text = re.sub(r'  +', ' ', text)
    
    # Dangling comma after article
    text = re.sub(r'\b(the|a|an),\s+', r'\1 ', text, flags=re.IGNORECASE)
    
    # Double punctuation
    text = re.sub(r'([.,!?])([.,!?])', r'\1', text)
    
    ctx.rendered_text = text
    return ctx
```

### Recommendation
Add new pass `p75_cleanup_punctuation` to pipeline. Low risk, high impact.

---

## Gap 4: Grammar-Aware Reframing (Medium)

### Symptom
`"flashing aggressively"` → `"flashing described as aggressively"`

### Root Cause
Reframe template `"described as {original}"` doesn't account for:
- Adverb vs adjective
- Position in sentence
- Grammatical role

### Required Infrastructure Change
**Option A: Separate Templates by Part-of-Speech**
```yaml
- id: interp_aggressive
  match:
    patterns: ["aggressive"]         # adjective
  reframe_template: "described as {original}"
  
- id: interp_aggressively
  match:
    patterns: ["aggressively"]       # adverb
  reframe_template: "in a manner described as aggressive"
```

**Option B: Template Macros**
```yaml
reframe_template: "{if_adverb:in a manner described as|described as} {original_adj_form}"
```
- Requires template engine enhancement

**Option C: Dedicated Reframe Logic**
- Move reframing out of simple templates
- Use Python function that receives POS tag
- Most flexible but more complex

### Recommendation
**Option A** is simplest - split rules by part of speech. More rules but clearer.

---

## Gap 5: Quote Boundary Protection (Medium)

### Symptom
Quotes getting mangled or modifications leaking into quoted content.

### Root Cause
1. Quote detection regex may miss edge cases
2. Policy rules fire on content inside quotes despite `preserve_quotes` rule
3. Priority 1000 should protect, but quote detection may fail

### Required Infrastructure Change
**Phase 1: Audit Quote Detection**
- Review `preserve_quotes` regex: `"\".*?\""`
- Test with: nested quotes, unicode quotes, escaped quotes

**Phase 2: Pre-Mark Quote Spans**
- In `p20_tag_spans`, explicitly mark quote boundaries as protected
- Tag spans with `SpanLabel.DIRECT_QUOTE`
- Policy engine checks span labels before applying rules

**Phase 3: Quote-Aware Segmentation**
- Ensure segmentation doesn't split mid-quote
- Add segment boundary constraint at quote boundaries

### Recommendation
Start with Phase 1 audit. If regex is fine, move to Phase 2 span marking.

---

## Implementation Priority

| Gap | Severity | Effort | Priority |
|-----|----------|--------|----------|
| Gap 1: Span Consumption | Critical | Medium | P0 |
| Gap 2: Context-Aware Intent | Critical | Medium | P0 |
| Gap 3: Punctuation Cleanup | Medium | Low | P1 |
| Gap 4: Grammar-Aware Reframe | Medium | Medium | P1 |
| Gap 5: Quote Protection | Medium | Medium | P2 |

---

## Proposed Implementation Order

### Sprint 1: Core Fixes (P0)
1. **Gap 1**: Add span consumption tracking to `p50_evaluate_policy.py`
2. **Gap 2**: Extend rule schema with `exempt_when_followed_by`

### Sprint 2: Quality Fixes (P1)  
3. **Gap 3**: Add `p75_cleanup_punctuation.py` pass
4. **Gap 4**: Split reframe rules by POS

### Sprint 3: Robustness (P2)
5. **Gap 5**: Audit and harden quote protection

---

## Acceptance Criteria

After fixes, the following test case MUST pass:

**Input:**
```
The thug cop behind the wheel was clearly looking for trouble. I just wanted to get home. The brutal, psychotic officers flashing aggressively. He yelled "STOP RIGHT THERE!"
```

**Expected Output:**
```
The officer behind the wheel was clearly looking for trouble. I just wanted to get home. The psychotic officers flashing in a manner described as aggressive. He yelled "STOP RIGHT THERE!"
```

**Transformations:**
- `thug cop` → `officer` (single replacement)
- `wanted to get home` → preserved (benign intent)
- `brutal,` → removed with comma cleanup
- `aggressively` → reframed grammatically
- Quote preserved exactly

---

## Implementation Summary (2026-01-14)

### ✅ Gap 1: Token Group Merging (COMPLETED)
**File**: `nnrt/policy/engine.py`

Implemented `_group_adjacent_matches()` method that:
- Groups adjacent matches with the SAME replacement target
- Merges groups into single transformations
- Generic solution - works for ANY adjacent words targeting same output

### ✅ Gap 2: Exempt Following Words (COMPLETED)
**Files**: `nnrt/policy/models.py`, `nnrt/policy/engine.py`, `nnrt/policy/loader.py`, `nnrt/policy/rulesets/base.yaml`

- Added `exempt_following: list[str]` to `RuleMatch` model
- Added `_check_exempt_following()` method to policy engine
- Updated loader to parse new YAML field
- Updated `intent_wanted_to` rule with exempt verbs

### ✅ Gap 3: Punctuation Cleanup Pass (COMPLETED)
**File**: `nnrt/passes/p75_cleanup_punctuation.py`

New pass added to pipeline that fixes:
- Double spaces
- Dangling commas after articles
- Double punctuation
- Space before punctuation
- Orphaned commas

### ✅ Gap 4: Grammar-Aware Reframes (COMPLETED)
**File**: `nnrt/policy/rulesets/base.yaml`

Split interpretation rules by part-of-speech:
- Adjectives: `"described as {original}"`
- Adverbs: `"in a manner described as [adjective]"`

### ✅ Gap 5: Quote Protection (COMPLETED)
**File**: `nnrt/policy/engine.py`

Implemented protected ranges for PRESERVE rules:
- When processing matches, first identify all PRESERVE matches (quotes, timestamps)
- Build list of protected character ranges
- Filter out any subsequent matches that fall inside protected ranges
- Added `_is_protected()` helper method

Result: Content inside quotes is now fully preserved verbatim.

---

## Test Results

All **205 tests pass** after implementing all 5 Gaps. ✅

