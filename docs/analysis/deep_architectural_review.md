# Deep Architectural Review & Critical Analysis

**Date:** 2026-01-14
**Scope:** "The Whole Tool" — Code, Data, Policy, Infrastructure.
**Verdict:** The system is functionally fragile and architecturally dishonest.

## 1. Executive Summary

NNRT v0.3.0 presents itself as a robust, modular "Narrative-to-Neutral" engine. However, a deep review reveals it is a "Potemkin Village":
- **Interfaces are bypassed:** While `nnrt/nlp/interfaces.py` defines clean abstractions, the actual passes (`p32`, `p34`) directly import and depend on specific libraries (`spacy`), checking internal attributes (`token.dep_`) rather than using the defined contracts.
- **The "Policy" is blind:** The Policy Engine (`p50`) scans raw text strings for keywords, completely ignoring the high-fidelity Entity/Event graph built in previous phases. This makes sophisticated policies (e.g. "Redact Victim Names") impossible to implement reliably.
- **Infrastructure is ignored:** The presence of `scripts/00_search_native_jars.py` suggests a Java/Native integration requirement or existing capability that was completely ignored in favor of hardcoding `transformers` and `flan-t5` in `nnrt/render/constrained.py`.

## 2. Structural Integrity Vulnerabilities

### 2.1 The "Shadow Pipeline" (p40)
As identified in the initial audit, `p40_build_ir.py` contains a complete, inferior extraction logic (Regex + Noun Chunking) that runs *only* if `p32/p34` fail. This means:
1.  **Non-Determinism:** The system's behavior changes radically based on whether a single pronoun is resolved.
2.  **Untestable State:** verification requires testing both the "Smart" path and the "Shadow" path.
3.  **Ambiguity Hiding:** If `p32` fails to resolve ambiguity, `p40` might blindly extract a noun, masking the uncertainty the user explicitly wants to capture.

### 2.2 Interface Bypass
`p34_extract_events.py` should implement or use `EventExtractor`. Instead, it embeds `spacy` logic directly.
- **Consequence:** We cannot swap the backend. If we wanted to use a `native_jar` for extraction later, we would have to rewrite the pass entirely.
- **Fix:** Refactor `p34` to use `EventExtractor` interface, and implement a `SpacyEventExtractor` backend.

### 2.3 Policy Disconnect
`p50_policy.py` runs *after* `build_ir`. It has access to the full Context. Yet, `nnrt/policy/engine.py` only implements regex matching on `text`.
- **Consequence:** We calculate semantic roles (`AUTHORITY`, `SUBJECT`) in `p32` but cannot write a policy rule that uses them. We can only write rules for the word "Officer".
- **Fix:** Update Policy Engine to match against `Entity` and `Event` objects, not just text.

## 3. Infrastructure & DevOps Gaps

### 3.1 Hardcoded Models
`nnrt/render/constrained.py` hardcodes `google/flan-t5-small`.
- **Risk:** This assumes internet access (for HuggingFace) and Python environment compatibility.
- **Conflict:** The user environment contains scripts for searching "native jars" and "tiny jar". This suggests a requirement for local, possibly non-Python model execution which we completely missed.

### 3.2 fragility of Whitelists
`p32` relies on `GENERIC_SUBJECTS` = `{"manager", "employee", ...}`.
`p34` relies on `VERB_TYPES` = `{"resist", "run", ...}`.
- **Risk:** Any term outside these sets is invisible. "The supervisor" is ignored. "The suspect struggled" is ignored (if 'struggle' is not in list).
- **Fix:** Move from Whitelists to **Structural Heuristics** (e.g. "Any Noun in Subject Position is an Entity Candidate").

## 4. Code Quality & Standards

### 4.1 "Garbage Loops" & Confusing Paths
The codebase contains multiple paths to the same goal (e.g. `p30` extracts identifiers, `p32` can extract identifiers, `p40` can extract roles). This redundancy is "garbage logic"—it adds complexity without value.

### 4.2 Missing Unit Tests
We relied on `test_no_hallucination.py` (System Test) to validate logic. As proven during the audit, we lacked unit tests for basic components. `p32` creates a `Reporter` entity always, which caught us by surprise during initial testing. This proves we don't know our own components.

## 5. Remediation Plan

We cannot proceed to Alpha with this foundation. We must:

1.  **Phase A: Decouple & Interface**
    - Refactor `p32`/`p34` to use `interfaces.py`.
    - Implement `SpacyBackend` implementing these interfaces.
2.  **Phase B: Kill The Shadow**
    - Delete `p40` extraction logic.
    - If `p32` misses something, FIX `p32`.
3.  **Phase C: Connect Policy**
    - Update Policy Engine to support `EntityMatch` rules.
4.  **Phase D: Infrastructure Integration**
    - Investigate `native_jars` scripts.
    - abstract `render/constrained.py` to allow local/native model execution.

**Action:** Pause all feature work. Execute Remediation Plan.
