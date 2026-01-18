"""
IR Schema v0.1 — Pydantic models for the Intermediate Representation.

The IR captures semantic structure without judgment.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from nnrt.ir.enums import (
    AllenRelation,
    DiagnosticLevel,
    EntityRole,
    EntityType,
    EventType,
    EvidenceType,
    GroupType,
    IdentifierType,
    MentionType,
    Participation,
    PolicyAction,
    RelationEvidence,
    SpanLabel,
    SpeechActType,
    StatementType,
    TemporalExpressionType,
    TemporalRelation,
    TimeGapType,
    TimeSource,
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
    
    # V9: Coreference-resolved text (set by p42_coreference when FastCoref available)
    resolved_text: Optional[str] = Field(
        default=None,
        description="Text with pronouns resolved to entity names (for V9 event extraction)"
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
    
    # V5: When/how the entity participated
    participation: Optional[Participation] = Field(None, description="Incident/post-incident/mentioned")
    
    # V6: Direct badge linkage for officers
    badge_number: Optional[str] = Field(None, description="Badge number if officer")


class Event(BaseModel):
    """A discrete occurrence in the narrative."""

    id: str = Field(..., description="Unique event identifier")
    type: EventType = Field(..., description="Event type")
    description: str = Field(..., description="Neutral description (verbatim)")

    # Evidence
    source_spans: list[str] = Field(default_factory=list, description="Supporting span IDs")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence")

    # Relationships (IDs link to Entity objects)
    actor_id: Optional[str] = Field(None, description="Entity performing action")
    target_id: Optional[str] = Field(None, description="Entity receiving action")
    temporal_marker: Optional[str] = Field(None, description="Time reference")
    
    # V5: Resolved labels for rendering (Actor/Action/Target schema)
    actor_label: Optional[str] = Field(None, description="Resolved actor name")
    action_verb: Optional[str] = Field(None, description="The action verb")
    target_label: Optional[str] = Field(None, description="Resolved target name")
    target_object: Optional[str] = Field(None, description="Non-entity target (e.g., 'the door')")

    # Flags
    is_uncertain: bool = Field(False, description="Explicitly uncertain")
    requires_context: bool = Field(False, description="References external context")


class SpeechAct(BaseModel):
    """
    Direct or reported speech in the narrative.
    
    V5: Enhanced with speaker attribution for proper quote rendering.
    Format: [Speaker] [verb]: "[content]"
    """

    id: str
    type: SpeechActType
    speaker_id: Optional[str] = None  # Entity ID
    content: str  # The actual quoted text
    is_direct_quote: bool
    source_span_id: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    
    # V5: Enhanced speaker attribution
    speaker_label: Optional[str] = Field(None, description="Human-readable speaker name")
    speech_verb: str = Field("said", description="Verb: said, yelled, asked, threatened")
    is_nested: bool = Field(False, description="Quote within a quote")
    raw_text: Optional[str] = Field(None, description="Original text including quotes")


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


# ============================================================================
# Phase 3: Semantic Understanding (v3)
# ============================================================================

class Mention(BaseModel):
    """
    A single reference to an entity in the narrative.
    
    Mentions are the building blocks of coreference chains. Each mention
    is a span of text that refers to some entity, whether by name,
    pronoun, or description.
    """
    
    id: str = Field(..., description="Unique mention identifier")
    
    # Location in text
    segment_id: str = Field(..., description="Segment containing this mention")
    start_char: int = Field(..., ge=0, description="Start offset within segment")
    end_char: int = Field(..., ge=0, description="End offset within segment")
    text: str = Field(..., description="The mention text as it appears")
    
    # Classification
    mention_type: MentionType = Field(..., description="How the entity is referenced")
    
    # Resolution (filled by coreference pass)
    resolved_entity_id: Optional[str] = Field(
        None, 
        description="Entity this mention refers to (None if unresolved)"
    )
    resolution_confidence: float = Field(
        0.0,
        ge=0.0, le=1.0,
        description="Confidence in entity resolution"
    )
    
    # For pronouns: grammatical features for agreement checking
    gender: Optional[str] = Field(None, description="he/she/they for pronouns")
    number: Optional[str] = Field(None, description="singular/plural")


class CoreferenceChain(BaseModel):
    """
    A chain linking all mentions that refer to the same entity.
    
    After coreference resolution, each entity has a chain containing
    all the ways it was referenced throughout the narrative.
    """
    
    id: str = Field(..., description="Unique chain identifier")
    
    # The canonical entity this chain represents
    entity_id: str = Field(..., description="The entity all mentions refer to")
    
    # All mentions in narrative order
    mention_ids: list[str] = Field(
        default_factory=list,
        description="Ordered list of mention IDs in this chain"
    )
    
    # Quality metrics
    confidence: float = Field(
        0.5,
        ge=0.0, le=1.0,
        description="Overall confidence that all mentions refer to same entity"
    )
    
    # Derived properties
    mention_count: int = Field(0, description="Number of mentions in chain")
    has_proper_name: bool = Field(False, description="Whether chain has a proper name mention")


class StatementGroup(BaseModel):
    """
    A semantic cluster of related atomic statements.
    
    Groups organize the narrative into coherent sections that can be
    rendered together and have a clear semantic purpose.
    """
    
    id: str = Field(..., description="Unique group identifier")
    
    # Classification
    group_type: GroupType = Field(..., description="Semantic category")
    title: str = Field(..., description="Human-readable group title")
    
    # Contents (in narrative order)
    statement_ids: list[str] = Field(
        default_factory=list,
        description="Atomic statement IDs in this group"
    )
    
    # Primary actor (for witness accounts, encounters)
    primary_entity_id: Optional[str] = Field(
        None,
        description="Main entity this group relates to"
    )
    
    # Temporal positioning
    temporal_anchor: Optional[str] = Field(
        None,
        description="Time marker for this group ('11:30 PM')"
    )
    sequence_in_narrative: int = Field(
        0,
        ge=0,
        description="Order this group appears in the narrative"
    )
    
    # Quality assessment
    evidence_strength: float = Field(
        0.5,
        ge=0.0, le=1.0,
        description="How well-documented this group is (0=weak, 1=documented)"
    )


# ============================================================================
# V6: Timeline Reconstruction Models
# ============================================================================

class TemporalExpression(BaseModel):
    """
    V6: A normalized temporal expression extracted from text.
    
    Follows TIMEX3-inspired normalization for consistent time handling.
    All times/dates are normalized to ISO format for comparison.
    """
    
    id: str = Field(..., description="Unique expression identifier")
    
    # Original text
    original_text: str = Field(..., description="Text as it appears: '11:30 PM'")
    type: TemporalExpressionType = Field(..., description="DATE, TIME, DURATION, etc.")
    
    # Normalized values (ISO format)
    normalized_value: Optional[str] = Field(
        None,
        description="ISO normalized: 'T23:30:00' for time, '2026-01-10' for date"
    )
    
    # For relative expressions
    anchor_type: Optional[str] = Field(
        None,
        description="What this is relative to: 'previous_event', 'document_time', 'explicit'"
    )
    anchor_reference: Optional[str] = Field(
        None,
        description="Reference ID if relative to another entry"
    )
    
    # Position in text
    start_char: int = Field(..., description="Start position in normalized text")
    end_char: int = Field(..., description="End position in normalized text")
    segment_id: str = Field(..., description="Source segment")
    
    # Confidence
    confidence: float = Field(
        0.8,
        ge=0.0, le=1.0,
        description="Confidence in extraction and normalization"
    )


class TemporalRelationship(BaseModel):
    """
    V6: An Allen-style temporal relation between two timeline elements.
    
    Captures how events/statements relate to each other in time.
    Uses full Allen's 13 interval relations for precision.
    """
    
    id: str = Field(..., description="Unique relation identifier")
    
    # The two elements being related
    source_id: str = Field(..., description="First element (event/statement ID)")
    target_id: str = Field(..., description="Second element (event/statement ID)")
    
    # Allen relation
    relation: AllenRelation = Field(..., description="Temporal relation type")
    
    # Evidence supporting this relation
    evidence_type: RelationEvidence = Field(
        RelationEvidence.NARRATIVE_ORDER,
        description="What evidence supports this relation"
    )
    evidence_text: Optional[str] = Field(
        None,
        description="The marker text that indicated this: 'then', 'while'"
    )
    
    # Confidence
    confidence: float = Field(
        0.5,
        ge=0.0, le=1.0,
        description="Confidence in this relation"
    )


class TimeGap(BaseModel):
    """
    V6: A detected gap in the timeline.
    
    Used for investigation question generation.
    Flags unexplained periods that may need follow-up.
    """
    
    id: str = Field(..., description="Unique gap identifier")
    
    # Position in timeline
    after_entry_id: str = Field(..., description="Entry before the gap")
    before_entry_id: str = Field(..., description="Entry after the gap")
    
    # Gap characteristics
    gap_type: TimeGapType = Field(..., description="EXPLAINED, UNEXPLAINED, etc.")
    estimated_duration_minutes: Optional[int] = Field(
        None,
        description="Estimated gap size in minutes (if calculable)"
    )
    
    # For explained gaps
    explanation_text: Optional[str] = Field(
        None,
        description="Marker explaining gap: '20 minutes later', 'the next day'"
    )
    
    # Investigation flags
    requires_investigation: bool = Field(
        False,
        description="Whether this gap should generate a question"
    )
    suggested_question: Optional[str] = Field(
        None,
        description="Auto-generated question for investigator"
    )


class TimelineEntry(BaseModel):
    """
    V6: A positioned element in the reconstructed timeline.
    
    Enhanced with multi-day support, normalized times, and gap linking.
    """
    
    id: str = Field(..., description="Unique timeline entry identifier")
    
    # What this entry represents
    event_id: Optional[str] = Field(None, description="Link to Event")
    statement_id: Optional[str] = Field(None, description="Link to AtomicStatement")
    group_id: Optional[str] = Field(None, description="Link to StatementGroup")
    
    # V6: Enhanced temporal information
    temporal_expression_id: Optional[str] = Field(
        None,
        description="Link to TemporalExpression with normalized time"
    )
    
    # V6: Multi-day support
    day_offset: int = Field(
        0,
        description="Days from incident: 0=incident day, 1=next day, etc."
    )
    
    # Normalized time (from TemporalExpression or computed)
    normalized_time: Optional[str] = Field(
        None,
        description="ISO time: 'T23:30:00'"
    )
    normalized_date: Optional[str] = Field(
        None,
        description="ISO date: '2026-01-10'"
    )
    
    # V6: Estimated offset for events without explicit time
    estimated_minutes_from_start: Optional[int] = Field(
        None,
        description="Estimated minutes from first event (for relative positioning)"
    )
    
    # Legacy fields (for backward compatibility)
    absolute_time: Optional[str] = Field(
        None,
        description="Original time string ('11:30 PM')"
    )
    date: Optional[str] = Field(
        None,
        description="Original date string ('January 15th, 2026')"
    )
    relative_time: Optional[str] = Field(
        None,
        description="Relative marker ('the next day', '20 minutes later')"
    )
    
    # Ordering
    sequence_order: int = Field(
        0,
        ge=0,
        description="Computed chronological order (0 = earliest)"
    )
    
    # V6: Gap linking
    gap_before_id: Optional[str] = Field(
        None,
        description="TimeGap ID for gap before this entry"
    )
    
    # V6: Source tracking
    time_source: TimeSource = Field(
        TimeSource.INFERRED,
        description="How this time was determined"
    )
    
    # V6: Relation links
    temporal_relation_ids: list[str] = Field(
        default_factory=list,
        description="TemporalRelationship IDs involving this entry"
    )
    
    # Legacy relation fields (for backward compatibility)
    before_entry_ids: list[str] = Field(
        default_factory=list,
        description="Entries that come before this one (legacy)"
    )
    after_entry_ids: list[str] = Field(
        default_factory=list,
        description="Entries that come after this one (legacy)"
    )
    
    # Confidence
    time_confidence: float = Field(
        0.5,
        ge=0.0, le=1.0,
        description="Confidence in temporal placement"
    )


class EvidenceClassification(BaseModel):
    """
    Evidence metadata for a statement.
    
    Classifies each statement by its source and reliability, enabling
    proper weighing of evidence in the final output.
    """
    
    id: str = Field(..., description="Unique classification identifier")
    
    # What is being classified
    statement_id: str = Field(..., description="AtomicStatement being classified")
    
    # Classification
    evidence_type: EvidenceType = Field(..., description="Source/type of evidence")
    
    # Source tracking
    source_entity_id: Optional[str] = Field(
        None,
        description="Who provided this information (for REPORTED type)"
    )
    
    # Corroboration
    corroborating_ids: list[str] = Field(
        default_factory=list,
        description="Statement IDs that support this statement"
    )
    contradicting_ids: list[str] = Field(
        default_factory=list,
        description="Statement IDs that contradict this statement"
    )
    
    # Quality assessment
    reliability: float = Field(
        0.5,
        ge=0.0, le=1.0,
        description="Reliability score based on type and corroboration"
    )


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

    # Core IR (Phase 1-2)
    segments: list[Segment] = Field(default_factory=list)
    spans: list[SemanticSpan] = Field(default_factory=list)
    identifiers: list["Identifier"] = Field(default_factory=list)
    entities: list[Entity] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
    speech_acts: list[SpeechAct] = Field(default_factory=list)
    
    # Atomic statements from decomposition
    atomic_statements: list = Field(default_factory=list, description="Atomic statements from decomposition")

    # v3: Semantic Understanding
    mentions: list[Mention] = Field(
        default_factory=list,
        description="All entity mentions in the narrative"
    )
    coreference_chains: list[CoreferenceChain] = Field(
        default_factory=list,
        description="Chains linking mentions to entities"
    )
    statement_groups: list[StatementGroup] = Field(
        default_factory=list,
        description="Semantic clusters of related statements"
    )
    timeline: list[TimelineEntry] = Field(
        default_factory=list,
        description="Temporally-ordered events"
    )
    evidence_classifications: list[EvidenceClassification] = Field(
        default_factory=list,
        description="Evidence type and reliability for statements"
    )
    
    # V6: Enhanced Timeline Reconstruction
    temporal_expressions: list[TemporalExpression] = Field(
        default_factory=list,
        description="Normalized temporal expressions from narrative"
    )
    temporal_relationships: list[TemporalRelationship] = Field(
        default_factory=list,
        description="Allen-style temporal relations between events"
    )
    time_gaps: list[TimeGap] = Field(
        default_factory=list,
        description="Detected gaps in the timeline"
    )

    # Metadata
    uncertainty: list[UncertaintyMarker] = Field(default_factory=list)
    policy_decisions: list[PolicyDecision] = Field(default_factory=list)
    trace: list[TraceEntry] = Field(default_factory=list)
    diagnostics: list[Diagnostic] = Field(default_factory=list)

    # Output
    rendered_text: Optional[str] = Field(None, description="Final rendered output")
    status: TransformStatus = Field(..., description="Transformation status")
    processing_duration_ms: float = Field(
        0.0, description="Total wall-clock time for transformation"
    )

