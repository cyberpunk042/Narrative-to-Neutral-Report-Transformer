"""
Pass 36 — Quote Speaker Resolution

V7 / Stage 1: Resolves quote speakers from context and patterns.

This pass updates SpeechAct objects with:
- speaker_resolved: True if speaker was identified
- speaker_label: The identified speaker name
- speaker_resolution_method: How the speaker was identified
- speaker_validation: "valid", "pronoun_only", or "unknown"

Logic migrated from V1 structured.py lines 1315-1410.
"""

import re
from typing import Optional

from nnrt.core.context import TransformContext
from nnrt.core.logging import get_pass_logger

PASS_NAME = "p36_resolve_quotes"
log = get_pass_logger(PASS_NAME)

# V8.1: Expanded list of speech verbs (from V1 lines 1316-1321)
SPEECH_VERBS = [
    ' said ', ' yelled ', ' shouted ', ' asked ', ' told ',
    ' screamed ', ' whispered ', ' replied ', ' answered ',
    ' explained ', ' stated ', ' mentioned ', ' demanded ',
    ' threatened ', ' warned ', ' muttered ', ' exclaimed ',
]

# Words that are NOT valid speakers (from V1 lines 1339-1343)
NOT_SPEAKERS = {
    'phone', 'face', 'me', 'him', 'her', 'them', 'us', 'it',
    'ear', 'car', 'head', 'arm', 'hand', 'back', 'porch',
    'saying', 'and', 'just', 'then', 'also', 'immediately',
}

# Name patterns for speaker extraction (from V1 lines 1346-1357)
NAME_PATTERNS = [
    r'(Officer\s+\w+)\s*$',
    r'(Sergeant\s+\w+)\s*$',
    r'(Detective\s+\w+)\s*$',
    r'(Captain\s+\w+)\s*$',
    r'(Lieutenant\s+\w+)\s*$',
    r'(Deputy\s+\w+)\s*$',
    r'(Dr\.\s+\w+)\s*$',
    r'(Mrs?\.\s+\w+(?:\s+\w+)?)\s*$',
    r'(Ms\.\s+\w+(?:\s+\w+)?)\s*$',
    r'(\w+\s+\w+)\s*$',  # Generic two-word name at end
    r'([Hh]e|[Ss]he|[Tt]hey)\s*$',  # Pronouns at end
]

# First-person patterns (from V1 lines 1382-1391)
FIRST_PERSON_PATTERNS = [
    'I tried to explain',
    'I explained',
    'I asked him',
    'I asked her',
    'I asked them',
    'I told him',
    'I told her',
    'I told them',
]


