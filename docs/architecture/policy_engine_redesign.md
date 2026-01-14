# Policy Engine Architecture Redesign

**Date**: 2026-01-14  
**Status**: 🏗️ DESIGN PHASE  
**Goal**: Scalable, maintainable, domain-aware policy ruleset system

---

## Problem Statement

Current architecture has **single `base.yaml`** with ~80 rules. To support all identified patterns, we need ~200+ rules. This creates:

1. **Maintainability Hell**: Single 1000+ line YAML file
2. **No Domain Separation**: Police, medical, legal all mixed
3. **No Category Control**: Can't enable/disable rule categories
4. **Testing Difficulty**: Can't test categories in isolation
5. **No Composition**: Can't share universal rules across domains

---

## Proposed Architecture

### Directory Structure

```
nnrt/policy/rulesets/
├── _meta/
│   └── schema.yaml           # Rule schema definition
├── _core/                    # Universal rules (always applied)
│   ├── quote_protection.yaml # Preserve quotes
│   ├── certainty.yaml        # clearly, obviously, absolutely
│   ├── extreme_modifiers.yaml# horrifying, devastating
│   ├── similes.yaml          # like a maniac, like a criminal
│   └── logical_conclusions.yaml # which proves, therefore
├── _categories/              # Category-specific rules
│   ├── intent_attribution.yaml    # wanted to, meant to, intended
│   ├── inflammatory_language.yaml # terrorize, corrupt, thugs
│   ├── legal_conclusions.yaml     # torture, crimes, innocent
│   ├── manner_adverbs.yaml        # viciously, brutally, menacingly
│   └── loaded_verbs.yaml          # screaming, slammed, attacked
├── domains/                  # Domain-specific overlays
│   ├── law_enforcement.yaml  # cop→officer, badge, brutality
│   ├── medical.yaml          # malpractice, negligence
│   ├── legal_proceedings.yaml# judge, court, verdict
│   └── workplace.yaml        # harassment, discrimination
├── profiles/                 # Pre-composed profiles
│   ├── standard.yaml         # Core + all categories
│   ├── law_enforcement.yaml  # Standard + law_enforcement domain
│   ├── medical.yaml          # Standard + medical domain
│   └── minimal.yaml          # Core only (lightest transformation)
└── base.yaml                 # Default = profiles/standard.yaml (backwards compat)
```

---

## Rule Composition System

### Profile Definition

```yaml
# profiles/law_enforcement.yaml
profile:
  id: law_enforcement
  name: "Law Enforcement Narrative Transformation"
  description: "Standard profile plus police/law enforcement specific rules"

includes:
  # Core (always included)
  - _core/quote_protection.yaml
  - _core/certainty.yaml
  - _core/extreme_modifiers.yaml
  - _core/similes.yaml
  - _core/logical_conclusions.yaml
  
  # Categories
  - _categories/intent_attribution.yaml
  - _categories/inflammatory_language.yaml
  - _categories/legal_conclusions.yaml
  - _categories/manner_adverbs.yaml
  - _categories/loaded_verbs.yaml
  
  # Domain-specific
  - domains/law_enforcement.yaml

settings:
  min_confidence: 0.7
  always_diagnose: true
  
# Optional overrides
overrides:
  - id: inflam_cop_singular
    enabled: true
    priority: 65  # Adjust priority
```

---

## Category Files

### Example: `_core/certainty.yaml`

```yaml
# Certainty Language - Universal
# These words assert subjective certainty as fact

category: certainty
description: "Transform epistemic/certainty language to hedged alternatives"
priority_range: [70, 79]

rules:
  - id: cert_clearly
    priority: 75
    description: "Remove 'clearly' - asserts certainty"
    match:
      type: keyword
      patterns: ["clearly"]
    action: remove

  - id: cert_obviously  
    priority: 75
    description: "Remove 'obviously'"
    match:
      type: keyword
      patterns: ["obviously"]
    action: remove

  - id: cert_definitely
    priority: 75
    description: "Remove definite assertions"
    match:
      type: keyword
      patterns: ["definitely", "certainly", "undoubtedly", "surely"]
    action: remove

  - id: cert_absolutely
    priority: 74
    description: "Remove 'absolutely' when not quantitative"
    match:
      type: keyword
      patterns: ["absolutely"]
    action: remove

  - id: cert_proves
    priority: 76
    description: "Soften 'which proves' logical conclusions"
    match:
      type: phrase
      patterns: ["which proves", "proves that", "this proves"]
    action: replace
    replacement: "which suggests"
```

### Example: `domains/law_enforcement.yaml`

