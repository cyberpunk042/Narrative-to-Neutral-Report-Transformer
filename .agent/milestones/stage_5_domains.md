# Stage 5: Domain System Completion

**Created**: 2026-01-18
**Status**: Phase 4 Complete ✅ (Domain System Fully Functional)

**Latest Progress (2026-01-18)**:
- ✅ Phase 1: Domain Schema - COMPLETE
  - Created `nnrt/domain/schema.py` with Pydantic models
  - Created `nnrt/domain/loader.py` with load/cache/merge functions
- ✅ Phase 2: Migrate Existing Rules - COMPLETE
  - Created `base.yaml` with 37 universal transformations
  - Migrated rules from _categories/ files
- ✅ Phase 3: Domain Composition - COMPLETE
  - Inheritance working: law_enforcement extends base
  - 50 rules total (37 base + 13 domain-specific)
- ✅ Phase 4: Integration - COMPLETE
  - Created `nnrt/domain/integration.py` - Bridge to PolicyEngine
  - Domain converts to PolicyRuleset (50 rules)
  - Vocabulary, entity roles, event types all extractable
- All 602 tests pass

## Objective

Complete the domain system so that each domain is a self-contained configuration with:
- Vocabulary (term synonyms and canonical forms)
- Extraction patterns (entity roles, event types)
- Classification rules (camera-friendly, follow-up, etc.)
- Transformation rules (neutralization patterns)

Enable clean domain composition and provide a template for adding new domains.

---

## Current State Analysis

### What Exists

The current domain system is partially implemented in `nnrt/policy/rulesets/`:

```
profiles/
  law_enforcement.yaml    # Profile that includes rule files
  
domains/
  law_enforcement.yaml    # Domain-specific transformation rules (167 lines)
  
_categories/              # Domain-agnostic transformations
  inflammatory_language.yaml
  intent_attribution.yaml
  interpretation.yaml
  legal_conclusions.yaml
  loaded_verbs.yaml
  manner_adverbs.yaml
  
_classification/          # Event classification rules
  camera_friendly.yaml
  neutralization.yaml
  
_context/                 # Context detection rules
  force_context.yaml
  injury_context.yaml
  timeline_context.yaml
  charge_context.yaml
  
_extraction/              # Entity extraction rules
  entity_roles.yaml       # Role patterns (6KB)
  
_grouping/                # Statement grouping
  statement_groups.yaml
```

### What's Missing

1. **Domain Schema Definition**: No formal specification of what a domain contains
2. **Vocabulary System**: Term synonyms/canonicalization not in domain config
3. **Domain Composition**: No mechanism for combining domains
4. **Domain Auto-Detection**: No automatic domain detection from narrative
5. **Template/Scaffolding**: No easy way to add new domains
6. **Validation**: No schema validation for domain configurations

---

## Proposed Domain Schema

### Complete Domain Structure

