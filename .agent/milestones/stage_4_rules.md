# Stage 4: Rule System Unification

**Status**: ✅ CORE COMPLETE  
**Dependencies**: Stage 3 (Renderer) ✅ COMPLETE  
**Estimated Effort**: 40-60 hours (2-3 weeks)

---

## Objective

Unify all rule types under the Policy Engine. Consolidate duplicated patterns scattered across Python files into YAML configurations. Define a single schema for all rules (transformation, classification, validation, extraction, context).

---

## Current State Analysis

### 1. Policy Engine (Current Capabilities)

The PolicyEngine (`nnrt/policy/engine.py`) currently supports:

**Rule Actions**:
- `REMOVE` — Delete matched text
- `REPLACE` — Replace matched text
- `REFRAME` — Wrap with template (e.g., "described as X")
- `FLAG` — Mark for review
- `REFUSE` — Block transformation
- `PRESERVE` — Protect from transformation
- `CLASSIFY` — Set a classification field (V7/Stage 1)
- `DISQUALIFY` — Mark as not camera-friendly (V7/Stage 1)
- `DETECT` — Detect pattern presence (V7/Stage 1)
- `STRIP` — Remove words for neutralization (V7/Stage 1)

**Match Types**:
- `keyword` — Word boundary matching
- `phrase` — Exact phrase matching
- `regex` — Regular expression
- `quoted` — Within quotes
- `span_label` — Match span labels
- `entity_role` — Match by entity role (semantic)
- `entity_type` — Match by entity type (semantic)
- `event_type` — Match by event type (semantic)

**Current YAML Files** (18 files):
```
rulesets/
├── base.yaml                    # Core ruleset
├── _categories/                 # Transformation rules
│   ├── inflammatory_language.yaml
│   ├── intent_attribution.yaml
│   ├── interpretation.yaml
│   ├── legal_conclusions.yaml
│   ├── loaded_verbs.yaml
│   └── manner_adverbs.yaml
├── _classification/             # Classification rules
│   ├── camera_friendly.yaml
│   └── neutralization.yaml
├── _core/                       # Core patterns
│   ├── certainty.yaml
│   ├── extreme_modifiers.yaml
│   ├── quote_protection.yaml
│   └── similes.yaml
├── domains/                     # Domain configs
│   └── law_enforcement.yaml
└── profiles/                    # Profile configs
    ├── law_enforcement.yaml
    └── medical.yaml
```

### 2. Scattered Pattern Constants

Pattern constants are scattered across **6+ Python files**:

| File | Patterns | Purpose |
|------|----------|---------|
| `p25_annotate_context.py` | CHARGE_PATTERNS, PHYSICAL_FORCE_PATTERNS, INJURY_PATTERNS, TIMELINE_PATTERNS, CREDIBILITY_PATTERNS, SARCASM_PATTERNS, NEGATION_PATTERNS, etc. | Context detection |
| `p32_extract_entities.py` | MEDICAL_ROLE_PATTERNS, LEGAL_ROLE_PATTERNS, INVESTIGATOR_PATTERNS, SUPERVISOR_PATTERNS | Role detection |
| `p46_group_statements.py` | ENCOUNTER_PATTERNS, MEDICAL_PATTERNS, WITNESS_PATTERNS, OFFICIAL_PATTERNS, EMOTIONAL_PATTERNS, etc. | Statement grouping |
| `p44a_temporal_expressions.py` | DATE_PATTERNS, TIME_PATTERNS, RELATIVE_PATTERNS | Temporal extraction |
| `ir/enums.py` | INTENT_ATTRIBUTION_PATTERNS, LEGAL_CHARACTERIZATION_PATTERNS, NARRATIVE_GLUE_PATTERNS | Classification |
| `render/structured.py` | INTERPRETIVE_DISQUALIFIERS, FOLLOW_UP_PATTERNS, SOURCE_DERIVED_PATTERNS, INTERPRETIVE_STRIP_WORDS | Rendering (DEPRECATED) |

**Total**: ~50+ pattern lists with ~400+ individual patterns

### 3. Identified Problems

