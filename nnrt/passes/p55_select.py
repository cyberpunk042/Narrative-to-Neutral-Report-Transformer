"""
Pass 55 — Selection

V7 / Stage 2: Select which atoms to include in output.

This pass classifies atoms into output sections:
- Events → OBSERVED EVENTS, FOLLOW-UP, SOURCE-DERIVED, NARRATIVE EXCERPTS
- Entities → INCIDENT PARTICIPANTS, POST-INCIDENT PROFESSIONALS, MENTIONED CONTACTS
- Quotes → PRESERVED QUOTES, QUARANTINE
- Timeline → RECONSTRUCTED TIMELINE

Uses pre-computed classification fields from Stage 1 (p35_classify_events).
"""

import re
from typing import Any

from nnrt.core.context import TransformContext
from nnrt.core.logging import get_pass_logger
from nnrt.selection.models import SelectionMode, SelectionResult

PASS_NAME = "p55_select"
log = get_pass_logger(PASS_NAME)


# =============================================================================
# Entity Selection Constants
# =============================================================================

# Roles that indicate incident participation
INCIDENT_ROLES = {
    'reporter', 'subject_officer', 'supervisor',
    'witness_civilian', 'witness_official', 'bystander'
}

# Roles that indicate post-incident professionals
POST_INCIDENT_ROLES = {
    'medical_provider', 'legal_counsel', 'investigator'
}

# Bare role labels that should be EXCLUDED (not properly named entities)
BARE_ROLE_LABELS = {
    'partner', 'passenger', 'suspect', 'manager', 'driver',
    'victim', 'witness', 'officer', 'the partner', 'his partner',
    'the suspect', 'a suspect', 'the manager', 'my manager'
}


# =============================================================================
# Timeline Selection Constants
# =============================================================================

# V7 / Stage 2: Updated to match V1 fragment starters (lines 1642-1646 + 1701-1702)
FRAGMENT_STARTS = {
    # Original
    'and', 'but', 'when', 'which', 'although', 'while', 'because',
    # Added from V1
    'to', 'for', 'from', 'by', 'where', 'who', 'until', 'unless',
    'what', 'how', 'why', 'if', 'or', 'yet'
}
PRONOUN_PATTERN = re.compile(r'^(He|She|They|It|We|I)\s', re.IGNORECASE)


# =============================================================================
# Mode Parsing
# =============================================================================

# Map CLI mode names to SelectionMode enum values
MODE_MAP = {
    'strict': SelectionMode.STRICT,
    'full': SelectionMode.FULL,
    'timeline': SelectionMode.TIMELINE,
    'events': SelectionMode.EVENTS_ONLY,
    'events_only': SelectionMode.EVENTS_ONLY,
    'recompose': SelectionMode.RECOMPOSITION,
    'recomposition': SelectionMode.RECOMPOSITION,
}


def _parse_mode(mode_str: str) -> SelectionMode:
    """Parse mode string to SelectionMode enum."""
    mode_str = mode_str.lower().strip()
    if mode_str in MODE_MAP:
        return MODE_MAP[mode_str]
    # Try to match enum value directly
    try:
        return SelectionMode(mode_str)
    except ValueError:
        log.warning("unknown_mode", mode=mode_str, using="strict")
        return SelectionMode.STRICT


