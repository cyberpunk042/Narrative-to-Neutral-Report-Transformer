"""
Tests for Pass 72 — Safety Scrub

Tests the final safety net that scrubs dangerous epistemic content
from rendered text.
"""

import pytest
from nnrt.passes.p72_safety_scrub import (
    safety_scrub,
    _clean_artifacts,
    LEGAL_SCRUB_PATTERNS,
    CONSPIRACY_SCRUB_PATTERNS,
    INVECTIVE_SCRUB_PATTERNS,
)
from nnrt.core.context import TransformContext, TransformRequest


class TestSafetyScrubPatterns:
    """Tests for pattern-based scrubbing."""
    
    # =========================================================================
    # Legal claims → Attributed form
    # =========================================================================
    
    @pytest.mark.parametrize("input_text,should_change", [
        ("This was racial profiling", True),
        ("This was clearly racial profiling", True),
        ("This was police brutality", True),
        ("They used excessive force", True),
        ("Officer approached me", False),  # Neutral - no change
    ])
    def test_legal_scrub_applied(self, input_text, should_change):
        """Legal claims should be scrubbed or attributed."""
        ctx = TransformContext.from_request(TransformRequest(text="test"))
        ctx.rendered_text = input_text
        
        result = safety_scrub(ctx)
        
        if should_change:
            assert result.rendered_text != input_text, f"'{input_text}' should be scrubbed"
        else:
            assert result.rendered_text == input_text, f"'{input_text}' should NOT be changed"
    
    # =========================================================================
    # Conspiracy → Removed entirely
    # =========================================================================
    
    @pytest.mark.parametrize("input_text", [
        "I know they always protect their own.",
        "they always protect their own",
        "massive cover-up",
    ])
    def test_conspiracy_scrub_removal(self, input_text):
        """Conspiracy claims should be removed."""
        ctx = TransformContext.from_request(TransformRequest(text="test"))
        ctx.rendered_text = f"Some text. {input_text} More text."
        
        result = safety_scrub(ctx)
        
        # The conspiracy phrase should be removed or significantly reduced
        assert input_text.lower() not in result.rendered_text.lower(), \
            f"'{input_text}' should be removed from output"
    
    # =========================================================================
    # Invective → Replaced with neutral
    # =========================================================================
    
    @pytest.mark.parametrize("input_text,invective,neutral", [
        ("The thug cop attacked me", "thug cop", "officer"),
    ])
    def test_invective_scrub_replacement(self, input_text, invective, neutral):
        """Invective should be replaced with neutral terms."""
        ctx = TransformContext.from_request(TransformRequest(text="test"))
        ctx.rendered_text = input_text
        
        result = safety_scrub(ctx)
        
        if invective.lower() in input_text.lower():
            # Should be replaced or removed
            assert invective.lower() not in result.rendered_text.lower(), \
                f"'{invective}' should be removed from output"


class TestCleanArtifacts:
    """Tests for _clean_artifacts helper."""
    
    def test_double_spaces_removed(self):
        """Double spaces should be collapsed."""
        assert _clean_artifacts("word  word") == "word word"
        assert _clean_artifacts("word   word") == "word word"
    
    def test_orphaned_punctuation_fixed(self):
        """Orphaned punctuation should be fixed."""
        assert _clean_artifacts("word .") == "word."
        assert _clean_artifacts("word ,") == "word,"
    
    def test_empty_parens_removed(self):
        """Empty parentheses should be removed."""
        assert _clean_artifacts("text () more") == "text  more"
        assert _clean_artifacts("text [] more") == "text  more"
    
    def test_double_dashes_removed(self):
        """Leftover -- -- patterns should be removed."""
        assert _clean_artifacts("text -- -- more") == "text  more"


class TestSafetyScrubIntegration:
    """Integration tests for full safety_scrub pass."""
    
    def test_clean_text_unchanged(self):
        """Clean text should pass through unchanged."""
        ctx = TransformContext.from_request(TransformRequest(text="test"))
        ctx.rendered_text = "Officer Rodriguez approached the reporter. He asked for identification."
        
        result = safety_scrub(ctx)
        
        assert result.rendered_text == ctx.rendered_text
    
    def test_no_rendered_text_returns_ctx(self):
        """Missing rendered_text should return context unchanged."""
        ctx = TransformContext.from_request(TransformRequest(text="test"))
        ctx.rendered_text = None
        
        result = safety_scrub(ctx)
        
        assert result.rendered_text is None


class TestPatternCoverage:
    """Tests to ensure pattern lists are populated."""
    
    def test_legal_scrub_patterns_exist(self):
        assert len(LEGAL_SCRUB_PATTERNS) > 0
    
    def test_conspiracy_scrub_patterns_exist(self):
        assert len(CONSPIRACY_SCRUB_PATTERNS) > 0
    
    def test_invective_scrub_patterns_exist(self):
        assert len(INVECTIVE_SCRUB_PATTERNS) > 0
