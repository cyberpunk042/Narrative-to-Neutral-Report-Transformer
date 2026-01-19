"""
Tests for the Selection Layer (Stage 2)

Tests that p55_select correctly filters atoms into output sections
based on classification and selection mode.
"""

import pytest
from dataclasses import dataclass
from typing import Optional

from nnrt.selection.models import SelectionMode, SelectionResult
from nnrt.passes.p55_select import (
    select,
    _select_events,
    _select_entities,
    _select_quotes,
    _select_timeline,
    _parse_mode,
)


# =============================================================================
# Test Mode Parsing
# =============================================================================

class TestModeParser:
    """Tests for mode string to enum conversion."""
    
    def test_parse_strict(self):
        assert _parse_mode("strict") == SelectionMode.STRICT
    
    def test_parse_full(self):
        assert _parse_mode("full") == SelectionMode.FULL
    
    def test_parse_timeline(self):
        assert _parse_mode("timeline") == SelectionMode.TIMELINE
    
    def test_parse_events_short(self):
        assert _parse_mode("events") == SelectionMode.EVENTS_ONLY
    
    def test_parse_events_full(self):
        assert _parse_mode("events_only") == SelectionMode.EVENTS_ONLY
    
    def test_parse_recompose_short(self):
        assert _parse_mode("recompose") == SelectionMode.RECOMPOSITION
    
    def test_parse_recomposition(self):
        assert _parse_mode("recomposition") == SelectionMode.RECOMPOSITION
    
    def test_parse_case_insensitive(self):
        assert _parse_mode("STRICT") == SelectionMode.STRICT
        assert _parse_mode("Full") == SelectionMode.FULL
    
    def test_parse_unknown_defaults_to_strict(self):
        """Unknown mode names should default to STRICT."""
        assert _parse_mode("unknown") == SelectionMode.STRICT


# =============================================================================
# Test SelectionResult
# =============================================================================

class TestSelectionResult:
    """Tests for SelectionResult dataclass."""
    
    def test_empty_result(self):
        result = SelectionResult(mode="strict")
        assert result.mode == "strict"
        assert len(result.observed_events) == 0
        assert len(result.follow_up_events) == 0
        assert len(result.narrative_excerpts) == 0
    
    def test_summary(self):
        result = SelectionResult(mode="strict")
        result.observed_events = ["e1", "e2"]
        result.narrative_excerpts = [("e3", "reason")]
        result.incident_participants = ["ent1"]
        
        summary = result.summary()
        assert "Selection[strict]" in summary
        assert "events=2/0/1" in summary
        assert "entities=1" in summary


# =============================================================================
# Mock Objects for Testing
# =============================================================================

@dataclass
class MockEvent:
    id: str
    description: str = ""
    is_camera_friendly: bool = True
    camera_friendly_confidence: float = 0.9
    camera_friendly_reason: Optional[str] = None
    is_follow_up: bool = False
    is_source_derived: bool = False
    is_fragment: bool = False
    actor_label: Optional[str] = None


@dataclass
class MockEntity:
    id: str
    label: str = ""
    role: str = "unknown"
    participation: Optional[str] = None
    type: str = "person"


@dataclass
class MockSpeechAct:
    id: str
    speaker_label: Optional[str] = None
    speaker_resolved: bool = False
    is_quarantined: bool = False
    quarantine_reason: Optional[str] = None


@dataclass
class MockTimelineEntry:
    id: str
    description: str = ""
    event_id: Optional[str] = None


@dataclass
class MockRequest:
    metadata: dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class MockContext:
    events: list = None
    entities: list = None
    speech_acts: list = None
    timeline: list = None
    atomic_statements: list = None  # V7 / Stage 2
    identifiers: list = None  # V7 / Stage 2
    request: MockRequest = None
    selection_result: SelectionResult = None
    trace: list = None
    
    def __post_init__(self):
        if self.events is None:
            self.events = []
        if self.entities is None:
            self.entities = []
        if self.speech_acts is None:
            self.speech_acts = []
        if self.timeline is None:
            self.timeline = []
        if self.atomic_statements is None:
            self.atomic_statements = []
        if self.identifiers is None:
            self.identifiers = []
        if self.request is None:
            self.request = MockRequest()
        if self.trace is None:
            self.trace = []
    
    def get_event_by_id(self, event_id):
        for event in self.events:
            if event.id == event_id:
                return event
        return None
    
    def add_trace(self, **kwargs):
        self.trace.append(kwargs)


# =============================================================================
# Test Event Selection
# =============================================================================

