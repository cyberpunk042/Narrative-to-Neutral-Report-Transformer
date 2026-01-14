"""
Policy Loader — Load and parse policy rulesets from YAML files.

Supports two modes:
1. Legacy: Load single YAML file (backwards compatible with base.yaml)
2. Profile: Load composed profile with includes from multiple category files
"""

from pathlib import Path
from typing import Optional

import yaml

from nnrt.policy.models import (
    MatchType,
    PolicyRule,
    PolicyRuleset,
    PolicySettings,
    RuleAction,
    RuleCondition,
    RuleDiagnostic,
    RuleMatch,
    ValidationRule,
)

# Default ruleset directory
RULESETS_DIR = Path(__file__).parent / "rulesets"


def load_ruleset(name: str = "base") -> PolicyRuleset:
    """
    Load a policy ruleset by name.
    
    First checks for a profile in profiles/, then falls back to
    direct file loading for backwards compatibility.
    
    Args:
        name: Ruleset/profile name (without .yaml extension)
        
    Returns:
        Parsed PolicyRuleset
        
    Raises:
        FileNotFoundError: If ruleset file doesn't exist
        ValueError: If ruleset is invalid
    """
    # Check for profile first
    profile_path = RULESETS_DIR / "profiles" / f"{name}.yaml"
    if profile_path.exists():
        return load_profile(name)
    
    # Check for legacy/direct file
    path = RULESETS_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Ruleset not found: {path}")
    
    with open(path) as f:
        data = yaml.safe_load(f)
    
    return parse_ruleset(data)


def load_profile(name: str) -> PolicyRuleset:
    """
    Load a composed profile from profiles/ directory.
    
    Profiles specify includes which are loaded and merged.
    """
    profile_path = RULESETS_DIR / "profiles" / f"{name}.yaml"
    if not profile_path.exists():
        raise FileNotFoundError(f"Profile not found: {profile_path}")
    
    with open(profile_path) as f:
        profile_data = yaml.safe_load(f)
    
    # Get profile metadata
    profile_info = profile_data.get("profile", {})
    settings_data = profile_data.get("settings", {})
    
    # Load and merge all included files
    all_rules: list[PolicyRule] = []
    
    for include_path in profile_data.get("includes", []):
        included_rules = _load_category_file(include_path)
        all_rules.extend(included_rules)
    
    # Apply any overrides
    for override in profile_data.get("overrides", []):
        _apply_override(all_rules, override)
    
    # Sort rules by priority (highest first)
    all_rules.sort(key=lambda r: r.priority, reverse=True)
    
    # Build settings
    settings = PolicySettings(
        min_confidence=settings_data.get("min_confidence", 0.7),
        always_diagnose=settings_data.get("always_diagnose", True),
        allow_override=settings_data.get("allow_override", True),
    )
    
    return PolicyRuleset(
        version=profile_info.get("version", "2.0"),
        name=profile_info.get("name", name),
        description=profile_info.get("description", ""),
        settings=settings,
        rules=all_rules,
        validation=[],
    )


def _load_category_file(relative_path: str) -> list[PolicyRule]:
    """Load rules from a category/domain file."""
    full_path = RULESETS_DIR / relative_path
    if not full_path.exists():
        print(f"Warning: Category file not found: {full_path}")
        return []
    
    with open(full_path) as f:
        data = yaml.safe_load(f)
    
    rules = []
    for rule_data in data.get("rules", []):
        rule = parse_rule(rule_data)
        if rule:
            rules.append(rule)
    
    return rules


def _apply_override(rules: list[PolicyRule], override: dict) -> None:
    """Apply an override to a rule in the list."""
    rule_id = override.get("id")
    for rule in rules:
        if rule.id == rule_id:
            if "enabled" in override:
                rule.enabled = override["enabled"]
            if "priority" in override:
                rule.priority = override["priority"]
            break


