"""
V6 Validation Module

Invariant-driven output system for NNRT.

Philosophy: Nothing renders unless it passes invariants.
- Valid content → Rendered section
- Invalid content → Quarantine bucket with explicit issues
"""

from nnrt.validation.event_invariants import (
    check_event_has_actor,
    check_event_has_verb,
    check_event_not_fragment,
)
from nnrt.validation.invariants import (
    Invariant,
    InvariantRegistry,
    InvariantResult,
    InvariantSeverity,
    QuarantineItem,
)
from nnrt.validation.provenance_invariants import (
    check_medical_has_attribution,
    check_verified_has_evidence,
)
from nnrt.validation.quote_invariants import (
    check_quote_has_speaker,
)

__all__ = [
    # Core
    "Invariant",
    "InvariantResult",
    "InvariantSeverity",
    "InvariantRegistry",
    "QuarantineItem",
    # Event invariants
    "check_event_has_actor",
    "check_event_not_fragment",
    "check_event_has_verb",
    # Quote invariants
    "check_quote_has_speaker",
    # Provenance invariants
    "check_verified_has_evidence",
    "check_medical_has_attribution",
]
