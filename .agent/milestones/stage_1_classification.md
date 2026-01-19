# Stage 1: Classification Layer Unification

## Objective

Move ALL classification logic from the renderer and scattered passes into a unified classification layer in the pipeline. Extend the Policy Engine to support classification rules alongside transformation rules.

**Outcome**: Classification decisions are made ONCE in the pipeline and stored on atoms. The renderer reads pre-classified atoms - no classification code in renderer.

---

## Current State

### Classification Logic Currently in Renderer (structured.py)

| Function/Logic | Lines | What It Does | Should Move To |
|----------------|-------|--------------|----------------|
| `is_strict_camera_friendly()` | 424-553 | 6-rule camera-friendly check | `p35_classify_events` |
| `neutralize_for_observed()` | 391-422 | Strip interpretive words | `p54_neutralize` |
| `is_follow_up_event()` | 564-567 | Detect post-incident actions | `p35_classify_events` |
| `is_source_derived()` | 569-572 | Detect research/conclusions | `p35_classify_events` |
| `_is_medical_provider_content()` | 1125-1134 | Route medical content | `p35_classify_events` |
| Timeline pronoun resolution | 1650-1697 | Resolve He/She/They | `p43_resolve_actors` |
| Quote speaker resolution | 1316-1400 | Resolve quote speakers | `p36_resolve_quotes` |

### Classification Patterns Currently Hardcoded

| Pattern Set | Location | Count | Purpose |
|-------------|----------|-------|---------|
| `INTERPRETIVE_DISQUALIFIERS` | structured.py:339 | ~45 | Disqualify from camera-friendly |
| `FOLLOW_UP_PATTERNS` | structured.py:359 | ~8 | Detect follow-up events |
| `SOURCE_DERIVED_PATTERNS` | structured.py:367 | ~12 | Detect source-derived content |
| `INTERPRETIVE_STRIP_WORDS` | structured.py:376 | ~30 | Words to neutralize |
| `CONJUNCTION_STARTS` | structured.py:445 | ~12 | Fragment detection |
| `VERB_STARTS` | structured.py:461 | ~25 | Fragment detection |
| `INTERPRETIVE_BLOCKERS` | structured.py:543 | ~15 | Content blockers |

### Classification Logic in Pipeline Passes

| Pass | What It Classifies |
|------|-------------------|
| `p27_epistemic_tag` | Epistemic type (self_report, inference, etc.) |
| `p32_extract_entities` | Entity role (partial) |
| `p48_classify_evidence` | Evidence type |
| `p72_safety_scrub` | Safety patterns (runs AFTER render!) |

---

## Target State

### New Classification Passes

```
Pipeline Order:
  ...
  p32_extract_entities   (existing - add Entity classification)
  p34_extract_events     (existing)
  p35_classify_events    (NEW - camera-friendly, follow-up, fragment)
  p36_resolve_quotes     (NEW - speaker resolution)
  p43_resolve_actors     (existing - add pronoun resolution)
  ...
  p50_policy             (existing - text transformation)
  p54_neutralize         (NEW - apply neutralization, store result)
  ...
```

### Classification Stored on Atoms (from Stage 0)

After classification passes run, atoms have:

```python
# Event
event.is_camera_friendly = True
event.camera_friendly_confidence = 0.95
event.camera_friendly_reason = "passed_all_rules"
event.camera_friendly_source = "p35_classify_events"
event.is_follow_up = False
event.is_fragment = False
event.contains_quote = False
event.contains_interpretive = True
event.interpretive_terms_found = ["brutally"]
event.neutralized_description = "Officer slammed him against the car"
event.neutralization_applied = True

# Entity
entity.is_valid_actor = True
entity.is_named = True
entity.is_named_confidence = 0.9
entity.gender = "male"
entity.gender_confidence = 0.8

# SpeechAct
quote.speaker_resolved = True
quote.speaker_resolution_confidence = 0.85
quote.is_quarantined = False
```

### Renderer Becomes Simple

```python
def render_observed_events(events: List[Event]) -> List[str]:
    """Render events - NO classification logic here."""
    lines = []
    for event in events:
        # Just READ pre-computed classification
        if event.is_camera_friendly and event.camera_friendly_confidence >= 0.7:
            text = event.neutralized_description or event.description
            lines.append(f"  • {text}")
    return lines
```

---

## Design: Extending the Policy Engine

### Current Policy Rule Types

```python
class RuleAction(str, Enum):
    REMOVE = "remove"      # Text transformation
    REPLACE = "replace"    # Text transformation
    REFRAME = "reframe"    # Text transformation
    FLAG = "flag"          # Add diagnostic
    REFUSE = "refuse"      # Refuse to process
    PRESERVE = "preserve"  # Protect from transformation
```

