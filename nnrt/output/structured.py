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
from nnrt.passes.p48_classify_evidence import _classify_epistemic_type


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
    
    V4 Alpha: Includes full epistemic tagging:
    - source: who is speaking
    - epistemic_type: what kind of content
    - polarity: asserted/denied/uncertain
    - evidence_source: what supports this
    """
    
    id: str = Field(..., description="Statement ID (stmt_XXXX)")
    type: str = Field(..., description="observation|claim|interpretation|quote|unknown")
    text: str = Field(..., description="Statement text")
    
    segment_id: str = Field(..., description="Source segment ID")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Classification confidence")
    
    clause_type: str = Field(..., description="root|conj|advcl|ccomp|quote")
    connector: Optional[str] = Field(None, description="Clause connector (and, because, etc.)")
    
    # V4 ALPHA: Epistemic tagging
    source: str = Field(default="reporter", description="Who is speaking: reporter|witness|medical|investigator|document")
    epistemic_type: str = Field(default="unknown", description="Content type: direct_event|self_report|interpretation|legal_claim|quote|etc")
    polarity: str = Field(default="asserted", description="asserted|denied|uncertain|hypothetical")
    evidence_source: str = Field(default="self_report", description="What supports this: direct_observation|self_report|document|inference")
    
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


# ============================================================================
# V4 ALPHA: Reference Data (Typed & Linked)
# ============================================================================

class ReferenceData(BaseModel):
    """
    V4 Alpha: Structured reference data extracted from narrative.
    
    All identifiers are typed and linked:
    - badge_map: links officers to badge numbers
    - dates: only absolute dates (no "today", "next day")
    - times: only clock times
    - locations: verified locations
    - names: extracted names (canonicalized)
    """
    
    # Badge linkage: {"Officer Jenkins": "4821", "Sergeant Williams": "2103"}
    badge_map: dict[str, str] = Field(
        default_factory=dict, 
        description="Officer name -> badge number mapping"
    )
    
    # Absolute dates only (no relative dates like "today")
    dates: list[str] = Field(
        default_factory=list,
        description="Explicit dates (no relative dates)"
    )
    
    # Clock times only
    times: list[str] = Field(
        default_factory=list,
        description="Explicit times (11:30 PM)"
    )
    
    # Verified locations
    locations: list[str] = Field(
        default_factory=list,
        description="Location names"
    )
    
    # Names (canonicalized - Officer Jenkins, not Officers Jenkins)
    names: list[str] = Field(
        default_factory=list,
        description="Person names (canonicalized)"
    )


# ============================================================================
# V3 Semantic Understanding Output Models
# ============================================================================

class MentionOutput(BaseModel):
    """A mention of an entity in the narrative (v3)."""
    
    id: str = Field(..., description="Mention ID (m_XXXX)")
    text: str = Field(..., description="The mention text as it appears")
    type: str = Field(..., description="proper_name|pronoun|title|descriptor")
    resolved_entity_id: Optional[str] = Field(None, description="Entity this refers to")
    confidence: float = Field(default=0.5, description="Resolution confidence")


class CoreferenceChainOutput(BaseModel):
    """A chain linking all mentions of an entity (v3)."""
    
    entity_id: str = Field(..., description="The entity all mentions refer to")
    entity_label: str = Field(..., description="Human-readable entity label")
    mentions: list[str] = Field(default_factory=list, description="Mention texts in order")
    mention_count: int = Field(default=0)
    has_proper_name: bool = Field(default=False)
    confidence: float = Field(default=0.5)


class TimelineEntryOutput(BaseModel):
    """A temporally-positioned event (v3)."""
    
    sequence_order: int = Field(..., description="Chronological position (0=first)")
    event_id: Optional[str] = Field(None)
    description: str = Field(..., description="What happened")
    absolute_time: Optional[str] = Field(None, description="Explicit time if known")
    relative_time: Optional[str] = Field(None, description="Relative time marker")
    confidence: float = Field(default=0.5)


class StatementGroupOutput(BaseModel):
    """A semantic cluster of related statements (v3)."""
    
    id: str = Field(..., description="Group ID")
    type: str = Field(..., description="encounter|medical|witness_account|official|emotional|quote")
    title: str = Field(..., description="Human-readable group title")
    statements: list[str] = Field(default_factory=list, description="Statement texts in this group")
    statement_count: int = Field(default=0)
    primary_entity: Optional[str] = Field(None, description="Main entity label")
    evidence_strength: float = Field(default=0.5)


class EvidenceClassificationOutput(BaseModel):
    """Evidence classification for a statement (v3)."""
    
    statement_id: str = Field(..., description="Statement this classifies")
    statement_text: Optional[str] = Field(None, description="Statement text for context")
    evidence_type: str = Field(..., description="direct_witness|reported|documentary|physical|inference")
    source: Optional[str] = Field(None, description="Source entity label for reported evidence")
    reliability: float = Field(default=0.5, description="0.0=unreliable to 1.0=highly reliable")
    corroborated_by: list[str] = Field(default_factory=list, description="Corroborating statement IDs")


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
    
    # V3: Semantic Understanding
    coreference_chains: list[CoreferenceChainOutput] = Field(
        default_factory=list,
        description="Coreference chains linking pronouns to entities"
    )
    timeline: list[TimelineEntryOutput] = Field(
        default_factory=list,
        description="Chronologically ordered events"
    )
    statement_groups: list[StatementGroupOutput] = Field(
        default_factory=list,
        description="Semantic clusters of related statements"
    )
    evidence_classifications: list[EvidenceClassificationOutput] = Field(
        default_factory=list,
        description="Evidence type and reliability for statements"
    )
    
    # =========================================================================
    # V4: Epistemic Classification Buckets
    # =========================================================================
    # These are NOT neutral - they are the reporter's interpretations and
    # must be explicitly labeled as such. Content here CANNOT be in
    # "statements" or "observations" or any neutral-claiming bucket.
    
    reporter_interpretations: list[AtomicStatementOutput] = Field(
        default_factory=list,
        description="Intent attribution and inferences BY THE REPORTER - NOT neutral"
    )
    
    reporter_legal_characterizations: list[AtomicStatementOutput] = Field(
        default_factory=list,
        description="Legal conclusions made by reporter (not qualified) - NOT neutral"
    )
    
    reporter_conspiracy_claims: list[AtomicStatementOutput] = Field(
        default_factory=list,
        description="Unfalsifiable conspiracy allegations - NOT neutral"
    )
    
    # V4 ALPHA: Typed and linked reference data
    reference_data: Optional[ReferenceData] = Field(
        None, 
        description="Structured reference data with badge linkage"
    )
    
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
    
    # =========================================================================
    # V4: Build atomic statements WITH EPISTEMIC ROUTING
    # =========================================================================
    # Statements with dangerous patterns are routed to explicit buckets,
    # NOT mixed into the general atomic_statements list.
    
    atomic_statements_out = []
    reporter_interpretations = []
    reporter_legal_characterizations = []
    reporter_conspiracy_claims = []
    
    for atomic in result.atomic_statements:
        stmt_type = atomic.type_hint.value if hasattr(atomic.type_hint, 'value') else str(atomic.type_hint)
        
        # V4: Get epistemic tagging from the statement itself (set by p27_epistemic_tag)
        epistemic_type = getattr(atomic, 'epistemic_type', 'unknown')
        polarity = getattr(atomic, 'polarity', 'asserted')
        source = getattr(atomic, 'source', 'reporter')
        evidence_source = getattr(atomic, 'evidence_source', 'self_report')
        
        # Legacy V4 classification (still used for _classify_epistemic_type patterns)
        legacy_type, matched_phrase = _classify_epistemic_type(atomic.text)
        
        # Use the more specific type if available
        if epistemic_type == 'unknown' and legacy_type:
            epistemic_type = legacy_type
        
        atomic_out = AtomicStatementOutput(
            id=atomic.id,
            type=stmt_type,
            text=atomic.text,
            segment_id=atomic.segment_id,
            confidence=atomic.confidence,
            clause_type=atomic.clause_type,
            connector=atomic.connector,
            # V4 ALPHA: Epistemic tagging fields
            source=source,
            epistemic_type=epistemic_type,
            polarity=polarity,
            evidence_source=evidence_source,
            derived_from=atomic.derived_from,
            flags=atomic.flags if epistemic_type == 'unknown' else atomic.flags + [f"V4_{epistemic_type.upper()}"],
        )
        
        # V4: Route based on epistemic type (using both new and legacy classification)
        if epistemic_type in ("interpretation", "intent_attribution"):
            reporter_interpretations.append(atomic_out)
        elif epistemic_type in ("legal_claim", "legal_characterization"):
            reporter_legal_characterizations.append(atomic_out)
        elif epistemic_type == "conspiracy_claim":
            reporter_conspiracy_claims.append(atomic_out)
        else:
            # Not a dangerous pattern - safe for general bucket
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

    # =========================================================================
    # V3: Semantic Understanding Data
    # =========================================================================
    
    # Build entity lookup for label resolution
    entity_lookup = {ent.id: ent for ent in result.entities}
    
    # Build coreference chains output
    coreference_chains_out = []
    for chain in result.coreference_chains:
        entity = entity_lookup.get(chain.entity_id)
        entity_label = entity.label if entity else "Unknown"
        
        # Get mention texts
        mention_texts = []
        for m_id in chain.mention_ids:
            mention = next((m for m in result.mentions if m.id == m_id), None)
            if mention:
                mention_texts.append(mention.text)
        
        coreference_chains_out.append(CoreferenceChainOutput(
            entity_id=chain.entity_id,
            entity_label=entity_label,
            mentions=mention_texts,
            mention_count=chain.mention_count,
            has_proper_name=chain.has_proper_name,
            confidence=chain.confidence,
        ))
    
    # Build timeline output
    timeline_out = []
    for entry in sorted(result.timeline, key=lambda x: x.sequence_order):
        # Get event description if available
        description = ""
        if entry.event_id:
            event = next((e for e in result.events if e.id == entry.event_id), None)
            if event:
                description = event.description
        
        timeline_out.append(TimelineEntryOutput(
            sequence_order=entry.sequence_order,
            event_id=entry.event_id,
            description=description,
            absolute_time=entry.absolute_time,
            relative_time=entry.relative_time,
            confidence=entry.time_confidence,
        ))
    
    # Build statement groups output
    statement_groups_out = []
    for group in result.statement_groups:
        # Get statement texts
        statement_texts = []
        for stmt_id in group.statement_ids:
            stmt = next((s for s in result.atomic_statements if s.id == stmt_id), None)
            if stmt:
                statement_texts.append(stmt.text)
        
        # Get primary entity label
        primary_entity_label = None
        if group.primary_entity_id:
            entity = entity_lookup.get(group.primary_entity_id)
            if entity:
                primary_entity_label = entity.label
        
        statement_groups_out.append(StatementGroupOutput(
            id=group.id,
            type=group.group_type.value,
            title=group.title,
            statements=statement_texts,
            statement_count=len(statement_texts),
            primary_entity=primary_entity_label,
            evidence_strength=group.evidence_strength,
        ))
    
    # Build evidence classifications output
    evidence_out = []
    for ev in result.evidence_classifications:
        # Get statement text
        stmt_text = None
        stmt = next((s for s in result.atomic_statements if s.id == ev.statement_id), None)
        if stmt:
            stmt_text = stmt.text
        
        # Get source entity label
        source_label = None
        if ev.source_entity_id:
            entity = entity_lookup.get(ev.source_entity_id)
            if entity:
                source_label = entity.label
        
        evidence_out.append(EvidenceClassificationOutput(
            statement_id=ev.statement_id,
            statement_text=stmt_text,
            evidence_type=ev.evidence_type.value,
            source=source_label,
            reliability=ev.reliability,
            corroborated_by=ev.corroborating_ids,
        ))
    
    # =========================================================================
    # V4 ALPHA: Build Reference Data with Badge Linkage
    # =========================================================================
    
    # Build badge map by finding badge numbers near officer names
    badge_map = {}
    
    # Get all officer entities
    officers = [e for e in result.entities if 
                getattr(e.role, 'value', str(e.role)) in ('subject_officer', 'supervisor', 'investigator', 'authority')]
    
    # Get all badge numbers
    badges = [i for i in result.identifiers if i.type.value == 'badge_number']
    
    # Try to link badges to officers by proximity in text
    # This is a heuristic - badge near name in same segment
    for officer in officers:
        officer_label = officer.label or ''
        # Normalize label (remove "Officer " prefix for matching)
        name_parts = officer_label.replace("Officer ", "").replace("Sergeant ", "").replace("Detective ", "").split()
        
        for badge in badges:
            # Check if badge and officer mention are in same segment
            officer_mentions = officer.mentions
            for mention in officer_mentions:
                mention_text = mention[5:] if isinstance(mention, str) and mention.startswith("text:") else str(mention)
                # Check if any name part is in the mention
                if any(part.lower() in mention_text.lower() for part in name_parts if len(part) > 2):
                    badge_map[officer_label] = badge.value
                    break
    
    # Build filtered identifier lists
    dates = []
    times = []
    locations = []
    names = []
    
    for ident in result.identifiers:
        if ident.type.value == 'date':
            # Already filtered by _is_valid_date
            dates.append(ident.value)
        elif ident.type.value == 'time':
            times.append(ident.value)
        elif ident.type.value == 'location':
            locations.append(ident.value)
        elif ident.type.value == 'name':
            # Canonicalize: ensure "Officer Jenkins" not "Officers Jenkins"
            name = ident.value
            if name.startswith("Officers "):
                name = "Officer " + name[9:]
            names.append(name)
    
    reference_data = ReferenceData(
        badge_map=badge_map,
        dates=dates,
        times=times,
        locations=locations,
        names=names,
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
        coreference_chains=coreference_chains_out,
        timeline=timeline_out,
        statement_groups=statement_groups_out,
        evidence_classifications=evidence_out,
        # V4: Epistemic classification buckets
        reporter_interpretations=reporter_interpretations,
        reporter_legal_characterizations=reporter_legal_characterizations,
        reporter_conspiracy_claims=reporter_conspiracy_claims,
        # V4 ALPHA: Reference data
        reference_data=reference_data,
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
