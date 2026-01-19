"""
TransformContext — Mutable state passed between pipeline passes.

Each pass reads prior artifacts and mutates only its allowed fields.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from nnrt.ir.schema_v0_1 import (
    CoreferenceChain,
    Diagnostic,
    Entity,
    EvidenceClassification,
    Event,
    Identifier,
    Mention,
    PolicyDecision,
    Segment,
    SemanticSpan,
    SpeechAct,
    StatementGroup,
    TemporalExpression,
    TemporalRelationship,
    TimeGap,
    TimelineEntry,
    TraceEntry,
    TransformResult,
    TransformStatus,
    UncertaintyMarker,
)


@dataclass
class TransformRequest:
    """Input to the transformation pipeline."""

    text: str
    request_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.request_id is None:
            self.request_id = str(uuid4())


@dataclass
class TransformContext:
    """
    Mutable context passed through pipeline passes.
    
    Each pass may read all fields but should only mutate
    the fields it is responsible for.
    """

    # Input
    request: TransformRequest
    raw_text: str
    normalized_text: str = ""

    # IR components (populated by passes)
    segments: list[Segment] = field(default_factory=list)
    spans: list[SemanticSpan] = field(default_factory=list)
    identifiers: list[Identifier] = field(default_factory=list)
    entities: list[Entity] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)
    speech_acts: list[SpeechAct] = field(default_factory=list)
    uncertainty: list[UncertaintyMarker] = field(default_factory=list)
    policy_decisions: list[PolicyDecision] = field(default_factory=list)
    
    # Atomic statements from p26_decompose
    # Each segment is decomposed into one or more atomic statements
    atomic_statements: list = field(default_factory=list)  # list[AtomicStatement]

    # v3: Semantic Understanding
    mentions: list[Mention] = field(default_factory=list)
    coreference_chains: list[CoreferenceChain] = field(default_factory=list)
    statement_groups: list[StatementGroup] = field(default_factory=list)
    timeline: list[TimelineEntry] = field(default_factory=list)
    evidence_classifications: list[EvidenceClassification] = field(default_factory=list)
    
    # V6: Enhanced Timeline Reconstruction
    temporal_expressions: list[TemporalExpression] = field(default_factory=list)
    temporal_relationships: list[TemporalRelationship] = field(default_factory=list)
    time_gaps: list[TimeGap] = field(default_factory=list)

    # Cross-pass decision communication
    # Maps span_id -> PolicyDecision that applies to this span
    span_decisions: dict[str, PolicyDecision] = field(default_factory=dict)
    
    # Protected character ranges per segment
    # Maps segment_id -> list of (start, end) ranges that should not be modified
    protected_ranges: dict[str, list[tuple[int, int]]] = field(default_factory=dict)

    # Trace and diagnostics
    trace: list[TraceEntry] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)

    # Output
    rendered_text: Optional[str] = None
    status: TransformStatus = TransformStatus.SUCCESS

    # Internal
    start_time: datetime = field(default_factory=datetime.now)
    
    # =========================================================================
    # V6: Quarantine Buckets for Invariant Failures
    # =========================================================================
    # Content that fails invariants goes here instead of being rendered
    # Format: {bucket_name: [(content, failures), ...]}
    quarantine: dict = field(default_factory=dict)
    
    # V6: Invariant check results for reporting
    invariant_results: list = field(default_factory=list)
    
    # =========================================================================
    # V7 / Stage 2: Selection Layer
    # =========================================================================
    # Selection result stores which atoms are selected for which output sections
    # Populated by p55_select pass, read by renderer
    selection_result: Any = None  # Optional[SelectionResult] - lazy import to avoid circular
    
    # =========================================================================
    # Selection Helpers
    # =========================================================================
    
    def get_event_by_id(self, event_id: str):
        """Get an event by ID."""
        for event in self.events:
            if event.id == event_id:
                return event
        return None
    
    def get_entity_by_id(self, entity_id: str):
        """Get an entity by ID."""
        for entity in self.entities:
            if entity.id == entity_id:
                return entity
        return None
    
    def get_speech_act_by_id(self, speech_act_id: str):
        """Get a speech act by ID."""
        for speech_act in self.speech_acts:
            if speech_act.id == speech_act_id:
                return speech_act
        return None
    
    def get_timeline_entry_by_id(self, entry_id: str):
        """Get a timeline entry by ID."""
        for entry in self.timeline:
            if entry.id == entry_id:
                return entry
        return None
    
    
    def quarantine_content(self, bucket: str, content, failures: list) -> None:
        """
        Add content to quarantine bucket.
        
        Args:
            bucket: Bucket name (e.g., "EVENTS_UNRESOLVED", "QUOTES_UNRESOLVED")
            content: The content that failed (Event, SpeechAct, etc.)
            failures: List of InvariantResult failures
        """
        if bucket not in self.quarantine:
            self.quarantine[bucket] = []
        self.quarantine[bucket].append((content, failures))
    
    def get_quarantine(self, bucket: str) -> list:
        """Get contents of a quarantine bucket."""
        return self.quarantine.get(bucket, [])
    
    def quarantine_summary(self) -> dict[str, int]:
        """Get count of items in each quarantine bucket."""
        return {k: len(v) for k, v in self.quarantine.items()}

    
    # =========================================================================
    # Cross-Pass Communication Helpers
    # =========================================================================
    
    def set_span_decision(self, span_id: str, decision: PolicyDecision) -> None:
        """
        Record a policy decision for a specific span.
        
        This allows downstream passes to know what was decided about a span
        without re-analyzing the text.
        """
        self.span_decisions[span_id] = decision
    
    def get_span_decision(self, span_id: str) -> Optional[PolicyDecision]:
        """Get the policy decision for a span, if any was recorded."""
        return self.span_decisions.get(span_id)
    
    def protect_span(self, span: SemanticSpan) -> None:
        """
        Mark a span's character range as protected from modification.
        
        Protected ranges will not be transformed by the render pass.
        """
        seg_id = span.segment_id
        if seg_id not in self.protected_ranges:
            self.protected_ranges[seg_id] = []
        self.protected_ranges[seg_id].append((span.start_char, span.end_char))
    
    def protect_range(self, segment_id: str, start: int, end: int) -> None:
        """Directly protect a character range in a segment."""
        if segment_id not in self.protected_ranges:
            self.protected_ranges[segment_id] = []
        self.protected_ranges[segment_id].append((start, end))
    
    def is_protected(self, segment_id: str, start: int, end: int) -> bool:
        """
        Check if a character range overlaps with any protected range.
        
        Returns True if ANY part of [start, end) overlaps with a protected range.
        """
        if segment_id not in self.protected_ranges:
            return False
        for pstart, pend in self.protected_ranges[segment_id]:
            # Check for overlap
            if start < pend and end > pstart:
                return True
        return False
    
    def has_context(self, segment_id: str, context: str) -> bool:
        """Check if a segment has a specific context annotation."""
        for seg in self.segments:
            if seg.id == segment_id:
                return context in seg.contexts
        return False
    
    def get_segment_contexts(self, segment_id: str) -> list[str]:
        """Get all context annotations for a segment."""
        for seg in self.segments:
            if seg.id == segment_id:
                return seg.contexts
        return []

    @classmethod
    def from_request(cls, request: TransformRequest) -> "TransformContext":
        """Create a context from a transform request."""
        return cls(
            request=request,
            raw_text=request.text,
        )

    def add_trace(self, pass_name: str, action: str, **kwargs: Any) -> None:
        """Add a trace entry."""
        self.trace.append(
            TraceEntry(
                id=str(uuid4()),
                timestamp=datetime.now(),
                pass_name=pass_name,
                action=action,
                before=kwargs.get("before"),
                after=kwargs.get("after"),
                affected_ids=kwargs.get("affected_ids", []),
            )
        )

    def add_diagnostic(
        self,
        level: str,
        code: str,
        message: str,
        source: str,
        affected_ids: Optional[list[str]] = None,
    ) -> None:
        """Add a diagnostic message."""
        from nnrt.ir.enums import DiagnosticLevel

        self.diagnostics.append(
            Diagnostic(
                id=str(uuid4()),
                level=DiagnosticLevel(level),
                code=code,
                message=message,
                source=source,
                affected_ids=affected_ids or [],
            )
        )

    def to_result(self) -> TransformResult:
        """Convert context to final TransformResult."""
        duration_ms = (datetime.now() - self.start_time).total_seconds() * 1000
        return TransformResult(
            request_id=self.request.request_id or str(uuid4()),
            timestamp=self.start_time,
            processing_duration_ms=duration_ms,
            # Core IR
            segments=self.segments,
            spans=self.spans,
            identifiers=self.identifiers,
            entities=self.entities,
            events=self.events,
            speech_acts=self.speech_acts,
            atomic_statements=self.atomic_statements,
            # v3: Semantic Understanding
            mentions=self.mentions,
            coreference_chains=self.coreference_chains,
            statement_groups=self.statement_groups,
            timeline=self.timeline,
            evidence_classifications=self.evidence_classifications,
            # V6: Enhanced Timeline
            temporal_expressions=self.temporal_expressions,
            temporal_relationships=self.temporal_relationships,
            time_gaps=self.time_gaps,
            # Metadata
            uncertainty=self.uncertainty,
            policy_decisions=self.policy_decisions,
            trace=self.trace,
            diagnostics=self.diagnostics,
            # Output
            rendered_text=self.rendered_text,
            status=self.status,
        )
