# Deep Architectural Analysis — NNRT Refactoring

## The Vision You're Describing

You said:
> "we have a lot of information in the structured output which contain valuable information that are themselves parts / pieces of the decomposition for recomposition"

This reveals a **fundamental architectural shift**:

**Current**: Decomposition → (mixing) → Single Output
**Target**: Decomposition → Classification → Selection → **Multiple Recomposition Modes**

The "pieces of decomposition" are:
- `AtomicStatement` - the core unit
- `Entity` - actors and objects
- `Event` - discrete occurrences
- `TimelineEntry` - temporal positioning
- `SpeechAct` - quotes/dialogue
- `EvidenceClassification` - verification status
- And more...

These ARE the **building blocks for recomposition**. The current system treats rendering as "formatting" but it's actually doing BOTH classification AND composition in the wrong place.

---

## The Four Layers That Should Exist

### Layer 1: DECOMPOSITION (Pipeline Passes p00-p50)
**Purpose**: Break narrative into atomic pieces, extract structure

**Input**: Raw narrative text
**Output**: IR with atoms (statements, entities, events, timeline)

**What Happens**:
- Segmentation (p10)
- Span tagging (p20)
- Statement decomposition (p26)
- Entity extraction (p32)
- Event extraction (p34)
- Timeline building (p44)

**Rules Used**: 
- Structural patterns (clause boundaries, connectors)
- Extraction patterns (names, dates, quotes)

**Status**: ✅ Largely exists, but some extraction patterns are domain-specific

---

### Layer 2: CLASSIFICATION (Pipeline Passes p25-p48 + NEW)
**Purpose**: Tag every atom with semantic metadata

**Input**: IR atoms
**Output**: IR atoms with classification fields filled

**What Should Happen**:
| Atom Type | Classification Fields |
|-----------|----------------------|
| AtomicStatement | `epistemic_type`, `provenance_status`, `is_camera_friendly`, `is_fragment`, `neutralization_applied` |
| Entity | `role`, `participation`, `gender`, `is_valid_actor` |
| Event | `camera_friendly`, `actor_resolved`, `is_complete`, `is_follow_up` |
| TimelineEntry | `quality_score`, `has_resolved_pronouns` |
| SpeechAct | `speaker_resolved`, `is_valid_quote` |

**Rules Used**:
- Epistemic rules (p27) - patterns for inference, self-report, etc.
- Camera-friendly rules - what's observable vs interpretive
- Validation rules - is_complete, has_actor, etc.
- Domain vocabulary - role classification, actor validation

**Status**: ⚠️ SPLIT between pipeline (p27, p48) and renderer (structured.py)

---

### Layer 3: SELECTION (Does not clearly exist)
**Purpose**: Choose which atoms to include based on output mode

**Input**: Classified IR
**Output**: Selected subset of atoms

**Modes**:
| Mode | Selection Criteria |
|------|-------------------|
| `strict` | Only camera_friendly=True, is_complete=True, has_actor=True |
| `full` | Everything, with proper attribution |
| `events_only` | Only Event atoms |
| `timeline_only` | Only TimelineEntry atoms |
| `recomposition` | Atoms needed for narrative reconstruction |

**Status**: ❌ Does not exist. Selection logic is scattered in renderer.

---

### Layer 4: RENDERING / RECOMPOSITION
**Purpose**: Format selected atoms into output

**Input**: Selected + classified atoms
**Output**: Formatted output (text, JSON, reconstructed narrative)

**Modes**:
| Mode | Output |
|------|--------|
| `structured_report` | Current plain-text report |
| `json` | Machine-readable |
| `recomposed_narrative` | Reconstructed neutral narrative |

**Status**: ⚠️ Exists (structured.py) but doing Layer 2 + 3 work

---

## What's Wrong: The Layer Violations

### The Renderer is Doing Classification (Layer 2 work in Layer 4)

```python
# In structured.py - this is CLASSIFICATION, not RENDERING
INTERPRETIVE_DISQUALIFIERS = ['horrifying', 'brutal', ...]

def is_strict_camera_friendly(text: str):  # This classifies!
    if first_word in CONJUNCTION_STARTS:
        return (False, "conjunction_start")
```

**Problem**: Classification logic is done at render-time, not stored on atoms.

### The Renderer is Doing Selection (Layer 3 work in Layer 4)

```python
# In structured.py - this is SELECTION, not RENDERING
for event in events:
    neutralized = neutralize_for_observed(event.description)
    passed, reason = is_strict_camera_friendly(neutralized)
    if not passed:
        rejected_events.append(event)  # Selection!
        continue
    strict_events.append(event)  # Selection!
```

