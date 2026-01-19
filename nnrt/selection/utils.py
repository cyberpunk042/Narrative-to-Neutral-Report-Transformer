"""
Selection Utilities — Stage 3

Helper functions for creating SelectionResult from TransformResult.
This allows downstream code (web server, CLI) to use the new rendering path
without needing access to TransformContext.
"""

from typing import Optional

from nnrt.selection.models import SelectionMode, SelectionResult


# Roles that indicate incident participation
INCIDENT_ROLES = {
    'reporter', 'subject_officer', 'supervisor', 
    'witness_civilian', 'witness_official', 'bystander'
}

# Roles that indicate post-incident professionals
POST_INCIDENT_ROLES = {
    'medical_provider', 'legal_counsel', 'investigator'
}

# Bare role labels to exclude
BARE_ROLE_LABELS = {
    'partner', 'passenger', 'suspect', 'manager', 'driver',
    'victim', 'witness', 'officer', 'the partner', 'his partner',
    'the suspect', 'a suspect', 'the manager', 'my manager'
}


def build_selection_from_result(result, mode: str = "strict") -> SelectionResult:
    """
    Build SelectionResult from TransformResult.
    
    This function replicates the selection logic from p55_select but works
    on TransformResult instead of TransformContext. Use this when you have
    a TransformResult and need SelectionResult for rendering.
    
    Args:
        result: TransformResult with events, entities, speech_acts, timeline
        mode: Selection mode string (strict, full, timeline, events_only)
        
    Returns:
        SelectionResult with atom IDs for each output section
    """
    sel = SelectionResult(mode=mode)
    
    mode_enum = _parse_mode(mode)
    
    # Select events
    _select_events_from_result(result, sel, mode_enum)
    
    # Select entities
    _select_entities_from_result(result, sel, mode_enum)
    
    # Select quotes
    _select_quotes_from_result(result, sel, mode_enum)
    
    # Select timeline
    _select_timeline_from_result(result, sel, mode_enum)
    
    return sel


def _parse_mode(mode_str: str) -> SelectionMode:
    """Parse mode string to SelectionMode enum."""
    mode_map = {
        'strict': SelectionMode.STRICT,
        'full': SelectionMode.FULL,
        'timeline': SelectionMode.TIMELINE,
        'events': SelectionMode.EVENTS_ONLY,
        'events_only': SelectionMode.EVENTS_ONLY,
        'recompose': SelectionMode.RECOMPOSITION,
        'recomposition': SelectionMode.RECOMPOSITION,
    }
    return mode_map.get(mode_str.lower(), SelectionMode.STRICT)


def _select_events_from_result(result, sel: SelectionResult, mode: SelectionMode) -> None:
    """Select events based on classification."""
    events = result.events if hasattr(result, 'events') else []
    
    for event in events:
        # Get classification fields
        is_camera_friendly = getattr(event, 'is_camera_friendly', False)
        is_follow_up = getattr(event, 'is_follow_up', False)
        is_source_derived = getattr(event, 'is_source_derived', False)
        is_fragment = getattr(event, 'is_fragment', False)
        
        if mode == SelectionMode.FULL:
            # Include all events
            sel.observed_events.append(event.id)
        elif mode == SelectionMode.STRICT:
            if is_camera_friendly and not is_fragment:
                if is_follow_up:
                    sel.follow_up_events.append(event.id)
                elif is_source_derived:
                    sel.source_derived_events.append(event.id)
                else:
                    sel.observed_events.append(event.id)
            else:
                # Non-camera-friendly goes to narrative excerpts
                reason = getattr(event, 'camera_friendly_reason', 'not_camera_friendly')
                sel.narrative_excerpts.append((event.id, reason))


def _select_entities_from_result(result, sel: SelectionResult, mode: SelectionMode) -> None:
    """Select entities based on role."""
    entities = result.entities if hasattr(result, 'entities') else []
    
    for entity in entities:
        label = getattr(entity, 'label', 'Unknown')
        role = getattr(entity, 'role', 'unknown')
        participation = getattr(entity, 'participation', None)
        
        # Skip bare role labels
        if label.lower().strip() in BARE_ROLE_LABELS:
            sel.excluded_entities.append(entity.id)
            continue
        
        # Normalize role
        if hasattr(role, 'value'):
            role = role.value
        role_lower = str(role).lower()
        
        # Use participation if set, otherwise infer from role
        if participation:
            if hasattr(participation, 'value'):
                participation = participation.value
            
            if participation == 'incident':
                sel.incident_participants.append(entity.id)
            elif participation == 'post_incident':
                sel.post_incident_pros.append(entity.id)
            else:
                sel.mentioned_contacts.append(entity.id)
        else:
            # Infer from role
            if role_lower in INCIDENT_ROLES:
                sel.incident_participants.append(entity.id)
            elif role_lower in POST_INCIDENT_ROLES:
                sel.post_incident_pros.append(entity.id)
            elif role_lower in {'workplace_contact', 'subject'}:
                sel.mentioned_contacts.append(entity.id)
            else:
                # Default for person types
                entity_type = getattr(entity, 'type', 'unknown')
                if hasattr(entity_type, 'value'):
                    entity_type = entity_type.value
                if str(entity_type).lower() == 'person':
                    sel.incident_participants.append(entity.id)


def _select_quotes_from_result(result, sel: SelectionResult, mode: SelectionMode) -> None:
    """Select quotes based on speaker resolution."""
    speech_acts = result.speech_acts if hasattr(result, 'speech_acts') else []
    
    for speech_act in speech_acts:
        speaker_label = getattr(speech_act, 'speaker_label', None)
        speaker_resolved = getattr(speech_act, 'speaker_resolved', False)
        
        # Consider resolved if: speaker_resolved=True OR speaker_label is set
        has_speaker = speaker_resolved or (speaker_label and speaker_label.strip())
        
        if has_speaker:
            sel.preserved_quotes.append(speech_act.id)
        else:
            sel.quarantined_quotes.append((speech_act.id, "unresolved_speaker"))


def _select_timeline_from_result(result, sel: SelectionResult, mode: SelectionMode) -> None:
    """Select timeline entries."""
    timeline = result.timeline if hasattr(result, 'timeline') else []
    
    for entry in timeline:
        # Get quality info
        display_quality = getattr(entry, 'display_quality', 'normal')
        pronouns_resolved = getattr(entry, 'pronouns_resolved', True)
        
        if mode == SelectionMode.STRICT:
            # Only high/normal quality, resolved pronouns
            if display_quality in ('high', 'normal') and pronouns_resolved:
                sel.timeline_entries.append(entry.id)
            else:
                reason = f"quality={display_quality}" if display_quality not in ('high', 'normal') else "pronouns_unresolved"
                sel.excluded_timeline.append((entry.id, reason))
        else:
            # Include all
            sel.timeline_entries.append(entry.id)
