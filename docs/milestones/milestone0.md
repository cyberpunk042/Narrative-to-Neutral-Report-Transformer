# NNRT — Milestone 0: Architecture & Technology Blueprint

## Purpose

Milestone 0 defines the **engineering blueprint** of NNRT before any serious implementation work begins.

The goal is not to produce running code, but to freeze:

* the system architecture
* the semantic pipeline
* the NLP strategy
* the IR (Intermediate Representation) contract
* module boundaries and responsibilities

This milestone exists to ensure NNRT is built as a **coherent compiler-like system**, not as an accretion of hacks.

---

## What Milestone 0 Is

Milestone 0 is a **design freeze milestone**.

It produces documents, diagrams, interfaces, and decisions that all later milestones must respect.

Minimal experimental prototypes may be used only to de-risk decisions (e.g. model feasibility), but no production code is written.

---

## What Milestone 0 Is Not

Milestone 0 does not:

* implement the pipeline
* ship a CLI or library
* process real-world narratives
* optimize performance

Any attempt to "just code a bit" beyond design validation is out of scope.

---

## System Overview (Compiler Analogy)

NNRT is designed as a **semantic transformation compiler**:

Raw Narrative → Normalization → Semantic Sensing → IR Construction → Policy Evaluation → IR Augmentation → Rendering → Validation → Output

The **IR is the source of truth**. Text output is a rendering.

---

## Core Architectural Principles

* IR-first architecture
* Deterministic policy and validation
* NLP models act as semantic sensors, not authorities
* Explicit refusal is a valid outcome
* Every transformation must be traceable
* Tool, not platform

---

## High-Level Pipeline (NNRT SuperSystem Mainline)

Stage 0: Input Normalization
Stage 1: Lexical & Syntactic Segmentation
Stage 2: Semantic Sensing (Span Tagging via NLP)
Stage 3: Identifier Extraction (Side-channel)
Stage 4: IR Construction (Events, Speech Acts, Observations)
Stage 5: Deterministic Policy Evaluation
Stage 6: Safe IR Augmentation
Stage 7: Constrained Rendering
Stage 8: Packaging (IR, Text, Trace, Diagnostics)
Stage 9: Validation & Regression Controls

Each stage is implemented as an isolated pass with a strict contract.

---

## NLP Backbone Decision Space

Milestone 0 must select one primary NLP strategy for Stages 2–4.

**All options must comply with the LLM Usage Policy** (see `/LLM_VS_NLP_POSITIONING.md`).

The architectural constraint is non-negotiable:

```
LLM → Candidate Generator
Engine → Validator & Gatekeeper
```

LLMs are necessary (human language is messy), but constrained (proposal only, never decision).

### Option A — Encoder + Classifier Heads

* Contextual encoder (e.g. BERT/DeBERTa class)
* Span and token classification for semantic labels
* Optional separate event extractor
* Lowest hallucination risk
* Most compiler-like
* **LLM role:** Semantic sensor only

### Option B — Small Instruction Model (JSON-only)

* Local instruct model (e.g. Flan-T5-small, Phi-3-mini)
* Strict structured outputs only (JSON schema enforced)
* Faster prototyping
* Requires strong validators
* **LLM role:** Structure suggester, never authority

### Option C — Hybrid ✅ SELECTED

* Encoder for tagging and extraction
* Small constrained generator only for rendering
* Best balance of safety and usability
* **LLM role:** Encoder senses, generator proposes, Engine validates

**Status:** FROZEN as of 2026-01-13

**Rationale:** Hybrid provides deterministic semantic sensing via encoder while allowing constrained generation for rendering. Passes the auditor test: encoder outputs are inspectable, generator input is IR (not raw text).

### Selection Criteria

The chosen option must pass the **auditor test**:

> "Could an external auditor reconstruct the transformation logic without trusting the model?"

**Decision recorded. This selection is now binding for implementation milestones.**

---

## Intermediate Representation (IR) — v0.1 Goals

The IR captures **semantic structure without judgment**.

Design goals:

* minimal
* typed
* versioned
* incomplete by default
* never invents facts

Initial IR concerns:

* segments
* semantic spans
* entities (roles, not identities)
* events
* speech acts
* uncertainty markers
* policy decisions
* trace entries

IR complexity must grow only when justified by failure cases.

---

## Core Modules

Core

* Engine (pipeline runner)
* Context (mutable state between passes)
* Contracts (IR, Trace, Diagnostics, Request, Result)
* Validators (schema, safety, idempotence)

Passes

* Normalize
* Segment
* Tag Spans (NLP)
* Extract Identifiers
* Build IR
* Evaluate Policy
* Augment IR
* Render
* Package Output

NLP

* SpanTagger interface
* EventExtractor interface
* Model adapters (local backends)

Policy

* Deterministic rule engine
* Reason codes
* Refusal logic

Render

* Template renderer
* Optional constrained generator renderer

---

## Pass Contract

Each pass:

* receives a TransformContext
* may read prior artifacts
* may mutate only its allowed fields
* must append trace entries for every change
* must be deterministic

Passes do not communicate directly with each other.

---

## Validation Strategy

Validation is mandatory and layered:

* IR schema validation
* Forbidden vocabulary checks
* No-new-facts heuristic checks
* Idempotence checks
* Confidence-based refusal thresholds

Validation failures must surface as diagnostics or refusal, never silent correction.

---

## API Surface (Planned)

Core

* transform(request) → result
* runPipeline(pipelineId, request) → result

NLP

* tagSpans(segments) → span tags
* extractEvents(segments, tags) → events

Policy

* evaluate(ir, tags) → decisions
* shouldRefuse(decisions) → refusal

Render

* render(ir, policy) → text

---

## Diagrams (Conceptual)

Component Flow:
Input → Normalize → Segment → Tag Spans → Extract IDs → Build IR → Policy → IR Augment → Render → Validate → Output

Data Flow:
Text → Spans → IR → Policy Decisions → Rendered Text + Trace

Sequence:
Engine invokes passes in order; each pass mutates context and appends trace; validators run before final output.

---

## Milestone 0 Exit Criteria

Milestone 0 is complete when:

* Implementation language is chosen
* NLP backbone option is chosen
* IR v0.1 is fully specified
* Pipeline stages and pass inventory are frozen
* Module boundaries are documented
* Validators are defined
* Diagrams and API surface are documented

At this point, implementation milestones may begin.

---

## Next Step After Milestone 0

Milestone 1 will strictly implement the architecture defined here without deviation.

Any architectural change after Milestone 0 requires a new design document.

---

## Closing Note

Milestone 0 exists to ensure NNRT is engineered deliberately.

This document is the contract that prevents the system from becoming accidental, opaque, or unbounded.
