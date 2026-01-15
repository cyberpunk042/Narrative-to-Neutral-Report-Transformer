"""
V6 Provenance Invariants

Invariants for provenance and source attribution:
- VERIFIED_HAS_EVIDENCE: "Verified" status requires non-reporter source
- MEDICAL_HAS_ATTRIBUTION: Medical findings must have provider attribution
- PROVENANCE_NOT_CONTRADICTORY: Can't be "verified" and "needs verification"
"""

from nnrt.validation.invariants import (
    Invariant,
    InvariantResult,
    InvariantSeverity,
    InvariantRegistry,
)


def check_verified_has_evidence(stmt) -> InvariantResult:
    """
    Invariant: "Verified" status requires non-reporter source.
    
    Examples:
        ✅ source=medical, status=verified (has external source)
        ✅ source=document, status=verified (has external source)
        ❌ source=reporter, status=verified (no external evidence)
    """
    status = getattr(stmt, 'provenance_status', 'unknown')
    source = getattr(stmt, 'source_type', 'reporter')
    text = getattr(stmt, 'text', str(stmt))[:80]
    
    # Only check if status is "verified"
    if status != 'verified':
        return InvariantResult(
            passes=True,
            invariant_id="VERIFIED_HAS_EVIDENCE",
            message=f"Status is '{status}', not verified"
        )
    
    # If verified, must have non-reporter source
    if source == 'reporter':
        return InvariantResult(
            passes=False,
            invariant_id="VERIFIED_HAS_EVIDENCE",
            message="Cannot be 'verified' with only reporter as source",
            failed_content=text,
            quarantine_bucket="PROVENANCE_ERRORS"
        )
    
    return InvariantResult(
        passes=True,
        invariant_id="VERIFIED_HAS_EVIDENCE",
        message=f"Verified with source: {source}"
    )


def check_medical_has_attribution(stmt, target_section: str = None) -> InvariantResult:
    """
    Invariant: Medical findings must have provider attribution.
    
    Examples:
        ✅ "Dr. Foster documented bruises" (has provider)
        ❌ "injuries were consistent with force" (no provider)
    """
    text = getattr(stmt, 'text', str(stmt)).lower()
    
    # Medical provider indicators
    providers = ['dr.', 'dr ', 'doctor', 'nurse', 'emt', 'paramedic', 'physician']
    medical_verbs = ['documented', 'diagnosed', 'noted', 'observed', 'recorded']
    
    has_provider = any(p in text for p in providers)
    has_medical_verb = any(v in text for v in medical_verbs)
    
    # If it looks like medical content but no provider
    medical_terms = ['injury', 'injuries', 'bruise', 'sprain', 'abrasion', 'trauma']
    looks_medical = any(t in text for t in medical_terms)
    
    if looks_medical and has_medical_verb and not has_provider:
        return InvariantResult(
            passes=False,
            invariant_id="MEDICAL_HAS_ATTRIBUTION",
            message="Medical finding without provider attribution",
            failed_content=text[:80],
            quarantine_bucket="ATTRIBUTION_NEEDED"
        )
    
    return InvariantResult(
        passes=True,
        invariant_id="MEDICAL_HAS_ATTRIBUTION",
        message="Has proper attribution" if has_provider else "Not medical content"
    )


def check_claim_vs_action(stmt) -> InvariantResult:
    """
    Invariant: Distinguish claims from actions.
    
    "I researched his record" is an ACTION (Reporter did something)
    "He has 12 complaints" is a CLAIM (needs provenance)
    
    Actions don't need external provenance. Claims do.
    """
    text = getattr(stmt, 'text', str(stmt)).lower()
    epistemic = getattr(stmt, 'epistemic_type', 'unknown')
    
    # Reporter action verbs (don't need external provenance)
    action_verbs = ['i went', 'i filed', 'i called', 'i researched', 'i found', 
                   'i received', 'i asked', 'i said', 'i told']
    
    is_action = any(v in text for v in action_verbs)
    
    # If tagged as needing provenance but it's actually an action
    if is_action and epistemic in ('legal_claim', 'conspiracy_claim'):
        return InvariantResult(
            passes=False,
            invariant_id="CLAIM_VS_ACTION",
            message="Tagged as claim but appears to be reporter action",
            failed_content=text[:80],
            quarantine_bucket="CLASSIFICATION_REVIEW"
        )
    
    return InvariantResult(
        passes=True,
        invariant_id="CLAIM_VS_ACTION",
        message="Correctly classified"
    )


# Register all provenance invariants
def _register_provenance_invariants():
    """Register all provenance invariants with the registry."""
    
    InvariantRegistry.register(Invariant(
        id="VERIFIED_HAS_EVIDENCE",
        description="Verified status requires non-reporter source",
        severity=InvariantSeverity.HARD,
        check_fn=check_verified_has_evidence,
        quarantine_bucket="PROVENANCE_ERRORS"
    ))
    
    InvariantRegistry.register(Invariant(
        id="MEDICAL_HAS_ATTRIBUTION",
        description="Medical findings must have provider attribution",
        severity=InvariantSeverity.SOFT,
        check_fn=check_medical_has_attribution,
        quarantine_bucket="ATTRIBUTION_NEEDED"
    ))
    
    InvariantRegistry.register(Invariant(
        id="CLAIM_VS_ACTION",
        description="Distinguish claims (need provenance) from actions (don't)",
        severity=InvariantSeverity.SOFT,
        check_fn=check_claim_vs_action,
        quarantine_bucket="CLASSIFICATION_REVIEW"
    ))


# Auto-register on import
_register_provenance_invariants()