def resolve_quotes(ctx: TransformContext) -> TransformContext:
    """
    Resolve quote speakers from context and patterns.
    
    V7 / Stage 1: Migrates speaker resolution logic from V1 renderer
    to populate SpeechAct fields during pipeline processing.
    
    Updates:
    - speaker_resolved: True if speaker was identified
    - speaker_label: The resolved speaker name
    - speaker_resolution_method: "speech_verb", "first_person", "entity_match"
    - speaker_validation: "valid", "pronoun_only", "unknown"
    - is_quarantined: True if no speaker could be resolved
    - quarantine_reason: Why the quote was quarantined
    """
    if not ctx.speech_acts:
        log.debug("no_speech_acts", message="No speech acts to resolve")
        return ctx
    
    resolved_count = 0
    quarantined_count = 0
    
    for speech_act in ctx.speech_acts:
        # Skip if already resolved
        if speech_act.speaker_resolved:
            resolved_count += 1
            continue
        
        # Get text to analyze
        text = speech_act.raw_text or speech_act.content or ""
        
        speaker_label = None
        resolution_method = None
        validation = "unknown"
        
        # =====================================================================
        # Method 1: Speech verb pattern (V1 lines 1324-1378)
        # =====================================================================
        for verb in SPEECH_VERBS:
            if verb in text:
                parts = text.split(verb, 1)
                speaker_text = parts[0].strip()
                
                # V8.1: "I asked", "I tried to explain" -> Reporter
                if speaker_text.lower() in ['i', 'i also', 'i then']:
                    speaker_label = "Reporter"
                    resolution_method = "first_person"
                    validation = "valid"
                else:
                    # Try to extract speaker name from pattern
                    extracted = _extract_speaker_from_text(speaker_text)
                    if extracted:
                        speaker_label = extracted["speaker"]
                        resolution_method = "speech_verb"
                        validation = extracted["validation"]
                
                # Extract speech verb for SpeechAct
                speech_act.speech_verb = verb.strip()
                break
        
        # =====================================================================
        # Method 2: First-person patterns (V1 lines 1381-1397)
        # =====================================================================
        if not speaker_label:
            for pattern in FIRST_PERSON_PATTERNS:
                if text.startswith(pattern):
                    speaker_label = "Reporter"
                    resolution_method = "first_person"
                    validation = "valid"
                    break
        
        # =====================================================================
        # Method 3: Entity context matching (new for Stage 1)
        # =====================================================================
        if not speaker_label and ctx.entities:
            # Check if any entity is mentioned in the text
            for entity in ctx.entities:
                if entity.label and entity.label in text:
                    speaker_label = entity.label
                    resolution_method = "entity_match"
                    validation = "valid"
                    break
        
        # =====================================================================
        # Update SpeechAct fields
        # =====================================================================
        if speaker_label:
            speech_act.speaker_label = speaker_label
            speech_act.speaker_resolved = True
            speech_act.speaker_resolution_method = resolution_method
            speech_act.speaker_validation = validation
            speech_act.is_quarantined = False
            speech_act.quarantine_reason = None
            
            # Set confidence based on validation
            if validation == "valid":
                speech_act.speaker_resolution_confidence = 0.85
            elif validation == "pronoun_only":
                speech_act.speaker_resolution_confidence = 0.5
            else:
                speech_act.speaker_resolution_confidence = 0.3
            
            resolved_count += 1
        else:
            # Quarantine: no speaker could be resolved
            speech_act.speaker_resolved = False
            speech_act.is_quarantined = True
            speech_act.quarantine_reason = "no_speaker_identified"
            speech_act.speaker_validation = "unknown"
            speech_act.speaker_resolution_confidence = 0.0
            
            quarantined_count += 1
    
    log.info(
        "resolved_quotes",
        total=len(ctx.speech_acts),
        resolved=resolved_count,
        quarantined=quarantined_count,
    )
    
    ctx.add_trace(
        pass_name=PASS_NAME,
        action="resolve_quotes",
        after=f"Resolved {resolved_count}/{len(ctx.speech_acts)} quotes, {quarantined_count} quarantined",
    )
    
    return ctx


def _extract_speaker_from_text(speaker_text: str) -> Optional[dict]:
    """
    Extract speaker name from text using patterns.
    
    Returns dict with 'speaker' and 'validation' keys, or None if no match.
    """
    for pattern in NAME_PATTERNS:
        match = re.search(pattern, speaker_text)
        if match:
            candidate = match.group(1).strip()
            
            # Validate: check if any word in candidate is a non-speaker word
            words = candidate.lower().split()
            if any(w in NOT_SPEAKERS for w in words):
                continue  # Try next pattern
            
            # Check if it's a pronoun
            is_pronoun = candidate.lower() in {'he', 'she', 'they'}
            
            return {
                "speaker": candidate,
                "validation": "pronoun_only" if is_pronoun else "valid"
            }
    
    # Fallback: take last 30 chars max
    if speaker_text:
        fallback = speaker_text[-30:].strip() if len(speaker_text) > 30 else speaker_text
        return {
            "speaker": fallback,
            "validation": "unknown"
        }
    
    return None
