# NNRT — Python Project Structure & Domain-Oriented Style

This document defines the **Python-first engineering structure** of NNRT.

NNRT uses Python for feasibility and NLP ecosystem leverage. The project remains **IR-first** and **compiler-like** in organization, but does not attempt to mimic other languages.

---

## 1. Goals

* Keep the project readable and scalable as features grow
* Separate domain concepts from infrastructure code
* Make pipeline stages explicit and modular
* Ensure artifacts (IR, trace, diagnostics) are first-class
* Keep NLP backends pluggable and isolated

---

## 2. Architectural Style

NNRT follows a domain-oriented structure:

* The domain is expressed through the IR model and related enums
* The pipeline is expressed through isolated passes
* The engine orchestrates passes, not domain logic
* NLP is treated as a replaceable sensor layer

---

## 3. Source Tree Layout (Recommended)

nnrt/
core/
engine.py
context.py
contracts.py
versioning.py

ir/
schema_v0_1.py
enums.py
serialization.py

passes/
p00_normalize.py
p10_segment.py
p20_tag_spans.py
p30_extract_identifiers.py
p40_build_ir.py
p50_policy.py
p60_augment_ir.py
p70_render.py
p80_package.py

nlp/
interfaces.py
backends/
stub.py
hf_encoder.py
json_instruct.py

policy/
engine.py
rulesets/

render/
template.py
constrained.py

validate/
schema.py
forbidden_vocab.py
no_new_facts.py
idempotence.py

cli/
main.py

data/
synthetic/
golden/

docs/
IR_SPEC_v0_1.md
PIPELINES.md
PASS_CONTRACT.md
ADRs/

tests/

---

## 4. Domain Layer

### 4.1 IR as the Domain

The Intermediate Representation (IR) is the domain model.

* IR is versioned
* IR is the primary artifact
* Rendered text is derived from IR

IR fields should remain minimal and only expand when justified by failure cases.

### 4.2 Domain Enums and Codes

All labels, roles, rule identifiers, reason codes, and diagnostic codes live in `ir/enums.py`.

No stringly-typed constants scattered across passes.

---

## 5. Pipeline Layer

### 5.1 Passes are explicit modules

Each pass corresponds to one conceptual stage of the SuperSystem pipeline.

* Passes are ordered and named
* Pass files use an explicit prefix (p00, p10, …)
* Passes may read prior artifacts from context
* Passes may mutate only their intended fields

### 5.2 Pass Implementation Style

Passes may be written as:

* a small class with an `apply(ctx)` method, or
* a function that receives and mutates context

Choose the simplest approach per pass.

Passes must:

* append trace entries for meaningful changes
* surface issues via diagnostics
* avoid hidden side effects

---

## 6. Orchestration Layer

The engine:

* selects a pipeline by ID
* runs passes in order
* manages validation and packaging

The engine is not where domain logic lives.

---

## 7. NLP Layer

NLP is treated as a replaceable sensor layer.

* Passes call NLP through interfaces
* Backends live under `nlp/backends/`
* Backends must output structured data

Early development may use a stub backend to validate architecture.

---

## 8. Policy and Rendering

Policy is deterministic and produces explicit decisions.

Rendering turns policy-approved IR into neutral narrative.

Policy and rendering must not be embedded inside NLP backends.

---

## 9. Validation and Testing

Validators and tests are organized as first-class modules.

* Validators live under `validate/`
* Tests lock behavior against a synthetic corpus

---

## 10. Conventions

* Prefer clear names over clever names
* Prefer small modules over deep inheritance
* Prefer structured artifacts over implicit behavior
* Prefer deterministic behavior over convenience

---

## Closing Note

NNRT uses Python for practicality.

The discipline of NNRT comes from:

* explicit passes
* an IR-first domain model
* deterministic policy
* traceable transformations

Not from forcing Python to behave like another language.