### New Rule Types Needed

```python
class RuleAction(str, Enum):
    # Existing
    REMOVE = "remove"
    REPLACE = "replace"
    REFRAME = "reframe"
    FLAG = "flag"
    REFUSE = "refuse"
    PRESERVE = "preserve"
    
    # NEW: Classification actions
    CLASSIFY = "classify"           # Set a classification field
    DISQUALIFY = "disqualify"       # Mark as not camera-friendly
    DETECT = "detect"               # Detect presence of pattern (boolean)
    STRIP = "strip"                 # Strip words but keep sentence
```

### Classification Rule Schema

```yaml
# In rulesets/structure/camera_friendly.yaml

rules:
  # Rule Type 1: Disqualify (marks is_camera_friendly=False)
  - id: cf_conjunction_start
    category: camera_friendly
    priority: 100
    description: "Disqualify events starting with conjunctions"
    match:
      type: regex
      patterns:
        - "^(but|and|when|which|although|while|because|since|that|where|if|though|unless)\\s"
    action: disqualify
    classification:
      field: is_camera_friendly
      value: false
      reason: "conjunction_start:{matched}"

  # Rule Type 2: Detect (sets boolean flag)
  - id: cf_contains_quote
    category: camera_friendly
    priority: 90
    description: "Detect embedded quotes"
    match:
      type: regex
      patterns:
        - "[\"""]"
    action: detect
    classification:
      field: contains_quote
      value: true

  # Rule Type 3: Strip (neutralization)
  - id: neut_brutal_adverb
    category: neutralization
    priority: 80
    description: "Strip 'brutally' adverb"
    match:
      type: keyword
      patterns: ["brutally"]
    action: strip
    # Result stored in neutralized_description
```

---

## Implementation Plan

### Step 1: Extend Policy Models (models.py)

```python
# Add new action types
class RuleAction(str, Enum):
    # ... existing ...
    CLASSIFY = "classify"
    DISQUALIFY = "disqualify"
    DETECT = "detect"
    STRIP = "strip"

# Add classification output schema
@dataclass
class ClassificationResult:
    field: str              # Which field to set
    value: Any              # What value to set
    reason: Optional[str]   # Why this classification
    confidence: float       # How confident
```

### Step 2: Extend Policy Engine (engine.py)

```python
def apply_classification_rules(
    self,
    text: str,
    atom_type: str,  # "event", "entity", "quote"
) -> List[ClassificationResult]:
    """
    Apply classification rules and return results.
    Does NOT modify atoms - just returns classifications.
    """
    results = []
    
    for rule in self.get_rules_by_action([CLASSIFY, DISQUALIFY, DETECT]):
        matches = self._match_rule(rule, text)
        for match in matches:
            results.append(ClassificationResult(
                field=rule.classification["field"],
                value=rule.classification["value"],
                reason=rule.classification.get("reason", "").format(matched=match.matched_text),
                confidence=rule.confidence or 0.9,
            ))
    
    return results
```

### Step 3: Create p35_classify_events.py

```python
"""
Pass 35 — Event Classification

Applies classification rules to all events, setting:
- is_camera_friendly + reason + confidence
- is_follow_up
- is_fragment
- contains_quote
- contains_interpretive
"""

from nnrt.policy.engine import get_policy_engine

def classify_events(ctx: TransformContext) -> TransformContext:
    engine = get_policy_engine()
    
    for event in ctx.events:
        # Apply classification rules
        results = engine.apply_classification_rules(
            text=event.description,
            atom_type="event"
        )
        
        # Apply results to event fields
        for result in results:
            setattr(event, result.field, result.value)
            # Also set confidence and reason if applicable
            if hasattr(event, f"{result.field}_confidence"):
                setattr(event, f"{result.field}_confidence", result.confidence)
            if hasattr(event, f"{result.field}_reason"):
                setattr(event, f"{result.field}_reason", result.reason)
        
        # Default: if no disqualify rules matched, it passes
        if event.is_camera_friendly is None:
            event.is_camera_friendly = True
            event.camera_friendly_confidence = 0.9
            event.camera_friendly_reason = "passed_all_rules"
        
        event.camera_friendly_source = "p35_classify_events"
    
    return ctx
```

### Step 4: Create p54_neutralize.py

```python
"""
Pass 54 — Neutralization

Applies strip rules to create neutralized versions of text.
Stores results in neutralized_description fields.
"""

def neutralize(ctx: TransformContext) -> TransformContext:
    engine = get_policy_engine()
    
    for event in ctx.events:
        if event.contains_interpretive:
            neutralized = engine.apply_strip_rules(event.description)
            if neutralized != event.description:
                event.neutralized_description = neutralized
                event.neutralization_applied = True
    
    return ctx
```

