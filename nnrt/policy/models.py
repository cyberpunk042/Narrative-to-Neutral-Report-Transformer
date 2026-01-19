"""
Policy Models — Data structures for policy rules.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class RuleAction(str, Enum):
    """Actions a rule can take."""
    # --- Text Transformation Actions ---
    REMOVE = "remove"
    REPLACE = "replace"
    REFRAME = "reframe"
    FLAG = "flag"
    REFUSE = "refuse"
    PRESERVE = "preserve"
    
    # --- V7 / Stage 1: Classification Actions ---
    # These actions set fields on atoms rather than transforming text
    CLASSIFY = "classify"      # Set a classification field to a value
    DISQUALIFY = "disqualify"  # Mark as not camera-friendly (is_camera_friendly=False)
    DETECT = "detect"          # Detect presence of pattern, set boolean field
    STRIP = "strip"            # Strip words for neutralization (remove but keep sentence)
    
    # --- V7 / Stage 4: Context, Grouping, and Extraction Actions ---
    # These actions support pattern migration from Python to YAML
    CONTEXT = "context"        # Set segment context (replaces Python PATTERNS)
    GROUP = "group"            # Assign to statement group
    EXTRACT = "extract"        # Populate extraction fields (roles, temporal, etc.)


class MatchType(str, Enum):
    """Types of pattern matching.
    
    Text-based matching:
    - KEYWORD: Word boundary matching
    - PHRASE: Exact phrase matching
    - REGEX: Regular expression matching
    - QUOTED: Content within quotes
    - SPAN_LABEL: Match span labels
    
    Semantic matching (uses Entity/Event graph):
    - ENTITY_ROLE: Match entities by their role (e.g., AUTHORITY, VICTIM)
    - ENTITY_TYPE: Match entities by their type (e.g., PERSON, VEHICLE)
    - EVENT_TYPE: Match events by their type (e.g., ACTION, VERBAL)
    """
    # Text-based matching
    KEYWORD = "keyword"
    PHRASE = "phrase"
    REGEX = "regex"
    QUOTED = "quoted"
    SPAN_LABEL = "span_label"
    
    # Semantic matching (NEW)
    ENTITY_ROLE = "entity_role"
    ENTITY_TYPE = "entity_type"
    EVENT_TYPE = "event_type"


@dataclass
class RuleMatch:
    """Pattern matching configuration for a rule."""
    type: MatchType
    patterns: list[str]
    context: list[str] = field(default_factory=list)
    case_sensitive: bool = False
    # Skip rule if match is followed by any of these words (within 20 chars)
    # Used to prevent "wanted to go home" from being transformed
    exempt_following: list[str] = field(default_factory=list)


@dataclass
class RuleDiagnostic:
    """Diagnostic to emit when rule matches."""
    level: str  # error, warning, info
    code: str
    message: str


@dataclass
class RuleCondition:
    """
    Context-aware condition for rule application.
    
    A rule with a condition will only apply if the condition is met.
    This enables context-aware transformations without hardcoding in Python.
    """
    # Segment must have ALL of these contexts for rule to apply
    context_includes: list[str] = field(default_factory=list)
    
    # Segment must NOT have ANY of these contexts for rule to apply  
    context_excludes: list[str] = field(default_factory=list)
    
    # Span must have this label for rule to apply
    span_label: Optional[str] = None
    
    # Segment must match this regex pattern for rule to apply
    segment_pattern: Optional[str] = None


@dataclass
class ClassificationOutput:
    """
    V7 / Stage 1: Output specification for classification rules.
    
    When a rule with action=CLASSIFY/DISQUALIFY/DETECT matches,
    this specifies what field to set and to what value.
    """
    # Which field on the atom to set
    field: str
    
    # Value to set (for CLASSIFY/DETECT/DISQUALIFY)
    value: Any = None
    
    # Reason template (can include {matched} for the matched text)
    reason: Optional[str] = None
    
    # Confidence in this classification (0.0-1.0)
    confidence: float = 0.9


@dataclass
class PolicyRule:
    """A single policy rule.
    
    V7/Stage 4: Extended with domain, tags, and extends for composition.
    """
    id: str
    category: str
    priority: int
    description: str
    match: RuleMatch
    action: RuleAction
    replacement: Optional[str] = None
    reframe_template: Optional[str] = None
    diagnostic: Optional[RuleDiagnostic] = None
    condition: Optional[RuleCondition] = None  # Context-aware condition
    enabled: bool = True
    
    # V7 / Stage 1: Classification output (for CLASSIFY/DISQUALIFY/DETECT actions)
    classification: Optional[ClassificationOutput] = None
    
    # V7 / Stage 4: Composition and domain support
    domain: Optional[str] = None       # Domain restriction (e.g., "law_enforcement")
    tags: list[str] = field(default_factory=list)  # Tags for grouping/filtering
    extends: Optional[str] = None      # Parent rule ID to extend


@dataclass
class RuleOverride:
    """Override for a rule in composition.
    
    Allows profiles/domains to modify specific fields of a rule.
    """
    id: str                            # Rule ID to override
    enabled: Optional[bool] = None     # Override enabled state
    priority: Optional[int] = None     # Override priority
    replacement: Optional[str] = None  # Override replacement text
    classification: Optional[ClassificationOutput] = None  # Override output


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
    """A complete policy ruleset.
    
    V7/Stage 4: Extended with composition support (extends, includes, overrides).
    """
    version: str
    name: str
    description: str
    settings: PolicySettings
    rules: list[PolicyRule]
    validation: list[ValidationRule]
    
    # V7 / Stage 4: Composition
    extends: Optional[str] = None          # Base ruleset to extend
    includes: list[str] = field(default_factory=list)  # Rulesets to include
    overrides: list[RuleOverride] = field(default_factory=list)  # Rule overrides
    domain: Optional[str] = None           # Domain this ruleset belongs to
    
    def get_rules_by_category(self, category: str) -> list[PolicyRule]:
        """Get rules filtered by category."""
        return [r for r in self.rules if r.category == category and r.enabled]
    
    def get_rules_by_tag(self, tag: str) -> list[PolicyRule]:
        """Get rules filtered by tag."""
        return [r for r in self.rules if tag in r.tags and r.enabled]
    
    def get_rules_by_domain(self, domain: str) -> list[PolicyRule]:
        """Get rules for a specific domain (or domain-agnostic)."""
        return [r for r in self.rules 
                if (r.domain is None or r.domain == domain) and r.enabled]
    
    def get_rules_sorted(self) -> list[PolicyRule]:
        """Get rules sorted by priority (highest first)."""
        return sorted(
            [r for r in self.rules if r.enabled],
            key=lambda r: r.priority,
            reverse=True
        )

