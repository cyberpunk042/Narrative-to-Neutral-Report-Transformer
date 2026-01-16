"""
IR — Intermediate Representation

The IR is the source of truth for all transformations.
Text output is a rendering of the IR.
"""

from nnrt.ir.enums import (
    AllenRelation,
    DiagnosticLevel,
    EntityRole,
    EventType,
    IdentifierType,
    PolicyAction,
    RelationEvidence,
    SegmentContext,
    SpanLabel,
    SpeechActType,
    StatementType,
    TemporalExpressionType,
    TimeGapType,
    TimeSource,
    TransformStatus,
    UncertaintyType,
)
from nnrt.ir.schema_v0_1 import (
    Diagnostic,
    Entity,
    Event,
    ExtractedIdentifier,
    Identifier,
    PolicyDecision,
    Segment,
    SemanticSpan,
    SpeechAct,
    TemporalExpression,
    TemporalRelationship,
    TimeGap,
    TimelineEntry,
    TraceEntry,
    TransformResult,
    UncertaintyMarker,
)

__all__ = [
    # V6: Timeline Enums
    "AllenRelation",
    "TemporalExpressionType",
    "TimeSource",
    "TimeGapType",
    "RelationEvidence",
    # Enums
    "SpanLabel",
    "SegmentContext",
    "EntityRole",
    "IdentifierType",
    "EventType",
    "SpeechActType",
    "StatementType",
    "UncertaintyType",
    "PolicyAction",
    "DiagnosticLevel",
    "TransformStatus",
    # V6: Timeline Models
    "TemporalExpression",
    "TemporalRelationship",
    "TimeGap",
    "TimelineEntry",
    # Models
    "Segment",
    "SemanticSpan",
    "Entity",
    "ExtractedIdentifier",
    "Identifier",
    "Event",
    "SpeechAct",
    "UncertaintyMarker",
    "PolicyDecision",
    "TraceEntry",
    "Diagnostic",
    "TransformResult",
]