**Problem**: Selection happens during rendering, not as a separate phase.

### The Classification Fields Are Not On The Atoms

The `AtomicStatement` has many fields, but NOT:
- `is_camera_friendly` - computed at render time
- `is_follow_up_event` - computed at render time
- `neutralized_text` - computed at render time (on Segment, not AtomicStatement)

These should be PRE-COMPUTED in the pipeline.

---

## The Rule System: Current State

### THREE Types of "Rules" Currently Exist

**1. Policy Rules (YAML)** — Used by PolicyEngine
```yaml
# In rulesets/*.yaml
- id: inflam_brutal
  match:
    type: keyword
    patterns: ["brutal"]
  action: remove
```
**Applied in**: p50_policy, p70_render
**Used for**: Text transformation

**2. Pattern Lists (Python)** — Scattered in passes
```python
# In p27_epistemic_tag.py
STATE_INJURY_PATTERNS = [
    r'\bwrists?\s+were\s+(bleeding|bruised)\b',
    ...
]
```
**Applied in**: Individual passes
**Used for**: Classification (epistemic tagging)

**3. Inline Logic (Python)** — In renderer
```python
# In structured.py
CONJUNCTION_STARTS = ['but', 'and', 'when', ...]
if first_word in CONJUNCTION_STARTS:
    return (False, "conjunction_start")
```
**Applied in**: Renderer
**Used for**: Classification + Selection at render time

### These Should ALL Be Unified Under the Policy System

But the Policy System needs to be EXTENDED:

| Current Policy | Extended Policy |
|----------------|-----------------|
| Match → Transform text | Match → Transform text |
| | Match → Classify atom |
| | Match → Validate atom |
| Validation (basic) | Validation (extended) |
| | Selection predicates |

---

## The Domain System: What It Should Look Like

### Current: Domains as Vocabulary Only

```yaml
# domains/law_enforcement.yaml
rules:
  - id: le_cop_singular
    patterns: ["cop"]
    action: replace
    replacement: "officer"
```

### Target: Domains as Complete Configuration

```yaml
# domains/law_enforcement.yaml
domain: law_enforcement

vocabulary:
  roles:
    incident:
      - reporter
      - subject_officer
      - witness_civilian
    post_incident:
      - medical_provider
      - legal_counsel
  
  titles:
    authority:
      - officer
      - sergeant
      - detective
    medical:
      - dr
      - nurse
  
  items:
    contraband:
      - cocaine
      - heroin
    weapons:
      - gun
      - knife

extraction:
  patterns:
    officer_name: r'\b(Officer|Sergeant|Detective)\s+[A-Z][a-z]+'
    badge_number: r'badge\s*#?\s*(\d{4,5})'

classification:
  camera_friendly:
    valid_actor_patterns:
      - r'^Officer\s+\w+'
      - r'^Sergeant\s+\w+'
    invalid_actor_patterns:
      - r'^He\s+'
      - r'^She\s+'

transformation:
  rules:
    - id: le_cop_to_officer
      patterns: ["cop"]
      action: replace
      replacement: "officer"
```

---

## The Composition Pattern

You said:
> "we will need to find a way to augment those list/array that will combine if selected (all by default)"

### Current: Profile Includes

```yaml
# profiles/law_enforcement.yaml
includes:
  - _core/quote_protection.yaml
  - _categories/inflammatory_language.yaml
  - domains/law_enforcement.yaml
```

### Target: Multi-Level Composition

```yaml
# profiles/law_enforcement_medical.yaml
profile:
  id: law_enforcement_medical
  
base:
  - _core/  # All core rules
  - common/ # Domain-agnostic

domains:
  primary: law_enforcement
  secondary:
    - medical  # Medical terminology in law enforcement context

overrides:
  - id: medical_diagnosed
    priority: +10  # Increase priority in this context

disabled:
  - le_violence_modifier  # Too aggressive for medical context

custom:
  - path: ./my_department_rules.yaml
```

### Composition Resolution

```python
def compose_ruleset(profile: Profile) -> ComposedRuleset:
    """
    Compose a complete ruleset from profile specification.
    
    1. Load base rules (always included)
    2. Load primary domain
    3. Load secondary domains (with lower priority)
    4. Apply overrides
    5. Remove disabled rules
    6. Add custom rules
    """
```

---

## The Recomposition Vision

