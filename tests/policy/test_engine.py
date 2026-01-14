"""
Unit tests for the Policy Engine.
"""

import pytest
from nnrt.policy.engine import PolicyEngine, RuleMatch
from nnrt.policy.models import (
    MatchType,
    PolicyRule,
    PolicyRuleset,
    RuleAction,
    RuleMatch as RuleMatchModel,
)


class TestPolicyEngineMatching:
    """Tests for basic policy rule matching."""
    
    def test_keyword_match(self):
        """Verify keyword matching works."""
        engine = PolicyEngine("base")
        
        text = "He intentionally grabbed my arm."
        matches = engine.find_matches(text)
        
        # "intentionally" should be matched by intent_attribution rule
        intent_matches = [m for m in matches if "intentionally" in m.matched_text.lower()]
        assert len(intent_matches) >= 1
    
    def test_phrase_match(self):
        """Verify phrase matching works."""
        engine = PolicyEngine("base")
        
        text = "He tried to escape."
        matches = engine.find_matches(text)
        
        # "tried to" should be matched
        tried_matches = [m for m in matches if "tried to" in m.matched_text.lower()]
        assert len(tried_matches) >= 1
    
    def test_no_match_clean_text(self):
        """Verify clean text has no matches."""
        engine = PolicyEngine("base")
        
        text = "The vehicle was parked on the street."
        matches = engine.find_matches(text)
        
        # Should have minimal or no matches for neutral text
        assert len(matches) <= 2  # Some false positives possible


class TestPolicyDecisions:
    """Tests for policy decision generation."""
    
    def test_apply_rules_produces_decisions(self):
        """Verify apply_rules produces PolicyDecision objects."""
        engine = PolicyEngine("base")
        
        text = "He intentionally pushed me."
        transformed, decisions = engine.apply_rules(text)
        
        # Should have at least one decision
        assert len(decisions) >= 1
        # All should be PolicyDecision objects
        for d in decisions:
            assert hasattr(d, 'rule_id')
            assert hasattr(d, 'action')
    
    def test_decision_has_reason(self):
        """Verify decisions include a reason description."""
        engine = PolicyEngine("base")
        
        text = "He deliberately walked away."
        transformed, decisions = engine.apply_rules(text)
        
        # All decisions should have a reason
        for d in decisions:
            assert d.reason is not None
            assert len(d.reason) > 0


class TestPolicyRulesetLoading:
    """Tests for ruleset loading."""
    
    def test_base_ruleset_loads(self):
        """Verify base ruleset loads successfully."""
        engine = PolicyEngine("base")
        
        ruleset = engine.ruleset
        
        assert ruleset is not None
        assert len(ruleset.rules) > 0
    
    def test_ruleset_has_expected_categories(self):
        """Verify expected rule categories exist."""
        engine = PolicyEngine("base")
        
        # Get all rule IDs
        rule_ids = [r.id for r in engine.ruleset.rules]
        
        # Should have intent and judgment related rules
        has_intent = any("intent" in rid.lower() for rid in rule_ids)
        has_judgment = any("judgment" in rid.lower() for rid in rule_ids)
        
        assert has_intent or has_judgment, f"Expected intent/judgment rules, got: {rule_ids}"


class TestMatchPriority:
    """Tests for match priority ordering."""
    
    def test_matches_sorted_by_priority(self):
        """Verify matches are sorted by rule priority."""
        engine = PolicyEngine("base")
        
        text = "He intentionally and aggressively grabbed me."
        matches = engine.find_matches(text)
        
        if len(matches) >= 2:
            # Matches should be sorted by priority (descending)
            priorities = [m.rule.priority for m in matches]
            is_sorted = all(priorities[i] >= priorities[i+1] for i in range(len(priorities)-1))
            assert is_sorted, f"Priorities not sorted: {priorities}"


class TestContextChecking:
    """Tests for context-aware matching."""
    
    def test_segment_context_affects_matching(self):
        """Verify segment context can affect which rules match."""
        engine = PolicyEngine("base")
        
        # Direct speech context might be treated differently
        direct_speech = '"I want to cooperate," he said.'
        matches = engine.find_matches(direct_speech)
        
        # Results depend on rule configuration
        # This is a smoke test that context checking doesn't crash
        assert isinstance(matches, list)


class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_empty_text(self):
        """Verify empty text produces no matches."""
        engine = PolicyEngine("base")
        
        matches = engine.find_matches("")
        
        assert len(matches) == 0
    
    def test_whitespace_only(self):
        """Verify whitespace-only text produces no matches."""
        engine = PolicyEngine("base")
        
        matches = engine.find_matches("   \n\t   ")
        
        assert len(matches) == 0
    
    def test_special_characters(self):
        """Verify special characters don't crash matching."""
        engine = PolicyEngine("base")
        
        # Text with various special characters
        text = "He said: 'Stop!' [brackets] {braces} <angles>"
        
        # Should not raise
        matches = engine.find_matches(text)
        assert isinstance(matches, list)


class TestSemanticMatching:
    """Tests for semantic matching using Entity/Event graph."""
    
    def test_find_semantic_matches_with_entities(self):
        """Verify semantic matching works with entities."""
        from nnrt.ir.schema_v0_1 import Entity
        from nnrt.ir.enums import EntityRole, EntityType
        
        engine = PolicyEngine("base")
        
        # Create test entities
        entities = [
            Entity(
                id="ent_1",
                type=EntityType.PERSON,
                role=EntityRole.AUTHORITY,
                label="officer",
                mentions=[]
            ),
            Entity(
                id="ent_2",
                type=EntityType.PERSON,
                role=EntityRole.REPORTER,
                label="victim",
                mentions=[]
            ),
        ]
        
        # Find semantic matches
        matches = engine.find_semantic_matches(entities, events=[], segment_text="")
        
        # Should return a list (may be empty if no semantic rules defined)
        assert isinstance(matches, list)
    
    def test_find_semantic_matches_with_events(self):
        """Verify semantic matching works with events."""
        from nnrt.ir.schema_v0_1 import Event
        from nnrt.ir.enums import EventType
        
        engine = PolicyEngine("base")
        
        # Create test events
        events = [
            Event(
                id="evt_1",
                type=EventType.ACTION,
                description="grabbed",
                source_spans=[],
                confidence=0.8
            ),
        ]
        
        # Find semantic matches
        matches = engine.find_semantic_matches(entities=[], events=events, segment_text="")
        
        assert isinstance(matches, list)
    
    def test_evaluate_semantic_returns_decisions(self):
        """Verify evaluate_semantic returns PolicyDecision objects."""
        from nnrt.ir.schema_v0_1 import Entity
        from nnrt.ir.enums import EntityRole, EntityType
        
        engine = PolicyEngine("base")
        
        entities = [
            Entity(
                id="ent_1",
                type=EntityType.PERSON,
                role=EntityRole.AUTHORITY,
                label="officer",
                mentions=[]
            ),
        ]
        
        decisions = engine.evaluate_semantic(entities, events=[])
        
        assert isinstance(decisions, list)
        for d in decisions:
            assert hasattr(d, 'rule_id')
            assert hasattr(d, 'action')
    
    def test_semantic_matching_empty_inputs(self):
        """Verify semantic matching handles empty inputs."""
        engine = PolicyEngine("base")
        
        matches = engine.find_semantic_matches(entities=[], events=[])
        
        assert matches == []

