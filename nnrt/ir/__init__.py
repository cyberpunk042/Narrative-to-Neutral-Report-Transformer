"""
IR — Intermediate Representation

The IR is the source of truth for all transformations.
Text output is a rendering of the IR.
"""

from nnrt.ir.enums import (
    DiagnosticLevel,
    EntityRole,
    EventType,
    IdentifierType,
    PolicyAction,
    SpanLabel,
    SpeechActType,
    TransformStatus,
    UncertaintyType,
)
from nnrt.ir.schema_v0_1 import (
    Diagnostic,
    Entity,
    Event,
    ExtractedIdentifier,
    PolicyDecision,
    Segment,
    SemanticSpan,
    SpeechAct,
    TraceEntry,
    TransformResult,
    UncertaintyMarker,
)

__all__ = [
    # Enums
    "SpanLabel",
    "EntityRole",
    "IdentifierType",
    "EventType",
    "SpeechActType",
    "UncertaintyType",
    "PolicyAction",
    "DiagnosticLevel",
    "TransformStatus",
    # Models
    "Segment",
    "SemanticSpan",
    "Entity",
    "ExtractedIdentifier",
    "Event",
    "SpeechAct",
    "UncertaintyMarker",
    "PolicyDecision",
    "TraceEntry",
    "Diagnostic",
    "TransformResult",
]