def select(ctx: TransformContext, mode: SelectionMode = None) -> TransformContext:
    """
    Select which atoms to include in output based on mode.
    
    Uses PRE-COMPUTED classification fields from Stage 1:
    - event.is_camera_friendly
    - event.is_follow_up
    - event.is_source_derived
    - event.is_fragment
    - event.camera_friendly_reason
    
    For entities, quotes, and timeline, uses existing schema fields
    since they don't have dedicated classification passes yet.
    
    Args:
        ctx: Transform context with classified atoms
        mode: Selection mode (default: from request metadata or STRICT)
    
    Returns:
        ctx with selection_result populated
    """
    # Read mode from request metadata if not explicitly passed
    if mode is None:
        mode_str = ctx.request.metadata.get('selection_mode', 'strict')
        mode = _parse_mode(mode_str)
    
    result = SelectionResult(mode=mode.value)
    
    # =========================================================================
    # Event Selection
    # =========================================================================
    
    result = _select_events(ctx, result, mode)
    
    # =========================================================================
    # Entity Selection
    # =========================================================================
    
    result = _select_entities(ctx, result, mode)
    
    # =========================================================================
    # Quote Selection
    # =========================================================================
    
    result = _select_quotes(ctx, result, mode)
    
    # =========================================================================
    # Timeline Selection
    # =========================================================================
    
    result = _select_timeline(ctx, result, mode)
    
    # =========================================================================
    # V7 / Stage 2: Statement Selection (by epistemic_type)
    # =========================================================================
    
    result = _select_statements(ctx, result, mode)
    
    # =========================================================================
    # V7 / Stage 2: Identifier Selection
    # =========================================================================
    
    result = _select_identifiers(ctx, result, mode)
    
    # =========================================================================
    # Store result and log
    # =========================================================================
    
    result.stats = {
        'total_events': len(ctx.events),
        'total_entities': len(ctx.entities),
        'total_quotes': len(ctx.speech_acts),
        'total_timeline': len(ctx.timeline),
        'selected_observed': len(result.observed_events),
        'selected_followup': len(result.follow_up_events),
        'selected_excerpts': len(result.narrative_excerpts),
        'selected_entities': (
            len(result.incident_participants) +
            len(result.post_incident_pros) +
            len(result.mentioned_contacts)
        ),
        'selected_quotes': len(result.preserved_quotes),
        'quarantined_quotes': len(result.quarantined_quotes),
        'selected_timeline': len(result.timeline_entries),
    }
    
    ctx.selection_result = result
    
    log.info(
        "selection_complete",
        mode=mode.value,
        observed=len(result.observed_events),
        follow_up=len(result.follow_up_events),
        source_derived=len(result.source_derived_events),
        excerpts=len(result.narrative_excerpts),
        entities=result.stats['selected_entities'],
        quotes=len(result.preserved_quotes),
        timeline=len(result.timeline_entries),
    )
    
    ctx.add_trace(
        pass_name=PASS_NAME,
        action="select_atoms",
        after=result.summary(),
    )
    
    return ctx


def _select_events(
    ctx: TransformContext,
    result: SelectionResult,
    mode: SelectionMode
) -> SelectionResult:
    """Select events based on classification and mode."""
    
    for event in ctx.events:
        if mode == SelectionMode.STRICT:
            # V7 FIX: Follow-up and source-derived events don't require camera-friendly status
            # They represent different event types with different validation requirements
            
            # Route 1: Follow-up events (post-incident actions like ER visit, filing complaint)
            if event.is_follow_up:
                result.follow_up_events.append(event.id)
                continue
            
            # Route 2: Source-derived events (research, conclusions, third-party claims)
            if event.is_source_derived:
                result.source_derived_events.append(event.id)
                continue
            
            # Route 3: Camera-friendly events with confidence threshold
            if event.is_camera_friendly and event.camera_friendly_confidence >= 0.7:
                result.observed_events.append(event.id)
            
            elif not event.is_camera_friendly:
                # Failed camera-friendly check — goes to narrative excerpts
                reason = event.camera_friendly_reason or "failed_classification"
                result.narrative_excerpts.append((event.id, reason))
            
            else:
                # Low confidence — also goes to excerpts
                result.narrative_excerpts.append((event.id, "low_confidence"))
        
        elif mode == SelectionMode.FULL:
            # Include all events in observed (for debugging)
            result.observed_events.append(event.id)
        
        elif mode == SelectionMode.EVENTS_ONLY:
            # Include all events (same as FULL for events)
            result.observed_events.append(event.id)
        
        elif mode == SelectionMode.TIMELINE:
            # Include all events (timeline mode focuses on timeline entries)
            result.observed_events.append(event.id)
        
        elif mode == SelectionMode.RECOMPOSITION:
            # Include all for recomposition
            result.observed_events.append(event.id)
    
    return result