You said:
> "Then when we are done with this refactor (a while later) we will create the recomposition version, keeping always the current basic neutralization as example of original neutralized"

### What This Means Architecturally

**Mode 1: Neutralized Report (Current)**
- Takes classified atoms
- Renders as structured report
- Shows sections: OBSERVED EVENTS, QUOTES, CLAIMS, etc.

**Mode 2: Recomposed Narrative (Future)**
- Takes classified atoms
- Reconstructs as flowing prose
- Maintains neutrality but reads like a narrative
- Example: "According to the reporter, at approximately 11:30 PM..."

### The Atoms Enable Both

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLASSIFIED IR                           │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │
│  │ Statement 1  │ │ Statement 2  │ │ Statement 3  │  ...       │
│  │ epistemic:   │ │ epistemic:   │ │ epistemic:   │            │
│  │  observation │ │  self_report │ │  inference   │            │
│  │ camera: ✓    │ │ camera: ✗    │ │ camera: ✗    │            │
│  │ actor: Ofc.J │ │ actor: Rptr  │ │ actor: Rptr  │            │
│  └──────────────┘ └──────────────┘ └──────────────┘            │
└─────────────────────────────────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
          ▼               ▼               ▼
    ┌──────────┐   ┌──────────┐   ┌──────────┐
    │ SELECTION│   │ SELECTION│   │ SELECTION│
    │  strict  │   │   full   │   │ recomp.  │
    └──────────┘   └──────────┘   └──────────┘
          │               │               │
          ▼               ▼               ▼
    ┌──────────┐   ┌──────────┐   ┌──────────┐
    │ RENDER   │   │ RENDER   │   │ RENDER   │
    │ report   │   │ report   │   │narrative │
    └──────────┘   └──────────┘   └──────────┘
```

---

## The Actual Refactoring Scope

This is NOT just "move arrays to YAML". This is:

### 1. Define the Canonical Atom Schema
- What fields does each atom type need?
- Which fields are set by decomposition vs classification?
- Add missing fields: `is_camera_friendly`, `neutralized_text`, `is_complete`

### 2. Create the Classification Layer
- NEW pass(es) that classify atoms
- Move classification logic from renderer to pipeline
- Classification rules loaded from Policy System

### 3. Create the Selection Layer
- NEW pass or component that selects atoms for output
- Configurable per output mode
- Selection predicates loaded from configuration

### 4. Extend the Policy System
- Add `classify` rule type
- Add `validate` rule type
- Add domain vocabulary beyond just transformation rules

### 5. Simplify the Renderer
- Remove ALL classification logic
- Remove ALL selection logic
- Keep ONLY formatting logic

### 6. Unify Scattered Patterns
- Consolidate p72_safety_scrub with policy rules
- Consolidate p27 patterns as classification rules in YAML
- Remove duplicate patterns between files

### 7. Prepare for Recomposition
- Ensure IR has all fields needed
- Create recomposition renderer (future)

---

## Migration Reality

This is not a "Phase 1-4 over days" situation. This is:

### Foundation Work (Weeks)
1. Define extended atom schema
2. Design Policy System extensions
3. Design Selection layer

### Incremental Migration (Months)
4. Create one classification rule type, test with one pattern set
5. Migrate one category of patterns
6. Repeat for all categories
7. Create Selection layer
8. Migrate renderer to display-only
9. Add recomposition renderer

### The "Keep Current as Example"
Throughout, the current output format should be preserved as the default, with tests ensuring no regression.

---

## Summary: The Actual Scope

| Aspect | Surface View (What I Said Before) | Deep View (What You're Describing) |
|--------|-----------------------------------|-----------------------------------|
| Arrays | Move to YAML | Part of unified Policy Schema |
| Rules | Deduplicate | Extend Policy Engine with new rule types |
| Domains | Already exists | Extend to full vocabulary + patterns + classification |
| Renderer | Simplify | Remove 2 layers (classification + selection) |
| Output | Single format | Multiple modes (report, narrative, JSON) |
| Architecture | Cleanup | Add Selection layer, extend Classification layer |

You were right - I was seeing the surface. The real refactor is about:

1. **Layer separation** (decomposition vs classification vs selection vs rendering)
2. **Atom-centric design** (all metadata on atoms, not computed at render time)
3. **Unified rule system** (one Policy Engine for all rule types)
4. **Domain completeness** (vocabulary + patterns + classification + transformation)
5. **Output flexibility** (multiple recomposition modes)
6. **Future recomposition** (narrative reconstruction from atoms)

---

*Deep Analysis — 2026-01-18*
