# NNRT — Scope, Constraints, and Ethical Guidelines

This document exists to **define boundaries**.

NNRT is intentionally constrained. Those constraints are not limitations of ambition; they are **design decisions** that protect users, contributors, and downstream adopters.

Breaking these constraints breaks the project.

---

## 1. Core Position

NNRT is a **language transformation tool**.

It does not seek truth, justice, or resolution.
It does not arbitrate disputes.
It does not assign responsibility.

Its sole function is to **restructure first-person narratives into neutral, non-accusatory, procedurally safe forms**.

---

## 2. Hard Scope Boundaries (Non-Negotiable)

NNRT will **never**:

* Collect real-world reports
* Host user submissions
* Publish or distribute narratives
* Rank, score, or label individuals or institutions
* Aggregate narratives into profiles or patterns
* Act as an accountability, reporting, or enforcement platform
* Perform fact-checking or verification
* Infer intent, legality, or wrongdoing

Any implementation that violates these boundaries is **no longer NNRT**.

---

## 3. Tool, Not Platform

NNRT is designed as:

* A local library
* A CLI utility
* Or an embeddable transformation component

It is **not**:

* A service
* A website
* An API endpoint receiving public input
* A moderation system

Responsibility for how outputs are used lies entirely with the consumer of the tool.

---

## 4. Deterministic and Inspectable by Design

All transformations must be:

* Deterministic
* Rule-based
* Inspectable in source code
* Reproducible given the same input

NNRT must not:

* Learn from user input
* Adapt behavior over time
* Use opaque or non-explainable models

Explainability is a core ethical requirement.

---

## 5. Experience Over Accusation

NNRT preserves **experience**, not judgment.

Outputs must:

* Remain first-person
* Describe observable actions and statements
* Avoid legal, moral, or psychological conclusions

NNRT intentionally avoids words that imply:

* Guilt
* Intent
* Illegality
* Motive

This is not denial of harm — it is refusal to adjudicate.

---

## 6. Identifier Handling Ethics

Explicit identifiers (e.g. names, badge numbers, employee IDs):

* Are removed from narrative output by default
* May be extracted into optional, non-narrative metadata
* Must not be associated with conclusions or claims
* Must not alter the meaning of the narrative

Metadata exists for **contextual linkage only** and may be discarded entirely.

---

## 7. No Emergent Authority

NNRT must not evolve into:

* A truth engine
* A reputation system
* A proxy court
* A substitute for journalism or legal process

If users interpret NNRT output as authoritative judgment, the design has failed.

---

## 8. Ethical Motivation vs Ethical Action

NNRT is motivated by widely documented difficulties in expressing experiences involving power imbalance, authority, or vulnerability.

Motivation does **not** justify overreach.

Ethical action here means:

* Restraint
* Precision
* Transparency
* Respect for downstream consequences

---

## 9. Synthetic Examples Only

All examples included in this project:

* Are fictional, synthetic, or anonymized
* Exist solely to demonstrate transformation behavior
* Do not represent real individuals or events

NNRT does not solicit real-world narratives.

---

## 10. Responsibility of Downstream Use

This project provides a **method**, not an outcome.

Anyone integrating NNRT into larger systems bears full responsibility for:

* Legal compliance
* Ethical deployment
* User safety
* Contextual safeguards

NNRT explicitly disclaims responsibility for downstream applications.

---

## 11. If These Constraints Feel Frustrating

That reaction is expected.

NNRT exists precisely because unconstrained speech and constrained systems collide in harmful ways.

The project chooses **endurance over immediacy**, and **procedural integrity over catharsis**.

---

## Closing Statement

NNRT does not claim to fix injustice.

It demonstrates that **language can be handled with more care than current systems allow**, without turning tools into judges.

These constraints are the project.

Removing them removes the point.