def _select_entities(
    ctx: TransformContext,
    result: SelectionResult,
    mode: SelectionMode
) -> SelectionResult:
    """Select entities based on role and participation."""
    
    for entity in ctx.entities:
        label = getattr(entity, 'label', '') or ''
        role = getattr(entity, 'role', 'unknown')
        participation = getattr(entity, 'participation', None)
        
        # Normalize role to string
        if hasattr(role, 'value'):
            role = role.value
        role_lower = str(role).lower()
        
        if mode == SelectionMode.STRICT:
            # Skip bare role labels (not properly named)
            if label.lower().strip() in BARE_ROLE_LABELS:
                result.excluded_entities.append(entity.id)
                continue
            
            # Use participation if set, otherwise infer from role
            if participation:
                if hasattr(participation, 'value'):
                    participation = participation.value
                
                if participation == 'incident':
                    result.incident_participants.append(entity.id)
                elif participation == 'post_incident':
                    result.post_incident_pros.append(entity.id)
                else:
                    result.mentioned_contacts.append(entity.id)
            else:
                # Infer from role
                if role_lower in INCIDENT_ROLES:
                    result.incident_participants.append(entity.id)
                elif role_lower in POST_INCIDENT_ROLES:
                    result.post_incident_pros.append(entity.id)
                elif role_lower in {'workplace_contact', 'subject'}:
                    result.mentioned_contacts.append(entity.id)
                else:
                    # Default: if it's a person, assume incident
                    entity_type = getattr(entity, 'type', 'unknown')
                    if hasattr(entity_type, 'value'):
                        entity_type = entity_type.value
                    if str(entity_type).lower() == 'person':
                        result.incident_participants.append(entity.id)
        
        elif mode in (SelectionMode.FULL, SelectionMode.RECOMPOSITION):
            # Include all entities using same categorization
            if label.lower().strip() in BARE_ROLE_LABELS:
                result.excluded_entities.append(entity.id)
            elif role_lower in INCIDENT_ROLES or role_lower in {'reporter', 'subject_officer'}:
                result.incident_participants.append(entity.id)
            elif role_lower in POST_INCIDENT_ROLES:
                result.post_incident_pros.append(entity.id)
            else:
                result.mentioned_contacts.append(entity.id)
        
        # EVENTS_ONLY and TIMELINE skip entities
    
    return result


def _select_quotes(
    ctx: TransformContext,
    result: SelectionResult,
    mode: SelectionMode
) -> SelectionResult:
    """Select quotes based on speaker resolution."""
    
    for speech_act in ctx.speech_acts:
        # Check if speaker is resolved
        # Use speaker_label as proxy since speaker_resolved isn't populated yet
        speaker_label = getattr(speech_act, 'speaker_label', None)
        speaker_resolved = getattr(speech_act, 'speaker_resolved', False)
        is_quarantined = getattr(speech_act, 'is_quarantined', False)
        
        # Consider resolved if: speaker_resolved=True OR speaker_label is set
        has_speaker = speaker_resolved or (speaker_label and speaker_label.strip())
        
        if mode == SelectionMode.STRICT:
            if is_quarantined:
                reason = getattr(speech_act, 'quarantine_reason', 'previously_quarantined')
                result.quarantined_quotes.append((speech_act.id, reason))
            elif has_speaker:
                result.preserved_quotes.append(speech_act.id)
            else:
                result.quarantined_quotes.append((speech_act.id, "speaker_unresolved"))
        
        elif mode in (SelectionMode.FULL, SelectionMode.RECOMPOSITION):
            # Include all quotes
            if has_speaker:
                result.preserved_quotes.append(speech_act.id)
            else:
                result.quarantined_quotes.append((speech_act.id, "speaker_unresolved"))
        
        # EVENTS_ONLY and TIMELINE skip quotes
    
    return result


