"""
V6 Core Invariant Infrastructure

Provides the foundation for invariant-driven output:
- Invariant: A machine-checkable rule
- InvariantResult: Outcome of checking an invariant
- InvariantRegistry: Central registry of all invariants
- QuarantineItem: Content that failed invariants
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, List, Optional


class InvariantSeverity(str, Enum):
    """How to handle invariant failures."""
    
    HARD = "hard"      # Content goes to quarantine, NOT rendered in main section
    SOFT = "soft"      # Content renders with ⚠️ warning
    INFO = "info"      # Log only, no output change


@dataclass
class InvariantResult:
    """Result of checking an invariant."""
    
    passes: bool
    invariant_id: str
    message: str
    failed_content: Optional[str] = None
    quarantine_bucket: Optional[str] = None
    severity: InvariantSeverity = InvariantSeverity.HARD
    
    def __repr__(self) -> str:
        status = "✅ PASS" if self.passes else "❌ FAIL"
        return f"{status} [{self.invariant_id}] {self.message}"


@dataclass
class QuarantineItem:
    """Content that failed one or more invariants."""
    
    content: Any                           # The original content (Event, SpeechAct, etc.)
    content_preview: str                   # Human-readable preview (first 100 chars)
    failures: List[InvariantResult]        # All failed invariant checks
    content_type: str = "unknown"          # "event", "quote", "statement", etc.
    
    @property
    def issue_summary(self) -> str:
        """Single-line summary of issues."""
        return "; ".join(f.message for f in self.failures)


@dataclass
class Invariant:
    """
    A machine-checkable rule that content must pass.
    
    Invariants are the core of V6's "nothing renders unless valid" philosophy.
    """
    
    id: str                                # Unique identifier (e.g., "EVENT_HAS_ACTOR")
    description: str                       # Human-readable description
    severity: InvariantSeverity            # How to handle failures
    check_fn: Callable[[Any], InvariantResult]  # Function that checks the invariant
    quarantine_bucket: str                 # Where failed content goes
    
    def check(self, content: Any) -> InvariantResult:
        """Check this invariant against content."""
        result = self.check_fn(content)
        # Ensure the result has correct metadata
        result.invariant_id = self.id
        result.severity = self.severity
        if not result.passes and not result.quarantine_bucket:
            result.quarantine_bucket = self.quarantine_bucket
        return result


class InvariantRegistry:
    """
    Central registry of all invariants.
    
    Usage:
        InvariantRegistry.register(my_invariant)
        result = InvariantRegistry.check("EVENT_HAS_ACTOR", event)
        results = InvariantRegistry.check_all(event, ["EVENT_HAS_ACTOR", "EVENT_NOT_FRAGMENT"])
    """
    
    _invariants: dict[str, Invariant] = {}
    
    @classmethod
    def register(cls, invariant: Invariant) -> None:
        """Register an invariant."""
        cls._invariants[invariant.id] = invariant
    
    @classmethod
    def get(cls, invariant_id: str) -> Optional[Invariant]:
        """Get an invariant by ID."""
        return cls._invariants.get(invariant_id)
    
    @classmethod
    def check(cls, invariant_id: str, content: Any) -> InvariantResult:
        """Check a single invariant against content."""
        inv = cls._invariants.get(invariant_id)
        if not inv:
            return InvariantResult(
                passes=False,
                invariant_id=invariant_id,
                message=f"Unknown invariant: {invariant_id}",
            )
        return inv.check(content)
    
    @classmethod
    def check_all(cls, content: Any, invariant_ids: List[str]) -> List[InvariantResult]:
        """Check multiple invariants against content."""
        return [cls.check(id, content) for id in invariant_ids]
    
    @classmethod
    def check_all_registered(cls, content: Any, content_type: str) -> List[InvariantResult]:
        """Check all invariants applicable to a content type."""
        results = []
        for inv in cls._invariants.values():
            # Check if this invariant applies to this content type
            # Convention: invariant ID starts with content type (e.g., EVENT_HAS_ACTOR)
            if inv.id.startswith(content_type.upper()):
                results.append(inv.check(content))
        return results
    
    @classmethod
    def list_all(cls) -> List[str]:
        """List all registered invariant IDs."""
        return list(cls._invariants.keys())
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registered invariants (for testing)."""
        cls._invariants.clear()


def validate_content(
    content: Any,
    invariant_ids: List[str],
    content_preview: Optional[str] = None,
    content_type: str = "unknown"
) -> tuple[bool, Optional[QuarantineItem]]:
    """
    Validate content against multiple invariants.
    
    Returns:
        (passes_all, quarantine_item)
        - passes_all: True if content passes ALL invariants
        - quarantine_item: None if passes, QuarantineItem if fails
    """
    results = InvariantRegistry.check_all(content, invariant_ids)
    failures = [r for r in results if not r.passes]
    
    if not failures:
        return True, None
    
    # Create quarantine item
    preview = content_preview or str(content)[:100]
    quarantine = QuarantineItem(
        content=content,
        content_preview=preview,
        failures=failures,
        content_type=content_type,
    )
    
    return False, quarantine
