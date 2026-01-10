# NNRT — Project Governance, Planning, and Documentation Guidelines

This document defines **how NNRT is developed**, not what it does.

NNRT treats planning, analysis, and documentation as first-class artifacts. Code is a downstream product.

---

## 1. Core Principle

> **Nothing is built without being named, scoped, analyzed, and documented first.**

This is not bureaucracy. It is how NNRT avoids drift, overreach, and accidental authority.

---

## 2. Hierarchical Planning Model

NNRT development is structured into four explicit layers:

1. **Milestones** — major phases of capability
2. **Milestone Documents** — intent, boundaries, and exit criteria
3. **Feature Documents** — detailed design for discrete functionality
4. **Analysis & Planning Documents** — risk, alternatives, and validation

No layer may skip the one above it.

---

## 3. Milestones

### 3.1 What a Milestone Is

A milestone represents:

* A coherent capability boundary
* A conceptual phase of the project
* A point at which the project could reasonably stop

Milestones are **few**, **intentional**, and **non-overlapping**.

---

### 3.2 Milestone Document Requirements

Each milestone must have a dedicated document containing:

* Purpose and motivation
* Explicit scope
* Explicit non-goals
* Ethical considerations
* Technical constraints
* Success criteria (what "done" means)
* Reasons the milestone might be abandoned

A milestone is not considered active until its document exists.

---

## 4. Feature-Level Documentation

### 4.1 When a Feature Needs Its Own Document

A feature **must** have a dedicated document if it:

* Introduces new transformation logic
* Affects narrative semantics
* Touches identifiers or metadata
* Introduces configuration options
* Alters guarantees defined in SCOPE_AND_ETHICS

Small mechanical changes may be documented inline.

---

### 4.2 Feature Document Structure

Each feature document should include:

* Problem statement
* Intended behavior
* Explicit constraints
* Rejected alternatives (with reasons)
* Ethical considerations
* Failure modes
* Testability notes
  n
  Features are approved by clarity, not by enthusiasm.

---

## 5. Analysis Documents

Analysis documents exist to **slow development down** intentionally.

They are required when:

* A design choice has legal or ethical implications
* Multiple approaches are plausible
* The risk of misuse exists

Analysis documents should cover:

* Context and assumptions
* Risks (technical, legal, ethical)
* Trade-offs
* Why this choice is acceptable *now*
* Conditions under which the choice should be revisited

---

## 6. Planning Documents

Planning documents translate approved analysis into execution steps.

They include:

* Ordered tasks
* Dependencies
* Validation steps
* Explicit stop points

Planning documents are not implementation guides; they are **intent guides**.

---

## 7. Document Lifecycle

Documents move through states:

* Draft
* Reviewed
* Active
* Frozen
* Archived

Once a document is frozen:

* Its constraints are binding
* Changes require a new document

---

## 8. Change Discipline

NNRT does not accept:

* "Small" changes that alter guarantees
* "Temporary" shortcuts
* Silent scope expansion

Any change that affects:

* Scope
* Ethics
* Guarantees
* Authority perception

Requires explicit documentation.

---

## 9. Relationship to Code

Code must:

* Reference the document that justified its existence
* Be traceable to a feature or milestone
* Be removable if the corresponding document is revoked

If code cannot be explained by a document, it does not belong.

---

## 10. Why This Exists

NNRT operates in a sensitive conceptual space.

The greatest risk is not bugs — it is **becoming something it never intended to be**.

These guidelines ensure:

* Deliberate evolution
* Ethical restraint
* Clear authorship of decisions
* Long-term defensibility

---

## Closing Statement

NNRT is not built by accident.

It advances one carefully defined step at a time.

Planning is part of the product.
