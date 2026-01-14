# NNRT — Milestone 1: Core NLP Integration

## Purpose

Milestone 1 implements the **semantic sensing layer** of NNRT — the NLP components that detect structure in human narrative.

This milestone transforms the stub pipeline into a functional prototype that can:

- Segment text into sentences
- Tag spans with semantic labels
- Extract basic entities and events
- Produce meaningful neutral output

---

## Scope

### In Scope

1. **Sentence segmentation** — Replace regex stub with proper NLP segmentation
2. **Span tagging** — Implement encoder-based span classification
3. **Entity detection** — Identify actors and their roles
4. **Basic event extraction** — Extract observable actions
5. **Simple rendering** — Template-based neutral output from IR

### Out of Scope (Milestone 2+)

- Constrained LLM rendering
- Advanced event relationship mapping
- Production-grade policy rules
- Performance optimization
- Multi-language support

---

## Architecture Decisions (Inherited from M0)

| Component | Decision |
|-----------|----------|
| NLP Backbone | **Hybrid** — Encoder for tagging, generator for rendering |
| Encoder Model | DeBERTa-v3-base or similar transformer encoder |
| Segmentation | spaCy for sentence splitting |
| Span Classification | Fine-tuned token classification or zero-shot |

---

## Implementation Plan

### Phase 1: NLP Infrastructure

1. Add NLP dependencies (transformers, spacy, torch)
2. Implement spaCy-based segmentation (p10_segment)
3. Create model loading utilities

### Phase 2: Span Tagging

1. Implement span tagger interface with HuggingFace encoder
2. Create label mapping for NNRT semantic labels
3. Integrate into p20_tag_spans pass

### Phase 3: Entity & Event Extraction

1. Implement entity extraction from tagged spans
2. Implement basic event extraction
3. Integrate into p40_build_ir pass

### Phase 4: Rendering

1. Implement template-based neutral rendering
2. Generate neutral reframings from IR
3. Integrate into p70_render pass

### Phase 5: Validation & Testing

1. Create integration tests with synthetic narratives
2. Validate against golden outputs
3. Measure semantic preservation

---

## Model Selection Criteria

The encoder model must:

1. Run locally (no API calls)
2. Fit in reasonable VRAM (< 8GB)
3. Support sequence classification / NER tasks
4. Have strong contextual understanding

Candidates:

| Model | Size | Pros | Cons |
|-------|------|------|------|
| DeBERTa-v3-base | 184M | Strong NLU, efficient | Needs fine-tuning |
| roberta-base | 125M | Well-tested, fast | Less nuanced |
| ModernBERT-base | 150M | Latest architecture | Less ecosystem |

**Initial choice:** Start with a pre-trained NER/classification model, then evaluate fine-tuning needs.

---

## LLM Policy Compliance

Per `/LLM_VS_NLP_POSITIONING.md`:

- Encoder outputs are **sensor data**, not decisions
- All span labels include **confidence scores**
- IR construction is **deterministic** from spans
- Rendering produces **candidates**, not final truth
- Ambiguity is **preserved**, not resolved

Every pass must pass the auditor test:
> "Could an external auditor reconstruct the transformation logic without trusting the model?"

---

## Exit Criteria

Milestone 1 is complete when:

- [x] `nnrt transform` produces meaningful neutral output
- [x] Span tagging uses real NLP model (not stub) — *spaCy-based*
- [x] Entities and events are extracted from narrative
- [x] Output preserves semantic content of input
- [x] Tests validate transformation quality — *34 tests, 3 golden cases*
- [x] Diagnostics show confidence levels

**STATUS: COMPLETE** as of 2026-01-13

---

## Dependencies

```toml
[project.optional-dependencies]
nlp = [
    "transformers>=4.35",
    "torch>=2.0",
    "spacy>=3.7",
    "accelerate>=0.25",
]
```

---

## Next Step After Milestone 1

Milestone 2 will add:

- Constrained LLM rendering (optional)
- Advanced policy rules
- Identifier extraction
- Production hardening
