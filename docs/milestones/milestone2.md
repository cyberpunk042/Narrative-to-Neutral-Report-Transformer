# NNRT — Milestone 2: Advanced Features & Production Hardening

## Purpose

Milestone 2 builds on the functional pipeline from M1 to add:

1. **Constrained LLM rendering** — Optional fluent output via small instruction model
2. **Advanced policy rules** — Configurable, composable rule sets
3. **Identifier extraction** — Badge numbers, locations, timestamps
4. **Production hardening** — Error handling, logging, configuration

---

## Scope

### In Scope

1. **Constrained LLM rendering** (Optional)
   - Small instruction model (Flan-T5-small or Phi-3-mini)
   - Strict JSON schema enforcement
   - Multiple candidate generation
   - Human-reviewable output

2. **Policy rule system**
   - Configurable rule sets (YAML-based)
   - Rule composition and priority
   - Conditional transformations
   - Explicit refusal handling

3. **Identifier extraction**
   - Badge/ID numbers (regex + NER)
   - Location names
   - Timestamps and durations
   - Contact information (phone, address)

4. **Production hardening**
   - Structured logging
   - Configuration management
   - Graceful error handling
   - Performance metrics

### Out of Scope (Milestone 3+)

- Web API / REST interface
- Database integration
- Multi-language support
- Custom model fine-tuning

---

## Architecture Decisions

### Constrained LLM Usage (Per Policy)

Per `/LLM_VS_NLP_POSITIONING.md`:

| Allowed | Forbidden |
|---------|-----------|
| Rewrite IR to fluent text | Add new information |
| Propose multiple candidates | Resolve ambiguity |
| Mark uncertainty | Assert confidence |
| Suggest alternatives | Make final decisions |

**Key constraint:** Generator input is IR only, not raw text.

### Model Selection

| Model | Size | Use Case | Constraint Method |
|-------|------|----------|-------------------|
| Flan-T5-small | 80M | Rendering | Prompt engineering |
| Phi-3-mini | 3.8B | Complex rendering | JSON schema |
| Llama-3.2-1B | 1B | Alternative | Structured output |

**Initial choice:** Flan-T5-small for low resource usage.

---

## Implementation Plan

### Phase 1: Policy Rule System

1. Define YAML rule schema
2. Implement rule loader
3. Create base rule set
4. Integrate with p50_policy pass

### Phase 2: Identifier Extraction

1. Regex patterns for common identifiers
2. spaCy NER integration
3. Identifier normalization
4. Integration with p30_extract_identifiers pass

### Phase 3: Constrained LLM Rendering

1. Create LLM interface abstraction
2. Implement Flan-T5 backend
3. Build IR-to-prompt converter
4. Candidate generation and selection
5. Integration with p70_render pass

### Phase 4: Production Hardening

1. Structured logging (structlog)
2. Configuration via YAML/env
3. Error classification and handling
4. Performance timing

### Phase 5: Testing & Documentation

1. LLM output validation tests
2. Policy rule tests
3. End-to-end integration tests
4. API documentation

---

## LLM Rendering Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│     IR      │ ──> │  IR → Prompt │ ──> │   Flan-T5   │
│  (source)   │     │  Converter   │     │   (render)  │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                │
                                                ▼
                    ┌──────────────┐     ┌─────────────┐
                    │   Validate   │ <── │  Candidates │
                    │   & Select   │     │  (N options)│
                    └──────┬───────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   Output    │
                    │  (neutral)  │
                    └─────────────┘
```

**Key invariants:**
- LLM only sees IR, never raw input
- All outputs are candidate suggestions
- Validation rejects invalid outputs
- Human can review/reject any candidate

---

## Exit Criteria

Milestone 2 is complete when:

- [x] Policy rules are configurable via YAML — *base.yaml with 15 rules*
- [x] Identifiers are extracted (badge, location, time) — *regex + spaCy NER*
- [x] LLM rendering produces fluent neutral text (optional mode) — *Flan-T5-small*
- [x] LLM output is validated against IR (no new facts) — *validate_llm_output()*
- [ ] Structured logging is implemented — *deferred*
- [ ] Configuration is externalized — *partially (env vars, YAML)*
- [x] Tests cover all new functionality — *34 tests passing*

**STATUS: MOSTLY COMPLETE** as of 2026-01-13

Remaining:
- Structured logging (structlog integration)
- Full configuration management

---

## Dependencies

```toml
[project.optional-dependencies]
llm = [
    "transformers>=4.35",
    "torch>=2.0",
    "accelerate>=0.25",
]
production = [
    "structlog>=23.0",
    "pyyaml>=6.0",
]
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| LLM adds facts | Strict IR-only input, output validation |
| Model size too large | Start with Flan-T5-small (80M) |
| Non-deterministic output | Temperature=0, seed fixing |
| Policy conflicts | Priority-based rule resolution |

---

## Success Metrics

1. **LLM compliance:** 100% of outputs traceable to IR
2. **Identifier recall:** >90% of common identifiers extracted
3. **Rule coverage:** Base ruleset handles 80% of common cases
4. **Performance:** <5s transformation time for typical narrative
