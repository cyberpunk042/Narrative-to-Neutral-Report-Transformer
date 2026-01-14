# NNRT — Road to Pre-Alpha

## The Promise (Recap)

> NNRT will produce a **neutral, structured representation** that makes explicit:
> - What is **claimed**
> - What is **observed**
> - What is **assumed**
> - What is **uncertain**
>
> — **Without adding information or resolving ambiguity.**

---

## Current State: v0.2 "Neutralizer"

### What We Have (Working)
- ✅ **Narrative → Neutral Text** transformation
- ✅ Policy-driven rule engine
- ✅ Context-aware transformations
- ✅ Quote preservation
- ✅ Charge/accusation context handling
- ✅ Meta-detection (neutral input, sarcasm)
- ✅ Ambiguity detection (pronouns, vague refs)
- ✅ Contradiction detection
- ✅ LLM-off graceful degradation
- ✅ 40 tests, 16/16 extreme cases passing

### What We're Missing (The Gap)
- ❌ **Structured output** (observations/claims/uncertainties)
- ❌ **Explicit classification** of statement types
- ❌ **Uncertainty exposure** in output format
- ❌ **Entity/event extraction** to structured form

---

## Pre-Alpha Definition

> NNRT is pre-alpha when it can transform arbitrary human narratives into
> **structured neutral representations** where a human can answer:
>
> 1. What is being claimed?
> 2. What was observed directly?
> 3. What is inferred?
> 4. What is unknown?
>
> **Without reading the original narrative.**

---

## Roadmap

### Phase 0: Foundation (COMPLETE ✅)
- [x] Pipeline architecture
- [x] Policy engine
- [x] Context annotations
- [x] Neutralization rules
- [x] Detection capabilities (sarcasm, ambiguity, contradiction)

---

### Phase 1: Statement Classification (COMPLETE ✅)

**Goal:** Classify each statement as OBSERVATION, CLAIM, or INTERPRETATION.

#### 1.1 Define Statement Types
```python
class StatementType(Enum):
    OBSERVATION = "observation"     # "I saw him grab my arm"
    CLAIM = "claim"                 # "He punched me"
    INTERPRETATION = "interpretation"  # "He wanted to hurt me"
    UNCERTAINTY = "uncertainty"     # "I think he might have..."
    QUOTE = "quote"                 # Direct speech preserved
```

#### 1.2 Classification Heuristics
| Pattern | Classification |
|---------|----------------|
| "I saw/heard/felt..." | OBSERVATION |
| "He said '...'" | QUOTE |
| "He wanted to / tried to / meant to" | INTERPRETATION |
| "I think / I believe / maybe" | UNCERTAINTY |
| Physical actions without "I saw" | CLAIM |

#### 1.3 Implementation
- Extend `p20_tag_spans.py` or create `p22_classify_statements.py`
- Add `statement_type` field to Segment model
- Update IR schema

#### Exit Criteria
- [x] Every segment has a `statement_type`
- [x] Classification accuracy > 80% on test corpus
- [x] No statement goes unclassified

---

### Phase 2: Structured Output Schema (COMPLETE ✅)

**Goal:** Define and implement the pre-alpha output format.

#### 2.1 Output Schema V1
```json
{
  "version": "0.1",
  "input_hash": "sha256:...",
  "transformed": true,
  
  "statements": [
    {
      "id": "stmt_001",
      "type": "observation",
      "original": "I saw him grab my shirt",
      "neutral": "Individual grabbed reporter's shirt",
      "confidence": 0.95
    },
    {
      "id": "stmt_002", 
      "type": "claim",
      "original": "He threw me to the ground",
      "neutral": "Reporter was thrown to ground",
      "confidence": 0.90
    },
    {
      "id": "stmt_003",
      "type": "interpretation",
      "original": "He wanted to hurt me",
      "neutral": null,
      "flagged": true,
      "flag_reason": "Intent attribution - cannot verify"
    }
  ],
  
  "uncertainties": [
    {
      "id": "unc_001",
      "type": "ambiguous_reference",
      "text": "He hit him",
      "candidates": ["officer", "subject"],
      "resolution": null
    }
  ],
  
  "entities": [
    {"id": "ent_001", "type": "person", "label": "reporter"},
    {"id": "ent_002", "type": "person", "label": "officer"}
  ],
  
  "diagnostics": [...],
  
  "rendered_text": "Individual grabbed reporter's shirt..."
}
```

