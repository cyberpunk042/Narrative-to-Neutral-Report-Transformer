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

from typing import Dict, List, Any, Set
from collections import defaultdict


# V6: Section Registry to prevent duplicate sections
class SectionRegistry:
    """Track rendered sections to prevent duplicates."""
    
    _rendered: Set[str] = set()
    
    @classmethod
    def can_render(cls, section_name: str) -> bool:
        """Check if section can be rendered (not already done)."""
        if section_name in cls._rendered:
            return False
        cls._rendered.add(section_name)
        return True
    
    @classmethod
    def reset(cls) -> None:
        """Reset for a new render."""
        cls._rendered.clear()


def format_structured_output(
    rendered_text: str,
    atomic_statements: List[Any],
    entities: List[Any],
    events: List[Any],
    identifiers: List[Any],
    metadata: Dict[str, Any] = None,
    # V6: Timeline and gap data (optional for backward compatibility)
    timeline: List[Any] = None,
    time_gaps: List[Any] = None,
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
        timeline: V6 - Optional list of TimelineEntry objects
        time_gaps: V6 - Optional list of TimeGap objects
    
    Returns:
        Plain text formatted as official report
    """
    # V6: Reset section registry for this render
    SectionRegistry.reset()
    
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
            
            # =====================================================================
            # V6: Officer identification with linked badges
            # =====================================================================
            # Use badge_number field on Entity for proper linkage
            # =====================================================================
            officer_titles = {'officer', 'sergeant', 'detective', 'lieutenant', 'deputy', 'captain'}
            
            # Build officer list from entities (with linked badges)
            officer_lines = []
            linked_badges = set()
            
            if entities:
                for entity in entities:
                    if entity.label and any(t in entity.label.lower() for t in officer_titles):
                        if entity.badge_number:
                            officer_lines.append(f"    • {entity.label} (Badge #{entity.badge_number})")
                            linked_badges.add(entity.badge_number)
                        else:
                            officer_lines.append(f"    • {entity.label}")
            
            # Add any unlinked badges from identifiers
            badges = ident_by_type.get('badge_number', [])
            unlinked_badges = [b for b in badges if b not in linked_badges]
            
            if officer_lines or unlinked_badges:
                lines.append("  OFFICER IDENTIFICATION:")
                for line in officer_lines:
                    lines.append(line)
                for badge in unlinked_badges:
                    lines.append(f"    • Badge #{badge} (officer unknown)")
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
        
        # =====================================================================
        # V6: SOURCE-DERIVED INFORMATION with Provenance Validation
        # =====================================================================
        # Uses VERIFIED_HAS_EVIDENCE invariant to ensure honest status labels.
        # =====================================================================
        if source_derived:
            from nnrt.validation import check_verified_has_evidence
            
            lines.append("SOURCE-DERIVED INFORMATION")
            lines.append("─" * 70)
            lines.append("  ⚠️ The following claims require external provenance verification:")
            lines.append("")
            
            for idx, text in enumerate(source_derived[:10], 1):
                lines.append(f"  [{idx}] CLAIM: {text[:100]}{'...' if len(text) > 100 else ''}")
                
                # Get provenance from atomic_statements
                source_type = "Reporter"
                prov_status = "Needs Provenance"
                
                if atomic_statements:
                    for stmt in atomic_statements:
                        if hasattr(stmt, 'text') and stmt.text.strip() == text.strip():
                            source_type = getattr(stmt, 'source_type', 'reporter').title()
                            raw_status = getattr(stmt, 'provenance_status', 'needs_provenance')
                            
                            # V6: Map to honest display labels
                            status_labels = {
                                'verified': 'Verified ✅',           # Only with external evidence
                                'cited': 'Cited (unverified)',      # Has attribution but not verified
                                'self_attested': 'Self-Attested',   # Reporter's word only
                                'inference': 'Inference',           # Reporter's interpretation
                                'needs_provenance': 'Needs Provenance ⚠️',
                                'missing': 'Needs Provenance ⚠️',
                            }
                            prov_status = status_labels.get(raw_status, f'{raw_status.title()} ⚠️')
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
    # V6: SELF-REPORTED STATE with Medical Content Filtering
    # =========================================================================
    # Medical provider content (Dr., Nurse documented/diagnosed) goes to
    # MEDICAL_FINDINGS, not SELF-REPORTED.
    # =========================================================================
    
    def _is_medical_provider_content(text: str) -> bool:
        """Check if content is from a medical provider (should go to MEDICAL_FINDINGS)."""
        text_lower = text.lower()
        providers = ['dr.', 'dr ', 'doctor', 'nurse', 'emt', 'paramedic', 'physician', 'therapist']
        medical_verbs = ['documented', 'diagnosed', 'noted', 'observed', 'confirmed', 'stated that my injuries']
        
        has_provider = any(p in text_lower for p in providers)
        has_verb = any(v in text_lower for v in medical_verbs)
        
        return has_provider and has_verb
    
    # Collect medical content that needs routing
    medical_content_from_self_report = []
    
    # Acute state (during incident)
    if statements_by_epistemic.get('state_acute'):
        non_medical = [t for t in statements_by_epistemic['state_acute'] if not _is_medical_provider_content(t)]
        medical_content_from_self_report.extend([t for t in statements_by_epistemic['state_acute'] if _is_medical_provider_content(t)])
        
        if non_medical:
            lines.append("SELF-REPORTED STATE (ACUTE - During Incident)")
            lines.append("─" * 70)
            for text in non_medical:
                lines.append(f"  • Reporter reports: {text}")
            lines.append("")
    
    # Physical injuries - CRITICAL: filter out medical provider content
    if statements_by_epistemic.get('state_injury'):
        non_medical = [t for t in statements_by_epistemic['state_injury'] if not _is_medical_provider_content(t)]
        medical_content_from_self_report.extend([t for t in statements_by_epistemic['state_injury'] if _is_medical_provider_content(t)])
        
        if non_medical:
            lines.append("SELF-REPORTED INJURY (Physical)")
            lines.append("─" * 70)
            for text in non_medical:
                lines.append(f"  • Reporter reports: {text}")
            lines.append("")
    
    # Psychological after-effects
    if statements_by_epistemic.get('state_psychological'):
        non_medical = [t for t in statements_by_epistemic['state_psychological'] if not _is_medical_provider_content(t)]
        medical_content_from_self_report.extend([t for t in statements_by_epistemic['state_psychological'] if _is_medical_provider_content(t)])
        
        if non_medical:
            lines.append("SELF-REPORTED STATE (Psychological)")
            lines.append("─" * 70)
            for text in non_medical:
                lines.append(f"  • Reporter reports: {text}")
            lines.append("")
    
    # Socioeconomic impact
    if statements_by_epistemic.get('state_socioeconomic'):
        non_medical = [t for t in statements_by_epistemic['state_socioeconomic'] if not _is_medical_provider_content(t)]
        medical_content_from_self_report.extend([t for t in statements_by_epistemic['state_socioeconomic'] if _is_medical_provider_content(t)])
        
        if non_medical:
            lines.append("SELF-REPORTED IMPACT (Socioeconomic)")
            lines.append("─" * 70)
            for text in non_medical:
                lines.append(f"  • Reporter reports: {text}")
            lines.append("")
    
    # General self-report (fallback for non-categorized)
    if statements_by_epistemic.get('self_report'):
        non_medical = [t for t in statements_by_epistemic['self_report'] if not _is_medical_provider_content(t)]
        medical_content_from_self_report.extend([t for t in statements_by_epistemic['self_report'] if _is_medical_provider_content(t)])
        
        if non_medical:
            lines.append("SELF-REPORTED STATE (General)")
            lines.append("─" * 70)
            for text in non_medical:
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
    # V6: MEDICAL FINDINGS - doctor statements, diagnoses
    # =========================================================================
    # Includes content from epistemic type + content routed from SELF-REPORTED
    # =========================================================================
    all_medical = list(statements_by_epistemic.get('medical_finding', []))
    all_medical.extend(medical_content_from_self_report)
    
    if all_medical:
        lines.append("MEDICAL FINDINGS (as reported by Reporter)")
        lines.append("─" * 70)
        lines.append("  ℹ️ Medical provider statements cited by Reporter")
        lines.append("  Status: Cited (no medical record attached)")
        lines.append("")
        
        seen = set()
        for text in all_medical:
            # Dedupe
            if text in seen:
                continue
            seen.add(text)
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
    
    # =========================================================================
    # V6: PRESERVED QUOTES with Invariant Validation
    # =========================================================================
    # Quotes MUST have resolved speakers to render in main section.
    # Quotes with Unknown/pronoun speakers go to quarantine.
    # =========================================================================
    
    if statements_by_type.get('quote') or (hasattr(metadata, 'speech_acts') if metadata else False):
        from nnrt.validation import check_quote_has_speaker, InvariantSeverity
        
        validated_quotes = []     # Pass speaker validation
        quarantined_quotes = []   # Fail speaker validation
        
        # Process speech_acts if available
        if metadata and hasattr(metadata, 'speech_acts') and metadata.speech_acts:
            for sa in metadata.speech_acts:
                # Validate speaker
                result = check_quote_has_speaker(sa)
                
                if result.passes:
                    validated_quotes.append(sa)
                else:
                    quarantined_quotes.append((sa, [result]))
        
        # Also process statement-based quotes
        for text in statements_by_type.get('quote', []):
            # Create a mock object for validation
            class MockQuote:
                speaker_label = None
                content = text
            
            # Try to extract speaker from text
            if " said " in text:
                parts = text.split(" said ", 1)
                MockQuote.speaker_label = parts[0].strip()[:50]
                MockQuote.content = parts[1] if len(parts) > 1 else text
            elif " yelled " in text:
                parts = text.split(" yelled ", 1)
                MockQuote.speaker_label = parts[0].strip()[:50]
                MockQuote.content = parts[1] if len(parts) > 1 else text
            elif " shouted " in text:
                parts = text.split(" shouted ", 1)
                MockQuote.speaker_label = parts[0].strip()[:50]
                MockQuote.content = parts[1] if len(parts) > 1 else text
            else:
                MockQuote.speaker_label = None
                MockQuote.content = text
            
            mock = MockQuote()
            result = check_quote_has_speaker(mock)
            
            if result.passes:
                validated_quotes.append(mock)
            else:
                quarantined_quotes.append((mock, [result]))
        
        # Render validated quotes
        if validated_quotes:
            lines.append("PRESERVED QUOTES (SPEAKER RESOLVED)")
            lines.append("─" * 70)
            
            seen = set()
            for quote in validated_quotes:
                speaker = getattr(quote, 'speaker_label', 'Unknown')
                verb = getattr(quote, 'speech_verb', 'said')
                content = getattr(quote, 'content', '')
                is_nested = getattr(quote, 'is_nested', False)
                
                # Dedupe
                if content in seen:
                    continue
                seen.add(content)
                
                # Clean content
                if content.startswith('"') and content.endswith('"'):
                    content = content[1:-1]
                
                if is_nested:
                    lines.append(f"  ⚠️ {speaker} {verb}: {content}")
                    lines.append(f"      (nested quote - attribution may need review)")
                else:
                    lines.append(f"  • {speaker} {verb}: {content}")
            
            lines.append("")
        
        # Render quarantined quotes
        if quarantined_quotes:
            lines.append("QUOTES (SPEAKER UNRESOLVED)")
            lines.append("─" * 70)
            lines.append("  ⚠️ These quotes could not be attributed to a speaker:")
            lines.append("")
            
            for quote, failures in quarantined_quotes[:10]:  # Limit
                content = getattr(quote, 'content', str(quote))[:60]
                issues = "; ".join(f.message for f in failures)
                
                lines.append(f'  ❌ "{content}..."')
                lines.append(f"      Issues: {issues}")
                lines.append("")
            
            if len(quarantined_quotes) > 10:
                lines.append(f"  ... and {len(quarantined_quotes) - 10} more unattributed quotes")
                lines.append("")
        
        # Validation stats
        total = len(validated_quotes) + len(quarantined_quotes)
        if total > 0:
            passed = len(validated_quotes)
            lines.append(f"  📊 Quote Validation: {passed}/{total} passed ({100*passed//total}%)")
            lines.append("")
    
    # =========================================================================
    # V6: EVENT VALIDATION (Quarantine Only)
    # =========================================================================
    # CRITICAL: The "validated events" section was generating incorrect facts
    # (wrong actor attributions, misattributed actions). Until event extraction
    # is fixed upstream, we ONLY show quarantine stats - no validated list.
    # =========================================================================
    
    if events:
        from nnrt.validation import (
            check_event_has_actor,
            check_event_not_fragment,
            check_event_has_verb,
            InvariantSeverity,
        )
        
        # Validate and categorize events
        validated_events = []      # Pass all HARD invariants
        quarantined_events = []    # Fail one or more HARD invariants
        
        for event in events:
            # Check all event invariants
            results = [
                check_event_has_actor(event),
                check_event_not_fragment(event),
                check_event_has_verb(event),
            ]
            
            # Separate HARD failures from SOFT warnings
            hard_failures = [r for r in results if not r.passes and r.severity == InvariantSeverity.HARD]
            
            if hard_failures:
                quarantined_events.append((event, hard_failures))
            else:
                validated_events.append(event)
        
        # NOTE: We do NOT render validated_events list because event extraction
        # is generating incorrect actor assignments. This would introduce
        # factual errors into the report. Example errors we were seeing:
        # - "Officer Rodriguez call 911" (was actually Patricia Chen)
        # - "Officer Jenkins document bruises" (was medical provider)
        # - "Officer Rodriguez receive a letter" (was Reporter)
        #
        # The validated list will be restored when p34_extract_events is fixed.
        
        # Render quarantine info only
        if quarantined_events:
            lines.append("EVENTS (ACTOR UNRESOLVED)")
            lines.append("─" * 70)
            lines.append("  ⚠️ These events could not be validated for neutral rendering:")
            lines.append("")
            
            for event, failures in quarantined_events[:10]:  # Limit display
                desc = getattr(event, 'description', str(event))[:80]
                issues = "; ".join(f.message for f in failures)
                
                lines.append(f"  ❌ {desc}")
                lines.append(f"      Issues: {issues}")
                lines.append("")
            
            if len(quarantined_events) > 10:
                lines.append(f"  ... and {len(quarantined_events) - 10} more events with unresolved actors")
                lines.append("")
        
        # Validation stats
        total = len(events)
        passed = len(validated_events)
        failed = len(quarantined_events)
        if total > 0:
            lines.append(f"  📊 Event Validation: {passed}/{total} passed ({100*passed//total}%)")
            lines.append(f"  ⚠️ Validated events list disabled pending event extraction fixes")
            lines.append("")
    
    # ==========================================================================
    # V6: RECONSTRUCTED TIMELINE SECTION
    # ==========================================================================
    if timeline and len(timeline) > 0:
        lines.append("─" * 70)
        lines.append("")
        lines.append("RECONSTRUCTED TIMELINE")
        lines.append("─" * 70)
        lines.append("Events ordered by reconstructed chronology. Day offsets show multi-day span.")
        lines.append("")
        
        # Group entries by day
        entries_by_day = {}
        for entry in timeline:
            day = getattr(entry, 'day_offset', 0)
            if day not in entries_by_day:
                entries_by_day[day] = []
            entries_by_day[day].append(entry)
        
        # Map event IDs to descriptions
        event_map = {e.id: e for e in events} if events else {}
        
        # Gap map for investigation markers
        gap_map = {}
        investigation_count = 0
        if time_gaps:
            for gap in time_gaps:
                gap_map[gap.before_entry_id] = gap
                if getattr(gap, 'requires_investigation', False):
                    investigation_count += 1
        
        # Render each day
        for day_offset in sorted(entries_by_day.keys()):
            day_entries = entries_by_day[day_offset]
            
            # Day header
            if day_offset == 0:
                day_label = "INCIDENT DAY (Day 0)"
            elif day_offset == 1:
                day_label = "NEXT DAY (Day 1)"
            elif day_offset < 7:
                day_label = f"DAY {day_offset}"
            elif day_offset < 30:
                weeks = day_offset // 7
                day_label = f"~{weeks} WEEK{'S' if weeks > 1 else ''} LATER (Day {day_offset})"
            elif day_offset < 100:
                months = day_offset // 30
                day_label = f"~{months} MONTH{'S' if months > 1 else ''} LATER (Day {day_offset})"
            else:
                months = day_offset // 30
                day_label = f"~{months} MONTHS LATER (Day {day_offset})"
            
            lines.append(f"  ┌─── {day_label} ───")
            lines.append("  │")
            
            for entry in day_entries:
                # Get event description
                event = event_map.get(entry.event_id) if entry.event_id else None
                desc = getattr(event, 'description', entry.event_id or 'Unknown event')[:50] if event else entry.event_id or 'Unknown'
                
                # Time info
                time_info = ""
                if entry.normalized_time:
                    # Convert T23:30:00 to 11:30 PM display
                    time_val = entry.normalized_time
                    try:
                        import re
                        match = re.match(r'T(\d{2}):(\d{2})', time_val)
                        if match:
                            h, m = int(match.group(1)), int(match.group(2))
                            ampm = "AM" if h < 12 else "PM"
                            h = h % 12 or 12
                            time_info = f"[{h}:{m:02d} {ampm}] "
                    except:
                        time_info = f"[{time_val}] "
                elif entry.absolute_time:
                    time_info = f"[{entry.absolute_time}] "
                elif entry.relative_time:
                    time_info = f"[{entry.relative_time}] "
                
                # Source indicator
                source = getattr(entry, 'time_source', None)
                source_icon = ""
                if source:
                    source_val = source.value if hasattr(source, 'value') else str(source)
                    if source_val == 'explicit':
                        source_icon = "⏱️"  # Explicit time
                    elif source_val == 'relative':
                        source_icon = "⟳"  # Relative/derived
                    else:
                        source_icon = "○"  # Inferred
                
                # Check for gap before this entry
                gap_marker = ""
                if entry.id in gap_map:
                    gap = gap_map[entry.id]
                    if getattr(gap, 'requires_investigation', False):
                        gap_marker = " ⚠️ "
                
                lines.append(f"  │  {source_icon} {time_info}{gap_marker}{desc}")
            
            lines.append("  │")
        
        lines.append("  └─────────────────────────────")
        
        # Legend
        lines.append("")
        lines.append("  Legend: ⏱️=explicit time  ⟳=relative time  ○=inferred  ⚠️=gap needs investigation")
        lines.append("")
        
        # Investigation questions if any
        if investigation_count > 0 and time_gaps:
            lines.append("  ⚠️ TIMELINE GAPS REQUIRING INVESTIGATION:")
            lines.append("")
            
            gap_num = 1
            for gap in time_gaps:
                if getattr(gap, 'requires_investigation', False):
                    question = getattr(gap, 'suggested_question', 'What happened during this gap?')
                    gap_type = getattr(gap, 'gap_type', None)
                    gap_type_val = gap_type.value if hasattr(gap_type, 'value') else str(gap_type)
                    
                    lines.append(f"    {gap_num}. [{gap_type_val.upper()}] {question}")
                    gap_num += 1
                    
                    if gap_num > 5:  # Limit display
                        remaining = investigation_count - 5
                        if remaining > 0:
                            lines.append(f"    ... and {remaining} more gaps to investigate")
                        break
            
            lines.append("")
        
        # Summary stats
        explicit_count = sum(1 for e in timeline if getattr(e, 'time_source', None) and 
                           (getattr(e.time_source, 'value', str(e.time_source)) == 'explicit'))
        relative_count = sum(1 for e in timeline if getattr(e, 'time_source', None) and 
                           (getattr(e.time_source, 'value', str(e.time_source)) == 'relative'))
        inferred_count = len(timeline) - explicit_count - relative_count
        
        lines.append(f"  📊 Timeline: {len(timeline)} events across {len(entries_by_day)} day(s)")
        lines.append(f"      ⏱️ Explicit times: {explicit_count}  ⟳ Relative: {relative_count}  ○ Inferred: {inferred_count}")
        if investigation_count > 0:
            lines.append(f"      ⚠️ Gaps needing investigation: {investigation_count}")
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