### Step 5: Create Classification Rule YAML Files

```yaml
# rulesets/structure/camera_friendly.yaml

category: camera_friendly
description: "Rules for camera-friendly event classification"

rules:
  # --- Structural Disqualifiers ---
  
  - id: cf_conjunction_start
    priority: 100
    match:
      type: regex
      patterns:
        - "^(?i)(but|and|when|which|although|while)\\b"
    action: disqualify
    classification:
      field: is_camera_friendly
      value: false
      reason: "conjunction_start"

  - id: cf_verb_start
    priority: 99
    match:
      type: regex
      patterns:
        - "^(?i)(twisted|grabbed|pushed|slammed|found|tried)\\b"
    action: disqualify
    classification:
      field: is_camera_friendly
      value: false
      reason: "verb_start_no_actor"

  # --- Content Detectors ---
  
  - id: cf_detect_quote
    priority: 90
    match:
      type: regex
      patterns:
        - '[""\"]'
    action: detect
    classification:
      field: contains_quote
      value: true

  - id: cf_detect_interpretive
    priority: 89
    match:
      type: keyword
      patterns:
        - "brutal"
        - "brutally"
        - "vicious"
        - "assault"
        - "torture"
    action: detect
    classification:
      field: contains_interpretive
      value: true
```

### Step 6: Migrate Renderer to Read-Only

```python
# BEFORE (in structured.py)
for event in events:
    neutralized = neutralize_for_observed(event.description)  # COMPUTE
    passed, reason = is_strict_camera_friendly(neutralized)   # COMPUTE
    if passed:
        strict_events.append(neutralized)

# AFTER
for event in events:
    if event.is_camera_friendly:  # READ pre-computed
        text = event.neutralized_description or event.description
        strict_events.append(text)
```

### Step 7: Update Pipeline Registration

```python
# In pipeline configuration
PASSES = [
    # ...
    ("p35_classify_events", classify_events),
    # ...
    ("p54_neutralize", neutralize),
    # ...
]
```

---

## Migration Inventory

### Patterns to Migrate to YAML

| From | Pattern Set | To YAML File |
|------|-------------|--------------|
| structured.py:339 | INTERPRETIVE_DISQUALIFIERS | `structure/camera_friendly.yaml` (detect) |
| structured.py:359 | FOLLOW_UP_PATTERNS | `structure/event_category.yaml` (classify) |
| structured.py:367 | SOURCE_DERIVED_PATTERNS | `structure/event_category.yaml` (classify) |
| structured.py:376 | INTERPRETIVE_STRIP_WORDS | `neutralization/strip_words.yaml` (strip) |
| structured.py:445 | CONJUNCTION_STARTS | `structure/camera_friendly.yaml` (disqualify) |
| structured.py:461 | VERB_STARTS | `structure/camera_friendly.yaml` (disqualify) |
| structured.py:543 | INTERPRETIVE_BLOCKERS | `structure/camera_friendly.yaml` (disqualify) |

### Functions to Remove from Renderer

| Function | Replacement |
|----------|-------------|
| `is_strict_camera_friendly()` | Read `event.is_camera_friendly` |
| `neutralize_for_observed()` | Read `event.neutralized_description` |
| `is_follow_up_event()` | Read `event.is_follow_up` |
| `is_source_derived()` | Read atom field |
| `is_camera_friendly()` | Read `event.is_camera_friendly` |

---

## Known Limitations & Trust Considerations

### Classification Rule Limitations

| Rule Type | Known Gaps |
|-----------|-----------|
| Regex patterns | Can't handle semantic meaning, only lexical |
| Keyword matching | Context-dependent words may be misclassified |
| Conjunction detection | "And Officer Jenkins..." should pass but won't |

### Confidence Handling

```python
# When multiple rules apply, combine confidences
def combine_classification_results(results: List[ClassificationResult]) -> ClassificationResult:
    if not results:
        return ClassificationResult(field="is_camera_friendly", value=True, confidence=0.5)
    
    # If any disqualify, use lowest confidence
    disqualifiers = [r for r in results if r.value == False]
    if disqualifiers:
        return min(disqualifiers, key=lambda r: r.confidence)
    
    # All passed - average confidence
    avg_conf = sum(r.confidence for r in results) / len(results)
    return ClassificationResult(field="is_camera_friendly", value=True, confidence=avg_conf)
```

### Fallback Behavior

