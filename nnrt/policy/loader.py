"""
Policy Loader — Load and parse policy rulesets from YAML files.
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
    RuleDiagnostic,
    RuleMatch,
    ValidationRule,
)

# Default ruleset directory
RULESETS_DIR = Path(__file__).parent / "rulesets"


def load_ruleset(name: str = "base") -> PolicyRuleset:
    """
    Load a policy ruleset by name.
    
    Args:
        name: Ruleset name (without .yaml extension)
        
    Returns:
        Parsed PolicyRuleset
        
    Raises:
        FileNotFoundError: If ruleset file doesn't exist
        ValueError: If ruleset is invalid
    """
    path = RULESETS_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Ruleset not found: {path}")
    
    with open(path) as f:
        data = yaml.safe_load(f)
    
    return parse_ruleset(data)


def load_ruleset_from_path(path: Path) -> PolicyRuleset:
    """Load a ruleset from an arbitrary path."""
    with open(path) as f:
        data = yaml.safe_load(f)
    return parse_ruleset(data)


def parse_ruleset(data: dict) -> PolicyRuleset:
    """Parse ruleset from dictionary."""
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
        
        return PolicyRule(
            id=data["id"],
            category=data["category"],
            priority=data["priority"],
            description=data["description"],
            match=match,
            action=RuleAction(data["action"]),
            replacement=data.get("replacement"),
            reframe_template=data.get("reframe_template"),
            diagnostic=diagnostic,
            enabled=data.get("enabled", True),
        )
    except (KeyError, ValueError) as e:
        # Log warning and skip invalid rule
        print(f"Warning: Skipping invalid rule: {e}")
        return None


def list_rulesets() -> list[str]:
    """List available ruleset names."""
    return [p.stem for p in RULESETS_DIR.glob("*.yaml")]


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