def load_ruleset_from_path(path: Path) -> PolicyRuleset:
    """Load a ruleset from an arbitrary path."""
    with open(path) as f:
        data = yaml.safe_load(f)
    return parse_ruleset(data)


def parse_ruleset(data: dict) -> PolicyRuleset:
    """Parse ruleset from dictionary (legacy format)."""
    # Parse settings
    settings_data = data.get("settings", {})
    settings = PolicySettings(
        min_confidence=settings_data.get("min_confidence", 0.7),
        always_diagnose=settings_data.get("always_diagnose", True),
        allow_override=settings_data.get("allow_override", True),
    )
    
    # Parse rules
    rules = []
    for rule_data in data.get("rules", []):
        rule = parse_rule(rule_data)
        if rule:
            rules.append(rule)
    
    # Parse validation rules
    validation = []
    for val_data in data.get("validation", []):
        validation.append(ValidationRule(
            id=val_data["id"],
            description=val_data["description"],
            type=val_data["type"],
            terms=val_data.get("terms", []),
        ))
    
    return PolicyRuleset(
        version=data.get("version", "1.0"),
        name=data.get("name", "unnamed"),
        description=data.get("description", ""),
        settings=settings,
        rules=rules,
        validation=validation,
    )


def parse_rule(data: dict) -> Optional[PolicyRule]:
    """Parse a single rule from dictionary."""
    try:
        # Parse match config
        match_data = data["match"]
        match = RuleMatch(
            type=MatchType(match_data["type"]),
            patterns=match_data["patterns"],
            context=match_data.get("context", []),
            case_sensitive=match_data.get("case_sensitive", False),
            exempt_following=match_data.get("exempt_following", []),
        )
        
        # Parse diagnostic if present
        diagnostic = None
        if "diagnostic" in data:
            diag_data = data["diagnostic"]
            diagnostic = RuleDiagnostic(
                level=diag_data["level"],
                code=diag_data["code"],
                message=diag_data["message"],
            )
        
        # Parse condition if present
        condition = None
        if "condition" in data:
            cond_data = data["condition"]
            condition = RuleCondition(
                context_includes=cond_data.get("context_includes", []),
                context_excludes=cond_data.get("context_excludes", []),
                span_label=cond_data.get("span_label"),
                segment_pattern=cond_data.get("segment_pattern"),
            )
        
        return PolicyRule(
            id=data["id"],
            category=data.get("category", "uncategorized"),
            priority=data.get("priority", 50),
            description=data.get("description", ""),
            match=match,
            action=RuleAction(data["action"]),
            replacement=data.get("replacement"),
            reframe_template=data.get("reframe_template"),
            diagnostic=diagnostic,
            condition=condition,
            enabled=data.get("enabled", True),
        )
    except (KeyError, ValueError) as e:
        # Log warning and skip invalid rule
        print(f"Warning: Skipping invalid rule: {e}")
        return None


def list_rulesets() -> list[str]:
    """List available ruleset names (including profiles)."""
    direct = [p.stem for p in RULESETS_DIR.glob("*.yaml")]
    profiles = [p.stem for p in (RULESETS_DIR / "profiles").glob("*.yaml")]
    return list(set(direct + profiles))


def list_profiles() -> list[str]:
    """List available profile names."""
    profiles_dir = RULESETS_DIR / "profiles"
    if not profiles_dir.exists():
        return []
    return [p.stem for p in profiles_dir.glob("*.yaml")]


# Cache for loaded rulesets
_cache: dict[str, PolicyRuleset] = {}


def get_ruleset(name: str = "base", use_cache: bool = True) -> PolicyRuleset:
    """Get a ruleset, using cache by default."""
    if use_cache and name in _cache:
        return _cache[name]
    
    ruleset = load_ruleset(name)
    _cache[name] = ruleset
    return ruleset


def clear_cache() -> None:
    """Clear the ruleset cache."""
    _cache.clear()