1. **Duplication**: Same patterns appear in multiple files
   - Example: "brutally" appears in both `structured.py` and `manner_adverbs.yaml`
   - Example: Quote patterns appear in multiple places

2. **Inconsistent Format**: Patterns are defined as:
   - Python lists of strings
   - Python sets of strings
   - YAML rule files
   - Inline regex patterns

3. **No Composition**: Can't combine rules from multiple sources
   - Domain + Base + Profile not cleanly composable
   - No inheritance or extension mechanism

4. **No Validation**: Python patterns aren't validated at load time
   - Typos not caught until runtime
   - No schema validation

---

## Target State

### 1. Unified Rule Schema

All rules follow the same schema:

```yaml
rules:
  - id: pattern_id              # Required: Unique identifier
    category: category_name     # Required: Rule category
    priority: 100               # Required: Priority (lower = earlier)
    description: "..."          # Required: Human description
    
    # Matching
    match:
      type: keyword|phrase|regex|entity_role|...
      patterns: [...]           # Required: Patterns to match
      context: [...]            # Optional: Context words required
      exempt_following: [...]   # Optional: Words that exempt match
      case_sensitive: false     # Optional: Case sensitivity
    
    # Action
    action: remove|replace|reframe|classify|detect|...
    replacement: "..."          # For replace action
    reframe_template: "..."     # For reframe action
    
    # Classification (for classify/detect/disqualify)
    classification:
      field: field_name         # Field to set
      value: any                # Value to set
      reason: "..."             # Reason template
      confidence: 0.9           # Confidence score
    
    # Conditions
    condition:
      context_includes: [...]   # Required contexts
      context_excludes: [...]   # Excluded contexts
      span_label: ...           # Required span label
    
    # Metadata
    enabled: true               # Optional: Enable/disable
    domain: law_enforcement     # Optional: Domain restriction
    tags: [neutralization, ...]  # Optional: Tags for grouping
```

### 2. New Rule Categories

Add new rule categories for currently hardcoded patterns:

```
rulesets/
├── _context/                    # Context detection rules
│   ├── charge_context.yaml
│   ├── force_context.yaml
│   ├── injury_context.yaml
│   ├── timeline_context.yaml
│   └── credibility_context.yaml
├── _extraction/                 # Extraction patterns
│   ├── temporal.yaml           # Date/time patterns
│   ├── entity_roles.yaml       # Role detection
│   └── locations.yaml          # Location patterns
├── _grouping/                   # Statement grouping rules
│   ├── encounter_group.yaml
│   ├── medical_group.yaml
│   └── emotional_group.yaml
└── _validation/                 # Validation rules
    ├── actor_resolution.yaml
    └── quote_attribution.yaml
```

### 3. Rule Composition System

```yaml
# profiles/law_enforcement.yaml
extends: base
includes:
  - _categories/inflammatory_language
  - _categories/legal_conclusions
  - _context/force_context
  - _extraction/entity_roles
domain: law_enforcement
overrides:
  # Override specific rules from base
  - id: inflam_psychotic
    enabled: false  # Disable for this profile
```

### 4. Pattern Migration Map

| Source File | Patterns | Target YAML |
|-------------|----------|-------------|
| `p25_annotate_context.py` | CHARGE_PATTERNS | `_context/charge_context.yaml` |
| `p25_annotate_context.py` | PHYSICAL_FORCE_PATTERNS | `_context/force_context.yaml` |
| `p25_annotate_context.py` | INJURY_PATTERNS | `_context/injury_context.yaml` |
| `p25_annotate_context.py` | TIMELINE_PATTERNS | `_context/timeline_context.yaml` |
| `p25_annotate_context.py` | SARCASM_PATTERNS | `_context/sarcasm_context.yaml` |
| `p32_extract_entities.py` | MEDICAL_ROLE_PATTERNS | `_extraction/entity_roles.yaml` |
| `p32_extract_entities.py` | LEGAL_ROLE_PATTERNS | `_extraction/entity_roles.yaml` |
| `p46_group_statements.py` | ENCOUNTER_PATTERNS | `_grouping/encounter_group.yaml` |
| `p46_group_statements.py` | MEDICAL_PATTERNS | `_grouping/medical_group.yaml` |
| `p44a_temporal_expressions.py` | DATE_PATTERNS | `_extraction/temporal.yaml` |
| `render/structured.py` | INTERPRETIVE_DISQUALIFIERS | (already in camera_friendly.yaml) |

