"""
Tests for p27_epistemic_tag — Issue #2 Legal Taxonomy Fix.

Tests that legal claims are correctly classified into sub-types:
- legal_claim_direct: Pure legal allegations
- legal_claim_admin: Administrative outcomes
- legal_claim_causation: Medical/psych causation claims
- legal_claim_attorney: Attorney opinions
"""

import pytest
from nnrt.passes.p27_epistemic_tag import _classify_epistemic


class TestLegalClaimDirect:
    """Test that direct legal allegations are classified correctly."""
    
    def test_excessive_force_is_direct(self):
        """'Excessive force' is a direct legal allegation."""
        epistemic_type, evidence_source, _ = _classify_epistemic(
            "The officer used excessive force"
        )
        assert epistemic_type == "legal_claim_direct"
        assert evidence_source == "inference"
    
    def test_false_arrest_is_direct(self):
        """'False arrest' is a direct legal claim."""
        epistemic_type, _, _ = _classify_epistemic(
            "This was a false arrest"
        )
        assert epistemic_type == "legal_claim_direct"
    
    def test_civil_rights_violation_is_direct(self):
        """'Civil rights violation' is a direct legal claim."""
        epistemic_type, _, _ = _classify_epistemic(
            "This was a civil rights violation"
        )
        assert epistemic_type == "legal_claim_direct"
    
    def test_police_brutality_is_direct(self):
        """'Police brutality' is a direct legal claim."""
        epistemic_type, _, _ = _classify_epistemic(
            "I experienced police brutality"
        )
        assert epistemic_type == "legal_claim_direct"
    
    def test_racial_profiling_is_direct(self):
        """'Racial profiling' is a direct legal claim."""
        epistemic_type, _, _ = _classify_epistemic(
            "This was clearly racial profiling"
        )
        assert epistemic_type == "legal_claim_direct"


class TestLegalClaimAdmin:
    """Test that administrative outcomes are classified correctly."""
    
    def test_within_policy_is_admin(self):
        """'Within policy' is an admin outcome."""
        epistemic_type, evidence_source, _ = _classify_epistemic(
            "The conduct was found to be within policy"
        )
        assert epistemic_type == "legal_claim_admin"
        assert evidence_source == "document"
    
    def test_internal_affairs_found_is_admin(self):
        """'IA found' is an admin outcome."""
        epistemic_type, _, _ = _classify_epistemic(
            "Internal affairs found no wrongdoing"
        )
        assert epistemic_type == "legal_claim_admin"
    
    def test_received_letter_is_admin(self):
        """'Received a letter' is an admin document."""
        epistemic_type, _, _ = _classify_epistemic(
            "I received a letter stating the complaint was unfounded"
        )
        assert epistemic_type == "legal_claim_admin"
    
    def test_exonerated_is_admin(self):
        """'Exonerated' is an admin outcome."""
        epistemic_type, _, _ = _classify_epistemic(
            "The officer was exonerated"
        )
        assert epistemic_type == "legal_claim_admin"
    
    def test_filed_complaint_is_admin(self):
        """'Filed a formal complaint' is an admin action."""
        epistemic_type, _, _ = _classify_epistemic(
            "I filed a formal complaint"
        )
        assert epistemic_type == "legal_claim_admin"


class TestLegalClaimCausation:
    """Test that causation claims are classified correctly."""
    
    def test_ptsd_caused_by_is_causation(self):
        """'PTSD caused by' is a causation claim."""
        epistemic_type, _, _ = _classify_epistemic(
            "My PTSD was directly caused by the incident"
        )
        assert epistemic_type == "legal_claim_causation"
    
    def test_as_result_of_is_causation(self):
        """'As a result of' is a causation claim."""
        epistemic_type, _, _ = _classify_epistemic(
            "I suffer from anxiety as a direct result of the encounter"
        )
        assert epistemic_type == "legal_claim_causation"
    
    def test_due_to_trauma_is_causation(self):
        """'Due to the trauma' is a causation claim."""
        epistemic_type, _, _ = _classify_epistemic(
            "I can no longer work due to the trauma"
        )
        assert epistemic_type == "legal_claim_causation"
    
    def test_directly_caused_is_causation(self):
        """'Directly caused' is a causation claim."""
        epistemic_type, _, _ = _classify_epistemic(
            "The actions directly caused my injuries"
        )
        assert epistemic_type == "legal_claim_causation"


class TestLegalClaimAttorney:
    """Test that attorney opinions are classified correctly."""
    
    def test_attorney_says_is_attorney(self):
        """'Attorney says' is an attorney opinion."""
        epistemic_type, evidence_source, _ = _classify_epistemic(
            "My attorney says this is the clearest case"
        )
        assert epistemic_type == "legal_claim_attorney"
        assert evidence_source == "opinion"
    
    def test_lawyer_believes_is_attorney(self):
        """'Lawyer believes' is an attorney opinion."""
        epistemic_type, _, _ = _classify_epistemic(
            "My lawyer believes we have a strong case"
        )
        assert epistemic_type == "legal_claim_attorney"
    
    def test_clearest_case_is_attorney(self):
        """'Clearest case' triggers attorney opinion pattern."""
        epistemic_type, _, _ = _classify_epistemic(
            "This is the clearest case of misconduct"
        )
        assert epistemic_type == "legal_claim_attorney"
    
    def test_from_legal_standpoint_is_attorney(self):
        """'From a legal standpoint' is attorney language."""
        epistemic_type, _, _ = _classify_epistemic(
            "From a legal standpoint, this was unlawful"
        )
        assert epistemic_type == "legal_claim_attorney"


class TestLegalTaxonomyDistinction:
    """Test that the taxonomy correctly distinguishes claim types."""
    
    def test_direct_vs_admin(self):
        """Direct allegations vs admin outcomes are distinct."""
        # Direct allegation
        direct_type, _, _ = _classify_epistemic("This was excessive force")
        
        # Admin outcome
        admin_type, _, _ = _classify_epistemic("Found to be within policy")
        
        assert direct_type == "legal_claim_direct"
        assert admin_type == "legal_claim_admin"
    
    def test_causation_vs_direct(self):
        """Causation claims vs direct allegations are distinct."""
        # Causation
        causation_type, _, _ = _classify_epistemic("PTSD directly caused by the incident")
        
        # Direct
        direct_type, _, _ = _classify_epistemic("This was police brutality")
        
        assert causation_type == "legal_claim_causation"
        assert direct_type == "legal_claim_direct"
    
    def test_attorney_vs_direct(self):
        """Attorney opinions vs direct allegations are distinct."""
        # Attorney
        attorney_type, _, _ = _classify_epistemic("My attorney says this is illegal")
        
        # Direct (no attorney reference)
        direct_type, _, _ = _classify_epistemic("This was an illegal arrest")
        
        assert attorney_type == "legal_claim_attorney"
        assert direct_type == "legal_claim_direct"
