# Pre-Alpha Audit & Critical Analysis

**Date:** 2026-01-14
**Status:** CRITICAL REVIEW
**Verdict:** Pre-Alpha v0.3.0 is **NOT** conceptually complete due to structural debt.

## 1. Executive Summary
While the automated validation suite passes, the underlying architecture has degraded into a "hybrid" state where legacy logic (`p40_build_ir.py`) competes with new high-fidelity passes (`p32`, `p34`). This creates non-deterministic duplicate paths, reduces maintainability, and violates the "Infrastructure First" principle. The project improperly declared "Ready" by masking these structural flaws with successful integration tests.

## 2. Critical Findings

### 2.1 The "Fallback Trap" (Duplicated Logic)
The most severe issue is the conditional logic in `p40_build_ir.py`:
```python
run_entity_extraction = len(entities) == 0
run_event_extraction = len(events) == 0
```
This implies the system has **two completely different ways** of extracting meaning:
1.  **Path A (High Fidelity):** `p32` (Pronoun Resolution, Named Entities) + `p34` (Dependency Parsing).
2.  **Path B (Legacy Fallback):** `p40` (Naive Noun Chunking + Regex).

**Impact:** consistency is impossible. If `p32` yields zero entities (e.g., input has no people), `p40` suddenly wakes up and runs a totally different algorithm (`_identify_role`) that might hallucinate or misclassify terms. Debugging becomes a nightmare of "which pass ran?".

### 2.2 Fragmented Responsibilities
Entity extraction logic is scattered across **three** places:
1.  `p30_extract_identifiers.py`: Extracts regex patterns (e.g. "Officer Smith").
2.  `p32_extract_entities.py`: Extracts logic-based entities (e.g. "He", "The suspect").
3.  `p40_build_ir.py`: Extracts "Legacy" entities via `_identify_role`.

**Impact:** `p32` tries to read `p30`'s output, but if `p30` misses something and `p32` misses it, `p40` might invent it. We have multiple "sources of truth" for what constitutes an entity.

### 2.3 Skipped Tests (Quality Gap)
We rushed to Integration/Validation testing (`test_no_hallucination.py`) without implementing **Unit Tests** for the complex logic in `p32` and `p34`.
*   **Missing:** `tests/passes/test_p32_entities.py` (Verify pronoun resolution isolation).
*   **Missing:** `tests/passes/test_p34_events.py` (Verify verb whitelist behavior).
*   **Impact:** We are verifying the *whole* pipeline output but cannot guarantee the reliability of individual components.

### 2.4 Fragile Validation (Exemptions)
In `test_no_hallucination.py`, we explicitly exempted specific labels:
```python
if ent.label == "Individual (Unidentified)":
    continue
```
This mask a rigid behavior in the system. While necessary for the test to pass now, it represents a "magic string" dependency that shouldn't be hardcoded in verification suites.

### 2.5 "Ugly" Hacks
*   **Bracket Removal Hack:** In `p40`, we modified `_build_neutral_description` to remove brackets `[]` solely to pass the hallucination test. This fixes the symptom (hallucination flag) but ignores the root cause (why are we adding brackets in the first place? And why is `p40` running?).
*   **Generic Subjects Hardcoding:** `p32` relies on a hardcoded set of `GENERIC_SUBJECTS` ("partner", "manager", "employee"). This brittle whitelist approach will fail as soon as a new noun appears (e.g. "The supervisor").

## 3. Corrective Action Plan

We must refactor before proceeding to Phase 6 (Alpha).

### Phase A: Architecture Cleanup
1.  **Purge Legacy Extraction:** Remove ALL extraction logic from `p40_build_ir.py`.
    *   `p40` becomes a strict assembler (`assemble_ir`).
    *   If `p32`/`p34` produce nothing, the result is *nothing* (transparent failure), not a fallback to inferior logic.
2.  **Consolidate Entity Logic:**
    *   Ensure `p32` is the **single source of truth** for Entity creation.
    *   If `p30` (identifiers) is valuable, `p32` must explicitly consume and structure them, and `p30` should arguably be merged into `p32` or strictly defined as a "pre-processor".

### Phase B: Test-Driven Hardening
1.  **Create Unit Tests:** Implement `tests/passes/` suite.
    *   Test `p32` with small fragments ("He ran").
    *   Test `p34` with specific verbs.
2.  **Remove Magic Strings:** Refactor validation to handle generated labels robustly (e.g. verify the *pattern* of generated labels rather than hardcoded exemptions).

### Phase C: Logic Robustness
1.  **Replace Whitelists:** Move away from `GENERIC_SUBJECTS` set. Use dependency parsing to identify **ANY** Subject Noun as a potential entity candidate, rather than a hardcoded list.
    *   "The [NOUN]" in subject position -> Candidate.

## 4. Conclusion
The current "Pre-Alpha" is a functional prototype but an architectural prototype. To meet the "DevOps / Infrastructure First" standard, we must execute **Phase A (Cleanup)** and **Phase B (Testing)** immediately.
