# STAGE 5 AUDIT: Domain System Completion

**Audit Date**: 2026-01-19
**Reference**: V1 structured.py (structured_py_git_version.py, 2019 lines)
**Milestone**: `.agent/milestones/stage_5_domains.md`

---

## Stage 5 Objective (from milestone document)

> Complete the domain system so that each domain is a self-contained configuration with:
> - Vocabulary (term synonyms and canonical forms)
> - Extraction patterns (entity roles, event types)
> - Classification rules (camera-friendly, follow-up, etc.)
> - Transformation rules (neutralization patterns)

---

## PART 1: VERIFY FILES CREATED

### Claimed Files

| File | Claimed | Status |
|------|---------|--------|
| `nnrt/domain/__init__.py` | Yes | ✅ EXISTS (1129 bytes) |
| `nnrt/domain/schema.py` | 270 lines | ✅ EXISTS (10897 bytes) |
| `nnrt/domain/loader.py` | 230 lines | ✅ EXISTS (7919 bytes) |
| `nnrt/domain/integration.py` | Yes | ✅ EXISTS (5246 bytes, 207 lines) |
| `nnrt/domain/configs/base.yaml` | 280 lines, 37 rules | ✅ EXISTS |
| `nnrt/domain/configs/law_enforcement.yaml` | 430 lines | ✅ EXISTS (488 lines) |

**Verdict: Files created as claimed ✅**

---

## PART 2: VERIFY DOMAIN CONTENT

### law_enforcement.yaml Analysis

| Section | Content | Lines |
|---------|---------|-------|
| domain | id, name, version, description, extends: base | 1-12 |
| vocabulary | actors (4), actions (4), locations (3), modifiers (3) | 17-143 |
| entity_roles | 8 roles (SUBJECT_OFFICER, REPORTER, etc.) | 148-248 |
| event_types | 7 types (USE_OF_FORCE, ARREST, etc.) | 253-340 |
| classification | camera_friendly, follow_up | 345-368 |
| transformations | 14 rules | 373-444 |
| diagnostics | 3 flags | 449-464 |
| metadata | typical_actors, locations, timeline | 469-487 |

**Total: 488 lines with comprehensive law enforcement domain configuration ✅**

---

## PART 3: VERIFY INTEGRATION

### integration.py Functions

| Function | Purpose | Status |
|----------|---------|--------|
| `domain_to_ruleset()` | Convert Domain → PolicyRuleset | ✅ EXISTS |
| `get_domain_ruleset()` | Get PolicyRuleset by domain ID | ✅ EXISTS |
| `get_vocabulary_replacements()` | Get derogatory→neutral map | ✅ EXISTS |
| `get_entity_role_keywords()` | Get role detection keywords | ✅ EXISTS |
| `get_event_type_verbs()` | Get event type verbs | ✅ EXISTS |
| `get_camera_friendly_verbs()` | Get camera-friendly verbs | ✅ EXISTS |

**Verdict: Integration layer exists ✅**

---

## PART 4: CRITICAL FINDING — DOMAIN SYSTEM IS UNUSED

### Search Results

| Search | Result |
|--------|--------|
| `from nnrt.domain` in passes/ | ❌ NO RESULTS |
| `from nnrt.domain` in render/ | ❌ NO RESULTS |
| `nnrt.domain` in tests/ | ❌ NO RESULTS |
| `get_domain` usage | ❌ ONLY IN domain/ module itself |
| `load_domain` usage | ❌ ONLY IN domain/ module itself |
| `domain_to_ruleset` usage | ❌ ONLY IN domain/ module itself |

**The domain system is COMPLETELY UNUSED by:**
- ❌ Any pass (p25, p32, p35, p46, etc.)
- ❌ The renderer (structured.py)
- ❌ The pipeline
- ❌ Any tests

---

## PART 5: V1 FUNCTIONALITY NOT PROVIDED BY DOMAIN

### V1 Entity Role Categorization (lines 151-167)

V1 uses inline constants:
```python
INCIDENT_ROLES = {'reporter', 'subject_officer', 'supervisor', ...}
POST_INCIDENT_ROLES = {'medical_provider', 'legal_counsel', 'investigator'}
BARE_ROLE_LABELS = {'partner', 'passenger', 'suspect', ...}
```

Domain provides via `entity_roles[].participation: incident|post_incident`

**But nobody calls `get_entity_role_keywords()` to use them!**

### V1 Camera-Friendly Logic (lines 424-553)

V1 uses inline patterns:
```python
CONJUNCTION_STARTS = [...]
VERB_STARTS = [...]
INTERPRETIVE_BLOCKERS = [...]
```