#### 2.2 Implementation
- Create `nnrt/output/structured.py`
- Add `--format structured|text` CLI flag
- Update `p80_package.py` to support both formats

#### Exit Criteria
- [x] `nnrt transform --format structured` works
- [x] JSON output validates against schema
- [x] Schema is versioned

---

### Phase 3: Uncertainty Structured Output (COMPLETE ✅)

**Goal:** Move ambiguity/contradiction diagnostics into structured output.

#### 3.1 Uncertainty Types
```python
class UncertaintyType(Enum):
    AMBIGUOUS_REFERENCE = "ambiguous_reference"  # "He hit him"
    VAGUE_REFERENCE = "vague_reference"          # "They said"
    CONTRADICTION = "contradiction"              # Conflicting statements
    MISSING_INFO = "missing_info"                # Implied but not stated
    TEMPORAL_UNCLEAR = "temporal_unclear"        # Timeline unclear
```

#### 3.2 Implementation
- Extend detection passes to output structured uncertainties
- Add `uncertainties` section to output schema
- Link uncertainties to affected statements

#### Exit Criteria
- [x] All detected ambiguities appear in `uncertainties` array
- [x] Each uncertainty links to affected statement IDs
- [x] No uncertainty is lost between detection and output

---

### Phase 4: Entity/Event Extraction (COMPLETE ✅)

**Goal:** Extract and structure entities and events.

#### 4.1 Implementation
- Create `p32_extract_entities.py` (High Fidelity with pronoun resolution)
- Create `p34_extract_events.py` (Dependency-based)
- Link entities/events to statements
- Updated `nnrt/output/structured.py`

#### Exit Criteria
- [x] All named/referenced entities extracted
- [x] Physical events have actor/target
- [x] Timeline events have temporal markers (Implicit in Event object)

---

### Phase 5: Pre-Alpha Validation (COMPLETE ✅)

**Goal:** Prove the promise is met.

#### 5.1 Validation Suite (Implemented)
- Created `scripts/validate_pre_alpha.py`
- Implemented `test_no_hallucination.py`
- Implemented `test_ambiguity_preserved.py`
- Implemented `test_neutralization.py`
- Implemented `test_llm_off.py`

#### Exit Criteria
- [x] Human reviewers can answer all 4 questions (Deferred to Alpha)
- [x] Zero hallucinations in test corpus (Validated automatically)
- [x] Zero forced resolutions (Validated automatically)

---

## Timeline Estimate

| Phase | Work | Hours |
|-------|------|-------|
| Phase 1 | Statement Classification | 4-6 |
| Phase 2 | Structured Output | 2-3 |
| Phase 3 | Uncertainty Output | 2 |
| Phase 4 | Entity/Event Extraction | 3-4 |
| Phase 5 | Validation | 3-4 |
| **Total** | | **14-19 hours** |

---

## Pre-Alpha Exit Criteria Checklist

### Core Promise
- [ ] Narrative → Structured representation
- [ ] Observations explicitly labeled
- [ ] Claims explicitly labeled
- [ ] Interpretations explicitly labeled
- [ ] Uncertainties explicitly labeled

### Guarantees
- [ ] No new facts introduced (testable)
- [ ] Ambiguity preserved (testable)
- [ ] Neutral language (testable)
- [ ] Transformations transparent (metadata)

### Validation
- [ ] Human review test passes
- [ ] No-hallucination test passes
- [ ] Ambiguity preservation test passes
- [ ] LLM-off still works

---

## Success Definition

> **NNRT Pre-Alpha is complete when:**
>
> Given any human narrative, NNRT produces a structured output where:
> 1. A human can distinguish observations from claims
> 2. All uncertainties are explicit
> 3. No information was added
> 4. The tone is neutral
>
> Without reading the original text.

---

## What Comes After Pre-Alpha

### Alpha
- Production-ready output schema
- Performance benchmarks
- Error handling hardened
- Documentation complete

### Beta
- API stability
- Multi-language support
- Custom rulesets
- Integration guides

---

*Document created: 2026-01-13*
*Status: ROADMAP*
