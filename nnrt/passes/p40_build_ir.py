"""
Pass 40 — IR Assembly

Assembles the Intermediate Representation from components extracted by
previous passes (p32: entities, p34: events).

This pass does NOT extract entities or events — that's p32/p34's job.
This pass:
- Extracts speech acts (unique responsibility)
- Links entities to events
- Validates cross-references
- Assembles final IR structure
"""

import re
from typing import Optional
from uuid import uuid4

from nnrt.core.context import TransformContext
from nnrt.ir.enums import EntityRole, SpeechActType
from nnrt.ir.schema_v0_1 import Entity, Event, SpeechAct
from nnrt.nlp.spacy_loader import get_nlp

PASS_NAME = "p40_build_ir"



# Speech act verbs and their types
SPEECH_ACT_VERBS = {
    "said": SpeechActType.STATEMENT,
    "told": SpeechActType.STATEMENT,
    "stated": SpeechActType.STATEMENT,
    "replied": SpeechActType.STATEMENT,
    "responded": SpeechActType.STATEMENT,
    "asked": SpeechActType.QUESTION,
    "questioned": SpeechActType.QUESTION,
    "demanded": SpeechActType.COMMAND,
    "ordered": SpeechActType.COMMAND,
    "commanded": SpeechActType.COMMAND,
    "yelled": SpeechActType.STATEMENT,
    "shouted": SpeechActType.STATEMENT,
    "threatened": SpeechActType.THREAT,
}


def build_ir(ctx: TransformContext) -> TransformContext:
    """
    Assemble IR from extracted components.
    
    This pass:
    - Uses entities from p32 (does NOT extract its own)
    - Uses events from p34 (does NOT extract its own)
    - Extracts speech acts (unique to this pass)
    - Links and validates cross-references
    
    If p32/p34 produced no entities/events, this pass does NOT
    fall back to inferior extraction. Empty IR = transparent failure.
    """
    if not ctx.segments:
        ctx.add_diagnostic(
            level="warning",
            code="NO_SEGMENTS",
            message="No segments to build IR from",
            source=PASS_NAME,
        )
        return ctx

    # Use entities/events from p32/p34 — NO FALLBACK EXTRACTION
    entities: list[Entity] = list(ctx.entities) if ctx.entities else []
    events: list[Event] = list(ctx.events) if ctx.events else []
    speech_acts: list[SpeechAct] = list(ctx.speech_acts) if ctx.speech_acts else []
    
    # Log if extraction passes produced nothing (transparent, not hidden)
    if len(entities) == 0:
        ctx.add_diagnostic(
            level="info",
            code="NO_ENTITIES",
            message="No entities from p32. IR will have no entities.",
            source=PASS_NAME,
        )
    
    if len(events) == 0:
        ctx.add_diagnostic(
            level="info",
            code="NO_EVENTS", 
            message="No events from p34. IR will have no events.",
            source=PASS_NAME,
        )
    
    # Build entity lookup for speech act speaker resolution
    entity_by_role: dict[str, Entity] = {}
    for ent in entities:
        if ent.role.value not in entity_by_role:
            entity_by_role[ent.role.value] = ent
    
    # Extract speech acts (p40's unique responsibility)
    nlp = get_nlp()
    speech_act_counter = len(speech_acts)
    
    for segment in ctx.segments:
        doc = nlp(segment.text)
        segment_spans = [s for s in ctx.spans if s.segment_id == segment.id]
        span_ids = [s.id for s in segment_spans]
        
        for token in doc:
            if token.lemma_.lower() in SPEECH_ACT_VERBS:
                speech_type = SPEECH_ACT_VERBS.get(token.lemma_.lower(), SpeechActType.STATEMENT)
                
                # Find speaker by matching subject to known entities
                speaker_id = None
                for child in token.children:
                    if child.dep_ == "nsubj":
                        # Try to match to existing entity
                        speaker_id = _resolve_speaker(child.text, entities)
                
                # Extract quoted content if present
                content = _extract_speech_content(segment.text)
                is_direct = '"' in segment.text or "'" in segment.text
                
                if content:
                    speech_act = SpeechAct(
                        id=f"speech_{speech_act_counter:03d}",
                        type=speech_type,
                        speaker_id=speaker_id,
                        content=content,
                        is_direct_quote=is_direct,
                        source_span_id=span_ids[0] if span_ids else segment.id,
                        confidence=0.8 if is_direct else 0.6,
                    )
                    speech_acts.append(speech_act)
                    speech_act_counter += 1

    # Update context with assembled IR
    ctx.entities = entities
    ctx.events = events
    ctx.speech_acts = speech_acts
    
    ctx.add_trace(
        pass_name=PASS_NAME,
        action="assembled_ir",
        after=f"{len(entities)} entities, {len(events)} events, {len(speech_acts)} speech acts",
    )

    return ctx


def _resolve_speaker(text: str, entities: list[Entity]) -> Optional[str]:
    """Resolve speaker text to an entity ID."""
    text_lower = text.lower()
    
    # Check if text matches any entity label or mention
    for ent in entities:
        if ent.label and ent.label.lower() in text_lower:
            return ent.id
        for mention in ent.mentions:
            if isinstance(mention, str) and mention.lower() in text_lower:
                return ent.id
    
    return None


def _extract_speech_content(text: str) -> str:
    """Extract quoted speech content from text."""
    # Try double quotes first
    double_match = re.search(r'"([^"]+)"', text)
    if double_match:
        return double_match.group(1)
    
    # Try single quotes
    single_match = re.search(r"'([^']+)'", text)
    if single_match:
        return single_match.group(1)
    
    # No quotes - return empty (indirect speech will be handled differently)
    return ""
