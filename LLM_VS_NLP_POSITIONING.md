# NNRT — LLM Usage Policy and Positioning

## Purpose

This document defines **how NNRT uses language models** and why.

This is not a tooling preference. It is a design boundary that determines whether NNRT remains defensible.

---

## The Core Rule

> **LLMs are allowed to assist the transformation.**
> **LLMs are not allowed to define the transformation.**

This distinction is non-negotiable.

---

## Why LLMs Are Necessary

A strict "no LLMs" policy sounds principled, but it breaks down in practice.

### The Problem NNRT Solves

NNRT maps **human expression → formal structure**.

Humans submit input that is:

* Non-linear
* Redundant
* Emotional
* Context-dependent
* Grammatically inconsistent
* Full of ellipsis and implication

Example input:

> "He was clearly trying to intimidate me, standing way too close, smirking, after everything that happened before."

A deterministic parser alone cannot reliably:

* Separate observation from interpretation
* Preserve factual intent
* Avoid over-stripping meaning
* Handle edge cases without exploding rule complexity

### Why Rules Alone Don't Scale

A pure rule-based system requires:

* Thousands of edge-case rules
* Constant maintenance
* Domain-specific grammar trees
* Language-specific handling
* Extremely brittle behavior

You would end up reimplementing half of linguistics — poorly, with worse results.

### What LLMs Are Good At

LLMs are **semantic compressors and rewriters**, not judges.

They excel at:

* Rephrasing without losing meaning
* Handling messy, long-form narrative
* Detecting implied structure
* Suggesting neutral phrasings
* Operating across domains without brittle rules

Crucially: **they can propose structure without asserting correctness.**

That is the exact capability NNRT needs.

---

## The Correct Mental Model

LLMs are **linguistic adapters**, not decision-makers.

Think of them as:

* Smart text normalizers
* Semantic shapers
* Structure suggesters

**Not** as:

* Reasoners
* Judges
* Authorities

---

## What Makes LLM Usage Safe

### The Architectural Pattern

```
LLM → Candidate Generator
Engine → Validator & Gatekeeper
```

**Never the reverse.**

If the Engine cannot verify the output without the LLM, the design is wrong.

### The Inversion That Makes This Work

| Without LLMs | With Constrained LLMs |
|--------------|----------------------|
| Rules try to understand humans → they fail | LLMs help translate humans → rules enforce meaning |

**Translation ≠ interpretation.**

---

## Allowed vs. Forbidden LLM Roles

### Allowed

LLMs may:

* Rewrite text into neutral tone **without adding information**
* Label sentences (observation / claim / interpretation)
* Propose multiple neutral rewrites for user selection
* Flag ambiguity or missing data
* Suggest metadata candidates (never assert them)
* Propose sentence splits
* Mark uncertainty explicitly
* Generate multiple candidate neutral forms

All LLM outputs must be:

* Explicitly marked as suggested
* Reviewable
* Rejectable
* Deterministically post-processed

### Forbidden

LLMs must not:

* Infer intent or motive
* Resolve contradictions
* Guess facts
* Fill missing details
* Decide credibility
* Collapse uncertainty
* Select the "best" interpretation
* Increase certainty
* Produce a "final" authoritative output

**The final structure is produced by rules + schema, not by model judgment.**

---

## Determinism Requirement

Even with LLMs involved:

* The same input must produce structurally equivalent output
* Ambiguity must be preserved, not resolved
* Confidence must never increase automatically
* Any non-deterministic step must be annotated

**If you cannot explain why a transformation occurred, it must not occur.**

---

## Testable Boundaries

### The Auditor Test

> "Could an external auditor reconstruct the transformation logic without trusting the model?"

If the answer is **no** — the LLM is doing too much.

### The Ambiguity Test

> "Could two reasonable readers disagree after reading this output?"

If **yes** → NNRT did its job.
If **no** → NNRT overstepped.

### The Fallback Test

> "If you removed the LLM tomorrow, would the system still work, but badly?"

* If **yes** → acceptable (LLMs are quality multipliers)
* If **no** → unacceptable (LLMs have become foundations)

---

## NNRT-Specific Constraints

At the NNRT layer specifically:

### Allowed at NNRT Level

* Rewriting into neutral tone
* Proposing sentence splits
* Labeling clauses
* Marking ambiguity explicitly
* Generating multiple candidate neutral forms

### Forbidden at NNRT Level

* Selecting the "best" interpretation
* Increasing certainty
* Resolving contradictions
* Filling missing facts
* Producing a single authoritative rewrite

NNRT output must always look like:

> "Here are possible neutral interpretations of what was written."

**Never:**

> "Here is what happened."

---

## One-Sentence Policies

### General Policy

> NNRT may use language models as assistive tools for neutralization, but all factual structure, classification, and guarantees are enforced by deterministic rules, not model judgment.

### NNRT-Specific Policy

> NNRT may use LLMs to translate narrative into structured neutral candidates, but it must never reduce ambiguity or assert meaning.

If that line is crossed, NNRT stops being a transformer and becomes an author.

---

## How to Describe This Publicly

### Never Say

* "We use AI to understand reports."
* "An LLM that analyzes incidents."
* "An automated truth system."

### Always Say

* "Automated language tools may assist in rewriting submissions into neutral form, but all transformations follow fixed, auditable rules and do not infer meaning or intent."

That wording matters.

---

## Why This Positioning Matters

LLMs are powerful — and dangerous — when treated as authoritative systems.

If LLMs:

* Infer intent
* Fill gaps
* Resolve ambiguity implicitly
* Decide what "really happened"
* Smooth contradictions

…then you've destroyed neutrality.

At that point, you are no longer normalizing — **you are authoring.**

That creates:

* Hidden bias
* Non-determinism
* Legal exposure
* Trust collapse
* Impossible audits

This is exactly what NNRT must avoid.

---

## Summary

NNRT is a **deterministic NLP pipeline** that uses LLMs as **constrained semantic sensors**.

LLMs are:

* Necessary (because human language is messy)
* Constrained (proposal only, never decision)
* Subordinate (Engine validates, LLM suggests)
* Auditable (transformations must be explainable without trusting the model)

NNRT uses models.
NNRT is not a model.

---

## Closing Note

This boundary is the line that keeps the system honest.

If this ever feels fuzzy, return to the auditor test:

> "Could an external auditor reconstruct the transformation logic without trusting the model?"

If yes — proceed.
If no — stop and redesign.