```python
def classify_event_with_fallback(event: Event, engine: PolicyEngine) -> None:
    try:
        results = engine.apply_classification_rules(event.description, "event")
        apply_results(event, results)
    except Exception as e:
        # Fallback: conservative defaults
        event.is_camera_friendly = False
        event.camera_friendly_confidence = 0.0
        event.camera_friendly_reason = f"classification_error:{e}"
        event.camera_friendly_source = "fallback"
        log.error("classification_failed", event_id=event.id, error=str(e))
```

---

## Testing Strategy

### Unit Tests for Classification Rules

```python
def test_conjunction_start_disqualifies():
    """Events starting with 'but' should be disqualified."""
    result = classify_text("But then he ran away")
    assert result.is_camera_friendly == False
    assert "conjunction_start" in result.camera_friendly_reason

def test_named_actor_qualifies():
    """Events with named actors should qualify."""
    result = classify_text("Officer Jenkins grabbed the wallet")
    assert result.is_camera_friendly == True
    assert result.camera_friendly_confidence >= 0.8

def test_interpretive_detected():
    """Interpretive language should be detected."""
    result = classify_text("Officer brutally slammed him")
    assert result.contains_interpretive == True
    assert "brutally" in result.interpretive_terms_found
```

### Integration Tests

```python
def test_pipeline_populates_classification():
    """Full pipeline should populate classification fields."""
    result = transform("Officer Jenkins grabbed my arm.")
    event = result.events[0]
    
    assert event.is_camera_friendly is not None
    assert event.camera_friendly_source == "p35_classify_events"

def test_renderer_uses_precomputed():
    """Renderer should not re-compute classification."""
    # Mock event with classification already set
    event = Event(
        id="e1",
        description="Test event",
        is_camera_friendly=True,
        camera_friendly_confidence=0.9,
    )
    
    # Renderer should just read the field
    output = render_event(event)
    assert "Test event" in output
```

### Regression Tests

```python
def test_output_unchanged_after_migration():
    """Output should be identical before and after migration."""
    for case in load_golden_cases():
        old_output = transform_with_old_renderer(case.input)
        new_output = transform_with_new_pipeline(case.input)
        
        # Core content should match
        assert_outputs_equivalent(old_output, new_output)
```

---

## Done Criteria

- [x] `RuleAction` extended with CLASSIFY, DISQUALIFY, DETECT, STRIP ✅ (2026-01-18)
- [x] `PolicyEngine.apply_classification_rules()` implemented ✅ (2026-01-18)
- [x] `PolicyEngine.apply_strip_rules()` implemented ✅ (2026-01-18)
- [x] `ClassificationOutput` dataclass added to models ✅ (2026-01-18)
- [x] `_get_replacement()` updated to handle STRIP action ✅ (2026-01-18)
- [x] Span consumption fixed for DETECT/CLASSIFY rules ✅ (2026-01-18)
- [x] `p35_classify_events` pass created and wired ✅ (2026-01-18)
  - Now uses PolicyEngine classification rules from YAML
  - Handles: conjunction starts, verb starts, quotes, interpretive content, follow-ups, actor resolution
  - Includes neutralization (integrated, not separate p54)
- [x] `p54_neutralize` — integrated into p35 (neutralization via apply_strip_rules) ✅
- [x] Classification YAML files created:
  - [x] `_classification/camera_friendly.yaml` ✅ (2026-01-18)
  - [x] `_classification/neutralization.yaml` ✅ (2026-01-18)
- [x] Profile updated to include classification rules ✅ (2026-01-18)
- [x] Policy loader updated to parse classification field ✅ (2026-01-18)
- [x] Event classification fields populated by pipeline ✅ (2026-01-18)
- [x] Event generator uses pre-computed classification ✅ (2026-01-18)
- [x] Renderer classification functions deprecated ✅ (2026-01-18)
  - Added deprecation notices to: neutralize_for_observed, is_strict_camera_friendly, 
    is_camera_friendly, is_follow_up_event, is_source_derived
  - Functions kept for V8 fallback path but marked deprecated
- [ ] Renderer reads pre-computed fields only (deferred — V8 fallback still needed)
- [x] All tests pass ✅ (578 passed, 2026-01-18)
- [x] Golden case outputs unchanged ✅ (2026-01-18)

---

## Dependencies

**Blocked by**: Stage 0 (Atom Schema) - needs classification fields to exist

**Blocks**: 
- Stage 2 (Selection Layer) - needs classified atoms
- Stage 3 (Renderer Simplification) - needs classification out of renderer

---

## Estimated Effort

- Policy Engine extension: 8-12 hours
- New passes (p35, p54): 8-12 hours
- YAML rule files: 4-6 hours
- Renderer migration: 4-8 hours
- Testing: 8-12 hours
- **Total: 2-3 weeks**

---

*Stage 1 Document — 2026-01-18*