---

## Implementation Plan

### Phase 1: Schema Extension (8-12 hours)

1. **Extend PolicyRule model** with new fields:
   - `domain: Optional[str]` — Domain restriction
   - `tags: list[str]` — Tags for filtering
   - `extends: Optional[str]` — Parent rule to extend

2. **Add PolicyRuleset model** with composition:
   - `extends: Optional[str]` — Base ruleset to extend
   - `includes: list[str]` — Rulesets to include
   - `overrides: list[PolicyRule]` — Rules to override

3. **Extend loader** for composition:
   - Load base ruleset first
   - Merge includes
   - Apply overrides

### Phase 2: New Rule Actions (12-16 hours)

1. **Add CONTEXT action** — Sets segment context:
   ```yaml
   - id: ctx_physical_force
     action: context
     classification:
       field: contexts
       value: ["physical_force", "incident"]
   ```

2. **Add GROUP action** — Assigns to statement group:
   ```yaml
   - id: grp_medical
     action: group
     classification:
       field: statement_group
       value: "medical"
   ```

3. **Add EXTRACT action** — Populates extraction fields:
   ```yaml
   - id: ext_role_medical
     action: extract
     classification:
       field: entity_role
       value: "medical_provider"
   ```

### Phase 3: Pattern Migration (15-20 hours)

1. **Create new YAML files** for each category:
   - `_context/` directory with context detection rules
   - `_extraction/` directory with extraction patterns
   - `_grouping/` directory with grouping rules

2. **Migrate patterns** one category at a time:
   - Start with lowest-traffic patterns
   - Add deprecation warnings to Python constants
   - Update tests to use YAML rules

3. **Update passes** to use PolicyEngine:
   - `p25_annotate_context` → use `_context/` rules
   - `p32_extract_entities` → use `_extraction/entity_roles`
   - `p46_group_statements` → use `_grouping/` rules

### Phase 4: Cleanup & Validation (5-8 hours)

1. **Remove deprecated Python patterns** (after validation)
2. **Add schema validation** for YAML files
3. **Add rule linting** (duplicate detection, unused rules)
4. **Update documentation**

---

## Testing Strategy

### Unit Tests
- Rule loading and validation
- Pattern matching for each action type
- Composition (extends, includes, overrides)
- Migration equivalence (Python patterns = YAML rules)

### Integration Tests
- Full pipeline with new rule system
- Profile switching
- Domain-specific behavior

### Migration Tests (Critical)
```python
def test_pattern_migration_equivalence():
    """Ensure YAML rules match Python patterns exactly."""
    from nnrt.passes.p25_annotate_context import CHARGE_PATTERNS
    
    engine = get_policy_engine()
    rules = engine.get_rules_by_tag("charge_context")
    
    patterns_from_yaml = [p for r in rules for p in r.match.patterns]
    
    assert set(patterns_from_yaml) == set(CHARGE_PATTERNS)
```

---

## Done Criteria

### Phase 1: Schema Extension
- [x] PolicyRule model extended with domain, tags, extends ✅ (2026-01-18)
- [x] PolicyRuleset extended with extends, includes, overrides ✅ (2026-01-18)
- [x] RuleOverride model created ✅ (2026-01-18)
- [x] Loader parses domain, tags, extends ✅ (2026-01-18)
- [x] New RuleActions added (CONTEXT, GROUP, EXTRACT) ✅ (2026-01-18)
- [x] Prototype YAML created: `_context/force_context.yaml` ✅ (2026-01-18)
- [x] get_rules_by_tag() method works ✅ (2026-01-18)
- [x] get_rules_by_domain() method works ✅ (2026-01-18)
- [x] All 602 tests pass ✅ (2026-01-18)

