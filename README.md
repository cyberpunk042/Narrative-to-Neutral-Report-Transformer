# NNRT — Narrative-to-Neutral Report Transformer

## Overview

NNRT (Narrative-to-Neutral Report Transformer) is an open‑source **text transformation tool** designed to convert raw first‑person narratives into **neutral, fact‑focused, legally cautious summaries**.

The project explores how structured, procedural language transformation can help preserve lived experiences while reducing risks associated with misrepresentation, escalation, or unintended legal exposure.

NNRT is a **tool**, not a platform.

It does not collect, host, verify, adjudicate, or publish real‑world reports.

---

## Motivation

Across the world, individuals regularly report difficulties when describing experiences involving power imbalances — particularly in contexts such as policing, law enforcement, detention, or other authority‑driven encounters.

These difficulties often arise from a structural tension:

* Lived experiences are emotional, fragmented, and human
* Public or legal contexts demand precision, neutrality, and restraint
* Misaligned language can unintentionally escalate conflict, liability, or misunderstanding

This project is motivated by the observation — widely documented in journalism, academic research, court proceedings, and oversight reports — that **accountability mechanisms frequently depend on how experiences are articulated**, not only on what occurred.

NNRT explores whether **automated, neutral transformation of first‑person narratives** can help bridge this gap without acting as a judge, investigator, or authority.

---

## What This Project Is

NNRT is:

* A **local text‑to‑text transformer**
* A **procedural pipeline**, not an opinion engine
* A **proof of concept** for narrative normalization
* Focused on **language hygiene**, not truth determination

It takes an input narrative and produces a constrained output that:

* Preserves first‑person perspective
* Focuses on observable actions and direct statements
* Removes legal conclusions, intent attribution, and inflammatory phrasing
* Applies consistent, repeatable transformation rules

---

## What This Project Is NOT

NNRT is **not**:

* A reporting platform
* A complaint submission system
* A verification or fact‑checking tool
* A legal judgment engine
* A database of incidents
* A police rating or accountability system

NNRT does **not**:

* Determine whether events occurred
* Determine legality or illegality
* Assign fault, guilt, or intent
* Replace courts, journalism, or oversight bodies

---

## Design Principles

1. **Process Over Judgment**
   The tool applies deterministic transformation rules and makes no evaluative claims.

2. **Experience, Not Accusation**
   Output language reflects what the narrator experienced or observed, without asserting conclusions.

3. **Uniform Treatment**
   All inputs are transformed using the same pipeline, without selective moderation.

4. **Non-Authoritative Output**
   The transformed text does not claim verification or factual validation.

5. **Minimal Surface Area**
   No storage, publishing, ranking, or aggregation is performed.

6. **Identifier Neutrality**
   Explicit identifiers (e.g. names, badge numbers, employee IDs) are removed from narrative output by default. When present, such identifiers may be extracted into optional, non-narrative metadata without implying attribution, responsibility, or judgment. Consumers of the output may discard this metadata entirely.

---

## Transformation Concept (High‑Level)

A typical transformation pipeline may include:

1. **Narrative Capture** — raw first‑person input (private, local)
2. **Entity Stripping** — removal of names, identifiers, and labels
3. **Action Extraction** — identification of observable actions and commands
4. **First‑Person Reframing** — consistent experiential phrasing
5. **Legal Hygiene Pass** — removal of conclusions, intent, and charged terminology
6. **Neutral Output Generation** — constrained narrative suitable for contextual review

The exact implementation is intentionally transparent and inspectable.

---

## Example Scope

All examples included in this repository are:

* Fictional
* Synthetic
* Or heavily anonymized

They are provided **solely** to demonstrate transformation behavior.

This project does **not** solicit or process real‑world submissions.

---

## Ethical Position

NNRT does not attempt to resolve disputes or determine truth.

Its purpose is to demonstrate that **language structure itself can either obscure or preserve meaning**, especially in contexts involving authority, vulnerability, or imbalance of power.

Ethical accountability is treated here as a **procedural problem**, not a punitive one.

---

## Intended Audience

This project may be of interest to:

* Researchers studying narrative framing and accountability
* Journalists exploring structured testimony workflows
* Legal technologists examining speech‑risk reduction
* Designers of civic or oversight tools
* Developers interested in text normalization pipelines

---

## Legal Notice

This software:

* Makes no factual claims
* Expresses no opinions about real individuals or institutions
* Does not assert wrongdoing
* Does not validate user input

Use of this software does not imply endorsement of any claim or narrative.

---

## Status

This repository currently contains a **proof of concept** only.

It is not intended for production use.

---

## License

Licensed under a permissive open‑source license. See `LICENSE` for details.

---

## Closing Note

NNRT is an exploration of how careful process design can allow difficult experiences to be expressed **without becoming accusations**, and **without requiring individuals to navigate legal complexity on their own**.

It does not claim to solve injustice.

It demonstrates one way language can be handled more responsibly under constraint.
