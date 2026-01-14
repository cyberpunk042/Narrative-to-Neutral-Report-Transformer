"""
Policy Engine — Deterministic rule evaluation.

Policy rules are explicit, traceable, and deterministic.
They decide what survives into output, not the NLP models.
"""

import re
from dataclasses import dataclass
from typing import Optional
from uuid import uuid4

from nnrt.ir.enums import PolicyAction
from nnrt.ir.schema_v0_1 import PolicyDecision
from nnrt.policy.loader import get_ruleset
from nnrt.policy.models import (
    MatchType,
    PolicyRule,
    PolicyRuleset,
    RuleAction,
)


@dataclass
class RuleMatch:
    """Result of a rule matching against text."""
    rule: PolicyRule
    matched_text: str
    start: int
    end: int


class PolicyEngine:
    """
    Deterministic policy rule engine.
    
    Evaluates rules against text and produces explicit policy decisions.
    Rules are loaded from YAML configuration files.
    """

    def __init__(self, ruleset_name: str = "base") -> None:
        """
        Initialize the policy engine.
        
        Args:
            ruleset_name: Name of the ruleset to load
        """
        self._ruleset: Optional[PolicyRuleset] = None
        self._ruleset_name = ruleset_name

    @property
    def ruleset(self) -> PolicyRuleset:
        """Lazy-load the ruleset."""
        if self._ruleset is None:
            self._ruleset = get_ruleset(self._ruleset_name)
        return self._ruleset

    def find_matches(self, text: str) -> list[RuleMatch]:
        """
        Find all rule matches in text.
        
        Args:
            text: Text to search
            
        Returns:
            List of matches, sorted by priority then position
        """
        matches: list[RuleMatch] = []
        
        for rule in self.ruleset.get_rules_sorted():
            rule_matches = self._match_rule(rule, text)
            matches.extend(rule_matches)
        
        # Sort by priority (desc) then position (asc)
        matches.sort(key=lambda m: (-m.rule.priority, m.start))
        
        return matches

    def _match_rule(self, rule: PolicyRule, text: str) -> list[RuleMatch]:
        """Match a single rule against text."""
        matches: list[RuleMatch] = []
        search_text = text if rule.match.case_sensitive else text.lower()
        
        for pattern in rule.match.patterns:
            search_pattern = pattern if rule.match.case_sensitive else pattern.lower()
            
            if rule.match.type == MatchType.KEYWORD:
                # Word boundary matching
                regex = re.compile(rf'\b{re.escape(search_pattern)}\b', re.IGNORECASE)
                for m in regex.finditer(text):
                    # Check context if specified
                    if self._check_context(text, m.start(), m.end(), rule.match.context):
                        matches.append(RuleMatch(
                            rule=rule,
                            matched_text=m.group(),
                            start=m.start(),
                            end=m.end(),
                        ))
                        
            elif rule.match.type == MatchType.PHRASE:
                # Exact phrase matching
                idx = 0
                while True:
                    pos = search_text.find(search_pattern, idx)
                    if pos == -1:
                        break
                    matches.append(RuleMatch(
                        rule=rule,
                        matched_text=text[pos:pos + len(pattern)],
                        start=pos,
                        end=pos + len(pattern),
                    ))
                    idx = pos + 1
                    
            elif rule.match.type == MatchType.REGEX:
                # Regex matching
                try:
                    regex = re.compile(pattern, re.IGNORECASE if not rule.match.case_sensitive else 0)
                    for m in regex.finditer(text):
                        matches.append(RuleMatch(
                            rule=rule,
                            matched_text=m.group(),
                            start=m.start(),
                            end=m.end(),
                        ))
                except re.error:
                    pass  # Invalid regex, skip
                    
            elif rule.match.type == MatchType.QUOTED:
                # Match quoted text
                for quote_pattern in [r'"([^"]*)"', r"'([^']*)'", r'"([^"]*)"']:
                    regex = re.compile(quote_pattern)
                    for m in regex.finditer(text):
                        matches.append(RuleMatch(
                            rule=rule,
                            matched_text=m.group(),
                            start=m.start(),
                            end=m.end(),
                        ))
        
        return matches

    def _check_context(
        self, text: str, start: int, end: int, context: list[str]
    ) -> bool:
        """Check if match has required context words nearby."""
        if not context:
            return True
        
        # Look in a window around the match
        window_start = max(0, start - 50)
        window_end = min(len(text), end + 50)
        window = text[window_start:window_end].lower()
        
        return any(ctx.lower() in window for ctx in context)
    
    def _check_condition(
        self, rule: PolicyRule, segment_contexts: list[str]
    ) -> bool:
        """
        Check if a rule's condition is met given segment contexts.
        
        Returns True if rule should be applied, False if it should be skipped.
        """
        condition = rule.condition
        if condition is None:
            return True  # No condition = always apply
        
        # Check context_includes: ALL must be present
        if condition.context_includes:
            for ctx in condition.context_includes:
                if ctx not in segment_contexts:
                    return False
        
        # Check context_excludes: NONE must be present
        if condition.context_excludes:
            for ctx in condition.context_excludes:
                if ctx in segment_contexts:
                    return False
        
        return True

    def apply_rules(self, text: str) -> tuple[str, list[PolicyDecision]]:
        """
        Apply all matching rules to text.
        
        Args:
            text: Text to transform
            
        Returns:
            Tuple of (transformed_text, policy_decisions)
        """
        return self.apply_rules_with_context(text, [])
    
    def apply_rules_with_context(
        self, text: str, segment_contexts: list[str]
    ) -> tuple[str, list[PolicyDecision]]:
        """
        Apply all matching rules to text, respecting segment contexts.
        
        Args:
            text: Text to transform
            segment_contexts: Context annotations for this segment
            
        Returns:
            Tuple of (transformed_text, policy_decisions)
        """
        decisions: list[PolicyDecision] = []
        matches = self.find_matches(text)
        
        # Track which positions have been modified
        modified_ranges: list[tuple[int, int]] = []
        
        # Build list of transformations to apply
        transformations: list[tuple[int, int, str, PolicyRule]] = []
        
        for match in matches:
            # NEW: Check if rule's condition is met
            if not self._check_condition(match.rule, segment_contexts):
                continue  # Skip - condition not met
            
            # Skip if this range overlaps with already modified range
            if any(
                start <= match.start < end or start < match.end <= end
                for start, end in modified_ranges
            ):
                continue
            
            # Determine replacement
            replacement = self._get_replacement(match)
            
            if replacement is not None:
                transformations.append((
                    match.start,
                    match.end,
                    replacement,
                    match.rule,
                ))
                modified_ranges.append((match.start, match.end))
            
            # Create policy decision
            decisions.append(self._create_decision(match))
        
        # Apply transformations in reverse order (to preserve positions)
        result = text
        for start, end, replacement, rule in sorted(
            transformations, key=lambda t: t[0], reverse=True
        ):
            result = result[:start] + replacement + result[end:]
        
        return result, decisions

    def _get_replacement(self, match: RuleMatch) -> Optional[str]:
        """Get the replacement text for a match."""
        rule = match.rule
        
        if rule.action == RuleAction.REMOVE:
            return ""
        elif rule.action == RuleAction.REPLACE:
            return rule.replacement or ""
        elif rule.action == RuleAction.REFRAME:
            if rule.reframe_template:
                return rule.reframe_template.replace("{original}", match.matched_text)
            return match.matched_text
        elif rule.action == RuleAction.PRESERVE:
            return None  # Don't modify
        elif rule.action == RuleAction.FLAG:
            return None  # Just flag, don't modify
        elif rule.action == RuleAction.REFUSE:
            return None  # Handled separately
        
        return None

    def _create_decision(self, match: RuleMatch) -> PolicyDecision:
        """Create a policy decision from a match."""
        action = PolicyAction.MODIFY
        if match.rule.action == RuleAction.REMOVE:
            action = PolicyAction.REMOVE
        elif match.rule.action == RuleAction.PRESERVE:
            action = PolicyAction.PRESERVE
        elif match.rule.action == RuleAction.FLAG:
            action = PolicyAction.FLAG
        elif match.rule.action == RuleAction.REFUSE:
            action = PolicyAction.REFUSE
        
        return PolicyDecision(
            id=str(uuid4()),
            rule_id=match.rule.id,
            action=action,
            reason=match.rule.description,
            affected_ids=[],
        )

    def should_refuse(self, matches: list[RuleMatch]) -> bool:
        """Check if any match requires refusal."""
        return any(m.rule.action == RuleAction.REFUSE for m in matches)


# Default engine instance
_engine: Optional[PolicyEngine] = None


def get_policy_engine(ruleset: str = "base") -> PolicyEngine:
    """Get or create a policy engine."""
    global _engine
    if _engine is None or _engine._ruleset_name != ruleset:
        _engine = PolicyEngine(ruleset)
    return _engine
