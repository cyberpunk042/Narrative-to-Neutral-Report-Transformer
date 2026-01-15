"""
Tests for Pass 27 — Epistemic Tagging

Tests the core V4 epistemic classification logic that tags statements
with their epistemic type (direct_event, self_report, interpretation, etc.)
"""

import pytest
from nnrt.passes.p27_epistemic_tag import (
    _classify_epistemic,
    _classify_polarity,
    SELF_REPORT_PATTERNS,
    INTERPRETATION_PATTERNS,
    LEGAL_CLAIM_PATTERNS,
    CONSPIRACY_PATTERNS,
    MEDICAL_FINDING_PATTERNS,
)


class TestClassifyEpistemic:
    """Tests for _classify_epistemic function."""
    
    # =========================================================================
    # direct_event: Physical actions observable by camera
    # =========================================================================
    
    @pytest.mark.parametrize("text", [
        "Officer grabbed my arm",
        "He twisted it behind my back",
        "They approached me with their hands on their weapons",
        "Officer Rodriguez put handcuffs on me",
        "Marcus Johnson was walking his dog",
        "She came out onto her porch",
        "Sergeant Williams came over to me",
        "I asked him what the problem was",
    ])
    def test_direct_event_physical_actions(self, text):
        """Physical actions should classify as direct_event."""
        epistemic_type, evidence_source, confidence = _classify_epistemic(text)
        assert epistemic_type == "direct_event", f"'{text}' should be direct_event, got {epistemic_type}"
    
    # =========================================================================
    # self_report: Internal states (fear, pain, trauma)
    # =========================================================================
    
    @pytest.mark.parametrize("text", [
        "I was so scared I froze in place",
        "I screamed in pain",
        "I was terrified",
        "I have permanent scars from their torture",
        "I now suffer from PTSD, anxiety, and depression",
        "I can no longer walk outside at night without having panic attacks",
        "The psychological trauma has been devastating",
        "I felt like hours had passed",
    ])
    def test_self_report_internal_states(self, text):
        """Internal states should classify as self_report."""
        epistemic_type, evidence_source, confidence = _classify_epistemic(text)
        assert epistemic_type == "self_report", f"'{text}' should be self_report, got {epistemic_type}"
    
    # =========================================================================
    # interpretation: Intent attribution, inference
    # =========================================================================
    
    @pytest.mark.parametrize("text", [
        "He obviously wanted to hurt me",
        "She was clearly trying to intimidate me",
        "He deliberately ignored my pleas",
        "They were clearly enjoying my suffering",
        "I could tell he was looking for trouble",
        "It was obvious they wanted to cover it up",
    ])
    def test_interpretation_intent_attribution(self, text):
        """Intent attributions should classify as interpretation."""
        epistemic_type, evidence_source, confidence = _classify_epistemic(text)
        assert epistemic_type == "interpretation", f"'{text}' should be interpretation, got {epistemic_type}"
    
    # =========================================================================
    # legal_claim: Legal characterizations
    # =========================================================================
    
    @pytest.mark.parametrize("text", [
        "This was racial profiling",
        "They used excessive force",
        "This was police brutality",
        "They searched me without consent",
        "This was an illegal detention",
        "He violated my civil rights",
        "This constitutes false imprisonment",
    ])
    def test_legal_claim_characterizations(self, text):
        """Legal characterizations should classify as legal_claim."""
        epistemic_type, evidence_source, confidence = _classify_epistemic(text)
        assert epistemic_type == "legal_claim", f"'{text}' should be legal_claim, got {epistemic_type}"
    
    # =========================================================================
    # conspiracy_claim: Unfalsifiable allegations
    # =========================================================================
    
    @pytest.mark.parametrize("text", [
        "They always protect their own",
        "This proves there's a massive cover-up",
        "Her call was mysteriously lost in the system",
        "They are conspiring to hide the truth",
        "Which proves they're hiding evidence",
        "This is part of a pattern of violence",
    ])
    def test_conspiracy_claim_unfalsifiable(self, text):
        """Conspiracy claims should classify as conspiracy_claim."""
        epistemic_type, evidence_source, confidence = _classify_epistemic(text)
        assert epistemic_type == "conspiracy_claim", f"'{text}' should be conspiracy_claim, got {epistemic_type}"
    
    # =========================================================================
    # medical_finding: Doctor statements, diagnoses
    # =========================================================================
    
    @pytest.mark.parametrize("text", [
        "Dr. Foster documented bruises on both wrists",
        "She documented bruises",
        "My therapist diagnosed me with PTSD",
        "The medical records show",
        "His injuries were consistent with significant force",
    ])
    def test_medical_finding_doctor_statements(self, text):
        """Medical findings should classify as medical_finding."""
        epistemic_type, evidence_source, confidence = _classify_epistemic(text)
        assert epistemic_type == "medical_finding", f"'{text}' should be medical_finding, got {epistemic_type}"