### Phase 2: PolicyEngine Integration
- [x] Implement handling for CONTEXT action in engine ✅ (2026-01-18)
- [x] Implement handling for GROUP action in engine ✅ (2026-01-18)
- [x] Implement handling for EXTRACT action in engine ✅ (2026-01-18)
- [x] apply_context_rules() method implemented ✅ (2026-01-18)
- [x] apply_group_rules() method implemented ✅ (2026-01-18)
- [x] apply_extract_rules() method implemented ✅ (2026-01-18)
- [x] get_context_rules(), get_group_rules(), get_extract_rules() ✅ (2026-01-18)
- [x] Force context rules integrated into law_enforcement profile ✅ (2026-01-18)
- [x] All 602 tests pass ✅ (2026-01-18)

### Phase 3: Pattern Migration (COMPLETE)
- [x] `_context/force_context.yaml` created ✅ (8 rules)
- [x] `_context/injury_context.yaml` created ✅ (9 rules)
- [x] `_context/timeline_context.yaml` created ✅ (9 rules)
- [x] `_context/charge_context.yaml` created ✅ (6 rules)
- [x] `_extraction/entity_roles.yaml` created ✅ (11 rules)
- [x] `_grouping/statement_groups.yaml` created ✅ (24 rules)
- **TOTAL: 67 Stage 4 rules in YAML**
- [x] p25_annotate_context updated to use PolicyEngine ✅ (2026-01-18)
- [ ] p32_extract_entities updated to use PolicyEngine (optional)
- [x] p46_group_statements updated to use PolicyEngine ✅ (2026-01-18)
- [x] All 602 tests pass ✅ (2026-01-18)

### Phase 4: Cleanup (COMPLETE)
- [x] Python pattern constants in p46 marked DEPRECATED ✅ (2026-01-18)
- [x] Python pattern constants in p25 marked DEPRECATED ✅ (2026-01-18)
- [ ] Schema validation added (optional future work)
- [x] No regressions in golden cases ✅ (2026-01-18)

---

## Dependencies

**Blocked by**: None (Stage 3 complete ✅)

**Blocks**:
- Stage 5 (Domain System) — needs rule composition
- Stage 6 (Recomposition) — benefits from unified rules

---

## Estimated Effort

| Phase | Effort | Risk |
|-------|--------|------|
| Phase 1: Schema Extension | 8-12 hours | Low |
| Phase 2: New Actions | 12-16 hours | Medium |
| Phase 3: Pattern Migration | 15-20 hours | Medium-High |
| Phase 4: Cleanup | 5-8 hours | Low |
| **Total** | **40-56 hours** | Medium |

---

## Open Questions

1. **Rule Versioning**: Should rules have version numbers for migration?
2. **Hot Reload**: Should YAML changes apply without restart?
3. **Performance**: Will loading many YAML files impact startup?
4. **Debugging**: How to trace which rule matched in production?
5. **Backwards Compatibility**: Support old Python patterns during transition?

---

## Architecture Impact

```
BEFORE (Current):
┌─────────────┐     ┌─────────────────┐     ┌──────────────────┐
│ Python Pass │ ──► │ Hardcoded       │ ──► │ Pass-specific    │
│             │     │ PATTERNS = [...] │     │ matching logic   │
└─────────────┘     └─────────────────┘     └──────────────────┘

AFTER (Stage 4):
┌─────────────┐     ┌─────────────────┐     ┌──────────────────┐
│ Python Pass │ ──► │ PolicyEngine    │ ──► │ Unified          │
│             │     │ (YAML rules)    │     │ matching logic   │
└─────────────┘     └─────────────────┘     └──────────────────┘
                           ▲
                           │
               ┌───────────┴───────────┐
               │ _context/             │
               │ _extraction/          │
               │ _grouping/            │
               │ _classification/      │
               │ _categories/          │
               └───────────────────────┘
```

---

## Next Steps

1. Review this plan with stakeholders
2. Begin Phase 1: Extend PolicyRule model
3. Create first YAML file (`_context/force_context.yaml`) as prototype
4. Update p25_annotate_context to use prototype
5. Iterate based on learnings
