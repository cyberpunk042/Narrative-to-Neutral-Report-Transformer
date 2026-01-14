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
                    match_end = pos + len(pattern)
                    # Check exempt_following
                    if not self._check_exempt_following(text, match_end, rule.match.exempt_following):
                        matches.append(RuleMatch(
                            rule=rule,
                            matched_text=text[pos:match_end],
                            start=pos,
                            end=match_end,
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
    
    def _check_exempt_following(
        self, text: str, match_end: int, exempt_following: list[str]
    ) -> bool:
        """
        Check if the match is followed by an exempt word.
        
        Returns True if exempt (should skip this match), False if not exempt.
        """
        if not exempt_following:
            return False
        
        # Look at the next 30 characters after the match
        lookahead = text[match_end:match_end + 30].lower().strip()
        
        # Check if any exempt word appears at the start of lookahead
        for exempt in exempt_following:
            exempt_lower = exempt.lower()
            if lookahead.startswith(exempt_lower):
                # Verify it's a word boundary (not part of a longer word)
                if len(lookahead) == len(exempt_lower) or not lookahead[len(exempt_lower)].isalpha():
                    return True
        
        return False

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
        
        Uses Token Group Merging with Protected Ranges:
        - First, identify PRESERVE matches (quotes, etc.) and protect their ranges
        - Any match inside a protected range is skipped
        - Group adjacent non-protected matches with same target
        - Merge each group into a single transformation
        
        Args:
            text: Text to transform
            segment_contexts: Context annotations for this segment
            
        Returns:
            Tuple of (transformed_text, policy_decisions)
        """
        decisions: list[PolicyDecision] = []
        matches = self.find_matches(text)
        
        # Filter matches by condition
        valid_matches: list[RuleMatch] = []
        for match in matches:
            if self._check_condition(match.rule, segment_contexts):
                valid_matches.append(match)
        
        # STEP 1: Find protected ranges from PRESERVE rules
        # These are ranges (like quote content) that should not be modified
        protected_ranges: list[tuple[int, int]] = []
        preserve_decisions: list[PolicyDecision] = []
        
        for match in valid_matches:
            if match.rule.action == RuleAction.PRESERVE:
                protected_ranges.append((match.start, match.end))
                preserve_decisions.append(self._create_decision(match))
        
        decisions.extend(preserve_decisions)
        
        # STEP 2: Filter out matches that fall inside protected ranges
        unprotected_matches: list[RuleMatch] = []
        for match in valid_matches:
            if match.rule.action == RuleAction.PRESERVE:
                continue  # Already handled
            if not self._is_protected(match.start, match.end, protected_ranges):
                unprotected_matches.append(match)
        
        # STEP 2.5: Consume spans - prevent overlapping matches
        # Sort by priority (high first), then by length (long first for ties)
        # When multiple rules match overlapping text, highest priority wins
        sorted_by_priority = sorted(
            unprotected_matches,
            key=lambda m: (-m.rule.priority, -(m.end - m.start))
        )
        
        consumed_chars: set[int] = set()
        non_overlapping_matches: list[RuleMatch] = []
        
        for match in sorted_by_priority:
            # Check if ANY character in this match is already consumed
            match_chars = set(range(match.start, match.end))
            if match_chars & consumed_chars:
                # Overlap detected - skip this lower-priority match
                continue
            
            # No overlap - accept this match and consume its characters
            non_overlapping_matches.append(match)
            consumed_chars.update(match_chars)
        
        # STEP 3: Group adjacent non-overlapping matches with same target
        match_groups = self._group_adjacent_matches(text, non_overlapping_matches)
        
        # Build transformations from groups
        transformations: list[tuple[int, int, str, list[PolicyRule]]] = []
        
        for group in match_groups:
            # All matches in group have same replacement - use first
            first_match = group[0]
            replacement = self._get_replacement(first_match)
            
            if replacement is not None:
                # Span covers entire group (first start to last end)
                group_start = min(m.start for m in group)
                group_end = max(m.end for m in group)
                
                transformations.append((
                    group_start,
                    group_end,
                    replacement,
                    [m.rule for m in group],
                ))
            
            # Create decisions for each match in group
            for match in group:
                decisions.append(self._create_decision(match))
        
        # Apply transformations in reverse order (to preserve positions)
        result = text
        for start, end, replacement, rules in sorted(
            transformations, key=lambda t: t[0], reverse=True
        ):
            result = result[:start] + replacement + result[end:]
        
        return result, decisions
    
    def _group_adjacent_matches(
        self, text: str, matches: list[RuleMatch]
    ) -> list[list[RuleMatch]]:
        """
        Group adjacent matches that have the same replacement target.
        
        Two matches are considered adjacent if they're separated only by whitespace.
        Matches with the same target (replacement text) are merged into groups.
        
        Returns list of groups, where each group's matches should be merged.
        """
        if not matches:
            return []
        
        # Sort by position
        sorted_matches = sorted(matches, key=lambda m: m.start)
        
        # Get replacement for each match
        match_replacements: list[tuple[RuleMatch, Optional[str]]] = [
            (m, self._get_replacement(m)) for m in sorted_matches
        ]
        
        groups: list[list[RuleMatch]] = []
        consumed_positions: set[int] = set()
        
        for i, (match, replacement) in enumerate(match_replacements):
            if i in consumed_positions:
                continue
            
            if replacement is None:
                # Non-modifying matches stay solo
                groups.append([match])
                consumed_positions.add(i)
                continue
            
            # Start a new group with this match
            current_group = [match]
            consumed_positions.add(i)
            current_end = match.end
            
            # Look ahead for adjacent matches with same replacement
            for j in range(i + 1, len(match_replacements)):
                if j in consumed_positions:
                    continue
                    
                next_match, next_replacement = match_replacements[j]
                
                # Check if adjacent (only whitespace between)
                gap = text[current_end:next_match.start]
                if gap.strip() != "":
                    # Non-whitespace gap - not adjacent
                    break
                
                # Check if same replacement target
                if next_replacement == replacement:
                    current_group.append(next_match)
                    consumed_positions.add(j)
                    current_end = next_match.end
                else:
                    # Different replacement - can't merge
                    break
            
            groups.append(current_group)
        
        return groups
    
    def _is_protected(
        self, start: int, end: int, protected_ranges: list[tuple[int, int]]
    ) -> bool:
        """
        Check if a span falls inside any protected range.
        
        A span is protected if it overlaps with (is contained in) a protected range.
        Protected ranges come from PRESERVE rules (e.g., quote content).
        """
        for p_start, p_end in protected_ranges:
            # Check if match is fully or partially inside the protected range
            if start >= p_start and end <= p_end:
                return True  # Fully contained
            if start < p_end and end > p_start:
                return True  # Partially overlapping
        return False

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

    # =========================================================================
    # Semantic Matching Methods (Phase D: Policy Engine Evolution)
    # =========================================================================
    
    def find_semantic_matches(
        self,
        entities: list,  # list[Entity]
        events: list,    # list[Event]
        segment_text: str = "",
    ) -> list[RuleMatch]:
        """
        Find semantic rule matches using the Entity/Event graph.
        
        This enables policies like:
        - "REDACT entities with role=VICTIM"
        - "FLAG events with actor.role=AUTHORITY"
        - "PRESERVE entities with type=PERSON"
        
        Args:
            entities: Entities from p32
            events: Events from p34
            segment_text: Original segment text (for position info)
            
        Returns:
            List of semantic matches
        """
        matches: list[RuleMatch] = []
        
        for rule in self.ruleset.get_rules_sorted():
            if rule.match.type == MatchType.ENTITY_ROLE:
                matches.extend(self._match_entity_role(rule, entities, segment_text))
            elif rule.match.type == MatchType.ENTITY_TYPE:
                matches.extend(self._match_entity_type(rule, entities, segment_text))
            elif rule.match.type == MatchType.EVENT_TYPE:
                matches.extend(self._match_event_type(rule, events, segment_text))
        
        # Sort by priority (desc)
        matches.sort(key=lambda m: -m.rule.priority)
        
        return matches
    
    def _match_entity_role(
        self,
        rule: PolicyRule,
        entities: list,  # list[Entity]
        segment_text: str,
    ) -> list[RuleMatch]:
        """Match entities by their role."""
        matches: list[RuleMatch] = []
        
        for entity in entities:
            entity_role = entity.role.value if hasattr(entity.role, 'value') else str(entity.role)
            
            for pattern in rule.match.patterns:
                if pattern.lower() == entity_role.lower():
                    # Create match representing this entity
                    matched_text = entity.label or f"Entity({entity.id})"
                    matches.append(RuleMatch(
                        rule=rule,
                        matched_text=matched_text,
                        start=0,  # Position info from entity mentions if available
                        end=len(matched_text),
                    ))
        
        return matches
    
    def _match_entity_type(
        self,
        rule: PolicyRule,
        entities: list,  # list[Entity]
        segment_text: str,
    ) -> list[RuleMatch]:
        """Match entities by their type."""
        matches: list[RuleMatch] = []
        
        for entity in entities:
            entity_type = entity.type.value if hasattr(entity.type, 'value') else str(entity.type)
            
            for pattern in rule.match.patterns:
                if pattern.lower() == entity_type.lower():
                    matched_text = entity.label or f"Entity({entity.id})"
                    matches.append(RuleMatch(
                        rule=rule,
                        matched_text=matched_text,
                        start=0,
                        end=len(matched_text),
                    ))
        
        return matches
    
    def _match_event_type(
        self,
        rule: PolicyRule,
        events: list,  # list[Event]
        segment_text: str,
    ) -> list[RuleMatch]:
        """Match events by their type."""
        matches: list[RuleMatch] = []
        
        for event in events:
            event_type = event.type.value if hasattr(event.type, 'value') else str(event.type)
            
            for pattern in rule.match.patterns:
                if pattern.lower() == event_type.lower():
                    matched_text = event.description or f"Event({event.id})"
                    matches.append(RuleMatch(
                        rule=rule,
                        matched_text=matched_text,
                        start=0,
                        end=len(matched_text),
                    ))
        
        return matches

    def evaluate_semantic(
        self,
        entities: list,
        events: list,
        segment_text: str = "",
    ) -> list[PolicyDecision]:
        """
        Evaluate semantic rules and return policy decisions.
        
        This is the entry point for semantic policy evaluation.
        
        Args:
            entities: Entities to evaluate
            events: Events to evaluate
            segment_text: Original segment text
            
        Returns:
            List of policy decisions
        """
        matches = self.find_semantic_matches(entities, events, segment_text)
        decisions = []
        
        for match in matches:
            decision = self._create_decision(match)
            decisions.append(decision)
        
        return decisions


# Default engine instance and profile configuration
_engine: Optional[PolicyEngine] = None
_default_profile: str = "law_enforcement"


def set_default_profile(profile: str) -> None:
    """Set the default profile for policy engine creation."""
    global _default_profile, _engine
    _default_profile = profile
    _engine = None  # Reset cached engine to use new profile


def get_default_profile() -> str:
    """Get the current default profile."""
    return _default_profile


def get_policy_engine(ruleset: Optional[str] = None) -> PolicyEngine:
    """Get or create a policy engine.
    
    Args:
        ruleset: Profile/ruleset name to use. If None, uses default profile.
    """
    global _engine
    profile_to_use = ruleset or _default_profile
    if _engine is None or _engine._ruleset_name != profile_to_use:
        _engine = PolicyEngine(profile_to_use)
    return _engine