class TestClassifyPolarity:
    """Tests for _classify_polarity function."""
    
    def test_denied_polarity(self):
        """Denials should be classified correctly."""
        assert _classify_polarity("I did not resist arrest") == "denied"
        assert _classify_polarity("He never apologized") == "denied"
        assert _classify_polarity("They didn't have any reason") == "denied"
    
    def test_uncertain_polarity(self):
        """Uncertainty should be classified correctly."""
        assert _classify_polarity("I think he grabbed me") == "uncertain"
        assert _classify_polarity("I believe they lied") == "uncertain"
        assert _classify_polarity("It seemed like they wanted to hurt me") == "uncertain"
        assert _classify_polarity("Maybe they were conspiring") == "uncertain"
    
    def test_asserted_polarity_default(self):
        """Default should be asserted."""
        assert _classify_polarity("Officer grabbed my arm") == "asserted"
        assert _classify_polarity("They put handcuffs on me") == "asserted"


class TestPatternCoverage:
    """Tests to ensure patterns cover expected cases."""
    
    def test_self_report_patterns_exist(self):
        """Ensure SELF_REPORT_PATTERNS is non-empty."""
        assert len(SELF_REPORT_PATTERNS) > 0
    
    def test_interpretation_patterns_exist(self):
        """Ensure INTERPRETATION_PATTERNS is non-empty."""
        assert len(INTERPRETATION_PATTERNS) > 0
    
    def test_legal_claim_patterns_exist(self):
        """Ensure LEGAL_CLAIM_PATTERNS is non-empty."""
        assert len(LEGAL_CLAIM_PATTERNS) > 0
    
    def test_conspiracy_patterns_exist(self):
        """Ensure CONSPIRACY_PATTERNS is non-empty."""
        assert len(CONSPIRACY_PATTERNS) > 0
    
    def test_medical_finding_patterns_exist(self):
        """Ensure MEDICAL_FINDING_PATTERNS is non-empty."""
        assert len(MEDICAL_FINDING_PATTERNS) > 0


class TestEdgeCases:
    """Tests for statements containing multiple epistemic markers.
    
    These test the classifier's priority ordering. More specific/dangerous
    types should win over general ones.
    """
    
    def test_intentional_excessive_force_is_legal_claim(self):
        """'He intentionally used excessive force' - has both interpretation 
        ('intentionally') and legal_claim ('excessive force').
        
        EXPECTED: legal_claim wins because it's more legally dangerous.
        """
        text = "He intentionally used excessive force"
        epistemic_type, _, _ = _classify_epistemic(text)
        # Legal claims are more dangerous and should take priority
        assert epistemic_type == "legal_claim", \
            f"'{text}' should be legal_claim (not interpretation), got {epistemic_type}"
    
    def test_clearly_racial_profiling_is_legal_claim(self):
        """'This was clearly racial profiling' - has interpretation marker
        ('clearly') but is a legal claim ('racial profiling').
        """
        text = "This was clearly racial profiling"
        epistemic_type, _, _ = _classify_epistemic(text)
        assert epistemic_type == "legal_claim", \
            f"'{text}' should be legal_claim, got {epistemic_type}"
    
    def test_deliberately_violated_rights_is_legal_claim(self):
        """'He deliberately violated my rights' - interpretation + legal.
        """
        text = "He deliberately violated my civil rights"
        epistemic_type, _, _ = _classify_epistemic(text)
        assert epistemic_type == "legal_claim", \
            f"'{text}' should be legal_claim, got {epistemic_type}"
    
    def test_brutally_assaulted_is_legal_not_interpretation(self):
        """'They brutally assaulted me' - has invective ('brutally') and
        could be seen as interpretation, but 'assault' is legal language.
        """
        text = "They brutally assaulted me"
        epistemic_type, _, _ = _classify_epistemic(text)
        # Should be legal_claim due to 'assault' language
        # (or direct_event if we're being neutral about physical actions)
        assert epistemic_type in ("legal_claim", "direct_event"), \
            f"'{text}' should be legal_claim or direct_event, got {epistemic_type}"
    
    def test_scared_during_assault_is_self_report(self):
        """'I was so scared during the assault' - has self_report ('scared')
        and legal language ('assault'). Self-report of fear is primary.
        """
        text = "I was so scared during the assault"
        epistemic_type, _, _ = _classify_epistemic(text)
        # The statement is primarily about the reporter's fear
        assert epistemic_type in ("self_report", "legal_claim"), \
            f"'{text}' should be self_report or legal_claim, got {epistemic_type}"
    
    def test_conspiracy_with_legal_claim(self):
        """'The cover-up proves police brutality' - conspiracy + legal.
        Conspiracy should win as it's more dangerous.
        """
        text = "This cover-up proves police brutality is real"
        epistemic_type, _, _ = _classify_epistemic(text)
        # Conspiracy claims are the most dangerous
        assert epistemic_type in ("conspiracy_claim", "legal_claim"), \
            f"'{text}' should be conspiracy_claim or legal_claim, got {epistemic_type}"

