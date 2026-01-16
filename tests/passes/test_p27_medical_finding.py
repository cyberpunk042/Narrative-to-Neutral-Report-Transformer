"""
Tests for p27_epistemic_tag — Issue #3 Medical Provider Finding Fix.

Tests that medical provider findings are correctly classified as
medical_finding instead of self_report when the subject is a provider.
"""

import pytest
from nnrt.passes.p27_epistemic_tag import _classify_epistemic


class TestMedicalProviderFinding:
    """Test that medical provider findings are correctly classified."""
    
    def test_she_documented_bruises_is_medical_finding(self):
        """Key Issue #3 case: 'She documented bruises' should be medical_finding."""
        epistemic_type, evidence_source, confidence = _classify_epistemic(
            "She documented bruises on my wrists"
        )
        assert epistemic_type == "medical_finding"
        assert evidence_source == "document"
    
    def test_he_noted_injuries_is_medical_finding(self):
        """'He noted injuries' with provider verb should be medical_finding."""
        epistemic_type, evidence_source, confidence = _classify_epistemic(
            "He noted several injuries on my arm"
        )
        assert epistemic_type == "medical_finding"
        assert evidence_source == "document"
    
    def test_doctor_documented_is_medical_finding(self):
        """Explicit doctor title should be medical_finding."""
        epistemic_type, evidence_source, confidence = _classify_epistemic(
            "Dr. Smith documented the bruises"
        )
        assert epistemic_type == "medical_finding"
        assert evidence_source == "document"
    
    def test_nurse_noted_is_medical_finding(self):
        """Nurse as subject should be medical_finding."""
        epistemic_type, evidence_source, confidence = _classify_epistemic(
            "The nurse noted swelling on my wrist"
        )
        assert epistemic_type == "medical_finding"
        assert evidence_source == "document"
    
    def test_diagnosed_with_is_medical_finding(self):
        """'Diagnosed with' implies medical source."""
        epistemic_type, evidence_source, confidence = _classify_epistemic(
            "I was diagnosed with PTSD"
        )
        assert epistemic_type == "medical_finding"
        assert evidence_source == "document"
    
    def test_medical_records_show_is_medical_finding(self):
        """Medical records as source should be medical_finding."""
        epistemic_type, evidence_source, confidence = _classify_epistemic(
            "Medical records show that I had bruises"
        )
        assert epistemic_type == "medical_finding"
        assert evidence_source == "document"
    
    def test_injuries_consistent_with_is_medical_finding(self):
        """'Injuries were consistent with' is medical language."""
        epistemic_type, evidence_source, confidence = _classify_epistemic(
            "My injuries were consistent with being handcuffed too tightly"
        )
        assert epistemic_type == "medical_finding"
        assert evidence_source == "document"


class TestSelfReportInjuryNotOverridden:
    """Test that true self-report injuries are still classified correctly."""
    
    def test_my_wrists_were_bleeding_is_self_report(self):
        """First-person injury description is self-report."""
        epistemic_type, evidence_source, confidence = _classify_epistemic(
            "My wrists were bleeding"
        )
        assert epistemic_type == "state_injury"
        assert evidence_source == "self_report"
    
    def test_i_was_in_pain_is_self_report(self):
        """First-person pain is self-report."""
        epistemic_type, evidence_source, confidence = _classify_epistemic(
            "I was in pain"
        )
        assert epistemic_type == "state_injury"
        assert evidence_source == "self_report"
    
    def test_injuries_on_my_arm_is_self_report(self):
        """Injuries 'to/on my [body part]' is self-report pattern."""
        epistemic_type, evidence_source, confidence = _classify_epistemic(
            "I had injuries on my arm"
        )
        assert epistemic_type == "state_injury"
        assert evidence_source == "self_report"


class TestMedicalVsSelfDistinction:
    """Test that the distinction between medical and self-report is correct."""
    
    def test_she_documented_vs_injuries_on_my(self):
        """Compare 'She documented' vs 'injuries on my' for same injury type."""
        # Medical finding (provider documented)
        medical_type, _, _ = _classify_epistemic("She documented my bruises")
        
        # Self-report (I claim via pattern 'injuries on my')
        self_type, _, _ = _classify_epistemic("I had injuries on my wrist")
        
        assert medical_type == "medical_finding"
        assert self_type == "state_injury"
    
    def test_documented_implies_provider(self):
        """The verb 'documented' implies a provider."""
        documented_type, doc_source, _ = _classify_epistemic("She documented the bruises")
        
        assert documented_type == "medical_finding"
        assert doc_source == "document"
