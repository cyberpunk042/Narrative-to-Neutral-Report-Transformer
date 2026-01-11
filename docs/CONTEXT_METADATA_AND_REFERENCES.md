# Context Metadata, References, and Complex-Term Support

## Purpose

This document defines how NNRT supports **rich metadata**, **external references**, and **complex domain-specific terminology** while remaining:

* non-adjudicative
* domain-agnostic
* IR-first
* compatible with multi-perspective narratives

All information described here exists as **metadata and annotations**, never as inferred facts or conclusions.

---

## Core Principle

> Metadata provides context. It does not provide truth.

NNRT treats metadata as an **envelope around the narrative**, not as evidence, interpretation, or authority.

---

## Context Metadata

Context metadata allows a narrative to be situated without altering its semantic content.

This metadata is:

* optional
* caller-provided
* opaque to NNRT logic
* never inferred by NNRT

### Context Scope

Context metadata may describe:

* geographic region
* jurisdiction
* organizational setting
* operational environment
* time or situational framing

NNRT stores this information but does not reason over it.

---

## Context Fields (Non-Exhaustive)

Context fields are intentionally extensible and not limited to a single domain.

Examples include:

### Location

* country
* region or state
* municipality
* facility or site

### Jurisdiction

* legal system or framework identifier
* administrative domain
* court or authority level (if relevant)

### Organization / Office

* agency or organization name
* department or unit
* office or division

### Environment

* interaction type (e.g. traffic stop, workplace meeting, inspection)
* operational mode (e.g. emergency, routine)
* temporal context (approximate, unknown allowed)

NNRT does not validate, normalize, or interpret these values.

---

## External References

NNRT supports references to **external documents or materials** that are relevant to a narrative or its interpretation.

References are **pointers**, not embedded content.

### Reference Use Cases

* laws or regulations
* policy manuals
* training documents
* case law or decisions
* reports
* transcripts
* audio or video sources

---

## Reference Structure

Each reference includes:

* reference type (e.g. law article, policy, case law, report, video)
* reference identifier (opaque)
* optional locator (URL, citation, repository path)
* optional jurisdiction or domain tag
* optional neutral note

NNRT does not verify reference accuracy or applicability.

---

## Complex-Term Support (Domain Vocabulary)

Certain words carry **complex, domain-specific meaning** that cannot be treated as ordinary language.

Examples include:

* eluding
* obstructing
* resisting
* interference
* compliance

NNRT does not interpret these terms as facts or determinations.

---

## Term Mentions vs. Assertions

NNRT distinguishes between:

* **term mentions** (a word used in the narrative)
* **term assertions** (a claim that the term accurately applies)

NNRT only captures **mentions**, never assertions.

---

## Term Mentions

When a complex term appears:

* it is recorded as a term mention
* it is linked to the exact text span where it appears
* it records who used the term (speaker or narrator)

This preserves linguistic fidelity without endorsing meaning.

---

## Domain Lexicons

NNRT may optionally load **domain lexicons** to support consistent handling of complex terms.

Lexicons:

* are data files, not code
* are scoped by domain or jurisdiction
* provide plain-language descriptions
* offer rendering guidance

Lexicons do not define correctness or applicability.

---

## Rendering Policy for Complex Terms

When rendering neutral narratives:

* complex terms may be preserved as quoted language
* framing must avoid endorsement
* examples include:

  * "the term used was 'obstructing'"
  * "I was told I was being accused of 'eluding'"

NNRT must not render such terms as established facts.

---

## Relationship to Multi-Perspective Narratives

Context metadata and references support multi-perspective use cases by:

* allowing different narratives to share context
* enabling responses to reference the same external materials
* preserving distinct interpretations without resolution

Metadata does not privilege one narrative over another.

---

## Non-Goals

This system does not:

* determine legal applicability
* validate references
* normalize jurisdictional differences
* resolve conflicting interpretations
* act as legal advice

---

## Design Constraint

If metadata, references, or term handling are used to imply correctness, blame, or truth, the system has violated NNRT design principles.

---

## Closing Note

Context, references, and complex terms exist to **support understanding without deciding meaning**.

NNRT preserves language, structure, and perspective while refusing to become an authority.

This separation is intentional and non-negotiable.
