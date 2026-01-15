"""
Structured Output — JSON format for NNRT results.

This module provides structured output that exposes:
- Statement classifications (observation/claim/interpretation/quote)
- Uncertainties (ambiguity, contradictions)
- Entities and events (future)
- Diagnostics and transformations

The goal: A human can answer "What is claimed vs observed vs inferred?"
without reading the original narrative.
"""

import hashlib
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from nnrt import __version__
from nnrt.ir.schema_v0_1 import TransformResult


SCHEMA_VERSION = "1.0"


# ============================================================================
# Output Models
# ============================================================================

class TransformationRecord(BaseModel):
    """A single transformation applied to text."""
    
    rule_id: str
    action: str
    original: str
    replacement: Optional[str] = None


class AtomicStatementOutput(BaseModel):
    """
    An atomic statement from the decomposition pipeline.
    
    This is the NEW output format aligned with the NNRT v2 schema:
    - Each statement is a single fact/claim/interpretation
    - Type is explicitly classified
    - Provenance (derived_from) links interpretations to sources
    """
    
    id: str = Field(..., description="Statement ID (stmt_XXXX)")
    type: str = Field(..., description="observation|claim|interpretation|quote|unknown")
    text: str = Field(..., description="Statement text")
    
    segment_id: str = Field(..., description="Source segment ID")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Classification confidence")
    
    clause_type: str = Field(..., description="root|conj|advcl|ccomp|quote")
    connector: Optional[str] = Field(None, description="Clause connector (and, because, etc.)")
    
    derived_from: list[str] = Field(default_factory=list, description="IDs of source statements")
    flags: list[str] = Field(default_factory=list, description="Classification flags")


class StatementOutput(BaseModel):
    """A classified statement from the narrative."""
    
    id: str = Field(..., description="Statement ID (stmt_XXX)")
    type: str = Field(..., description="observation|claim|interpretation|quote")
    original: str = Field(..., description="Original text")
    neutral: Optional[str] = Field(None, description="Neutralized text (if different)")
    
    segment_id: str = Field(..., description="Source segment ID")
    classification_confidence: float = Field(..., description="0.0-1.0")
    
    contexts: list[str] = Field(default_factory=list, description="Context annotations")
    transformations: list[TransformationRecord] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list, description="Warning flags")


class UncertaintyOutput(BaseModel):
    """An uncertainty or ambiguity in the narrative."""
    
    id: str = Field(..., description="Uncertainty ID (unc_XXX)")
    type: str = Field(..., description="ambiguous_reference|vague_reference|contradiction|missing_info")
    text: str = Field(..., description="The ambiguous text")
    segment_id: str = Field(..., description="Source segment ID")
    
    description: str = Field(..., description="Human-readable description")
    candidates: Optional[list[dict]] = Field(None, description="Possible interpretations")
    resolution: Optional[str] = Field(None, description="User-provided resolution (null = unresolved)")
    requires_human_review: bool = Field(default=True)


class EntityOutput(BaseModel):
    """An entity extracted from the narrative."""
    
    id: str = Field(..., description="Entity ID (ent_XXX)")
    type: str = Field(..., description="person|vehicle|location|organization")
    label: str = Field(..., description="Human-readable label")
    role: str = Field(..., description="reporter|subject|officer|witness|other")
    
    mentions: list[dict] = Field(default_factory=list)
    attributes: dict = Field(default_factory=dict)


class EventOutput(BaseModel):
    """An event extracted from the narrative."""
    
    id: str = Field(..., description="Event ID (evt_XXX)")
    type: str = Field(..., description="physical_contact|verbal|movement|legal")
    description: str = Field(..., description="Event description")
    
    actors: list[str] = Field(default_factory=list, description="Entity IDs")
    targets: list[str] = Field(default_factory=list, description="Entity IDs")
    source_statement: str = Field(..., description="Statement ID")
    confidence: float = Field(default=0.8)


class DiffTransform(BaseModel):
    """A single text transformation for diff visualization."""
    
    original: str = Field(..., description="Text that was changed")
    replacement: str = Field(default="", description="What it became (empty if deleted)")
    reason_code: str = Field(..., description="Machine-readable reason code")
    reason: str = Field(..., description="Human-readable explanation")
    position: list[int] = Field(..., description="[start, end] offsets in original segment")
    rule_id: Optional[str] = Field(None, description="Policy rule ID")


