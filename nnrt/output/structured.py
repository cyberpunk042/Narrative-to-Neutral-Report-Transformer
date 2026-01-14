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
    
    # Core content
    statements: list[StatementOutput] = Field(default_factory=list)
    uncertainties: list[UncertaintyOutput] = Field(default_factory=list)
    entities: list[EntityOutput] = Field(default_factory=list)
    events: list[EventOutput] = Field(default_factory=list)
    
    # Diagnostics
    diagnostics: list[dict] = Field(default_factory=list)
    
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
        stmt = StatementOutput(
            id=f"stmt_{i+1:03d}",
            type=seg.statement_type.value,
            original=seg.text,
            neutral=None,  # TODO: Track per-segment rendering
            segment_id=seg.id,
            classification_confidence=seg.statement_confidence,
            contexts=seg.contexts,
            transformations=[],  # TODO: Link transformations to segments
            flags=[],
        )
        statements.append(stmt)
    
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
    

    entities_out = []
    for ent in result.entities:
        entities_out.append(EntityOutput(
            id=ent.id,
            type=ent.type.value if hasattr(ent.type, "value") else str(ent.type),
            label=ent.label or "Unknown",
            role=ent.role.value if hasattr(ent.role, "value") else str(ent.role),
            mentions=[{"text": m} for m in ent.mentions],
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
            source_statement="unknown", # Linking logic to be refined
            confidence=evt.confidence
        ))

    return StructuredOutput(
        nnrt_version=__version__,
        schema_version=SCHEMA_VERSION,
        request_id=result.request_id,
        input_hash=input_hash,
        timestamp=result.timestamp,
        transformed=transformed,
        statements=statements,
        uncertainties=uncertainties,
        entities=entities_out,
        events=events_out,
        diagnostics=[d.model_dump() for d in result.diagnostics],
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
