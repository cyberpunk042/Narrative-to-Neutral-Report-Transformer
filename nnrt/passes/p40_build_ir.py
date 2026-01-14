"""
Pass 40 — IR Construction

Builds the core IR structures (entities, events, speech acts)
from segments and tagged spans using NLP analysis.
"""

from typing import Optional
from uuid import uuid4

from nnrt.core.context import TransformContext
from nnrt.ir.enums import EntityRole, EventType, SpanLabel, SpeechActType
from nnrt.ir.schema_v0_1 import Entity, Event, SpeechAct

PASS_NAME = "p40_build_ir"

# Lazy-loaded spaCy model
_nlp: Optional["spacy.language.Language"] = None


def _get_nlp() -> "spacy.language.Language":
    """Get or load the spaCy model."""
    global _nlp
    if _nlp is None:
        try:
            import spacy
            _nlp = spacy.load("en_core_web_sm")
        except OSError:
            raise RuntimeError(
                "spaCy model 'en_core_web_sm' not found. "
                "Install with: python -m spacy download en_core_web_sm"
            )
    return _nlp


# Pronouns that typically refer to reporter
REPORTER_PRONOUNS = {"i", "me", "my", "myself", "we", "us", "our"}

# Pronouns that typically refer to subject
SUBJECT_PRONOUNS = {"he", "she", "they", "him", "her", "them", "his", "their"}

# Authority role indicators
AUTHORITY_INDICATORS = {
    "officer", "police", "cop", "detective", "sergeant", "deputy",
    "guard", "agent", "official", "security",
}

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


def _identify_role(text: str) -> EntityRole:
    """Identify the role of an entity mention."""
    text_lower = text.lower()
    
    if any(p in text_lower.split() for p in REPORTER_PRONOUNS):
        return EntityRole.REPORTER
    
    if any(ind in text_lower for ind in AUTHORITY_INDICATORS):
        return EntityRole.AUTHORITY
    
    if any(p in text_lower.split() for p in SUBJECT_PRONOUNS):
        return EntityRole.SUBJECT
    
    return EntityRole.UNKNOWN


def _extract_event_type(verb_text: str) -> EventType:
    """Determine event type from verb."""
    verb_lower = verb_text.lower()
    
    # Movement verbs
    if any(v in verb_lower for v in ["walk", "go", "come", "run", "drove", "left", "arrived"]):
        return EventType.MOVEMENT
    
    # Verbal events
    if any(v in verb_lower for v in SPEECH_ACT_VERBS.keys()):
        return EventType.VERBAL
    
    # State changes
    if any(v in verb_lower for v in ["became", "turned", "got", "stopped", "started"]):
        return EventType.STATE_CHANGE
    
    # Default to action
    return EventType.ACTION


def build_ir(ctx: TransformContext) -> TransformContext:
    """
    Build IR structures from segments and spans.
    
    This pass:
    - Identifies entities and their roles
    - Extracts events from action spans
    - Detects speech acts
    - Links entities to events
    """
    if not ctx.segments:
        ctx.add_diagnostic(
            level="warning",
            code="NO_SEGMENTS",
            message="No segments to build IR from",
            source=PASS_NAME,
        )
        return ctx

    nlp = _get_nlp()
    
    # Use existing IR if present (from Phase 4 passes), otherwise initialize empty
    entities: list[Entity] = list(ctx.entities) if ctx.entities else []
    events: list[Event] = list(ctx.events) if ctx.events else []
    speech_acts: list[SpeechAct] = list(ctx.speech_acts) if ctx.speech_acts else []
    
    run_entity_extraction = len(entities) == 0
    run_event_extraction = len(events) == 0
    
    # Track entity mentions for deduplication (only used if running legacy extraction)
    entity_map: dict[str, Entity] = {}  # role -> entity
    
    entity_counter = len(entities)
    event_counter = len(events)
    speech_act_counter = len(speech_acts)
    
    for segment in ctx.segments:
        doc = nlp(segment.text)
        
        # Find segment's spans
        segment_spans = [s for s in ctx.spans if s.segment_id == segment.id]
        span_ids = [s.id for s in segment_spans]
        
        # Extract entities from noun chunks
        if run_entity_extraction:
            for chunk in doc.noun_chunks:
                role = _identify_role(chunk.text)
                
                # Create or find entity
                role_key = role.value
                if role_key not in entity_map:
                    entity = Entity(
                        id=f"ent_{entity_counter:03d}",
                        role=role,
                        mentions=[],
                    )
                    entity_map[role_key] = entity
                    entities.append(entity)
                    entity_counter += 1
                
                # Find matching span and add as mention
                for span in segment_spans:
                    if span.start_char <= chunk.start_char and chunk.end_char <= span.end_char:
                        if span.id not in entity_map[role_key].mentions:
                            entity_map[role_key].mentions.append(span.id)
                        break
        
        # Extract events from verbs
        if run_event_extraction:
            for token in doc:
                if token.pos_ == "VERB" and token.dep_ not in ("aux", "auxpass"):
                    # Get verb text
                    verb_text = token.text
                    event_type = _extract_event_type(verb_text)
                    
                    # Find actor (subject)
                    actor_id = None
                    target_id = None
                    
                    for child in token.children:
                        if child.dep_ in ("nsubj", "nsubjpass"):
                            subj_role = _identify_role(child.text)
                            if subj_role.value in entity_map:
                                actor_id = entity_map[subj_role.value].id
                        elif child.dep_ in ("dobj", "pobj"):
                            obj_role = _identify_role(child.text)
                            if obj_role.value in entity_map:
                                target_id = entity_map[obj_role.value].id
                    
                    # Build neutral description
                    description = _build_neutral_description(token, doc)
                    
                    event = Event(
                        id=f"evt_{event_counter:03d}",
                        type=event_type,
                        description=description,
                        source_spans=span_ids[:2],  # Link to first spans as evidence
                        confidence=0.75,
                        actor_id=actor_id,
                        target_id=target_id,
                        is_uncertain=False,
                        requires_context=False,
                    )
                    events.append(event)
                    event_counter += 1
        
        # Extract speech acts
        for token in doc:
            if token.lemma_.lower() in SPEECH_ACT_VERBS:
                speech_type = SPEECH_ACT_VERBS.get(token.lemma_.lower(), SpeechActType.STATEMENT)
                
                # Find speaker
                speaker_id = None
                for child in token.children:
                    if child.dep_ == "nsubj":
                        speaker_role = _identify_role(child.text)
                        if speaker_role.value in entity_map:
                            speaker_id = entity_map[speaker_role.value].id
                
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

    ctx.entities = entities
    ctx.events = events
    ctx.speech_acts = speech_acts
    
    ctx.add_trace(
        pass_name=PASS_NAME,
        action="built_ir",
        after=f"{len(entities)} entities, {len(events)} events, {len(speech_acts)} speech acts",
    )

    return ctx


def _build_neutral_description(verb_token, doc) -> str:
    """Build a neutral description of an event from a verb token."""
    # Collect verb and its dependents
    parts = []
    
    # Subject
    for child in verb_token.children:
        if child.dep_ in ("nsubj", "nsubjpass"):
            parts.append(f"[{child.text}]")
    
    # Verb phrase
    parts.append(verb_token.text)
    
    # Objects and complements
    for child in verb_token.children:
        if child.dep_ in ("dobj", "pobj", "attr", "acomp"):
            parts.append(child.text)
    
    return " ".join(parts) if parts else verb_token.text


def _extract_speech_content(text: str) -> str:
    """Extract quoted speech content from text."""
    import re
    
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
