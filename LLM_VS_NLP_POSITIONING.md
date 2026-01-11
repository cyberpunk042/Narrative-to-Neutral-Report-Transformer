# NNRT Positioning: NLP System, Not an LLM

## Purpose

This document clarifies how NNRT positions itself with respect to **LLMs** and **NLP systems**.

NNRT intentionally avoids being described as "an LLM" or "an AI that understands truth". This distinction is not marketing — it is architectural and ethical.

---

## Short Statement (Recommended Description)

> NNRT is a **deterministic NLP pipeline** that uses machine‑learning models as **semantic sensors**, not as decision‑makers.

LLMs may be used as components, but NNRT itself is **not** an LLM.

---

## Why This Distinction Matters

Large Language Models:

* Generate text
* Optimize for plausibility
* Fill gaps implicitly
* Can hallucinate structure, intent, or facts

These properties make LLMs powerful — and dangerous — when treated as authoritative systems.

NNRT is designed to avoid these failure modes.

---

## How NNRT Actually Works

NNRT follows a **compiler‑style NLP architecture**:

1. Input text is normalized
2. Semantic signals are extracted (tags, spans, events)
3. A structured Intermediate Representation (IR) is built
4. Deterministic policy rules are applied
5. Output text is rendered from IR under constraints

At no point is a model allowed to:

* decide truth
* reconcile perspectives
* invent missing facts
* resolve conflicts

---

## Role of Machine Learning in NNRT

Machine‑learning models are used only for **bounded perception tasks**, such as:

* detecting semantic spans
* classifying language categories
* extracting candidate events with evidence

They do **not**:

* control the pipeline
* decide what survives into output
* perform reasoning or adjudication

All ML outputs are treated as **untrusted input**.

---

## LLMs as Optional Components

When LLMs are used, they are constrained to:

* structured (JSON‑only) outputs
* evidence‑backed extraction
* confidence‑annotated suggestions

Their outputs are always:

* schema‑validated
* policy‑checked
* rejectable

NNRT can refuse or partially output results when model confidence or validation fails.

---

## NLP vs LLM: Practical Comparison

NLP System (NNRT):

* Structure‑first
* Deterministic rules
* Explicit refusal modes
* Traceable transformations
* Conservative by design

LLM‑centric System:

* Generation‑first
* Implicit reasoning
* No clear refusal semantics
* Difficult to audit
* Prone to confident error

NNRT deliberately chooses the former.

---

## How NNRT Describes Itself

Accurate descriptions include:

* "A semantic normalization pipeline"
* "A compiler‑style NLP transformer"
* "An IR‑based narrative processing system"
* "A deterministic NLP system with optional ML components"

Descriptions to avoid:

* "An AI that determines facts"
* "An LLM that analyzes incidents"
* "An automated truth system"

---

## Ethical Implication

By not presenting itself as an LLM, NNRT:

* avoids false authority
* avoids over‑trust by users
* makes failure explicit and inspectable
* preserves space for human judgment

NNRT does not replace interpretation.

It **structures language so interpretation is possible without distortion**.

---

## Closing Note

NNRT is conservative by design.

It uses modern NLP techniques without inheriting the epistemic risks of treating language models as judges.

In short:

> NNRT uses models.
> NNRT is not a model.
