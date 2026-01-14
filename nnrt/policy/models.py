"""
Policy Models — Data structures for policy rules.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class RuleAction(str, Enum):
    """Actions a rule can take."""
    REMOVE = "remove"
    REPLACE = "replace"
    REFRAME = "reframe"
    FLAG = "flag"
    REFUSE = "refuse"
    PRESERVE = "preserve"


class MatchType(str, Enum):
    """Types of pattern matching."""
    KEYWORD = "keyword"
    PHRASE = "phrase"
    REGEX = "regex"
    QUOTED = "quoted"
    SPAN_LABEL = "span_label"


@dataclass
class RuleMatch:
    """Pattern matching configuration for a rule."""
    type: MatchType
    patterns: list[str]
    context: list[str] = field(default_factory=list)
    case_sensitive: bool = False


@dataclass
class RuleDiagnostic:
    """Diagnostic to emit when rule matches."""
    level: str  # error, warning, info
    code: str
    message: str


@dataclass
class PolicyRule:
    """A single policy rule."""
    id: str
    category: str
    priority: int
    description: str
    match: RuleMatch
    action: RuleAction
    replacement: Optional[str] = None
    reframe_template: Optional[str] = None
    diagnostic: Optional[RuleDiagnostic] = None
    enabled: bool = True


@dataclass
class ValidationRule:
    """A validation rule for post-transformation checks."""
    id: str
    description: str
    type: str  # subset_check, forbidden_terms, perspective_check
    terms: list[str] = field(default_factory=list)


@dataclass
class PolicySettings:
    """Global policy settings."""
    min_confidence: float = 0.7
    always_diagnose: bool = True
    allow_override: bool = True


@dataclass
class PolicyRuleset:
    """A complete policy ruleset."""
    version: str
    name: str
    description: str
    settings: PolicySettings
    rules: list[PolicyRule]
    validation: list[ValidationRule]
    
    def get_rules_by_category(self, category: str) -> list[PolicyRule]:
        """Get rules filtered by category."""
        return [r for r in self.rules if r.category == category and r.enabled]
    
    def get_rules_sorted(self) -> list[PolicyRule]:
        """Get rules sorted by priority (highest first)."""
        return sorted(
            [r for r in self.rules if r.enabled],
            key=lambda r: r.priority,
            reverse=True
        )
