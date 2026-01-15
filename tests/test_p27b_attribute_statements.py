"""
Tests for Pass 27b — Statement Attribution & Aberration

Tests the V4 attribution and aberration logic that transforms dangerous
epistemic content into safe attributed forms or quarantines it.
"""

import pytest
from nnrt.passes.p27b_attribute_statements import (
    _check_aberration,
    _extract_legal_claim,
    _extract_interpretation,
    INVECTIVE_PATTERNS,
    UNFALSIFIABLE_PATTERNS,
    LEGAL_TERM_EXTRACTIONS,
    INTERPRETATION_EXTRACTIONS,
)


class TestCheckAberration:
    """Tests for _check_aberration function."""
    
    # =========================================================================
    # Invective → Must be aberrated
    # =========================================================================
    
    @pytest.mark.parametrize("text,expected_reason", [
        ("thug cop attacked me", "invective"),
        ("the psychotic officer", "invective"),
        ("the maniac was screaming", "invective"),
        ("brutally assaulted me", "invective"),
        ("viciously attacked", "invective"),
        ("savage beating", "toxic"),  # toxic combination
    ])
    def test_invective_aberration(self, text, expected_reason):
        """Invective should trigger aberration."""
        is_aberrated, reason = _check_aberration(text)
        assert is_aberrated, f"'{text}' should be aberrated"
        assert expected_reason in reason.lower(), f"Reason should contain '{expected_reason}', got '{reason}'"
    
    # =========================================================================
    # Conspiracy → Must be aberrated
    # =========================================================================
    
    @pytest.mark.parametrize("text", [
        "massive cover-up going on",
        "I know they always protect their own",
        "code of silence in the department",
        "this is a whitewash investigation",
        "this proves there's a conspiracy",
    ])
    def test_conspiracy_aberration(self, text):
        """Conspiracy claims should trigger aberration."""
        is_aberrated, reason = _check_aberration(text)
        assert is_aberrated, f"'{text}' should be aberrated"
        assert "unfalsifiable" in reason.lower(), f"Reason should contain 'unfalsifiable', got '{reason}'"
    
    # =========================================================================
    # Neutral → No aberration
    # =========================================================================
    
    @pytest.mark.parametrize("text", [
        "Officer approached me",
        "He put handcuffs on me",
        "Sergeant Williams arrived",
        "I went to the hospital",
        "She filed a complaint",
    ])
    def test_neutral_no_aberration(self, text):
        """Neutral statements should not be aberrated."""
        is_aberrated, reason = _check_aberration(text)
        assert not is_aberrated, f"'{text}' should NOT be aberrated, reason: {reason}"


class TestExtractLegalClaim:
    """Tests for _extract_legal_claim function."""
    
    @pytest.mark.parametrize("text,expected_term", [
        ("This was racial profiling", "racial profiling"),
        ("They used excessive force", "excessive force"),
        ("This is police brutality", "police brutality"),
        ("False arrest and imprisonment", "false arrest"),
        ("This was harassment", "harassment"),
    ])
    def test_legal_term_extraction(self, text, expected_term):
        """Legal terms should be extracted and attributed."""
        extracted_claim, attributed_text = _extract_legal_claim(text)
        
        assert extracted_claim is not None, f"Should extract claim from '{text}'"
        assert expected_term in extracted_claim.lower(), f"Extracted: '{extracted_claim}'"
        assert attributed_text is not None, f"Should generate attributed text"
        assert "reporter" in attributed_text.lower(), f"Attribution should mention reporter"
    
    def test_neutral_no_extraction(self):
        """Neutral text should not extract legal claim."""
        extracted, attributed = _extract_legal_claim("Officer approached me")
        assert extracted is None
        assert attributed is None


class TestExtractInterpretation:
    """Tests for _extract_interpretation function."""
    
    @pytest.mark.parametrize("text,expected_in_attribution", [
        ("He obviously wanted to hurt me", "reporter"),
        ("She clearly tried to intimidate me", "reporter"),
        ("He deliberately ignored my pleas", "reporter"),
        ("He was mocking me", "reporter"),
    ])
    def test_interpretation_extraction(self, text, expected_in_attribution):
        """Interpretations should be extracted and attributed."""
        extracted_claim, attributed_text = _extract_interpretation(text)
        
        assert extracted_claim is not None, f"Should extract interpretation from '{text}'"
        assert attributed_text is not None, f"Should generate attributed text"
        assert expected_in_attribution in attributed_text.lower(), f"Attribution should mention '{expected_in_attribution}'"
    
    def test_neutral_no_interpretation(self):
        """Neutral text should not extract interpretation."""
        extracted, attributed = _extract_interpretation("Officer approached me")
        assert extracted is None
        assert attributed is None


class TestPatternCoverage:
    """Tests to ensure pattern lists are populated."""
    
    def test_invective_patterns_exist(self):
        assert len(INVECTIVE_PATTERNS) > 0
    
    def test_unfalsifiable_patterns_exist(self):
        assert len(UNFALSIFIABLE_PATTERNS) > 0
    
    def test_legal_term_extractions_exist(self):
        assert len(LEGAL_TERM_EXTRACTIONS) > 0
    
    def test_interpretation_extractions_exist(self):
        assert len(INTERPRETATION_EXTRACTIONS) > 0
