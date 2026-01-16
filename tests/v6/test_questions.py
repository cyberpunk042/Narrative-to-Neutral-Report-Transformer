"""
Unit tests for V6 Question Generation.
"""

import pytest
from nnrt.v6.questions import (
    generate_all_questions,
    generate_questions_from_gaps,
    generate_questions_from_statements,
    QuestionPriority,
    QuestionCategory,
)


class MockGap:
    """Mock TimeGap for testing."""
    def __init__(self, gap_id, requires_investigation=True, gap_type="uncertain", 
                 suggested_question=None):
        self.id = gap_id
        self.requires_investigation = requires_investigation
        self.gap_type = type('obj', (object,), {'value': gap_type})()
        self.suggested_question = suggested_question


class MockStatement:
    """Mock AtomicStatement for testing."""
    def __init__(self, stmt_id, text):
        self.id = stmt_id
        self.text = text


class MockEvent:
    """Mock Event for testing."""
    def __init__(self, event_id, description, event_type="action"):
        self.id = event_id
        self.description = description
        self.type = type('obj', (object,), {'value': event_type})()


class TestQuestionGenerationFromGaps:
    """Tests for gap-based question generation."""
    
    def test_generates_question_from_gap(self):
        """Should generate a question from a timeline gap."""
        gaps = [MockGap("gap_001", requires_investigation=True)]
        
        questions = generate_questions_from_gaps(gaps, [])
        
        assert len(questions) >= 1
        assert questions[0].category == QuestionCategory.TIMELINE_GAP
    
    def test_critical_priority_for_uncertain_gaps(self):
        """Uncertain gaps should be critical priority."""
        gaps = [MockGap("gap_001", gap_type="uncertain")]
        
        questions = generate_questions_from_gaps(gaps, [])
        
        assert len(questions) >= 1
        assert questions[0].priority == QuestionPriority.CRITICAL
    
    def test_uses_suggested_question(self):
        """Should use the gap's suggested question if available."""
        suggested = "What happened between event A and event B?"
        gaps = [MockGap("gap_001", suggested_question=suggested)]
        
        questions = generate_questions_from_gaps(gaps, [])
        
        assert len(questions) >= 1
        assert questions[0].text == suggested
    
    def test_skips_non_investigation_gaps(self):
        """Should skip gaps not requiring investigation."""
        gaps = [MockGap("gap_001", requires_investigation=False)]
        
        questions = generate_questions_from_gaps(gaps, [])
        
        assert len(questions) == 0


class TestQuestionGenerationFromStatements:
    """Tests for statement-based question generation."""
    
    def test_vague_someone_generates_question(self):
        """'someone' should generate a clarification question."""
        stmts = [MockStatement("stmt_001", "Someone grabbed my arm")]
        
        questions = generate_questions_from_statements(stmts)
        
        # Should generate at least one question about "someone"
        assert len(questions) >= 1
        vague_questions = [q for q in questions if q.category == QuestionCategory.VAGUE_DESCRIPTION]
        assert len(vague_questions) >= 1
    
    def test_vague_something_generates_question(self):
        """'something' should generate a clarification question."""
        stmts = [MockStatement("stmt_001", "I hit my head on something")]
        
        questions = generate_questions_from_statements(stmts)
        
        assert len(questions) >= 1
    
    def test_passive_action_generates_actor_question(self):
        """Passive voice actions should generate 'who' questions."""
        stmts = [MockStatement("stmt_001", "I was grabbed and pushed to the ground")]
        
        questions = generate_questions_from_statements(stmts)
        
        actor_questions = [q for q in questions if q.category == QuestionCategory.MISSING_ACTOR]
        assert len(actor_questions) >= 1
    
    def test_injury_keywords_generate_questions(self):
        """Injury-related statements should generate medical questions."""
        stmts = [MockStatement("stmt_001", "My shoulder was hurting badly")]
        
        questions = generate_questions_from_statements(stmts)
        
        injury_questions = [q for q in questions if q.category == QuestionCategory.INJURY_DETAIL]
        assert len(injury_questions) >= 1
        assert injury_questions[0].priority == QuestionPriority.HIGH


class TestQuestionSetGeneration:
    """Tests for complete question set generation."""
    
    def test_generates_empty_set_with_no_input(self):
        """Should return empty set with no input."""
        question_set = generate_all_questions()
        
        assert question_set.total_count == 0
        assert len(question_set.questions) == 0
    
    def test_counts_priorities_correctly(self):
        """Should count priorities correctly."""
        gaps = [
            MockGap("gap_001", gap_type="uncertain"),  # Critical
            MockGap("gap_002", gap_type="day_boundary"),  # High
        ]
        
        question_set = generate_all_questions(time_gaps=gaps)
        
        assert question_set.critical_count >= 1
        assert question_set.high_count >= 1
    
    def test_sorts_by_priority(self):
        """Questions should be sorted by priority (critical first)."""
        gaps = [MockGap("gap_001", gap_type="uncertain")]
        stmts = [MockStatement("stmt_001", "Someone did something")]
        
        question_set = generate_all_questions(
            time_gaps=gaps,
            atomic_statements=stmts,
        )
        
        if len(question_set.questions) >= 2:
            # First question should be critical (from gap)
            assert question_set.questions[0].priority == QuestionPriority.CRITICAL
    
    def test_calculates_category_counts(self):
        """Should count questions by category."""
        gaps = [MockGap("gap_001")]
        stmts = [MockStatement("stmt_001", "Someone grabbed me")]
        
        question_set = generate_all_questions(
            time_gaps=gaps,
            atomic_statements=stmts,
        )
        
        assert question_set.timeline_gap_questions >= 1


class TestQuestionModel:
    """Tests for InvestigationQuestion model."""
    
    def test_question_has_required_fields(self):
        """Questions should have all required fields."""
        gaps = [MockGap("gap_001")]
        
        questions = generate_questions_from_gaps(gaps, [])
        
        assert len(questions) >= 1
        q = questions[0]
        assert q.id is not None
        assert q.text is not None
        assert q.category is not None
        assert q.priority is not None
    
    def test_question_has_rationale(self):
        """Questions should have rationale."""
        gaps = [MockGap("gap_001", gap_type="uncertain")]
        
        questions = generate_questions_from_gaps(gaps, [])
        
        assert len(questions) >= 1
        assert questions[0].rationale != ""
