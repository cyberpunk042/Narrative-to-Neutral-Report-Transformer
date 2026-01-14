"""
TransformContext — Mutable state passed between pipeline passes.

Each pass reads prior artifacts and mutates only its allowed fields.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from nnrt.ir.schema_v0_1 import (
    Diagnostic,
    Entity,
    Event,
    Identifier,
    PolicyDecision,
    Segment,
    SemanticSpan,
    SpeechAct,
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

    # Trace and diagnostics
    trace: list[TraceEntry] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)

    # Output
    rendered_text: Optional[str] = None
    status: TransformStatus = TransformStatus.SUCCESS

    # Internal
    start_time: datetime = field(default_factory=datetime.now)

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
        return TransformResult(
            request_id=self.request.request_id or str(uuid4()),
            timestamp=self.start_time,
            segments=self.segments,
            spans=self.spans,
            identifiers=self.identifiers,
            entities=self.entities,
            events=self.events,
            speech_acts=self.speech_acts,
            uncertainty=self.uncertainty,
            policy_decisions=self.policy_decisions,
            trace=self.trace,
            diagnostics=self.diagnostics,
            rendered_text=self.rendered_text,
            status=self.status,
        )
