# Infrastructure Gaps Analysis v2

**Date**: 2026-01-14  
**Status**: 🔍 COMPREHENSIVE SWEEP COMPLETE  
**Priority**: Alpha Quality  
**Patterns Found**: 35 problematic patterns in output

## Overview

After fixing the initial 5 infrastructure gaps, a comprehensive pattern sweep of the "Very Huge" test case revealed **35 additional patterns** that should be transformed but are not. These represent vocabulary/rule gaps, not architectural issues.

---

## Gap Summary by Category

| Category | Count | Severity | Examples |
|----------|-------|----------|----------|
| **Inflammatory** | 6 | High | terrorize, corrupt, thugs, whitewash |
| **Legal Conclusions** | 6 | High | torture, crimes, abuse of power |
| **Certainty Language** | 3 | Medium | clearly, absolutely, completely |
| **Extreme Modifiers** | 4 | Medium | horrifying, devastating, massive |
| **Intent Attribution** | 3 | Medium | conspiring, enjoying, mocking |
| **Manner Adverbs** | 2 | Medium | menacingly, brutally |
| **Loaded Verbs** | 3 | Medium | screaming, slammed, assaulting |
| **Similes** | 1 | Medium | like a maniac |
| **Logical Conclusions** | 1 | Medium | which proves |
| **Context-Dependent** | 6 | Low | racism, misconduct, civil rights |

---

## Category Details

### 1. Inflammatory Language (6 patterns) - HIGH PRIORITY

These words are emotionally charged and should be softened:

| Pattern | Current | Suggested Transform |
|---------|---------|---------------------|
| `terrorize` | unchanged | `affecting` or `impacting` |
| `corrupt` | unchanged | `described as problematic` |
| `impunity` | unchanged | remove |
| `thugs` | only in compound | `individuals` |
| `whitewash` | unchanged | `internal review` |
| `cover-up` | unchanged | `disputed findings` |

### 2. Legal Conclusions (6 patterns) - HIGH PRIORITY

Attribution of criminality or legal status:

| Pattern | Current | Suggested Transform |
|---------|---------|---------------------|
| `torture` | unchanged | `alleged mistreatment` |
| `crimes` | unchanged | `alleged conduct` |
| `criminal behavior` | unchanged | `alleged conduct` |
| `innocent` | unchanged | (context-dependent) |
| `illegal` | unchanged | `allegedly unlawful` |
| `abuse of power` | unchanged | `alleged misconduct` |

### 3. Certainty Language (3 patterns) - MEDIUM PRIORITY

Words asserting subjective certainty as fact:

| Pattern | Current | Suggested Transform |
|---------|---------|---------------------|
| `clearly` | unchanged | `appeared to` or remove |
| `absolutely` | unchanged | remove |
| `completely` | unchanged | remove or soften |

### 4. Extreme Modifiers (4 patterns) - MEDIUM PRIORITY

Hyperbolic descriptors:

| Pattern | Current | Suggested Transform |
|---------|---------|---------------------|
| `horrifying` | unchanged | `distressing` |
| `devastating` | unchanged | `significant` |
| `massive` | unchanged | `large` or `extensive` |
| `complete and total` | unchanged | `complete` |

### 5. Intent Attribution (3 patterns) - MEDIUM PRIORITY

Attributing mental states to others:

| Pattern | Current | Suggested Transform |
|---------|---------|---------------------|
| `conspiring` | unchanged | `discussing` |
| `enjoying` | unchanged | `described as appearing to enjoy` |
| `mocking` | unchanged | `described as dismissive` |

### 6. Manner Adverbs (2 patterns) - MEDIUM PRIORITY

| Pattern | Current | Suggested Transform |
|---------|---------|---------------------|
| `menacingly` | unchanged | `in a manner described as threatening` |
| `brutally` | should be removed | VERIFY - may be bug |

### 7. Loaded Verbs (3 patterns) - MEDIUM PRIORITY

| Pattern | Current | Suggested Transform |
|---------|---------|---------------------|
| `screaming` | unchanged | `speaking loudly` |
| `slammed` | unchanged | `moved forcefully against` |
| `assaulting` | should be transformed | VERIFY - may be bug |

### 8. Similes (1 pattern) - MEDIUM PRIORITY