class TestEventSelection:
    """Tests for event selection logic."""
    
    def test_strict_mode_camera_friendly_selected(self):
        """Camera-friendly events should go to observed_events."""
        result = SelectionResult(mode="strict")
        ctx = MockContext(events=[
            MockEvent(id="e1", is_camera_friendly=True, camera_friendly_confidence=0.9),
        ])
        
        result = _select_events(ctx, result, SelectionMode.STRICT)
        
        assert "e1" in result.observed_events
        assert len(result.narrative_excerpts) == 0
    
    def test_strict_mode_non_camera_friendly_to_excerpts(self):
        """Non-camera-friendly events should go to narrative_excerpts."""
        result = SelectionResult(mode="strict")
        ctx = MockContext(events=[
            MockEvent(
                id="e1",
                is_camera_friendly=False,
                camera_friendly_reason="conjunction_start"
            ),
        ])
        
        result = _select_events(ctx, result, SelectionMode.STRICT)
        
        assert len(result.observed_events) == 0
        assert ("e1", "conjunction_start") in result.narrative_excerpts
    
    def test_strict_mode_follow_up_routed(self):
        """Follow-up events should go to follow_up_events."""
        result = SelectionResult(mode="strict")
        ctx = MockContext(events=[
            MockEvent(
                id="e1",
                is_camera_friendly=True,
                camera_friendly_confidence=0.9,
                is_follow_up=True
            ),
        ])
        
        result = _select_events(ctx, result, SelectionMode.STRICT)
        
        assert "e1" in result.follow_up_events
        assert "e1" not in result.observed_events
    
    def test_strict_mode_source_derived_routed(self):
        """Source-derived events should go to source_derived_events."""
        result = SelectionResult(mode="strict")
        ctx = MockContext(events=[
            MockEvent(
                id="e1",
                is_camera_friendly=True,
                camera_friendly_confidence=0.9,
                is_source_derived=True
            ),
        ])
        
        result = _select_events(ctx, result, SelectionMode.STRICT)
        
        assert "e1" in result.source_derived_events
        assert "e1" not in result.observed_events
    
    def test_strict_mode_low_confidence_to_excerpts(self):
        """Low confidence events should go to narrative_excerpts."""
        result = SelectionResult(mode="strict")
        ctx = MockContext(events=[
            MockEvent(
                id="e1",
                is_camera_friendly=True,
                camera_friendly_confidence=0.5  # Below threshold
            ),
        ])
        
        result = _select_events(ctx, result, SelectionMode.STRICT)
        
        assert len(result.observed_events) == 0
        assert ("e1", "low_confidence") in result.narrative_excerpts
    
    def test_full_mode_includes_all(self):
        """FULL mode should include all events in observed."""
        result = SelectionResult(mode="full")
        ctx = MockContext(events=[
            MockEvent(id="e1", is_camera_friendly=True),
            MockEvent(id="e2", is_camera_friendly=False),
        ])
        
        result = _select_events(ctx, result, SelectionMode.FULL)
        
        assert "e1" in result.observed_events
        assert "e2" in result.observed_events
        assert len(result.narrative_excerpts) == 0


# =============================================================================
# Test Entity Selection
# =============================================================================

class TestEntitySelection:
    """Tests for entity selection logic."""
    
    def test_incident_role_categorized(self):
        """Entities with incident roles should go to incident_participants."""
        result = SelectionResult(mode="strict")
        ctx = MockContext(entities=[
            MockEntity(id="ent1", label="Officer Rodriguez", role="subject_officer"),
        ])
        
        result = _select_entities(ctx, result, SelectionMode.STRICT)
        
        assert "ent1" in result.incident_participants
    
    def test_post_incident_role_categorized(self):
        """Entities with post-incident roles should go to post_incident_pros."""
        result = SelectionResult(mode="strict")
        ctx = MockContext(entities=[
            MockEntity(id="ent1", label="Dr. Smith", role="medical_provider"),
        ])
        
        result = _select_entities(ctx, result, SelectionMode.STRICT)
        
        assert "ent1" in result.post_incident_pros
    
    def test_bare_role_excluded(self):
        """Bare role labels should be excluded."""
        result = SelectionResult(mode="strict")
        ctx = MockContext(entities=[
            MockEntity(id="ent1", label="partner", role="unknown"),
        ])
        
        result = _select_entities(ctx, result, SelectionMode.STRICT)
        
        assert "ent1" in result.excluded_entities
        assert "ent1" not in result.incident_participants


# =============================================================================
# Test Quote Selection
# =============================================================================

class TestQuoteSelection:
    """Tests for quote selection logic."""
    
    def test_resolved_quote_preserved(self):
        """Quotes with speaker_label should go to preserved_quotes."""
        result = SelectionResult(mode="strict")
        ctx = MockContext(speech_acts=[
            MockSpeechAct(id="q1", speaker_label="Officer Rodriguez"),
        ])
        
        result = _select_quotes(ctx, result, SelectionMode.STRICT)
        
        assert "q1" in result.preserved_quotes
    
    def test_unresolved_quote_quarantined(self):
        """Quotes without speaker should go to quarantined_quotes."""
        result = SelectionResult(mode="strict")
        ctx = MockContext(speech_acts=[
            MockSpeechAct(id="q1", speaker_label=None),
        ])
        
        result = _select_quotes(ctx, result, SelectionMode.STRICT)
        
        assert ("q1", "speaker_unresolved") in result.quarantined_quotes


# =============================================================================
# Test Full Pipeline Selection
# =============================================================================

class TestFullPipelineSelection:
    """Integration tests for the full select() function."""
    
    def test_select_populates_result(self):
        """select() should populate selection_result on context."""
        ctx = MockContext(
            events=[MockEvent(id="e1", is_camera_friendly=True)],
            entities=[MockEntity(id="ent1", label="John", role="reporter")],
            speech_acts=[MockSpeechAct(id="q1", speaker_label="John")],
            timeline=[MockTimelineEntry(id="t1", description="Event occurred")],
        )
        
        result_ctx = select(ctx, SelectionMode.STRICT)
        
        assert result_ctx.selection_result is not None
        assert result_ctx.selection_result.mode == "strict"
        assert len(result_ctx.selection_result.observed_events) == 1
    
    def test_select_reads_mode_from_metadata(self):
        """select() should read mode from request metadata."""
        ctx = MockContext(
            request=MockRequest(metadata={'selection_mode': 'full'}),
            events=[MockEvent(id="e1", is_camera_friendly=False)],
            entities=[],
            speech_acts=[],
            timeline=[],
        )
        
        result_ctx = select(ctx)
        
        assert result_ctx.selection_result.mode == "full"
        # In FULL mode, all events go to observed
        assert "e1" in result_ctx.selection_result.observed_events
