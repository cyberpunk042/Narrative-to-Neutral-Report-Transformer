"""
IR Schema v0.1 — Pydantic models for the Intermediate Representation.

The IR captures semantic structure without judgment.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from nnrt.ir.enums import (
    DiagnosticLevel,
    EntityRole,
    EntityType,
    EventType,
    IdentifierType,
    PolicyAction,
    SpanLabel,
    SpeechActType,
    StatementType,
    TransformStatus,
    UncertaintyType,
)

IR_VERSION = "0.1.0"


class SegmentTransform(BaseModel):
    """
    Record of a single text transformation within a segment.
    
    Used for diff visualization - tracks exactly what changed, where, and why.
    """
    
    original_text: str = Field(..., description="Text that was changed")
    replacement_text: str = Field(default="", description="What it became (empty if deleted)")
    reason_code: str = Field(..., description="Machine-readable reason code (e.g., intent_attribution)")
    reason_message: str = Field(..., description="Human-readable explanation")
    start_offset: int = Field(..., description="Start position within segment.text")
    end_offset: int = Field(..., description="End position within segment.text")
    policy_rule_id: Optional[str] = Field(None, description="ID of the policy rule that triggered this")


class Segment(BaseModel):
    """A contiguous chunk of input text."""

    id: str = Field(..., description="Unique segment identifier")
    text: str = Field(..., description="Original text")
    start_char: int = Field(..., description="Character offset in original input")
    end_char: int = Field(..., description="Character offset end")
    source_line: Optional[int] = Field(None, description="Line number if available")
    
    # NEW: Context annotations (set by p25_annotate_context)
    contexts: list[str] = Field(
        default_factory=list,
        description="Context classifications for this segment (SegmentContext values)"
    )
    quote_depth: int = Field(
        default=0,
        description="Nesting level of quotes (0 = not in quote, 1 = direct quote, 2 = quote in quote)"
    )
    source_type: str = Field(
        default="narrator",
        description="Who is the source of this content (narrator, subject, officer, witness)"
    )
    
    # Phase 1: Statement classification (set by p22_classify_statements)
    statement_type: StatementType = Field(
        default=StatementType.UNKNOWN,
        description="Epistemic status: observation, claim, interpretation, or quote"
    )
    statement_confidence: float = Field(
        default=0.0,
        ge=0.0, le=1.0,
        description="Confidence in statement_type classification"
    )
    
    # Rendering output (set by p70_render)
    neutral_text: Optional[str] = Field(
        default=None,
        description="Neutralized text after policy rules applied (None if unchanged)"
    )
    applied_rules: list[str] = Field(
        default_factory=list,
        description="IDs of policy rules that were applied to this segment"
    )
    
    # NEW: Transform tracking for diff visualization
    transforms: list[SegmentTransform] = Field(
        default_factory=list,
        description="Individual transformations applied to this segment"
    )


class SemanticSpan(BaseModel):
    """A tagged region within a segment."""

    id: str = Field(..., description="Unique span identifier")
    segment_id: str = Field(..., description="Parent segment")
    start_char: int = Field(..., description="Offset within segment")
    end_char: int = Field(..., description="Offset end")
    text: str = Field(..., description="Span text")
    label: SpanLabel = Field(..., description="Semantic label")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence")
    source: str = Field(..., description="Which pass/model produced this")


class ExtractedIdentifier(BaseModel):
    """An identifier extracted from text (deprecated, use Identifier)."""

    id: str
    type: IdentifierType
    value: str
    span_id: str
    confidence: float = Field(..., ge=0.0, le=1.0)


class Identifier(BaseModel):
    """A structured identifier extracted from the narrative."""

    id: str = Field(..., description="Unique identifier")
    type: IdentifierType = Field(..., description="The type of identifier")
    value: str = Field(..., description="The extracted value")
    original_text: str = Field(..., description="Original text as it appeared")
    start_char: int = Field(..., description="Start position in segment")
    end_char: int = Field(..., description="End position in segment")
    source_segment_id: str = Field(..., description="Segment this was extracted from")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence")


class Entity(BaseModel):
    """A detected actor or object in the narrative."""

    id: str = Field(..., description="Unique entity identifier")
    type: EntityType = Field(default=EntityType.UNKNOWN, description="Entity type")
    label: Optional[str] = Field(None, description="Human readable label")
    role: EntityRole = Field(..., description="Role enum")
    mentions: list[str] = Field(default_factory=list, description="Span IDs that reference this")
    extracted_identifiers: Optional[list[ExtractedIdentifier]] = Field(
        None, description="Optional extracted identifiers"
    )


class Event(BaseModel):
    """A discrete occurrence in the narrative."""

    id: str = Field(..., description="Unique event identifier")
    type: EventType = Field(..., description="Event type")
    description: str = Field(..., description="Neutral description")

    # Evidence
    source_spans: list[str] = Field(default_factory=list, description="Supporting span IDs")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence")

    # Relationships
    actor_id: Optional[str] = Field(None, description="Entity performing action")
    target_id: Optional[str] = Field(None, description="Entity receiving action")
    temporal_marker: Optional[str] = Field(None, description="Time reference")

    # Flags
    is_uncertain: bool = Field(False, description="Explicitly uncertain")
    requires_context: bool = Field(False, description="References external context")


class SpeechAct(BaseModel):
    """Direct or reported speech in the narrative."""

    id: str
    type: SpeechActType
    speaker_id: Optional[str] = None
    content: str
    is_direct_quote: bool
    source_span_id: str
    confidence: float = Field(..., ge=0.0, le=1.0)


class UncertaintyMarker(BaseModel):
    """Explicit marker of uncertainty in the IR."""

    id: str
    type: UncertaintyType
    text: Optional[str] = Field(None, description="The specific text causing uncertainty")
    description: str
    affected_ids: list[str] = Field(default_factory=list)
    source: str


class PolicyDecision(BaseModel):
    """A policy rule that was applied."""

    id: str
    rule_id: str
    action: PolicyAction
    reason: str
    affected_ids: list[str] = Field(default_factory=list)


class TraceEntry(BaseModel):
    """A single transformation trace entry."""

    id: str
    timestamp: datetime
    pass_name: str
    action: str
    before: Optional[str] = None
    after: Optional[str] = None
    affected_ids: list[str] = Field(default_factory=list)


class Diagnostic(BaseModel):
    """A diagnostic message."""

    id: str
    level: DiagnosticLevel
    code: str
    message: str
    source: str
    affected_ids: list[str] = Field(default_factory=list)


class TransformResult(BaseModel):
    """The complete output of an NNRT transformation."""

    version: str = Field(default=IR_VERSION, description="IR schema version")
    request_id: str = Field(..., description="Unique transformation ID")
    timestamp: datetime = Field(..., description="When transformation occurred")

    # Core IR
    segments: list[Segment] = Field(default_factory=list)
    spans: list[SemanticSpan] = Field(default_factory=list)
    identifiers: list["Identifier"] = Field(default_factory=list)
    entities: list[Entity] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
    speech_acts: list[SpeechAct] = Field(default_factory=list)
    
    # NEW: Atomic statements from decomposition
    atomic_statements: list = Field(default_factory=list, description="Atomic statements from decomposition")

    # Metadata
    uncertainty: list[UncertaintyMarker] = Field(default_factory=list)
    policy_decisions: list[PolicyDecision] = Field(default_factory=list)
    trace: list[TraceEntry] = Field(default_factory=list)
    diagnostics: list[Diagnostic] = Field(default_factory=list)

    # Output
    rendered_text: Optional[str] = Field(None, description="Final rendered output")
    status: TransformStatus = Field(..., description="Transformation status")