| Pattern | Current | Suggested Transform |
|---------|---------|---------------------|
| `like a maniac` | unchanged | remove entirely |
| `like a criminal` | `like a alleged criminal` | remove entirely |

### 9. Context-Dependent (6 patterns) - LOW PRIORITY

These may be appropriate depending on context:

| Pattern | Context | Decision |
|---------|---------|----------|
| `racism` | Factual accusation | May preserve |
| `misconduct` | Legal filing | Appropriate |
| `civil rights violations` | Legal filing | Appropriate |
| `wanted to` | With benign verb | Already handled |
| `lie` | In quote | Preserved correctly |
| `fabricated` | Outside quote | Should transform |

---

## Implementation Plan

### Phase 1: Bug Verification
First, check if these are rule gaps or bugs:
- `brutally` - should be caught by `inflam_manner` rule
- `assaulting` - should be caught by assault rules

### Phase 2: High Priority Rules (20 new rules)

```yaml
# Inflammatory
- id: inflam_terrorize
  patterns: ["terrorize", "terrorizing"]
  action: replace
  replacement: "affecting"

- id: inflam_corrupt
  patterns: ["corrupt", "corrupted"]
  action: reframe
  reframe_template: "described as {original}"

- id: inflam_impunity
  patterns: ["with impunity"]
  action: remove

- id: inflam_whitewash
  patterns: ["whitewash"]
  action: replace
  replacement: "internal review"

- id: inflam_coverup
  patterns: ["cover-up", "coverup"]
  action: replace
  replacement: "disputed process"

# Legal Conclusions
- id: legal_torture
  patterns: ["torture"]
  action: reframe
  reframe_template: "alleged {original}"

- id: legal_crimes
  patterns: ["crimes", "their crime"]
  action: reframe
  reframe_template: "alleged conduct"

- id: legal_abuse
  patterns: ["abuse of power"]
  action: replace
  replacement: "alleged misconduct"
```

### Phase 3: Medium Priority Rules (15 new rules)

```yaml
# Certainty Language
- id: cert_clearly
  patterns: ["clearly"]
  action: remove

- id: cert_absolute
  patterns: ["absolutely", "completely"]
  condition:
    context_excludes: ["quantitative"]  # "completely empty" is fine
  action: remove

# Extreme Modifiers
- id: extreme_horrifying
  patterns: ["horrifying", "horrific"]
  action: replace
  replacement: "distressing"

# Intent
- id: intent_conspiring
  patterns: ["conspiring", "plotting", "scheming"]
  action: replace
  replacement: "discussing"

# Similes
- id: simile_maniac
  patterns: ["like a maniac", "like a criminal", "like an animal", "like a thug"]
  action: remove

# Loaded Verbs
- id: verb_screaming
  patterns: ["screaming"]
  action: replace
  replacement: "speaking loudly"

- id: verb_slammed
  patterns: ["slammed"]
  action: replace
  replacement: "moved forcefully against"
```

---

## Priority Matrix

| Priority | Category | Rules Needed | Effort |
|----------|----------|--------------|--------|
| P0 | Inflammatory | 6 | Low |
| P0 | Legal Conclusions | 6 | Low |
| P1 | Certainty | 3 | Low |
| P1 | Extreme Modifiers | 4 | Low |
| P1 | Intent | 3 | Low |
| P1 | Manner Adverbs | 2 | Low |
| P1 | Loaded Verbs | 3 | Low |
| P1 | Similes | 2 | Low |
| P2 | Context-Dependent | 2 | Medium |

**Total**: ~30 new rules needed

---

## Acceptance Criteria

After implementing all rules, the output should have:
- Zero inflammatory terms (terrorize, corrupt, thugs, etc.)
- Zero unsoftened legal conclusions (torture, crimes, etc.)
- Zero certainty language (clearly, obviously, etc.)
- Zero extreme modifiers (horrifying, devastating, etc.)
- All quotes still preserved verbatim
- All timestamps/identifiers preserved

---

## Files to Modify

| File | Changes |
|------|---------|
| `nnrt/policy/rulesets/base.yaml` | Add ~30 new rules |
| `nnrt/passes/p75_cleanup_punctuation.py` | Minor boundary fixes |
