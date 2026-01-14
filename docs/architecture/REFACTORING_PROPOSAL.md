# NNRT Architecture Review & Refactoring Proposal

**Date:** 2026-01-13  
**Status:** ✅ COMPLETE

---

## Summary

The refactoring is complete. All four phases have been implemented:
- ✅ Phase 1: IR Enhancement
- ✅ Phase 2: Context Annotation Pass
- ✅ Phase 3: Policy Conditions
- ✅ Phase 4: Render Simplification

### 1. Scattered Context Logic

We have context-aware exceptions in **multiple places**:

```python
# In p70_render.py - hardcoded charge context check
charge_contexts = [
    "charged with", "charge of", "accused of"...
]
is_charge_context = any(ctx_phrase in segment.text.lower() for ctx_phrase in charge_contexts)

# In p70_render.py - hardcoded physical action exceptions
physical_actions = [
    "say", "speak", "breathe", "move"...
]
if "tried to" in phrase_lower:
    for action in physical_actions:
        if action in phrase_lower:
            return None  # Preserve
```

**Problems:**
- Same logic could be needed in multiple passes
- Exception lists are duplicated/hardcoded
- No central source of truth for "what contexts preserve what"
- Changes require editing Python code, not configuration

---

### 2. Poor Pass Communication

Passes don't share understanding of what they've already processed:

```
p20_tag_spans: Tags "assaulting" as LEGAL_CONCLUSION
p50_policy:    Flags "assaulting an officer" for preservation
p70_render:    Removes "assaulting" because it sees LEGAL_CONCLUSION span
               (doesn't know policy already said to preserve it)
```

**The fix we applied was a hack:**
```python
# Check if policy already decided to preserve this
is_charge_context = any(...)  # Re-analyze the text!
```

We're **re-analyzing** instead of **communicating**.

---

### 3. Competing Transformation Systems

We have TWO systems that can transform text:

1. **Policy Engine** — YAML rules, centralized, auditable
2. **Span-based Logic** — Python code, scattered, implicit

They operate sequentially but don't coordinate:

```python
# p70_render.py
rendered, decisions = engine.apply_rules(segment.text)  # Policy first
for span in segment_spans:
    if span.label == SpanLabel.LEGAL_CONCLUSION:
        rendered = _remove_phrase(...)  # Span logic second - may UNDO policy!
```

---

### 4. No Semantic Context in IR

The IR stores facts but not **relationships**:

```python
class Segment:
    text: str
    # No field for: "this segment describes a charge"
    # No field for: "this segment contains a direct quote"
    # No field for: "this segment is testimony vs official report"
```

Context is lost, so each pass must re-derive it.

---

## 🟢 Proposed Architecture

### Principle 1: Policy Is The Single Source Of Truth

**All transformation decisions should flow through the policy engine.**

```
           ┌─────────────────────────────────────────┐
           │           POLICY ENGINE                 │
           │  - YAML rules with context awareness    │
           │  - Returns DECISIONS, not transforms    │
           │  - Explicit preserve/transform/flag     │
           └─────────────┬───────────────────────────┘
                         │
                         ▼
           ┌─────────────────────────────────────────┐
           │           DECISION APPLICATOR           │
           │  - Applies decisions to text            │
           │  - Respects priority/conflict rules     │
           │  - No independent logic                 │
           └─────────────────────────────────────────┘
```

Span-based classification feeds INTO the policy engine, not around it:

```
NLP Sensing → Span Classification → Policy Evaluation → Decision Application
    ↓              ↓                      ↓                    ↓
  spaCy      LEGAL_CONCLUSION    "preserve if charge"    Apply to text
            INTENT_ATTRIBUTION   "transform if harm"
```

---

### Principle 2: Rich Semantic Context In IR

Add context annotations to segments:

```python
class SegmentContext(Enum):
    DIRECT_QUOTE = "direct_quote"        # Exact words spoken
    REPORTED_SPEECH = "reported_speech"  # Paraphrased speech
    CHARGE_DESCRIPTION = "charge"        # Legal charge/accusation
    PHYSICAL_DESCRIPTION = "physical"    # Observable physical events
    EMOTIONAL_STATEMENT = "emotional"    # Emotional impact/reaction
    TIMELINE = "timeline"                # Temporal sequence
    FACTUAL_OBSERVATION = "factual"      # Neutral observation

class Segment:
    id: str
    text: str
    contexts: list[SegmentContext]  # NEW: What kind of content is this?
    quote_depth: int = 0            # NEW: Are we inside quotes?
    source_type: str = "narrator"   # NEW: Who said this?
```

Then policy rules can reference context:

```yaml
- id: legal_term_in_charge
  match:
    patterns: ["assault", "battery"]
  condition:
    context_includes: charge_description
  action: preserve  # Don't transform if it's describing a charge

- id: legal_term_standalone
  match:
    patterns: ["assault", "battery"]
  condition:
    context_excludes: charge_description
  action: flag  # Transform if it's a conclusion
```