class DiffSegment(BaseModel):
    """Diff data for a single segment."""
    
    segment_id: str = Field(..., description="Segment identifier")
    original: str = Field(..., description="Original segment text")
    neutral: Optional[str] = Field(None, description="Neutralized text (if changed)")
    start_char: int = Field(..., description="Start offset in original input")
    end_char: int = Field(..., description="End offset in original input")
    transforms: list[DiffTransform] = Field(default_factory=list)
    changed: bool = Field(..., description="Whether this segment was modified")


class DiffData(BaseModel):
    """Complete diff visualization data."""
    
    segments: list[DiffSegment] = Field(default_factory=list)
    total_transforms: int = Field(default=0, description="Total number of transformations")
    segments_changed: int = Field(default=0, description="Number of segments that were modified")
    segments_unchanged: int = Field(default=0, description="Number of segments unchanged")


class StructuredOutput(BaseModel):
    """
    Complete structured output from NNRT.
    
    This is the pre-alpha output format that makes explicit:
    - What is observed vs claimed vs inferred
    - What is uncertain or ambiguous
    - What transformations were applied
    """
    
    # Metadata
    nnrt_version: str = Field(..., description="NNRT version")
    schema_version: str = Field(default=SCHEMA_VERSION, description="Output schema version")
    request_id: str = Field(..., description="Unique request ID")
    input_hash: str = Field(..., description="SHA256 of input text")
    timestamp: datetime = Field(..., description="Processing timestamp")
    transformed: bool = Field(..., description="Whether any transformations occurred")
    
    # Core content (legacy segment-based)
    statements: list[StatementOutput] = Field(default_factory=list)
    
    # NEW: Atomic statements from decomposition pipeline
    atomic_statements: list[AtomicStatementOutput] = Field(
        default_factory=list,
        description="Decomposed atomic statements with classification and provenance"
    )
    
    uncertainties: list[UncertaintyOutput] = Field(default_factory=list)
    entities: list[EntityOutput] = Field(default_factory=list)
    events: list[EventOutput] = Field(default_factory=list)
    
    # Diagnostics
    diagnostics: list[dict] = Field(default_factory=list)
    
    # Diff visualization data (NEW)
    diff_data: Optional[DiffData] = Field(None, description="Detailed diff data for visualization")
    
    # Rendered output
    rendered_text: str = Field(..., description="Final neutralized text")


# ============================================================================
# Conversion Functions
# ============================================================================