```yaml
domain:
  id: law_enforcement
  name: "Law Enforcement"
  version: "1.0"
  description: "Police encounters, use of force, arrests"

# ============================================================================
# VOCABULARY
# ============================================================================
vocabulary:
  # Canonical terms with synonyms
  actors:
    officer:
      synonyms: ["cop", "police officer", "patrolman", "peace officer"]
      derogatory: ["pig", "thug", "goon", "bully"]
      neutral_form: "officer"
    
    subject:
      synonyms: ["suspect", "perpetrator", "offender"]
      derogatory: ["criminal", "perp"]
      neutral_form: "individual"
    
    witness:
      synonyms: ["bystander", "observer"]
      neutral_form: "witness"

  actions:
    arrest:
      synonyms: ["apprehend", "take into custody", "collar"]
      neutral_form: "arrest"
    
    use_of_force:
      inflammatory: ["brutality", "violence", "attack"]
      neutral_form: "use of force"

  locations:
    patrol_car:
      synonyms: ["cruiser", "squad car", "police vehicle"]
      neutral_form: "patrol vehicle"

# ============================================================================
# ENTITY ROLES
# ============================================================================
entity_roles:
  - role: SUBJECT_OFFICER
    patterns:
      - "Officer {name}"
      - "Sergeant {name}"
      - "Detective {name}"
      - "Deputy {name}"
    badge_linkable: true
    participation: incident
    
  - role: REPORTER
    patterns:
      - "I"
      - "reporter"
      - "complainant"
    participation: incident
    is_primary: true
    
  - role: MEDICAL_PROVIDER
    patterns:
      - "Dr. {name}"
      - "Doctor {name}"
      - "EMT"
      - "paramedic"
      - "nurse"
    participation: post_incident
    
  - role: WITNESS_CIVILIAN
    patterns:
      - "witness"
      - "bystander"
    participation: incident

# ============================================================================
# EVENT TYPES
# ============================================================================
event_types:
  - type: USE_OF_FORCE
    verbs: ["grabbed", "pushed", "restrained", "struck", "tackled", "slammed"]
    requires_actor: true
    requires_target: true
    is_camera_friendly: true
    
  - type: ARREST
    verbs: ["arrested", "handcuffed", "detained", "apprehended"]
    requires_actor: true
    is_camera_friendly: true
    
  - type: VERBAL
    verbs: ["yelled", "shouted", "screamed", "ordered", "commanded"]
    is_camera_friendly: false  # Tone is subjective
    
  - type: MEDICAL
    verbs: ["examined", "treated", "diagnosed", "bandaged"]
    typical_actor_role: MEDICAL_PROVIDER
    participation: post_incident

# ============================================================================
# CLASSIFICATION RULES
# ============================================================================
classification:
  camera_friendly:
    # What makes an event observable by camera
    required:
      - has_named_actor
      - has_physical_action
    disqualifying:
      - contains_internal_state
      - contains_intent_attribution
      - contains_characterization
      
  follow_up:
    # Post-incident actions
    actor_roles: [MEDICAL_PROVIDER, INVESTIGATOR, LEGAL_COUNSEL]
    time_context: ["later", "afterward", "subsequently", "the next day"]
    
  timeline_relevant:
    # Events suitable for timeline
    requires:
      - has_time_reference
      - or: [is_camera_friendly, is_follow_up]

# ============================================================================
# TRANSFORMATION RULES
# ============================================================================
transformations:
  # Replacements
  - id: le_cop_to_officer
    match: ["cop", "cops"]
    replace: ["officer", "officers"]
    priority: 60
    
  - id: le_brutality
    match: ["brutality", "police brutality", "police violence"]
    replace: "use of force"
    priority: 85
    
  # Removals
  - id: le_violent_modifier
    match: ["violent"]
    remove: true
    context: ["before_officer", "before_cop"]
    priority: 70
    
  # Preservations (do not transform)
  - id: le_preserve_legal
    match: ["charged with assault", "assault on an officer"]
    preserve: true
    priority: 120
    
  # Attributions
  - id: le_no_reason
    match: ["for no reason", "without any reason"]
    replace: "-- reporter states no cause was given --"
    priority: 90

# ============================================================================
# DIAGNOSTICS
# ============================================================================
diagnostics:
  flags:
    - code: PHYSICAL_ACTION_DESCRIBED
      on_match: ["grabbed", "restrained", "handcuffed"]
      level: info
      message: "Physical action described - preserving factual content"
      
    - code: FORCE_DESCRIBED
      on_match: ["force", "struck", "hit"]
      level: warning
      message: "Use of force described - verify details"

# ============================================================================
# DOMAIN METADATA
# ============================================================================
metadata:
  typical_actors:
    - SUBJECT_OFFICER
    - REPORTER
    - WITNESS_CIVILIAN
    - MEDICAL_PROVIDER
  typical_locations:
    - traffic_stop
    - street
    - precinct
    - hospital
  typical_timeline:
    - incident
    - aftermath
    - medical_evaluation
    - investigation
```

---

## Implementation Plan

### Phase 1: Domain Schema ✅ COMPLETE

**Tasks**:
1. ✅ Create domain schema Pydantic models in `nnrt/domain/schema.py`
2. ✅ Create domain loader in `nnrt/domain/loader.py`
3. ✅ Create schema validation (Pydantic validates on load)