```yaml
# Law Enforcement Domain
# Rules specific to police/law enforcement narratives

domain: law_enforcement
description: "Transform law enforcement specific inflammatory language"
priority_range: [55, 69]

rules:
  - id: le_cop_singular
    priority: 60
    description: "Replace 'cop' with 'officer'"
    match:
      type: keyword
      patterns: ["cop"]
    action: replace
    replacement: "officer"

  - id: le_cop_plural
    priority: 60
    description: "Replace 'cops' with 'officers'"
    match:
      type: keyword
      patterns: ["cops"]
    action: replace
    replacement: "officers"

  - id: le_thug_officer
    priority: 80
    description: "Replace derogatory officer terms"
    match:
      type: keyword
      patterns: ["thug", "pig", "goon", "bully"]
    action: replace
    replacement: "officer"

  - id: le_brutality
    priority: 85
    description: "Soften 'brutality' to 'use of force'"
    match:
      type: keyword
      patterns: ["brutality", "police brutality"]
    action: replace
    replacement: "use of force"

  - id: le_badge_number
    priority: 900
    description: "Preserve badge numbers"
    match:
      type: regex
      patterns: ["badge\\s*(number|#)?\\s*\\d+"]
    action: preserve
```

---

## Loader Changes

### New Loader Interface

```python
class PolicyLoader:
    """Enhanced loader with composition support."""
    
    def load_profile(self, profile_name: str) -> PolicyRuleset:
        """Load a composed profile."""
        profile_path = RULESETS_DIR / "profiles" / f"{profile_name}.yaml"
        profile = self._load_yaml(profile_path)
        
        all_rules = []
        for include in profile.get("includes", []):
            included = self._load_yaml(RULESETS_DIR / include)
            all_rules.extend(included.get("rules", []))
        
        # Apply overrides
        for override in profile.get("overrides", []):
            self._apply_override(all_rules, override)
        
        return self._build_ruleset(all_rules, profile.get("settings", {}))
    
    def load_categories(self, categories: list[str]) -> PolicyRuleset:
        """Load specific categories only."""
        all_rules = []
        for cat in categories:
            cat_path = RULESETS_DIR / "_categories" / f"{cat}.yaml"
            if cat_path.exists():
                cat_data = self._load_yaml(cat_path)
                all_rules.extend(cat_data.get("rules", []))
        return self._build_ruleset(all_rules, {})
```

### Auto-Detection (Future)

```python
def detect_domain(text: str) -> str:
    """Auto-detect narrative domain for profile selection."""
    # Simple keyword-based detection
    le_keywords = ["officer", "police", "badge", "arrest", "patrol"]
    medical_keywords = ["doctor", "hospital", "patient", "diagnosis"]
    legal_keywords = ["judge", "court", "trial", "verdict", "attorney"]
    
    text_lower = text.lower()
    
    scores = {
        "law_enforcement": sum(1 for k in le_keywords if k in text_lower),
        "medical": sum(1 for k in medical_keywords if k in text_lower),
        "legal_proceedings": sum(1 for k in legal_keywords if k in text_lower),
    }
    
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "standard"
```

---

## Benefits

| Aspect | Current | Proposed |
|--------|---------|----------|
| **Files** | 1 large file | 15+ small focused files |
| **Lines per file** | 500+ | 50-100 |
| **Testing** | All or nothing | Per-category tests |
| **Domain support** | None | Full domain profiles |
| **Maintenance** | Hard | Easy (category owners) |
| **Customization** | Fork base.yaml | Override profiles |
| **Scaling** | Poor | Excellent |

---

## Migration Path

### Phase 1: Infrastructure (Create new structure, keep base.yaml working)
1. Create directory structure
2. Implement new loader with `includes` support
3. Split existing rules into category files
4. Create `profiles/standard.yaml` that includes all
5. Make `base.yaml` symlink to standard profile (backwards compat)

### Phase 2: Add Missing Rules
1. Add all 35 missing patterns to appropriate category files
2. Create law_enforcement domain overlay
3. Test comprehensive sweep

### Phase 3: API Enhancement
1. Add profile selection to CLI: `nnrt transform --profile law_enforcement`
2. Add domain auto-detection option
3. Add category enable/disable: `nnrt transform --disable-category certainty`

---

## Estimated Effort

| Phase | Work | Time |
|-------|------|------|
| Phase 1 | Directory + Loader + Split | 2-3 hours |
| Phase 2 | Add 35 rules | 1 hour |
| Phase 3 | CLI/API | 1 hour |

**Total**: ~4-5 hours for production-quality scalable system.

---

## Decision Required

**Option A**: Implement full redesign (Phase 1+2+3)
- Most scalable, future-proof
- More upfront work

**Option B**: Implement Phase 1+2 only
- Scalable structure
- CLI enhancement later

**Option C**: Quick fix - just add rules to base.yaml
- Fast but technical debt
- Will need refactor later anyway
