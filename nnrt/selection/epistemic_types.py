"""
Epistemic Type Taxonomy — Shared Contract

This module defines the epistemic types used throughout the pipeline.
It serves as the single source of truth between:
- p27_epistemic_tag.py (classification)
- p55_select.py (routing)
- structured_v2.py (rendering)

The taxonomy uses a hierarchical naming convention:
- Top-level types: "direct_event", "self_report", "inference", etc.
- Sub-types: "legal_claim_attorney", "state_injury", etc.

Routing uses PREFIX MATCHING:
- "legal_claim_*" → routes to legal_allegations
- "state_*" → routes to appropriate state bucket
"""

from enum import Enum
from typing import Dict, List, Tuple


# =============================================================================
# EPISTEMIC TYPE PREFIXES (for routing)
# =============================================================================

class EpistemicPrefix:
    """Top-level categories for routing atomic statements."""
    
    STATE_ACUTE = "state_acute"
    STATE_INJURY = "state_injury"
    STATE_PSYCHOLOGICAL = "state_psychological"
    STATE_SOCIOECONOMIC = "state_socioeconomic"
    SELF_REPORT = "self_report"
    
    LEGAL_CLAIM = "legal_claim"  # Matches legal_claim_*, legal_claim
    CHARACTERIZATION = "characterization"
    INFERENCE = "inference"
    INTERPRETATION = "interpretation"
    CONSPIRACY_CLAIM = "conspiracy_claim"
    
    MEDICAL_FINDING = "medical_finding"
    ADMIN_ACTION = "admin_action"
    
    DIRECT_EVENT = "direct_event"
    QUOTE = "quote"
    THIRD_PARTY = "third_party"
    NARRATIVE_GLUE = "narrative_glue"
    UNKNOWN = "unknown"


# =============================================================================
# ROUTING TABLE: Epistemic Type → SelectionResult Field
# =============================================================================

# Maps epistemic_type prefixes to SelectionResult field names
# Uses startswith() matching so "legal_claim_attorney" → "legal_allegations"

EPISTEMIC_TO_SELECTION_FIELD: Dict[str, str] = {
    # Self-reported states (fine-grained)
    "state_acute": "acute_state",
    "state_injury": "injury_state",
    "state_psychological": "psychological_state", 
    "state_socioeconomic": "socioeconomic_impact",
    "self_report": "general_self_report",
    
    # Legal/claims (prefix-matched)
    "legal_claim": "legal_allegations",  # Catches legal_claim_attorney, legal_claim_direct, etc.
    
    # Reporter opinions/inferences
    "characterization": "characterizations",
    "inference": "inferences",
    "interpretation": "interpretations",
    "conspiracy_claim": "contested_allegations",
    
    # Document-sourced
    "medical_finding": "medical_findings",
    "admin_action": "admin_actions",
    
    # Events (routed separately via event classification)
    "direct_event": None,  # Handled by event routing
    "quote": None,         # Handled by quote routing
    
    # Not routed to statement sections
    "third_party": None,
    "narrative_glue": None,
    "unknown": None,
}


def get_selection_field(epistemic_type: str) -> str | None:
    """
    Get the SelectionResult field for a given epistemic_type.
    
    Uses prefix matching: "legal_claim_attorney" → "legal_allegations"
    
    Returns None if the type shouldn't be routed to statement sections.
    """
    if not epistemic_type:
        return None
    
    # Try exact match first
    if epistemic_type in EPISTEMIC_TO_SELECTION_FIELD:
        return EPISTEMIC_TO_SELECTION_FIELD[epistemic_type]
    
    # Try prefix match (for sub-types like legal_claim_attorney)
    for prefix, field in EPISTEMIC_TO_SELECTION_FIELD.items():
        if epistemic_type.startswith(prefix):
            return field
    
    return None


# =============================================================================
# DISPLAY NAMES (for rendering)
# =============================================================================

EPISTEMIC_DISPLAY_NAMES: Dict[str, str] = {
    "state_acute": "Acute State (During Incident)",
    "state_injury": "Physical Injury",
    "state_psychological": "Psychological State",
    "state_socioeconomic": "Socioeconomic Impact",
    "self_report": "General Self-Report",
    
    "legal_claim": "Legal Allegation",
    "legal_claim_direct": "Direct Legal Allegation",
    "legal_claim_attorney": "Attorney Opinion",
    "legal_claim_causation": "Causation Claim",
    "legal_claim_admin": "Administrative Finding",
    
    "characterization": "Subjective Characterization",
    "inference": "Intent/Motive Inference",
    "interpretation": "Interpretation",
    "conspiracy_claim": "Contested Allegation",
    
    "medical_finding": "Medical Finding",
    "admin_action": "Administrative Action",
    
    "direct_event": "Direct Event",
    "quote": "Quote",
    "third_party": "Third-Party Report",
    "narrative_glue": "Narrative Glue",
    "unknown": "Unknown",
}


# =============================================================================
# VALIDATION: All types that should be routed
# =============================================================================

ROUTABLE_TYPES = [k for k, v in EPISTEMIC_TO_SELECTION_FIELD.items() if v is not None]

# Types that are handled by separate routing (events, quotes)
SEPARATELY_ROUTED = ["direct_event", "quote", "third_party"]

# Types that are intentionally not rendered
IGNORED_TYPES = ["narrative_glue", "unknown"]
