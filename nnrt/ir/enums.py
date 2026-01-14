"""
IR Enums — All semantic labels, roles, and codes.

No stringly-typed constants scattered across passes.
"""

from enum import Enum


class SpanLabel(str, Enum):
    """Semantic labels for spans."""

    # Factual content
    OBSERVATION = "observation"
    ACTION = "action"
    STATEMENT = "statement"

    # Interpretive content (flagged, not removed)
    INTERPRETATION = "interpretation"
    INFERENCE = "inference"
    EMOTIONAL = "emotional"

    # Structural
    TEMPORAL = "temporal"
    SPATIAL = "spatial"
    REFERENCE = "reference"

    # Problematic (require attention)
    LEGAL_CONCLUSION = "legal_conclusion"
    INTENT_ATTRIBUTION = "intent_attribution"
    INFLAMMATORY = "inflammatory"

    # Uncertain
    AMBIGUOUS = "ambiguous"
    UNKNOWN = "unknown"


class EntityRole(str, Enum):
    """Roles entities can play in a narrative."""

    REPORTER = "reporter"
    SUBJECT = "subject"
    WITNESS = "witness"
    AUTHORITY = "authority"
    INSTITUTION = "institution"
    OBJECT = "object"
    UNKNOWN = "unknown"


class IdentifierType(str, Enum):
    """Types of identifiers that can be extracted."""

    NAME = "name"
    BADGE_NUMBER = "badge_number"
    EMPLOYEE_ID = "employee_id"
    VEHICLE_PLATE = "vehicle_plate"
    LOCATION = "location"
    DATE = "date"
    TIME = "time"
    OTHER = "other"


class EventType(str, Enum):
    """Types of events that can be extracted."""

    ACTION = "action"
    VERBAL = "verbal"
    MOVEMENT = "movement"
    OBSERVATION = "observation"
    STATE_CHANGE = "state_change"
    UNKNOWN = "unknown"


class SpeechActType(str, Enum):
    """Types of speech acts."""

    STATEMENT = "statement"
    COMMAND = "command"
    QUESTION = "question"
    THREAT = "threat"
    UNKNOWN = "unknown"


class UncertaintyType(str, Enum):
    """Types of uncertainty."""

    AMBIGUOUS_REFERENCE = "ambiguous_reference"
    MISSING_CONTEXT = "missing_context"
    LOW_CONFIDENCE = "low_confidence"
    CONTRADICTORY = "contradictory"
    INCOMPLETE = "incomplete"


class PolicyAction(str, Enum):
    """Actions a policy rule can take."""

    ACCEPT = "accept"
    FLAG = "flag"
    TRANSFORM = "transform"
    STRIP = "strip"
    REFUSE = "refuse"
    WARN = "warn"


class DiagnosticLevel(str, Enum):
    """Diagnostic severity levels."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class TransformStatus(str, Enum):
    """Overall transformation status."""

    SUCCESS = "success"
    PARTIAL = "partial"
    REFUSED = "refused"
    ERROR = "error"
