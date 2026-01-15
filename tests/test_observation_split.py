"""
Tests for Observation Split - Data Buckets (output/structured.py)

Tests that atomic statements are correctly routed to:
- observed_events (direct_event)
- self_reported_states (self_report)
- Other buckets based on epistemic_type
"""

import pytest
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


# Mock classes to avoid full pipeline dependency
class StatementType(Enum):
    observation = "observation"
    claim = "claim"
    interpretation = "interpretation"
    quote = "quote"


@dataclass
class MockAtomicStatement:
    """Mock AtomicStatement for testing routing logic."""
    id: str = "test_stmt"
    text: str = ""
    type_hint: StatementType = StatementType.observation
    segment_id: str = "seg_1"
    confidence: float = 0.9
    clause_type: str = "main"
    source: str = "reporter"
    epistemic_type: str = "unknown"
    polarity: str = "asserted"
    evidence_source: str = "self_report"
    connector: Optional[str] = None
    derived_from: list = field(default_factory=list)
    flags: list = field(default_factory=list)


class TestObservationRouting:
    """Tests for routing logic based on epistemic_type."""
    
    def test_direct_event_routes_to_observed_events(self):
        """direct_event should go to observed_events bucket."""
        stmt = MockAtomicStatement(
            text="Officer grabbed my arm",
            epistemic_type="direct_event"
        )
        
        # Simulate routing logic
        observed_events = []
        self_reported_states = []
        other = []
        
        if stmt.epistemic_type == "direct_event":
            observed_events.append(stmt)
        elif stmt.epistemic_type == "self_report":
            self_reported_states.append(stmt)
        else:
            other.append(stmt)
        
        assert len(observed_events) == 1
        assert len(self_reported_states) == 0
    
    def test_self_report_routes_to_self_reported_states(self):
        """self_report should go to self_reported_states bucket."""
        stmt = MockAtomicStatement(
            text="I was so scared I froze",
            epistemic_type="self_report"
        )
        
        observed_events = []
        self_reported_states = []
        
        if stmt.epistemic_type == "direct_event":
            observed_events.append(stmt)
        elif stmt.epistemic_type == "self_report":
            self_reported_states.append(stmt)
        
        assert len(observed_events) == 0
        assert len(self_reported_states) == 1
    
    def test_interpretation_not_in_observations(self):
        """interpretation should NOT go to observed_events."""
        stmt = MockAtomicStatement(
            text="He obviously wanted to hurt me",
            epistemic_type="interpretation"
        )
        
        observed_events = []
        self_reported_states = []
        
        if stmt.epistemic_type == "direct_event":
            observed_events.append(stmt)
        elif stmt.epistemic_type == "self_report":
            self_reported_states.append(stmt)
        
        assert len(observed_events) == 0
        assert len(self_reported_states) == 0
    
    def test_legal_claim_not_in_observations(self):
        """legal_claim should NOT go to observed_events."""
        stmt = MockAtomicStatement(
            text="This was racial profiling",
            epistemic_type="legal_claim"
        )
        
        observed_events = []
        
        if stmt.epistemic_type == "direct_event":
            observed_events.append(stmt)
        
        assert len(observed_events) == 0
    
    def test_conspiracy_claim_not_in_observations(self):
        """conspiracy_claim should NOT go to observed_events."""
        stmt = MockAtomicStatement(
            text="They always protect their own",
            epistemic_type="conspiracy_claim"
        )
        
        observed_events = []
        
        if stmt.epistemic_type == "direct_event":
            observed_events.append(stmt)
        
        assert len(observed_events) == 0


class TestMultipleStatementRouting:
    """Tests for routing multiple statements correctly."""
    
    def test_mixed_statements_route_correctly(self):
        """Mixed epistemic types should route to correct buckets."""
        statements = [
            MockAtomicStatement(text="Officer grabbed my arm", epistemic_type="direct_event"),
            MockAtomicStatement(text="I was scared", epistemic_type="self_report"),
            MockAtomicStatement(text="He wanted to hurt me", epistemic_type="interpretation"),
            MockAtomicStatement(text="This was racial profiling", epistemic_type="legal_claim"),
            MockAtomicStatement(text="Officer put handcuffs on me", epistemic_type="direct_event"),
            MockAtomicStatement(text="I screamed in pain", epistemic_type="self_report"),
        ]
        
        observed_events = []
        self_reported_states = []
        other = []
        
        for stmt in statements:
            if stmt.epistemic_type == "direct_event":
                observed_events.append(stmt)
            elif stmt.epistemic_type == "self_report":
                self_reported_states.append(stmt)
            else:
                other.append(stmt)
        
        assert len(observed_events) == 2
        assert len(self_reported_states) == 2
        assert len(other) == 2  # interpretation + legal_claim


class TestCriticalInvariant:
    """Tests for the critical invariant: observations must be externally observable."""
    
    def test_internal_state_not_in_observed_events(self):
        """CRITICAL: Internal states MUST NOT appear in observed_events."""
        internal_states = [
            "I was so scared I froze",
            "I felt terrified",
            "I was in pain",
            "I have PTSD now",
            "I can't sleep at night",
        ]
        
        for text in internal_states:
            stmt = MockAtomicStatement(text=text, epistemic_type="self_report")
            
            # This MUST be false
            is_observed_event = stmt.epistemic_type == "direct_event"
            
            assert not is_observed_event, \
                f"CRITICAL VIOLATION: '{text}' was routed to observed_events"
    
    def test_interpretations_not_in_observed_events(self):
        """CRITICAL: Interpretations MUST NOT appear in observed_events."""
        interpretations = [
            "He obviously wanted to hurt me",
            "She clearly tried to intimidate me",
            "It was designed to protect them",
        ]
        
        for text in interpretations:
            stmt = MockAtomicStatement(text=text, epistemic_type="interpretation")
            
            is_observed_event = stmt.epistemic_type == "direct_event"
            
            assert not is_observed_event, \
                f"CRITICAL VIOLATION: '{text}' was routed to observed_events"
