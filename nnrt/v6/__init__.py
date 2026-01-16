"""
NNRT V6 - Verification Platform Features.

V6 introduces three major features:
1. Enhanced Timeline Reconstruction (timeline gaps, multi-day support)
2. Question Generation (automatic investigation questions)
3. Multi-Narrative Comparison (cross-reference multiple accounts)

Usage:
    from nnrt.v6.questions import generate_all_questions, QuestionSet
    from nnrt.v6.comparison import compare_narratives, ComparisonResult
"""

from nnrt.v6.questions import (
    generate_all_questions,
    QuestionSet,
    InvestigationQuestion,
    QuestionPriority,
    QuestionCategory,
)

from nnrt.v6.comparison import (
    compare_narratives,
    format_comparison_report,
    ComparisonResult,
    ComparisonFinding,
    ComparisonType,
    SeverityLevel,
)

__all__ = [
    # Questions
    "generate_all_questions",
    "QuestionSet",
    "InvestigationQuestion",
    "QuestionPriority",
    "QuestionCategory",
    # Comparison
    "compare_narratives",
    "format_comparison_report",
    "ComparisonResult",
    "ComparisonFinding",
    "ComparisonType",
    "SeverityLevel",
]