def _select_timeline(
    ctx: TransformContext,
    result: SelectionResult,
    mode: SelectionMode
) -> SelectionResult:
    """Select timeline entries based on completeness."""
    
    for entry in ctx.timeline:
        description = getattr(entry, 'description', '') or ''
        words = description.split()
        first_word = words[0].lower() if words else ''
        
        if mode in (SelectionMode.STRICT, SelectionMode.TIMELINE):
            # Check for fragment starts
            if first_word in FRAGMENT_STARTS:
                result.excluded_timeline.append((entry.id, f"fragment_start:{first_word}"))
                continue
            
            # Check for pronoun starts
            if PRONOUN_PATTERN.match(description):
                # Check if event has actor_label (indicates resolution)
                event_id = getattr(entry, 'event_id', None)
                if event_id:
                    event = ctx.get_event_by_id(event_id)
                    if event and event.actor_label:
                        # Resolved — include
                        result.timeline_entries.append(entry.id)
                        continue
                
                # Unresolved pronoun
                result.excluded_timeline.append((entry.id, "unresolved_pronoun"))
                continue
            
            # Passed checks
            result.timeline_entries.append(entry.id)
        
        elif mode in (SelectionMode.FULL, SelectionMode.RECOMPOSITION):
            # Include all timeline entries
            result.timeline_entries.append(entry.id)
        
        # EVENTS_ONLY skips timeline
    
    return result


def _select_statements(
    ctx: TransformContext,
    result: SelectionResult,
    mode: SelectionMode
) -> SelectionResult:
    """
    V7 / Stage 2: Select statements based on epistemic_type.
    
    Routes atomic statements to appropriate section buckets based on their
    epistemic_type classification from p27_epistemic_tag.
    
    Uses shared contract from nnrt.selection.epistemic_types which handles
    prefix matching for sub-types (e.g., legal_claim_attorney → legal_allegations).
    """
    from nnrt.selection.epistemic_types import get_selection_field
    
    if not ctx.atomic_statements:
        return result
    
    routed_count = 0
    unrouted_count = 0
    
    for stmt in ctx.atomic_statements:
        # Get epistemic_type from statement
        epistemic = getattr(stmt, 'epistemic_type', None)
        if not epistemic:
            unrouted_count += 1
            continue
        
        # Check for medical provider content flag (from p27)
        flags = getattr(stmt, 'flags', [])
        if 'medical_provider_content' in flags:
            result.medical_findings.append(stmt.id)
            routed_count += 1
            continue
        
        # Route by epistemic_type using shared contract (with prefix matching)
        target_field = get_selection_field(epistemic)
        if target_field:
            getattr(result, target_field).append(stmt.id)
            routed_count += 1
        else:
            unrouted_count += 1
    
    if routed_count > 0:
        log.debug(
            "statements_routed",
            routed=routed_count,
            unrouted=unrouted_count,
            total=len(ctx.atomic_statements),
        )
    
    return result


def _select_identifiers(
    ctx: TransformContext,
    result: SelectionResult,
    mode: SelectionMode
) -> SelectionResult:
    """
    V7 / Stage 2: Select identifiers by type.
    
    Groups identifiers into the identifiers_by_type dict for the
    REFERENCE DATA section.
    """
    if not ctx.identifiers:
        return result
    
    for ident in ctx.identifiers:
        # Get identifier type
        ident_type = getattr(ident, 'type', None)
        if hasattr(ident_type, 'value'):
            ident_type = ident_type.value
        ident_type = str(ident_type) if ident_type else 'unknown'
        
        # Initialize list if needed
        if ident_type not in result.identifiers_by_type:
            result.identifiers_by_type[ident_type] = []
        
        # Add identifier ID
        result.identifiers_by_type[ident_type].append(ident.id)
    
    return result
