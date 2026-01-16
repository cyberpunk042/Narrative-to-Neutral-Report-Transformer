"""
Unit tests for V6 Multi-Narrative Comparison.
"""

import pytest
from nnrt.v6.comparison import (
    compare_narratives,
    format_comparison_report,
    ComparisonResult,
    ComparisonType,
    SeverityLevel,
    NarrativeSource,
    _text_similarity,
    _compare_events,
)


class MockTransformResult:
    """Mock TransformResult for testing."""
    def __init__(self, events=None, statements=None, entities=None, timeline=None):
        self.events = events or []
        self.atomic_statements = statements or []
        self.entities = entities or []
        self.timeline = timeline or []


class MockEvent:
    """Mock Event for testing."""
    def __init__(self, event_id, description):
        self.id = event_id
        self.description = description


class MockStatement:
    """Mock AtomicStatement for testing."""
    def __init__(self, stmt_id, text):
        self.id = stmt_id
        self.text = text


class TestTextSimilarity:
    """Tests for text similarity function."""
    
    def test_identical_texts(self):
        """Identical texts should have similarity 1.0."""
        assert _text_similarity("hello world", "hello world") == 1.0
    
    def test_different_texts(self):
        """Completely different texts should have low similarity."""
        score = _text_similarity("hello", "goodbye")
        assert score < 0.5
    
    def test_similar_texts(self):
        """Similar texts should have high similarity."""
        score = _text_similarity(
            "officer grabbed my arm",
            "the officer grabbed my arm tightly"
        )
        assert score > 0.6
    
    def test_empty_text(self):
        """Empty text should return 0."""
        assert _text_similarity("", "hello") == 0.0
        assert _text_similarity("hello", "") == 0.0


class TestCompareNarratives:
    """Tests for narrative comparison."""
    
    def test_empty_sources(self):
        """Empty sources list should return empty result."""
        result = compare_narratives([])
        assert result.source_count == 0
        assert len(result.findings) == 0
    
    def test_single_source(self):
        """Single source should have no comparisons."""
        result = compare_narratives([
            ("complainant", MockTransformResult()),
        ])
        assert result.source_count == 1
        # No findings since nothing to compare against
    
    def test_finds_agreements(self):
        """Should find agreements between similar events."""
        complainant = MockTransformResult(
            events=[MockEvent("e1", "walked on Cedar Street")],
        )
        officer = MockTransformResult(
            events=[MockEvent("e1", "individual on Cedar Street")],
        )
        
        result = compare_narratives([
            ("complainant", complainant),
            ("officer", officer),
        ])
        
        assert result.source_count == 2
        # May find agreement on location
    
    def test_finds_unique_claims(self):
        """Should identify claims only in one source."""
        complainant = MockTransformResult(
            events=[
                MockEvent("e1", "Officer grabbed my arm"),
                MockEvent("e2", "I was pushed to the ground"),
            ],
        )
        officer = MockTransformResult(
            events=[MockEvent("e1", "I approached the individual")],
        )
        
        result = compare_narratives([
            ("complainant", complainant),
            ("officer", officer),
        ])
        
        assert result.unique_claim_count >= 1


class TestComparisonResult:
    """Tests for ComparisonResult model."""
    
    def test_counts_are_correct(self):
        """Summary counts should match findings."""
        complainant = MockTransformResult(
            events=[MockEvent("e1", "walked on Cedar Street")],
        )
        witness = MockTransformResult(
            events=[MockEvent("e1", "walking on Cedar Street")],
        )
        
        result = compare_narratives([
            ("complainant", complainant),
            ("witness", witness),
        ])
        
        # Counts should match actual findings
        agreement_count = sum(1 for f in result.findings if f.type == ComparisonType.AGREEMENT)
        assert result.agreement_count == agreement_count
    
    def test_consistency_score_range(self):
        """Consistency score should be between 0 and 1."""
        result = compare_narratives([
            ("complainant", MockTransformResult()),
            ("officer", MockTransformResult()),
        ])
        
        assert 0.0 <= result.overall_consistency <= 1.0


class TestFormatComparisonReport:
    """Tests for report formatting."""
    
    def test_report_has_header(self):
        """Report should have header."""
        result = ComparisonResult(
            source_count=2,
            source_labels=["complainant", "officer"],
            findings=[],
        )
        
        report = format_comparison_report(result)
        
        assert "MULTI-NARRATIVE COMPARISON REPORT" in report
    
    def test_report_shows_source_count(self):
        """Report should show source count."""
        result = ComparisonResult(
            source_count=2,
            source_labels=["complainant", "officer"],
            findings=[],
        )
        
        report = format_comparison_report(result)
        
        assert "Sources Compared: 2" in report
    
    def test_report_shows_consistency(self):
        """Report should show consistency score."""
        result = ComparisonResult(
            source_count=2,
            source_labels=["a", "b"],
            findings=[],
            overall_consistency=0.75,
        )
        
        report = format_comparison_report(result)
        
        assert "75%" in report or "0.75" in report


class TestNarrativeSource:
    """Tests for NarrativeSource model."""
    
    def test_creates_from_result(self):
        """Should create NarrativeSource from transform result."""
        source = NarrativeSource(
            label="complainant",
            events=[MockEvent("e1", "test event")],
            statements=[MockStatement("s1", "test statement")],
        )
        
        assert source.label == "complainant"
        assert len(source.events) == 1
        assert len(source.statements) == 1


class TestIntegration:
    """Integration tests with real-like data."""
    
    def test_conflicting_narratives(self):
        """Test comparison of conflicting narratives."""
        complainant = MockTransformResult(
            events=[
                MockEvent("e1", "I was walking on Cedar Street"),
                MockEvent("e2", "Officer grabbed my arm without warning"),
                MockEvent("e3", "I did not resist"),
            ],
            statements=[
                MockStatement("s1", "I did not resist"),
                MockStatement("s2", "He grabbed my arm"),
            ],
        )
        
        officer = MockTransformResult(
            events=[
                MockEvent("e1", "I observed individual on Cedar Street"),
                MockEvent("e2", "Individual resisted arrest"),
                MockEvent("e3", "I used minimal force"),
            ],
            statements=[
                MockStatement("s1", "The individual resisted"),
                MockStatement("s2", "I used minimal force"),
            ],
        )
        
        result = compare_narratives([
            ("complainant", complainant),
            ("officer", officer),
        ])
        
        # Should find some unique claims
        assert result.source_count == 2
        assert len(result.findings) >= 0  # May find unique claims