def build_structured_output(result: TransformResult, input_text: str) -> StructuredOutput:
    """
    Convert a TransformResult to StructuredOutput.
    
    This is the bridge between internal IR and external JSON API.
    """
    # Build statements from segments
    statements = []
    for i, seg in enumerate(result.segments):
        # Build transformation records from applied rules
        transformations = [
            TransformationRecord(
                rule_id=rule_id,
                action="transform",  # Generic action - could be enhanced
                original=seg.text,
                replacement=seg.neutral_text,
            )
            for rule_id in seg.applied_rules
        ]
        
        stmt = StatementOutput(
            id=f"stmt_{i+1:03d}",
            type=seg.statement_type.value,
            original=seg.text,
            neutral=seg.neutral_text,  # Now populated from segment
            segment_id=seg.id,
            classification_confidence=seg.statement_confidence,
            contexts=seg.contexts,
            transformations=transformations,  # Now populated from segment
            flags=[],
        )
        statements.append(stmt)
    
    # Build atomic statements from decomposition pipeline (NEW)
    atomic_statements_out = []
    for atomic in result.atomic_statements:
        stmt_type = atomic.type_hint.value if hasattr(atomic.type_hint, 'value') else str(atomic.type_hint)
        atomic_out = AtomicStatementOutput(
            id=atomic.id,
            type=stmt_type,
            text=atomic.text,
            segment_id=atomic.segment_id,
            confidence=atomic.confidence,
            clause_type=atomic.clause_type,
            connector=atomic.connector,
            derived_from=atomic.derived_from,
            flags=atomic.flags,
        )
        atomic_statements_out.append(atomic_out)
    
    # Build uncertainties from Markers (Phase 3)
    uncertainties = []
    
    for unc_marker in result.uncertainty:
        unc = UncertaintyOutput(
            id=unc_marker.id,
            type=unc_marker.type.value,
            text=unc_marker.text or unc_marker.description,
            segment_id=unc_marker.affected_ids[0] if unc_marker.affected_ids else "unknown",
            description=unc_marker.description,
            candidates=None,
            resolution=None,
            requires_human_review=True,
        )
        uncertainties.append(unc)
    
    # Compute input hash
    input_hash = f"sha256:{hashlib.sha256(input_text.encode()).hexdigest()[:16]}"
    
    # Determine if transformed
    transformed = result.rendered_text != input_text if result.rendered_text else False
    

    # Build span lookup for mention resolution
    span_lookup = {span.id: span.text for span in result.spans}
    
    entities_out = []
    for ent in result.entities:
        # Resolve mentions: span IDs -> actual text
        resolved_mentions = []
        for m in ent.mentions:
            if m.startswith("text:"):
                # Fallback format: "text:He" -> extract "He"
                resolved_mentions.append({"text": m[5:]})  # Strip "text:" prefix
            elif m in span_lookup:
                # Proper span ID -> look up text
                resolved_mentions.append({"text": span_lookup[m]})
            else:
                # Unknown format, pass through
                resolved_mentions.append({"text": m})
        
        entities_out.append(EntityOutput(
            id=ent.id,
            type=ent.type.value if hasattr(ent.type, "value") else str(ent.type),
            label=ent.label or "Unknown",
            role=ent.role.value if hasattr(ent.role, "value") else str(ent.role),
            mentions=resolved_mentions,
            attributes={}
        ))
        
    # Build events (Phase 4)
    events_out = []
    
    for evt in result.events:
        events_out.append(EventOutput(
            id=evt.id,
            type=evt.type.value,
            description=evt.description,
            actors=[evt.actor_id] if evt.actor_id else [],
            targets=[evt.target_id] if evt.target_id else [],
            source_statement="unknown",  # Linking logic to be refined
            confidence=evt.confidence
        ))

    # Build diff data from segment transforms (NEW)
    diff_segments = []
    total_transforms = 0
    segments_changed = 0
    segments_unchanged = 0
    
    for seg in result.segments:
        segment_transforms = []
        for t in seg.transforms:
            segment_transforms.append(DiffTransform(
                original=t.original_text,
                replacement=t.replacement_text,
                reason_code=t.reason_code,
                reason=t.reason_message,
                position=[t.start_offset, t.end_offset],
                rule_id=t.policy_rule_id,
            ))
        
        changed = seg.neutral_text is not None and seg.neutral_text != seg.text
        if changed:
            segments_changed += 1
        else:
            segments_unchanged += 1
        
        total_transforms += len(segment_transforms)
        
        diff_segments.append(DiffSegment(
            segment_id=seg.id,
            original=seg.text,
            neutral=seg.neutral_text,
            start_char=seg.start_char,
            end_char=seg.end_char,
            transforms=segment_transforms,
            changed=changed,
        ))
    
    diff_data = DiffData(
        segments=diff_segments,
        total_transforms=total_transforms,
        segments_changed=segments_changed,
        segments_unchanged=segments_unchanged,
    )

    return StructuredOutput(
        nnrt_version=__version__,
        schema_version=SCHEMA_VERSION,
        request_id=result.request_id,
        input_hash=input_hash,
        timestamp=result.timestamp,
        transformed=transformed,
        statements=statements,
        atomic_statements=atomic_statements_out,
        uncertainties=uncertainties,
        entities=entities_out,
        events=events_out,
        diagnostics=[d.model_dump() for d in result.diagnostics],
        diff_data=diff_data,
        rendered_text=result.rendered_text or "",
    )


def _map_diagnostic_to_uncertainty_type(code: str) -> str:
    """Map diagnostic codes to uncertainty types."""
    mapping = {
        "AMBIGUOUS_PRONOUN": "ambiguous_reference",
        "VAGUE_REFERENCE": "vague_reference",
        "PHYSICAL_CONTRADICTION": "contradiction",
        "SELF_CONTRADICTION": "contradiction",
        "SARCASM_DETECTED": "sarcasm",
    }
    return mapping.get(code, "other")
