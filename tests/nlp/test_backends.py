"""
Unit tests for NLP backends.
"""

import pytest
from nnrt.ir.enums import EntityRole, EntityType, EventType, SpanLabel
from nnrt.nlp.interfaces import SpanTagResult
from nnrt.nlp.backends.stub import StubSpanTagger, StubEntityExtractor, StubEventExtractor
from nnrt.nlp.backends.spacy_backend import SpacyEntityExtractor, SpacyEventExtractor


class TestStubBackends:
    """Tests for stub (no-op) backends."""

    def test_stub_span_tagger_returns_unknown(self):
        """Verify stub tagger returns single UNKNOWN span."""
        tagger = StubSpanTagger()
        results = tagger.tag("Hello world")
        
        assert len(results) == 1
        assert results[0].label == SpanLabel.UNKNOWN
        assert results[0].text == "Hello world"
        assert results[0].confidence == 0.0

    def test_stub_entity_extractor_returns_empty(self):
        """Verify stub entity extractor returns nothing."""
        extractor = StubEntityExtractor()
        results = extractor.extract("The officer approached.")
        
        assert len(results) == 0

    def test_stub_event_extractor_returns_empty(self):
        """Verify stub event extractor returns nothing."""
        extractor = StubEventExtractor()
        results = extractor.extract("He ran away.")
        
        assert len(results) == 0

    def test_backend_names(self):
        """Verify all stub backends have consistent naming."""
        assert StubSpanTagger().name == "stub"
        assert StubEntityExtractor().name == "stub"
        assert StubEventExtractor().name == "stub"


class TestSpacyEntityExtractor:
    """Tests for spaCy entity extraction."""

    def test_extracts_reporter_pronouns(self):
        """Verify 'I', 'me', 'my' map to Reporter role."""
        extractor = SpacyEntityExtractor()
        results = extractor.extract("I saw it happen.")
        
        reporter_results = [r for r in results if r.role == EntityRole.REPORTER]
        assert len(reporter_results) >= 1
        assert reporter_results[0].label == "Reporter"

    def test_extracts_authority_titles(self):
        """Verify authority titles are detected."""
        extractor = SpacyEntityExtractor()
        results = extractor.extract("The officer approached.")
        
        authority_results = [r for r in results if r.role == EntityRole.AUTHORITY]
        assert len(authority_results) >= 1

    def test_extracts_generic_subjects(self):
        """Verify generic subjects are detected."""
        extractor = SpacyEntityExtractor()
        results = extractor.extract("The driver fled the scene.")
        
        subject_results = [r for r in results if r.role == EntityRole.SUBJECT]
        assert len(subject_results) >= 1

    def test_mentions_include_positions(self):
        """Verify mentions include character positions."""
        extractor = SpacyEntityExtractor()
        results = extractor.extract("The officer stopped me.")
        
        # At least one result should have mentions with positions
        entities_with_mentions = [r for r in results if r.mentions]
        assert len(entities_with_mentions) >= 1
        
        # Mentions are tuples: (start, end, text)
        mention = entities_with_mentions[0].mentions[0]
        assert isinstance(mention, tuple)
        assert len(mention) == 3
        assert isinstance(mention[0], int)  # start
        assert isinstance(mention[1], int)  # end
        assert isinstance(mention[2], str)  # text

    def test_backend_name(self):
        """Verify backend name for tracing."""
        extractor = SpacyEntityExtractor()
        assert extractor.name == "spacy_entity"


class TestSpacyEventExtractor:
    """Tests for spaCy event extraction."""

    def test_extracts_action_verbs(self):
        """Verify action verbs create ACTION events."""
        extractor = SpacyEventExtractor()
        results = extractor.extract("He grabbed her arm.")
        
        action_events = [r for r in results if r.type == EventType.ACTION]
        assert len(action_events) >= 1

    def test_extracts_movement_verbs(self):
        """Verify movement verbs create MOVEMENT events."""
        extractor = SpacyEventExtractor()
        results = extractor.extract("She ran away quickly.")
        
        movement_events = [r for r in results if r.type == EventType.MOVEMENT]
        assert len(movement_events) >= 1

    def test_extracts_verbal_events(self):
        """Verify speech verbs create VERBAL events."""
        extractor = SpacyEventExtractor()
        results = extractor.extract("He yelled at the crowd.")
        
        verbal_events = [r for r in results if r.type == EventType.VERBAL]
        assert len(verbal_events) >= 1

    def test_includes_actor_mention(self):
        """Verify actor (subject) is extracted."""
        extractor = SpacyEventExtractor()
        results = extractor.extract("The officer grabbed my arm.")
        
        events_with_actors = [r for r in results if r.actor_mention]
        assert len(events_with_actors) >= 1

    def test_includes_target_mention(self):
        """Verify target (object) is extracted."""
        extractor = SpacyEventExtractor()
        results = extractor.extract("He hit the wall.")
        
        events_with_targets = [r for r in results if r.target_mention]
        assert len(events_with_targets) >= 1

    def test_includes_source_positions(self):
        """Verify events include source text positions."""
        extractor = SpacyEventExtractor()
        results = extractor.extract("He ran away.")
        
        assert len(results) >= 1
        event = results[0]
        assert event.source_start >= 0
        assert event.source_end > event.source_start

    def test_backend_name(self):
        """Verify backend name for tracing."""
        extractor = SpacyEventExtractor()
        assert extractor.name == "spacy_event"
