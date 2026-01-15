"""
Structured Output Formatter

Generates an official report format from TransformResult.
This is plain text output, not HTML.

Format:
══════════════════════════════════════════════════════════════════
                        NEUTRALIZED REPORT
══════════════════════════════════════════════════════════════════

PARTIES
──────────────────────────────────────────────────────────────────
  REPORTER:   [name/description]
  SUBJECT:    [name/description]
  ...

REFERENCE DATA
──────────────────────────────────────────────────────────────────
  Date:       [extracted date]
  Location:   [extracted location]
  ...

══════════════════════════════════════════════════════════════════
                         ACCOUNT SUMMARY
══════════════════════════════════════════════════════════════════

OBSERVATIONS
──────────────────────────────────────────────────────────────────
  • [observation text]
  ...

...etc
"""

from typing import Dict, List, Any
from collections import defaultdict


def format_structured_output(
    rendered_text: str,
    atomic_statements: List[Any],
    entities: List[Any],
    events: List[Any],
    identifiers: List[Any],
    metadata: Dict[str, Any] = None,
) -> str:
    """
    Format transform result as an official structured report.
    
    Args:
        rendered_text: The computed neutral prose
        atomic_statements: List of AtomicStatement objects
        entities: List of Entity objects
        events: List of Event objects
        identifiers: List of Identifier objects
        metadata: Optional metadata dict
    
    Returns:
        Plain text formatted as official report
    """
    lines = []
    
    # Header
    lines.append("═" * 70)
    lines.append("                        NEUTRALIZED REPORT")
    lines.append("═" * 70)
    lines.append("")
    
    # === V5: PARTIES with three-tier structure ===
    if entities:
        # V5: Categorize entities by participation
        incident_participants = []
        post_incident_pros = []
        mentioned_contacts = []
        
        # Roles that indicate incident participation
        INCIDENT_ROLES = {
            'reporter', 'subject_officer', 'supervisor', 
            'witness_civilian', 'witness_official', 'bystander'
        }
        
        # Roles that indicate post-incident professionals
        POST_INCIDENT_ROLES = {
            'medical_provider', 'legal_counsel', 'investigator'
        }
        
        # V5: Bare role labels that should be EXCLUDED from PARTIES
        # These are not properly named entities
        BARE_ROLE_LABELS = {
            'partner', 'passenger', 'suspect', 'manager', 'driver',
            'victim', 'witness', 'officer', 'the partner', 'his partner',
            'the suspect', 'a suspect', 'the manager', 'my manager'
        }
        
        for e in entities:
            label = getattr(e, 'label', 'Unknown')
            role = getattr(e, 'role', 'unknown')
            participation = getattr(e, 'participation', None)
            
            # V5: Skip bare role labels (not properly named)
            if label.lower().strip() in BARE_ROLE_LABELS:
                continue
            
            # Normalize role to string
            if hasattr(role, 'value'):
                role = role.value
            role_lower = str(role).lower()
            
            # Use participation if explicitly set, otherwise infer from role
            if participation:
                if hasattr(participation, 'value'):
                    participation = participation.value
                
                if participation == 'incident':
                    incident_participants.append((role_lower, label))
                elif participation == 'post_incident':
                    post_incident_pros.append((role_lower, label))
                else:
                    mentioned_contacts.append((role_lower, label))
            else:
                # Infer from role
                if role_lower in INCIDENT_ROLES:
                    incident_participants.append((role_lower, label))
                elif role_lower in POST_INCIDENT_ROLES:
                    post_incident_pros.append((role_lower, label))
                elif role_lower in {'workplace_contact', 'subject'}:
                    mentioned_contacts.append((role_lower, label))
                else:
                    # Default: if it's a person, assume incident
                    entity_type = getattr(e, 'type', 'unknown')
                    if hasattr(entity_type, 'value'):
                        entity_type = entity_type.value
                    if str(entity_type).lower() == 'person':
                        incident_participants.append((role_lower, label))
        
        lines.append("PARTIES")
        lines.append("─" * 70)
        
        # INCIDENT PARTICIPANTS
        if incident_participants:
            lines.append("  INCIDENT PARTICIPANTS:")
            for role, name in incident_participants:
                role_display = role.replace('_', ' ').title()
                lines.append(f"    • {name} ({role_display})")
        
        # POST-INCIDENT PROFESSIONALS
        if post_incident_pros:
            lines.append("  POST-INCIDENT PROFESSIONALS:")
            for role, name in post_incident_pros:
                role_display = role.replace('_', ' ').title()
                lines.append(f"    • {name} ({role_display})")
        
        # MENTIONED CONTACTS
        if mentioned_contacts:
            lines.append("  MENTIONED CONTACTS:")
            for role, name in mentioned_contacts:
                role_display = role.replace('_', ' ').title()
                lines.append(f"    • {name} ({role_display})")
        
        lines.append("")
    
    # === V5: REFERENCE DATA with structured temporal/location display ===
    if identifiers:
        ident_by_type = defaultdict(list)
        for ident in identifiers:
            ident_type = getattr(ident, 'type', None)
            if hasattr(ident_type, 'value'):
                ident_type = ident_type.value
            ident_type = str(ident_type) if ident_type else 'unknown'
            value = getattr(ident, 'value', str(ident))
            ident_by_type[ident_type].append(value)
        
        if ident_by_type:
            lines.append("REFERENCE DATA")
            lines.append("─" * 70)
            
            # V5: Primary incident date/time
            dates = ident_by_type.get('date', [])
            times = ident_by_type.get('time', [])
            if dates or times:
                lines.append("  INCIDENT DATETIME:")
                if dates:
                    lines.append(f"    Date: {dates[0]}")
                if times:
                    lines.append(f"    Time: {times[0]}")
                lines.append("")
            
            # V5: Primary incident location
            locations = ident_by_type.get('location', [])
            if locations:
                # First location is likely incident scene
                lines.append(f"  INCIDENT LOCATION: {locations[0]}")
                if len(locations) > 1:
                    lines.append("  SECONDARY LOCATIONS:")
                    for loc in locations[1:]:
                        lines.append(f"    • {loc}")
                lines.append("")
            
            # V5: Officer identification (filter to only officer-related names)
            badges = ident_by_type.get('badge_number', [])
            names = ident_by_type.get('name', [])
            
            # Filter names to only those that appear to be officers
            officer_titles = {'officer', 'sergeant', 'detective', 'lieutenant', 'deputy', 'captain'}
            officer_names = [n for n in names if any(t in n.lower() for t in officer_titles)]
            
            if badges or officer_names:
                lines.append("  OFFICER IDENTIFICATION:")
                for name in officer_names:
                    lines.append(f"    • {name}")
                for badge in badges:
                    lines.append(f"    • Badge #{badge}")
                lines.append("")
            
            # V5: Other identifiers (vehicle, employee ID, etc.)
            other_types = ['vehicle_plate', 'employee_id', 'other']
            has_other = any(ident_by_type.get(t) for t in other_types)
            if has_other:
                lines.append("  OTHER IDENTIFIERS:")
                for ident_type in other_types:
                    values = ident_by_type.get(ident_type, [])
                    if values:
                        label = ident_type.replace('_', ' ').title()
                        lines.append(f"    {label}: {', '.join(values)}")
                lines.append("")
    
    # === ACCOUNT SUMMARY HEADER ===
    lines.append("═" * 70)
    lines.append("                         ACCOUNT SUMMARY")
    lines.append("═" * 70)
    lines.append("")
    
    # Group atomic statements by type
    statements_by_type = defaultdict(list)
    # V4: Also group by epistemic_type for proper observation split
    statements_by_epistemic = defaultdict(list)
    
    # =========================================================================
    # V5: Camera-Friendly Filter
    # =========================================================================
    # NOTE: This filtering is intentionally in the renderer, not in extraction.
    # Rationale: All data is preserved in the IR (atomic_statements, events).
    # The renderer applies a DISPLAY filter to separate:
    #   - Camera-friendly content (can appear in "OBSERVED EVENTS")
    #   - Interpretive content (shown with attribution in other sections)
    # This is a VIEW concern, not a DATA concern. No data is lost.
    # =========================================================================
    
    INTERPRETIVE_DISQUALIFIERS = [
        # Characterizations
        'horrifying', 'horrific', 'brutal', 'brutally', 'viciously', 'vicious',
        'psychotic', 'maniac', 'thug', 'aggressive', 'aggressively', 
        'menacing', 'menacingly', 'distressing', 'terrifying', 'shocking',
        'excessive', 'mocking', 'laughing at', 'fishing',
        # Legal conclusions
        'innocent', 'guilty', 'criminal', 'illegal', 'unlawful', 'assault',
        'assaulting', 'torture', 'terrorize', 'misconduct', 'violation',
        # Intent attributions
        'deliberately', 'intentionally', 'clearly', 'obviously', 'wanted to',
        # Certainty markers
        'absolutely', 'completely', 'totally', 'definitely', 'certainly',
        # Cover-up/conspiracy language
        'cover-up', 'coverup', 'whitewash', 'conspiracy', 'conspiring',
        'hiding more', 'protect their own', 'always protect',
    ]
    
    # V4: Patterns that indicate "later discovered" facts (not incident-scene)
    # These are actual follow-up ACTIONS (reporter did something)
    FOLLOW_UP_PATTERNS = [
        'went to the emergency', 'went to the hospital', 'filed a complaint',
        'filed a formal', 'the next day', 'afterward', 'afterwards',
        'detective', 'took my statement',
    ]
    
    # V4.3: Patterns for source-derived information (needs provenance)
    # These are research results, comparisons, or conclusions - NOT observable
    SOURCE_DERIVED_PATTERNS = [
        'later found', 'later learned', 'found out', 'turned out',
        'found that', 'researched', 'so-called',
        'at least', 'other citizens', 'complaints against',
        'received a letter', 'three months later',
        'investigated', 'pursuing legal', 'my attorney',
    ]
    
    def is_camera_friendly(text: str) -> bool:
        """
        Check if statement is purely observational (no interpretive content).
        
        V4.3: Also requires proper subject (actor) for true camera-friendliness.
        "twisted it behind my back" is not camera-friendly - WHO twisted?
        """
        text_lower = text.lower()
        
        # Check for interpretive words
        for word in INTERPRETIVE_DISQUALIFIERS:
            if word in text_lower:
                return False
        
        # V4.3: Require proper subject - not a verb-first fragment
        words = text_lower.strip().split()
        if not words:
            return False
        
        first_word = words[0]
        # Fragments starting with verbs are not camera-friendly
        # (they lack the "who" - the actor)
        verb_starts = [
            'twisted', 'grabbed', 'pushed', 'slammed', 'found', 'tried',
            'stepped', 'saw', 'also', 'that', 'put', 'cut', 'filed',
        ]
        if first_word in verb_starts:
            return False
        
        return True
    
    def is_follow_up_event(text: str) -> bool:
        """Check if event is a true follow-up ACTION (reporter did something post-incident)."""
        text_lower = text.lower()
        return any(pattern in text_lower for pattern in FOLLOW_UP_PATTERNS)
    
    def is_source_derived(text: str) -> bool:
        """Check if statement is source-derived (research, comparison, conclusion)."""
        text_lower = text.lower()
        return any(pattern in text_lower for pattern in SOURCE_DERIVED_PATTERNS)
    
    for stmt in atomic_statements:
        stmt_type = getattr(stmt, 'type_hint', None)
        if hasattr(stmt_type, 'value'):
            stmt_type = stmt_type.value
        stmt_type = str(stmt_type) if stmt_type else 'unknown'
        text = getattr(stmt, 'text', str(stmt))
        statements_by_type[stmt_type].append(text)
        
        # V4: Group by epistemic type for observation split
        epistemic = getattr(stmt, 'epistemic_type', 'unknown')
        statements_by_epistemic[epistemic].append(text)
    
    # =========================================================================
    # V4: OBSERVED EVENTS - Quality filter: only camera-friendly statements
    # CRITICAL INVARIANT: If it contains interpretation, it doesn't belong here
    # =========================================================================
    if statements_by_epistemic.get('direct_event'):
        incident_events = []
        follow_up_events = []
        source_derived = []  # V4.3: Research results, conclusions - need provenance
        excluded_events = []  # Statements with interpretive content
        
        for text in statements_by_epistemic['direct_event']:
            if not is_camera_friendly(text):
                # Contains interpretive words - exclude from OBSERVED EVENTS
                excluded_events.append(text)
            elif is_source_derived(text):
                # V4.3: Research/conclusion - needs provenance
                source_derived.append(text)
            elif is_follow_up_event(text):
                follow_up_events.append(text)
            else:
                incident_events.append(text)
        
        # INCIDENT SCENE events (purely observational)
        if incident_events:
            lines.append("OBSERVED EVENTS (INCIDENT SCENE)")
            lines.append("─" * 70)
            for text in incident_events:
                lines.append(f"  • {text}")
            lines.append("")
        
        # FOLLOW-UP events (post-incident observable actions)
        if follow_up_events:
            lines.append("OBSERVED EVENTS (FOLLOW-UP ACTIONS)")
            lines.append("─" * 70)
            for text in follow_up_events:
                lines.append(f"  • {text}")
            lines.append("")
        
        # V5: SOURCE-DERIVED INFORMATION with provenance details
        # These need provenance verification - not directly observable
        if source_derived:
            lines.append("SOURCE-DERIVED INFORMATION")
            lines.append("─" * 70)
            lines.append("  ⚠️ The following claims require provenance verification:")
            lines.append("")
            for idx, text in enumerate(source_derived[:10], 1):  # Limit to 10
                lines.append(f"  [{idx}] CLAIM: {text[:100]}{'...' if len(text) > 100 else ''}")
                # Try to get provenance from atomic_statements if available
                source_type = "Reporter"
                prov_status = "Missing"
                if atomic_statements:
                    for stmt in atomic_statements:
                        if hasattr(stmt, 'text') and stmt.text.strip() == text.strip():
                            source_type = getattr(stmt, 'source_type', 'reporter').title()
                            prov_status = getattr(stmt, 'provenance_status', 'missing').title()
                            break
                lines.append(f"      Source: {source_type}")
                lines.append(f"      Status: {prov_status}")
                lines.append("")
            if len(source_derived) > 10:
                lines.append(f"  ... and {len(source_derived) - 10} more claims needing provenance")
                lines.append("")
        
        # REPORTER DESCRIPTIONS (excluded from OBSERVED EVENTS due to interpretive content)
        # Data is preserved with proper attribution
        if excluded_events:
            lines.append("REPORTER DESCRIPTIONS (contains characterization)")
            lines.append("─" * 70)
            for text in excluded_events:
                lines.append(f"  • Reporter describes: {text}")
            lines.append("")
    
    # =========================================================================
    # V5: SELF-REPORTED STATE with sub-categories
    # =========================================================================
    
    # Acute state (during incident)
    if statements_by_epistemic.get('state_acute'):
        lines.append("SELF-REPORTED STATE (ACUTE - During Incident)")
        lines.append("─" * 70)
        for text in statements_by_epistemic['state_acute']:
            lines.append(f"  • Reporter reports: {text}")
        lines.append("")
    
    # Physical injuries
    if statements_by_epistemic.get('state_injury'):
        lines.append("SELF-REPORTED INJURY (Physical)")
        lines.append("─" * 70)
        for text in statements_by_epistemic['state_injury']:
            lines.append(f"  • Reporter reports: {text}")
        lines.append("")
    
    # Psychological after-effects
    if statements_by_epistemic.get('state_psychological'):
        lines.append("SELF-REPORTED STATE (Psychological)")
        lines.append("─" * 70)
        for text in statements_by_epistemic['state_psychological']:
            lines.append(f"  • Reporter reports: {text}")
        lines.append("")
    
    # Socioeconomic impact
    if statements_by_epistemic.get('state_socioeconomic'):
        lines.append("SELF-REPORTED IMPACT (Socioeconomic)")
        lines.append("─" * 70)
        for text in statements_by_epistemic['state_socioeconomic']:
            lines.append(f"  • Reporter reports: {text}")
        lines.append("")
    
    # General self-report (fallback for non-categorized)
    if statements_by_epistemic.get('self_report'):
        lines.append("SELF-REPORTED STATE (General)")
        lines.append("─" * 70)
        for text in statements_by_epistemic['self_report']:
            lines.append(f"  • Reporter reports: {text}")
        lines.append("")
    
    # =========================================================================
    # V5: REPORTED CLAIMS (legal allegations only - explicit legal labels)
    # =========================================================================
    if statements_by_epistemic.get('legal_claim'):
        lines.append("LEGAL ALLEGATIONS (as asserted by Reporter)")
        lines.append("─" * 70)
        for text in statements_by_epistemic['legal_claim']:
            lines.append(f"  • Reporter alleges: {text}")
        lines.append("")
    
    # =========================================================================
    # V5: REPORTER CHARACTERIZATIONS (subjective language / adjectives)
    # e.g., "thug", "psychotic", "maniac", "corrupt"
    # =========================================================================
    if statements_by_epistemic.get('characterization'):
        lines.append("REPORTER CHARACTERIZATIONS (Subjective Language)")
        lines.append("─" * 70)
        for text in statements_by_epistemic['characterization']:
            lines.append(f"  • Opinion: {text}")
        lines.append("")
    
    # =========================================================================
    # V5: REPORTER INFERENCES (intent/motive/knowledge claims)
    # e.g., "looking for trouble", "wanted to inflict maximum damage"
    # =========================================================================
    if statements_by_epistemic.get('inference'):
        lines.append("REPORTER INFERENCES (Intent/Motive Claims)")
        lines.append("─" * 70)
        for text in statements_by_epistemic['inference']:
            lines.append(f"  • Reporter infers: {text}")
        lines.append("")
    
    # Legacy 'interpretation' bucket (for backward compatibility)
    if statements_by_epistemic.get('interpretation'):
        lines.append("REPORTER INTERPRETATIONS")
        lines.append("─" * 70)
        for text in statements_by_epistemic['interpretation']:
            lines.append(f"  • Reporter perceives: {text}")
        lines.append("")
    
    # =========================================================================
    # V4: CONTESTED ALLEGATIONS (conspiracy claims) - quarantined
    # These are unfalsifiable and should be clearly marked
    # =========================================================================
    if statements_by_epistemic.get('conspiracy_claim'):
        lines.append("CONTESTED ALLEGATIONS (unverifiable)")
        lines.append("─" * 70)
        for text in statements_by_epistemic['conspiracy_claim']:
            lines.append(f"  ⚠️ Unverified: {text}")
        lines.append("")
    
    # =========================================================================
    # V4: MEDICAL FINDINGS - doctor statements, diagnoses
    # =========================================================================
    if statements_by_epistemic.get('medical_finding'):
        lines.append("MEDICAL FINDINGS")
        lines.append("─" * 70)
        for text in statements_by_epistemic['medical_finding']:
            lines.append(f"  • {text}")
        lines.append("")
    
    # =========================================================================
    # V4: ADMINISTRATIVE ACTIONS - filings, complaints, etc.
    # =========================================================================
    if statements_by_epistemic.get('admin_action'):
        lines.append("ADMINISTRATIVE ACTIONS")
        lines.append("─" * 70)
        for text in statements_by_epistemic['admin_action']:
            lines.append(f"  • {text}")
        lines.append("")
    
    # === V5: PRESERVED QUOTES with speaker attribution ===
    if statements_by_type.get('quote') or (hasattr(metadata, 'speech_acts') if metadata else False):
        lines.append("PRESERVED QUOTES")
        lines.append("─" * 70)
        
        # First, try to use speech_acts from metadata if available
        speech_acts_used = []
        if metadata and hasattr(metadata, 'speech_acts') and metadata.speech_acts:
            for sa in metadata.speech_acts:
                speaker = getattr(sa, 'speaker_label', None) or 'Unknown'
                verb = getattr(sa, 'speech_verb', 'said')
                content = getattr(sa, 'content', '')
                is_nested = getattr(sa, 'is_nested', False)
                
                if content:
                    if is_nested:
                        lines.append(f"  ⚠️ {speaker} {verb}: {content}")
                        lines.append(f"      (nested quote - may have attribution issues)")
                    else:
                        lines.append(f"  • {speaker} {verb}: {content}")
                    speech_acts_used.append(content)
        
        # Fall back to statement-based quotes if no speech acts
        if not speech_acts_used:
            for text in statements_by_type.get('quote', []):
                # V5: Remove outer quotes if present
                clean_text = text
                if clean_text.startswith('"') and clean_text.endswith('"'):
                    clean_text = clean_text[1:-1]
                elif clean_text.startswith("'") and clean_text.endswith("'"):
                    clean_text = clean_text[1:-1]
                
                # Try to extract speaker from context
                speaker = "Unknown"
                if " said " in text or " says " in text:
                    parts = text.split(" said ") if " said " in text else text.split(" says ")
                    if len(parts) > 1:
                        speaker = parts[0].strip()[:50]  # Limit speaker name length
                        clean_text = parts[1] if len(parts[1]) > 10 else clean_text
                elif " yelled " in text or " shouted " in text:
                    speaker = "Speaker"  # Generic if we can't extract
                
                lines.append(f"  • {speaker}: {clean_text}")
        
        lines.append("")
    
    # === RECORDED EVENTS ===
    # V5: Use Actor/Action/Target schema for proper event rendering
    if events:
        # V5: Events must have resolved actors to be "camera-friendly"
        # Events with unresolved pronouns or no actor go to interpretive bucket
        camera_friendly_by_type = defaultdict(list)
        interpretive_events = []
        no_actor_events = []
        seen_events = set()
        
        for event in events:
            # V5: Use resolved actor_label if available
            actor = getattr(event, 'actor_label', None)
            action = getattr(event, 'action_verb', None)
            target = getattr(event, 'target_label', None) or getattr(event, 'target_object', None)
            desc = getattr(event, 'description', str(event))
            
            # Dedupe by description
            desc_normalized = ' '.join(desc.split())
            if desc_normalized in seen_events:
                continue
            seen_events.add(desc_normalized)
            
            # V5: Build formatted event line [ACTOR] [ACTION] [TARGET]
            if actor and action:
                # Remove pronouns from output
                if actor.lower() not in {'he', 'she', 'they', 'it', 'him', 'her', 'them'}:
                    event_line = f"{actor} {action}"
                    if target:
                        event_line += f" {target}"
                    
                    # Check camera-friendliness of the formatted line
                    if is_camera_friendly(event_line) and is_camera_friendly(desc):
                        # Get event type
                        etype = getattr(event, 'type', None)
                        if hasattr(etype, 'value'):
                            etype = etype.value
                        etype = str(etype) if etype else 'action'
                        camera_friendly_by_type[etype].append(event_line)
                    else:
                        interpretive_events.append(desc)
                else:
                    # Unresolved pronoun - move to no-actor bucket
                    no_actor_events.append(desc)
            else:
                # No actor or action - keep description but flag as incomplete
                if desc and len(desc) > 10:
                    # Check if it's interpretive
                    if not is_camera_friendly(desc):
                        interpretive_events.append(desc)
                    else:
                        no_actor_events.append(desc)
        
        # Render camera-friendly events with schema format
        type_labels = {
            'action': ('PHYSICAL ACTIONS', '💪'),
            'movement': ('MOVEMENT/POSITIONING', '🚶'),
            'verbal': ('VERBAL EXCHANGES', '💬'),
        }
        
        has_camera_friendly = any(camera_friendly_by_type.values())
        if has_camera_friendly:
            lines.append("RECORDED EVENTS (Camera-Friendly)")
            lines.append("─" * 70)
            
            for etype, (label, icon) in type_labels.items():
                if camera_friendly_by_type.get(etype):
                    lines.append(f"  {icon} {label}:")
                    for event_line in camera_friendly_by_type[etype]:
                        lines.append(f"      • {event_line}")
                    lines.append("")
            
            # Any other types
            for etype, event_lines in camera_friendly_by_type.items():
                if etype not in type_labels and event_lines:
                    lines.append(f"  📋 {etype.upper()}:")
                    for event_line in event_lines:
                        lines.append(f"      • {event_line}")
                    lines.append("")
        
        # V5: Events with unresolved actors (need more context)
        if no_actor_events:
            lines.append("EVENTS (ACTOR UNRESOLVED)")
            lines.append("─" * 70)
            for desc in no_actor_events[:10]:  # Limit to 10
                lines.append(f"  ⚠️ {desc[:80]}...")
            if len(no_actor_events) > 10:
                lines.append(f"  ... and {len(no_actor_events) - 10} more")
            lines.append("")
        
        # Render interpretive events with attribution
        if interpretive_events:
            lines.append("REPORTER'S CHARACTERIZATIONS (of events)")
            lines.append("─" * 70)
            for desc in interpretive_events:
                lines.append(f"  • Reporter describes: {desc[:100]}...")
            lines.append("")
    
    # === V5: RAW NEUTRALIZED NARRATIVE ===
    if rendered_text:
        lines.append("─" * 70)
        lines.append("")
        lines.append("RAW NEUTRALIZED NARRATIVE (AUTO-GENERATED)")
        lines.append("─" * 70)
        lines.append("⚠️ This is machine-generated neutralization. Review for accuracy.")
        lines.append("")
        lines.append(rendered_text)
        lines.append("")
    
    lines.append("═" * 70)
    
    return "\n".join(lines)