Domain provides via `classification.camera_friendly.disqualifying`

**But nobody calls the domain to get these patterns!**

### V1 Event Types (lines 628-633)

V1 uses:
```python
OBSERVABLE_EPISTEMIC_TYPES = ['direct_event', 'characterization', ...]
```

Domain provides via `event_types[].is_camera_friendly: true`

**But nobody calls `get_camera_friendly_verbs()` to use them!**

### V1 Follow-up Detection (lines 359-363)

V1 uses:
```python
FOLLOW_UP_PATTERNS = ['went to the emergency', 'went to the hospital', ...]
```

Domain provides via `classification.follow_up.time_contexts`

**But nobody reads the domain configuration!**

---

## PART 6: WHAT WOULD BE NEEDED FOR DOMAIN INTEGRATION

For the domain system to actually replace V1 inline logic:

### 1. p32_extract_entities.py should use domain entity_roles
```python
from nnrt.domain import get_domain
domain = get_domain('law_enforcement')
role_keywords = domain.get_entity_role_keywords()
```

### 2. p35_classify_events.py should use domain classification
```python
from nnrt.domain import get_domain
domain = get_domain('law_enforcement')
camera_friendly_verbs = domain.get_camera_friendly_verbs()
```

### 3. structured.py should use domain vocabulary
```python
from nnrt.domain import get_vocabulary_replacements
replacements = get_vocabulary_replacements(domain)
```

### 4. PolicyEngine should load domain rules
```python
from nnrt.domain import get_domain_ruleset
ruleset = get_domain_ruleset('law_enforcement')
engine.load_ruleset(ruleset)
```

**NONE of this integration exists!**

---

## PART 7: COMPARISON SUMMARY

### Domain YAML vs V1 Inline Logic

| Feature | Domain YAML | V1 Inline | Used? |
|---------|-------------|-----------|-------|
| Entity roles | 8 roles defined | INCIDENT_ROLES, POST_INCIDENT_ROLES | ❌ |
| Vocabulary | 17+ items | Hardcoded in structured.py | ❌ |
| Camera-friendly verbs | 40+ verbs | VERB_STARTS, CONJUNCTION_STARTS | ❌ |
| Follow-up patterns | time_contexts | FOLLOW_UP_PATTERNS | ❌ |
| Transformations | 14 rules | INTERPRETIVE_STRIP_WORDS | ❌ |
| Event types | 7 types | OBSERVABLE_EPISTEMIC_TYPES | ❌ |

---

## STAGE 5 VERDICT

### Status: ❌ **INCOMPLETE — Domain System Created But Not Integrated**

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Domain schema created | Yes | Yes | ✅ |
| Domain YAML files created | 2 | 2 | ✅ |
| Integration module created | Yes | Yes | ✅ |
| Passes use domain | Yes | No | ❌ |
| Renderer uses domain | Yes | No | ❌ |
| Tests verify domain | Yes | No | ❌ |
| V1 inline logic replaced | Yes | No | ❌ |

### What Was Done
1. ✅ Created `nnrt/domain/` module with schema, loader, integration
2. ✅ Created `law_enforcement.yaml` (488 lines) with comprehensive config
3. ✅ Created `base.yaml` with universal transformations
4. ✅ Created integration functions to convert Domain → PolicyRuleset
5. ✅ Domain extends mechanism works

### What Was NOT Done
1. ❌ NO passes import or use the domain system
2. ❌ NO renderer imports or uses the domain system
3. ❌ NO tests verify domain functionality
4. ❌ V1 inline patterns NOT replaced by domain lookups
5. ❌ PolicyEngine NOT automatically loading domain rules

### Critical Issue

**The domain system is a complete dead-end.** It was designed and implemented but never connected to actual code. Meanwhile, V1's `structured.py` still has 335 inline patterns that the domain was supposed to replace.

The milestone claims "Phase 4: Integration — COMPLETE ✅" but integration means "PolicyEngine CAN convert domain to ruleset", NOT "passes actually USE the domain".

---

## REMEDIATION REQUIRED

To complete Stage 5 properly:

1. **Connect domain to p32_extract_entities** — Use domain entity_roles for role detection
2. **Connect domain to p35_classify_events** — Use domain event_types for camera-friendly classification
3. **Connect domain to PolicyEngine init** — Auto-load domain ruleset at startup
4. **Connect domain to structured.py** — Use domain vocabulary replacements
5. **Add tests** — Verify domain loading, conversion, and usage
6. **Remove V1 inline patterns** — After domain connection verified

---

*Stage 5 Audit — 2026-01-19*