**Files created**:
- ✅ `nnrt/domain/__init__.py`
- ✅ `nnrt/domain/schema.py` - Domain Pydantic models (270 lines)
- ✅ `nnrt/domain/loader.py` - Load, cache, merge functions (230 lines)
- ✅ `nnrt/domain/configs/law_enforcement.yaml` - Complete domain (430 lines)

### Phase 2: Migrate Existing Rules ✅ COMPLETE

**Tasks**:
1. ✅ Created `base.yaml` domain with universal rules (37 transformations)
2. ✅ Migrated vocabulary from `_categories/` files:
   - inflammatory_language.yaml (13 rules)
   - loaded_verbs.yaml (10 rules)
   - intent_attribution.yaml (13 rules)
   - legal_conclusions.yaml (3 rules)
   - interpretation.yaml (3 rules)
3. ✅ Law enforcement domain extends base

**Files created**:
- ✅ `nnrt/domain/configs/base.yaml` - Universal rules (280 lines)
- ✅ Updated `law_enforcement.yaml` with `extends: base`

### Phase 3: Domain Composition ✅ COMPLETE

**Tasks**:
1. ✅ Domain composition via `extends: base` field
2. ✅ Merge logic in `loader.py` for lists and vocabularies
3. ✅ Law enforcement = base (37 rules) + LE-specific (13 rules) = 50 rules

**Verified**:
```
Base domain: 37 transformation rules
Law Enforcement domain: 50 rules (37 inherited + 13 domain-specific)
```

**Example**:
```yaml
# domains/medical_malpractice.yaml
extends: base
domain:
  id: medical_malpractice
  name: "Medical Malpractice"
  
vocabulary:
  # Domain-specific terms...
```

### Phase 4: Integration ✅ COMPLETE

**Tasks**:
1. ✅ Created `nnrt/domain/integration.py` - Bridge module
2. ✅ `domain_to_ruleset()` - Convert Domain to PolicyRuleset
3. ✅ `get_vocabulary_replacements()` - Get derogatory→neutral map
4. ✅ `get_entity_role_keywords()` - Get role detection keywords
5. ✅ `get_event_type_verbs()` - Get event type verbs
6. ✅ `get_camera_friendly_verbs()` - Get observable action verbs

**Verified**:
```
Domain converted to PolicyRuleset:
  Name: law_enforcement
  Rules: 50
  Description: Domain: Law Enforcement

Vocabulary replacements: 17 total
  "cop" -> "officer"
  "pig" -> "officer"
  ...
  
Camera-friendly verbs: 40 total
```

### Phase 5: Documentation & Template (Optional)

**Tasks**:
1. Create `docs/adding_a_domain.md`
2. Create domain template/scaffolding command
3. Add domain examples

---

## Success Criteria

1. **Single-file domain**: Each domain is one YAML file with all configuration
2. **Schema validation**: Domain YAML is validated on load
3. **Vocabulary normalization**: Term synonyms are handled by domain
4. **Backward compatibility**: Existing functionality preserved
5. **Easy extension**: New domains can be added by copying template
6. **Tests pass**: All 602 tests continue to pass

---

## Dependencies

- Stage 4 (Rule System) ✅ - Rules system foundation exists
- Stage 0 (Schema) ✅ - Atom classification fields populated
- Stage 1 (Classification) ✅ - Classification passes exist

No blockers.

---

## Notes

### Why Complete Domain System?

Currently, domain configuration is scattered across multiple files:
- `domain/law_enforcement.yaml` - Transformation rules
- `_extraction/entity_roles.yaml` - Entity patterns
- `_categories/*.yaml` - Shared vocabulary patterns
- Hardcoded patterns in Python passes

A complete domain system would:
1. Make domains self-contained and portable
2. Enable easy creation of new domains
3. Reduce reliance on hardcoded patterns
4. Support domain composition (medical + legal, etc.)

### Future: Domain Auto-Detection

Not in scope for Stage 5, but the system should support:
```python
domain = detect_domain(text)  # Returns 'law_enforcement', 'medical', etc.
```

This would use vocabulary patterns to identify the most likely domain.

---

*Document created: 2026-01-18*