---

### Principle 3: Pass Communication Via Context

The `TransformContext` should carry decisions, not just data:

```python
@dataclass
class TransformContext:
    # Current
    segments: list[Segment]
    spans: list[SemanticSpan]
    
    # NEW: Decisions made by earlier passes
    decisions: list[TransformDecision]
    
    # NEW: Context tags for segments
    segment_contexts: dict[str, list[SegmentContext]]
    
    # NEW: Protected ranges (don't touch these)
    protected_ranges: list[tuple[str, int, int]]  # (segment_id, start, end)
```

A pass can check: "Has another pass already decided about this?"

```python
def render(ctx: TransformContext) -> TransformContext:
    for segment in ctx.segments:
        for span in segment_spans:
            # Check if already protected
            if ctx.is_protected(segment.id, span.start_char, span.end_char):
                continue  # Skip - already handled
            
            # Check if policy already decided
            existing = ctx.get_decision_for_span(span.id)
            if existing and existing.action == "preserve":
                continue  # Skip - policy said preserve
```

---

### Principle 4: Context Annotation Pass

Add a new pass that annotates context BEFORE policy evaluation:

```
p00_normalize
p10_segment
p20_tag_spans
p25_annotate_context  ← NEW: Detect charge, quotes, physical, etc.
p30_extract_identifiers
p40_build_ir
p50_policy            ← Uses context annotations
p60_augment_ir
p70_render            ← Respects policy decisions, no independent logic
p80_package
```

The `p25_annotate_context` pass would:

1. Detect charge/accusation language patterns
2. Detect direct quote boundaries
3. Detect physical action descriptions
4. Tag segments with context enums

This centralizes all the "context understanding" in one place.

---

## 📋 Refactoring Tasks

### Phase 1: IR Enhancement (Low Risk)

1. Add `SegmentContext` enum to `ir/enums.py`
2. Add `contexts` field to `Segment` model
3. Add `protected_ranges` to `TransformContext`
4. Add helper methods: `is_protected()`, `protect_range()`, `get_decision_for_span()`

### Phase 2: Context Annotation Pass (Medium Risk)

1. Create `p25_annotate_context.py`
2. Move charge detection logic there
3. Move quote boundary detection there
4. Move physical action detection there
5. Update pipeline to include new pass

### Phase 3: Policy Enhancement (Medium Risk)

1. Add `condition` support to YAML rules
2. Support `context_includes` / `context_excludes`
3. Update policy engine to evaluate conditions
4. Migrate hardcoded exceptions to YAML conditions

### Phase 4: Render Simplification (High Risk)

1. Remove span-based transformation logic from render
2. Render only applies policy decisions
3. Add fallback: if no decision, preserve original
4. Test all cases for regressions

---

## ⚠️ Migration Strategy

Don't refactor all at once. Incremental approach:

1. **Add** new infrastructure alongside old
2. **Migrate** one exception type at a time
3. **Test** after each migration
4. **Remove** old code only after validation

Example order:
1. Charge context → YAML condition
2. Physical attempt → YAML condition
3. Quote preservation → YAML condition
4. Then remove hardcoded lists from Python

---

## 🧪 Test Strategy

Each migration needs:

1. **Before/After tests** — Same input should produce same output
2. **Edge case tests** — Ensure no regressions
3. **New capability tests** — Verify new conditions work

Add to `tests/test_context_aware.py`:

```python
def test_assault_in_charge_preserved():
    """Assault in charge context should be preserved."""
    
def test_assault_standalone_transformed():
    """Assault as accusation should be transformed."""
    
def test_tried_to_say_preserved():
    """Physical attempt to speak should be preserved."""
    
def test_tried_to_hurt_transformed():
    """Intent to harm should be transformed."""
```

---

## 🎯 Success Criteria

After refactoring:

1. **No hardcoded context lists in Python code**
2. **All exceptions defined in YAML**
3. **Passes communicate via context, not re-analysis**
4. **Single transformation authority (policy engine)**
5. **All 40+ tests still pass**
6. **Extreme cases still produce correct output**

---

## 📅 Timeline Estimate

| Phase | Effort | Risk |
|-------|--------|------|
| Phase 1: IR Enhancement | 1-2 hours | Low |
| Phase 2: Context Pass | 2-3 hours | Medium |
| Phase 3: Policy Enhancement | 2-3 hours | Medium |
| Phase 4: Render Simplification | 1-2 hours | High |
| Testing & Validation | 2-3 hours | - |
| **Total** | **8-13 hours** | - |

---

## 🤔 Open Questions

1. Should context be at segment level or span level?
2. How do we handle nested contexts (quote inside charge)?
3. Should policy rules have access to NLP features (POS tags)?
4. Do we need a "confidence" for context annotations?

---

## Next Steps

1. **Review this proposal** — Does it make sense?
2. **Prioritize** — What to do first?
3. **Start Phase 1** — Low risk, high value
4. **Commit current state** — Snapshot before refactor
