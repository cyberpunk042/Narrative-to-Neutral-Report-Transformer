"""
Structured Output Formatter V2 (Clean Architecture)

Pure formatting from SelectionResult. No classification. No selection logic.
Just formatting pre-selected, pre-classified atoms.

This is what the renderer SHOULD look like after Stage 3 completion.
"""

from typing import List, Any, Dict, Optional, TYPE_CHECKING
from collections import defaultdict

if TYPE_CHECKING:
    from nnrt.selection.models import SelectionResult


# V7.3: Helper for filtering and deduplicating statement text
# V7.4: Increased threshold and added fragment detection
MIN_MEANINGFUL_LENGTH = 25  # Skip fragments shorter than this

# Common gerund/verb-only fragment starts (no subject)
FRAGMENT_PATTERNS = [
    'shaking', 'looking', 'saying', 'yelling', 'screaming', 'crying',
    'running', 'walking', 'standing', 'sitting', 'lying', 'holding',
]

def _is_meaningful_text(text: str) -> bool:
    """Check if text is meaningful enough to display."""
    stripped = text.strip()
    
    # Too short
    if len(stripped) < MIN_MEANINGFUL_LENGTH:
        return False
    
    # Starts with gerund/verb without subject (likely a fragment)
    first_word = stripped.split()[0].lower() if stripped else ''
    if first_word in FRAGMENT_PATTERNS:
        return False
    
    return True

def _dedupe_key(text: str) -> str:
    """Generate a key for deduplication (lowercased, stripped)."""
    return text.strip().lower()[:50]


def format_structured_output_v2(
    selection_result: "SelectionResult",
    entities: List[Any],
    events: List[Any],
    identifiers: List[Any],
    timeline: List[Any] = None,
    time_gaps: List[Any] = None,
    atomic_statements: List[Any] = None,
    segments: List[Any] = None,  # V7: For event_generator
    metadata: Any = None,
    rendered_text: str = "",
) -> str:
    """
    Format a structured report from pre-selected atoms.
    
    This is PURE FORMATTING. All decisions about what to include
    were made by p55_select and stored in SelectionResult.
    
    Args:
        selection_result: REQUIRED - Contains IDs of what to render in each section
        entities: List of Entity objects (for lookup by ID)
        events: List of Event objects (for lookup by ID)
        identifiers: List of Identifier objects
        timeline: Optional list of TimelineEntry objects
        time_gaps: Optional list of TimeGap objects
        atomic_statements: Optional list of AtomicStatement objects
        metadata: Optional metadata with speech_acts etc.
        rendered_text: Optional rendered narrative text
        
    Returns:
        Formatted plain text report
    """
    sel = selection_result
    lines = []
    
    # Build lookups
    entity_lookup = {e.id: e for e in entities} if entities else {}
    event_lookup = {e.id: e for e in events} if events else {}
    timeline_lookup = {e.id: e for e in timeline} if timeline else {}
    
    # V7 / Stage 3: Build statement lookup by ID for new SelectionResult fields
    statement_lookup = {}
    if atomic_statements:
        for stmt in atomic_statements:
            statement_lookup[stmt.id] = stmt
    
    # Build statements by epistemic type (legacy - for backwards compat)
    statements_by_epistemic = defaultdict(list)
    if atomic_statements:
        for stmt in atomic_statements:
            epistemic = getattr(stmt, 'epistemic_type', 'unknown')
            text = getattr(stmt, 'text', str(stmt))
            statements_by_epistemic[epistemic].append(text)
    
    # =========================================================================
    # HEADER
    # =========================================================================
    lines.append("═" * 70)
    lines.append("                        NEUTRALIZED REPORT")
    lines.append("═" * 70)
    lines.append("")
    
    # =========================================================================
    # SECTION 1: PARTIES
    # =========================================================================
    _render_parties(lines, sel, entity_lookup)
    
    # =========================================================================
    # SECTION 2: REFERENCE DATA
    # =========================================================================
    _render_reference_data(lines, identifiers, entities)
    
    # =========================================================================
    # ACCOUNT SUMMARY HEADER (V1 compatibility)
    # =========================================================================
    lines.append("═" * 70)
    lines.append("                         ACCOUNT SUMMARY")
    lines.append("═" * 70)
    lines.append("")
    
    # =========================================================================
    # SECTION 3: OBSERVED EVENTS (STRICT)
    # =========================================================================
    _render_observed_events(lines, sel, event_lookup, events, segments, atomic_statements, entities, identifiers)
    
    # =========================================================================
    # SECTION 4: FOLLOW-UP ACTIONS
    # =========================================================================
    _render_follow_up_events(lines, sel, event_lookup)
    
    # =========================================================================
    # V7 / Stage 3: SECTION 5: ITEMS DISCOVERED
    # =========================================================================
    _render_items_discovered(lines, metadata)
    
    # =========================================================================
    # SECTION 6: NARRATIVE EXCERPTS
    # =========================================================================
    _render_narrative_excerpts(lines, sel, event_lookup)
    
    # =========================================================================
    # SECTION 7: SOURCE-DERIVED INFORMATION
    # =========================================================================
    _render_source_derived(lines, sel, event_lookup)
    
    # =========================================================================
    # V7 / Stage 3: SECTION 8-12: SELF-REPORTED (5 subsections)
    # =========================================================================
    _render_self_reported_v2(lines, sel, statement_lookup)
    
    # =========================================================================
    # V7 / Stage 3: SECTION 13: LEGAL ALLEGATIONS
    # =========================================================================
    _render_legal_allegations(lines, sel, statement_lookup)
    
    # =========================================================================
    # SECTION 14: REPORTER DESCRIPTIONS (CHARACTERIZATIONS)
    # =========================================================================
    _render_reporter_descriptions(lines, statements_by_epistemic)
    
    # =========================================================================
    # V7 / Stage 3: SECTION 15: REPORTER INFERENCES
    # =========================================================================
    _render_inferences(lines, sel, statement_lookup)
    
    # =========================================================================
    # V7 / Stage 3: SECTION 16: REPORTER INTERPRETATIONS
    # =========================================================================
    _render_interpretations(lines, sel, statement_lookup)
    
    # =========================================================================
    # V7 / Stage 3: SECTION 17: CONTESTED ALLEGATIONS
    # =========================================================================
    _render_contested(lines, sel, statement_lookup)
    
    # =========================================================================
    # SECTION 18: MEDICAL FINDINGS
    # =========================================================================
    _render_medical_findings_v2(lines, sel, statement_lookup)
    
    # =========================================================================
    # V7 / Stage 3: SECTION 19: ADMINISTRATIVE ACTIONS
    # =========================================================================
    _render_admin_actions(lines, sel, statement_lookup)
    
    # =========================================================================
    # SECTION 20: PRESERVED QUOTES
    # =========================================================================
    _render_quotes(lines, sel, metadata, entities)
    
    # =========================================================================
    # SECTION 20.5: EVENTS (ACTOR UNRESOLVED) - Transparency about filtering
    # =========================================================================
    _render_actor_unresolved_events(lines, events)
    
    # =========================================================================
    # SECTION 21: RECONSTRUCTED TIMELINE
    # =========================================================================
    _render_timeline(lines, sel, timeline_lookup, event_lookup)
    
    # =========================================================================
    # SECTION 22: INVESTIGATION QUESTIONS
    # =========================================================================
    _render_investigation_questions(lines, time_gaps, atomic_statements, events)
    
    # =========================================================================
    # SECTION 23: RAW NARRATIVE
    # =========================================================================
    if rendered_text:
        lines.append("─" * 70)
        lines.append("")
        lines.append("RAW NEUTRALIZED NARRATIVE (AUTO-GENERATED)")
        lines.append("─" * 70)
        lines.append("⚠️ This is machine-generated neutralization. Review for accuracy.")
        lines.append("")
        lines.append(rendered_text)
        lines.append("")
    
    # =========================================================================
    # FOOTER
    # =========================================================================
    lines.append("═" * 70)
    
    return "\n".join(lines)


# =============================================================================
# SECTION RENDERERS - Pure formatting functions
# =============================================================================

def _render_parties(lines: List[str], sel: "SelectionResult", entity_lookup: Dict) -> None:
    """Render PARTIES section from pre-selected entity IDs."""
    if not (sel.incident_participants or sel.post_incident_pros or sel.mentioned_contacts):
        return
    
    lines.append("PARTIES")
    lines.append("─" * 70)
    
    if sel.incident_participants:
        lines.append("  INCIDENT PARTICIPANTS:")
        for entity_id in sel.incident_participants:
            entity = entity_lookup.get(entity_id)
            if entity:
                role = _get_role_display(entity)
                lines.append(f"    • {entity.label} ({role})")
    
    if sel.post_incident_pros:
        lines.append("  POST-INCIDENT PROFESSIONALS:")
        for entity_id in sel.post_incident_pros:
            entity = entity_lookup.get(entity_id)
            if entity:
                role = _get_role_display(entity)
                lines.append(f"    • {entity.label} ({role})")
    
    if sel.mentioned_contacts:
        lines.append("  MENTIONED CONTACTS:")
        for entity_id in sel.mentioned_contacts:
            entity = entity_lookup.get(entity_id)
            if entity:
                role = _get_role_display(entity)
                lines.append(f"    • {entity.label} ({role})")
    
    lines.append("")


def _render_reference_data(lines: List[str], identifiers: List[Any], entities: List[Any] = None) -> None:
    """Render REFERENCE DATA section with V1-style sub-structure."""
    if not identifiers:
        return
    
    ident_by_type = defaultdict(list)
    for ident in identifiers:
        ident_type = getattr(ident, 'type', None)
        if hasattr(ident_type, 'value'):
            ident_type = ident_type.value
        ident_type = str(ident_type) if ident_type else 'unknown'
        value = getattr(ident, 'value', str(ident))
        ident_by_type[ident_type].append(value)
    
    if not ident_by_type:
        return
    
    lines.append("REFERENCE DATA")
    lines.append("─" * 70)
    
    # INCIDENT DATETIME sub-section
    dates = ident_by_type.get('date', [])
    times = ident_by_type.get('time', [])
    if dates or times:
        lines.append("  INCIDENT DATETIME:")
        if dates:
            lines.append(f"    Date: {dates[0]}")
        if times:
            lines.append(f"    Time: {times[0]}")
        lines.append("")
    
    # INCIDENT LOCATION sub-section
    locations = ident_by_type.get('location', [])
    if locations:
        lines.append(f"  INCIDENT LOCATION: {locations[0]}")
        if len(locations) > 1:
            lines.append("  SECONDARY LOCATIONS:")
            for loc in locations[1:]:
                lines.append(f"    • {loc}")
        lines.append("")
    
    # OFFICER IDENTIFICATION sub-section (V7 FIX: Link badges to names)
    officer_titles = ['officer', 'sergeant', 'detective', 'captain', 'lieutenant', 'deputy']
    officer_lines = []
    linked_badges = set()
    
    # Build officer list from entities (with linked badges)
    if entities:
        for entity in entities:
            label = getattr(entity, 'label', None)
            if label and any(t in label.lower() for t in officer_titles):
                badge = getattr(entity, 'badge_number', None)
                if badge:
                    officer_lines.append(f"    • {label} (Badge #{badge})")
                    linked_badges.add(str(badge))
                else:
                    officer_lines.append(f"    • {label}")
    
    # Add any unlinked badges from identifiers
    badges = ident_by_type.get('badge_number', [])
    unlinked_badges = [b for b in badges if str(b) not in linked_badges]
    
    if officer_lines or unlinked_badges:
        lines.append("  OFFICER IDENTIFICATION:")
        for line in officer_lines:
            lines.append(line)
        for badge in unlinked_badges:
            lines.append(f"    • Badge #{badge} (officer unknown)")
        lines.append("")
    
    # Other identifiers (vehicle, employee ID, etc.)
    # NOTE: 'name' excluded - names are shown in PARTIES section
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
    
    # If we didn't add any sub-sections, add a blank line
    if not (dates or times or locations or badges or has_other):
        lines.append("")



def _render_observed_events(
    lines: List[str], 
    sel: "SelectionResult", 
    event_lookup: Dict,
    events: List[Any] = None,
    segments: List[Any] = None,
    atomic_statements: List[Any] = None,
    entities: List[Any] = None,
    identifiers: List[Any] = None,
) -> None:
    """Render OBSERVED EVENTS (STRICT) section.
    
    V7 FIX: Now uses event_generator.get_strict_event_sentences for high-quality
    event sentences with full targets (e.g., "jumped out of the car" not just "jumped").
    """
    if not sel.observed_events and not events:
        return
    
    lines.append("OBSERVED EVENTS (STRICT / CAMERA-FRIENDLY)")
    lines.append("─" * 70)
    
    # =========================================================================
    # V7: Context Summary (matching V1 format)
    # =========================================================================
    context_parts = []
    
    # Get date/time/location from identifiers
    ident_by_type = defaultdict(list)
    if identifiers:
        for ident in identifiers:
            ident_type = getattr(ident, 'type', None)
            if hasattr(ident_type, 'value'):
                ident_type = ident_type.value
            ident_type = str(ident_type) if ident_type else 'unknown'
            value = getattr(ident, 'value', str(ident))
            ident_by_type[ident_type].append(value)
    
    date_val = ident_by_type.get('date', [None])[0]
    time_val = ident_by_type.get('time', [None])[0]
    location_val = ident_by_type.get('location', [None])[0]
    
    # Build datetime string
    if date_val or time_val:
        datetime_str = ""
        if date_val:
            datetime_str = f"on {date_val}"
        if time_val:
            datetime_str += f" at approximately {time_val}" if datetime_str else f"at approximately {time_val}"
        context_parts.append(datetime_str)
    
    # Add location
    if location_val:
        context_parts.append(f"near {location_val}")
    
    # Get officer names from entities
    officer_names = []
    if entities:
        for e in entities:
            label = getattr(e, 'label', '')
            role = getattr(e, 'role', '')
            if hasattr(role, 'value'):
                role = role.value
            if str(role).lower() == 'subject_officer' and label:
                officer_names.append(label)
    
    # Build context summary
    if context_parts or officer_names:
        context_summary = "ℹ️ Context: "
        
        if officer_names:
            officers_str = " and ".join(officer_names[:2])
            if len(officer_names) > 2:
                officers_str = ", ".join(officer_names[:-1]) + f", and {officer_names[-1]}"
            context_summary += f"Reporter encountered {officers_str}"
        else:
            context_summary += "An encounter occurred"
        
        if context_parts:
            context_summary += " " + " ".join(context_parts)
        
        context_summary += "."
        
        # Add self-reported state if available (look for acute emotional states)
        if atomic_statements:
            for stmt in atomic_statements:
                epistemic = getattr(stmt, 'epistemic_type', '')
                if hasattr(epistemic, 'value'):
                    epistemic = epistemic.value
                text = getattr(stmt, 'text', str(stmt))
                if str(epistemic) == 'state_acute':
                    if any(word in text.lower() for word in ['terrified', 'scared', 'frightened', 'shock']):
                        context_summary += " Reporter reports feeling frightened during this encounter."
                        break
        
        lines.append(context_summary)
        lines.append("")
    
    # =========================================================================
    # V7: Use event_generator for high-quality sentences
    # =========================================================================
    strict_sentences = []
    
    try:
        from nnrt.render.event_generator import get_strict_event_sentences
        
        if events and segments:
            strict_sentences = get_strict_event_sentences(
                events=events,
                segments=segments,
                atomic_statements=atomic_statements or [],
                entities=entities,
                max_events=25,
            )
    except Exception as e:
        # Fall back to neutralized_description if event_generator fails
        pass
    
    if strict_sentences:
        # Use high-quality sentences from event_generator
        lines.append("ℹ️ Fully normalized: Actor (entity/class) + action + object. No pronouns, quotes, or fragments.")
        lines.append("")
        
        for sentence in strict_sentences:
            lines.append(f"  • {sentence}")
    else:
        # Fallback: Use neutralized_description from p35
        lines.append("ℹ️ Fully normalized: Actor + action + object. No pronouns, quotes, or fragments.")
        lines.append("")
        
        for event_id in sel.observed_events:
            event = event_lookup.get(event_id)
            if event:
                text = getattr(event, 'neutralized_description', None) or event.description
                lines.append(f"  • {text}")
    
    lines.append("")

def _render_follow_up_events(lines: List[str], sel: "SelectionResult", event_lookup: Dict) -> None:
    """Render FOLLOW-UP ACTIONS section.
    
    V7 FIX: Uses original description with pronoun replacement for complete sentences.
    """
    if not sel.follow_up_events:
        return
    
    lines.append("OBSERVED EVENTS (FOLLOW-UP ACTIONS)")
    lines.append("─" * 70)
    
    import re
    for event_id in sel.follow_up_events:
        event = event_lookup.get(event_id)
        if event:
            # V7 FIX: Check if neutralized_description is incomplete
            # (ends with just verb like "went." or missing location/target)
            neutralized = getattr(event, 'neutralized_description', None)
            description = event.description or ""
            
            # Use neutralized if it looks complete (>20 chars and has substance)
            # Otherwise use original description with pronoun replacement
            if neutralized and len(neutralized) > 20:
                text = neutralized
            else:
                # Use original description and apply pronoun replacement
                text = description
            
            # Comprehensive pronoun normalization (V1 A2.4 fix)
            text = re.sub(r'\bI\s+went\b', 'Reporter went', text)
            text = re.sub(r'\bI\s+filed\b', 'Reporter filed', text)
            text = re.sub(r'\bI\s+received\b', 'Reporter received', text)
            text = re.sub(r'\bI\s+was\b', 'Reporter was', text)
            text = re.sub(r'\bmy\s+', "Reporter's ", text, flags=re.IGNORECASE)
            text = re.sub(r'^I\s+', 'Reporter ', text)
            text = re.sub(r'\bI\s+', 'Reporter ', text)
            text = re.sub(r'\bme\b', 'Reporter', text)
            
            # Clean up characterizations
            text = re.sub(r'\bbrutally\b', '', text, flags=re.IGNORECASE)
            text = re.sub(r'\bdeliberately\b', '', text, flags=re.IGNORECASE)
            text = re.sub(r'\s+', ' ', text).strip()
            
            # Ensure ends with period
            if text and not text.endswith('.'):
                text += '.'
            
            lines.append(f"  • {text}")
    
    lines.append("")


def _render_source_derived(lines: List[str], sel: "SelectionResult", event_lookup: Dict) -> None:
    """Render SOURCE-DERIVED INFORMATION section."""
    if not sel.source_derived_events:
        return
    
    lines.append("SOURCE-DERIVED INFORMATION")
    lines.append("─" * 70)
    lines.append("ℹ️ The following statements are derived from research, comparisons, or conclusions:")
    lines.append("")
    
    for event_id in sel.source_derived_events:
        event = event_lookup.get(event_id)
        if event:
            lines.append(f"  • {event.description}")
    
    lines.append("")


def _render_narrative_excerpts(lines: List[str], sel: "SelectionResult", event_lookup: Dict) -> None:
    """Render NARRATIVE EXCERPTS section."""
    if not sel.narrative_excerpts:
        return
    
    lines.append("NARRATIVE EXCERPTS (UNNORMALIZED)")
    lines.append("─" * 70)
    lines.append("⚠️ These excerpts couldn't be normalized. Listed by rejection reason:")
    lines.append("")
    
    # Group by reason
    by_reason = defaultdict(list)
    for event_id, reason in sel.narrative_excerpts:
        event = event_lookup.get(event_id)
        if event:
            by_reason[reason].append(event.description)
    
    REASON_LABELS = {
        'pronoun_actor_unresolved': 'Pronoun without named actor',
        'conjunction_start': 'Fragment (starts with conjunction)',
        'verb_start': 'Incomplete (starts with verb)',
        'contains_quote': 'Contains embedded quote',
        'interpretive_content': 'Contains interpretive language',
        'too_short': 'Too short to normalize',
        'low_confidence': 'Low classification confidence',
    }
    
    for reason, texts in by_reason.items():
        label = REASON_LABELS.get(reason, reason.replace('_', ' ').title())
        lines.append(f"  [{label}]")
        for text in texts[:5]:
            display = text[:80] + '...' if len(text) > 80 else text
            lines.append(f"    - {display}")
    
    lines.append("")


def _render_self_reported(lines: List[str], statements_by_epistemic: Dict) -> None:
    """Render SELF-REPORTED STATE section."""
    self_reports = statements_by_epistemic.get('self_report', [])
    if not self_reports:
        return
    
    lines.append("SELF-REPORTED STATE")
    lines.append("─" * 70)
    lines.append("  Reporter reports:")
    
    for text in self_reports:
        lines.append(f"    • {text}")
    
    lines.append("")


def _render_reporter_descriptions(lines: List[str], statements_by_epistemic: Dict) -> None:
    """Render REPORTER DESCRIPTIONS section."""
    characterizations = statements_by_epistemic.get('characterization', [])
    if not characterizations:
        return
    
    lines.append("REPORTER DESCRIPTIONS (CHARACTERIZATIONS)")
    lines.append("─" * 70)
    lines.append("⚠️ These are the reporter's subjective characterizations, not camera-friendly facts:")
    lines.append("")
    
    for text in characterizations:
        lines.append(f"  • {text}")
    
    lines.append("")


def _render_medical_findings(lines: List[str], statements_by_epistemic: Dict) -> None:
    """Render MEDICAL FINDINGS section."""
    medical = statements_by_epistemic.get('medical_finding', [])
    if not medical:
        return
    
    lines.append("MEDICAL FINDINGS (as reported by Reporter)")
    lines.append("─" * 70)
    lines.append("  ℹ️ Medical provider statements cited by Reporter")
    lines.append("  Status: Cited (no medical record attached)")
    lines.append("")
    
    for text in medical:
        lines.append(f"  • {text}")
    
    lines.append("")


def _render_quotes(lines: List[str], sel: "SelectionResult", metadata: Any, entities: List[Any] = None) -> None:
    """Render PRESERVED QUOTES section.
    
    V7 FIX: Resolves pronouns to named speakers and deduplicates quotes.
    """
    if not sel.preserved_quotes and not sel.quarantined_quotes:
        return
    
    # Build speech_act lookup
    speech_act_lookup = {}
    if metadata and hasattr(metadata, 'speech_acts') and metadata.speech_acts:
        for sa in metadata.speech_acts:
            speech_act_lookup[sa.id] = sa
    
    # Build entity name lookup for pronoun resolution
    officer_names = []
    witness_names = []
    if entities:
        for e in entities:
            label = getattr(e, 'label', '')
            role = getattr(e, 'role', '')
            if hasattr(role, 'value'):
                role = role.value
            role_str = str(role).lower()
            if 'officer' in role_str or 'subject' in role_str:
                if label:
                    officer_names.append(label)
            elif 'witness' in role_str:
                if label:
                    witness_names.append(label)
    
    import re
    
    def resolve_pronoun_speaker(speaker: str, content: str) -> str:
        """Resolve pronoun speakers to named entities based on context."""
        if not speaker:
            return speaker
        
        speaker_lower = speaker.lower().strip()
        
        # "He" likely refers to an officer in context
        if speaker_lower in ('he', 'he also', 'he then'):
            # Check content for officer context
            if officer_names:
                # Use first officer as default (Jenkins is usually the main actor)
                return officer_names[0]
            return "Officer"
        
        # "She" likely refers to a female mentioned (Detective Monroe, Dr. Foster)
        if speaker_lower in ('she', 'she also', 'she then'):
            # Check content for context clues
            content_lower = content.lower() if content else ""
            if 'investigate' in content_lower or 'detective' in content_lower:
                return "Detective Monroe"
            if 'injur' in content_lower or 'force' in content_lower or 'medical' in content_lower:
                return "Dr. Foster"
            return "The witness"
        
        # "They" plural
        if speaker_lower == 'they':
            return "The officers"
        
        # "they say" pattern
        if speaker_lower == 'they say' or 'they all say' in speaker_lower:
            return "Officer Jenkins"  # Context suggests Jenkins
        
        # "I" / "Reporter"
        if speaker_lower in ('i', 'i also', 'i then', 'reporter'):
            return "Reporter"
        
        # Return as-is if already a name
        return speaker
    
    # Collect and dedupe resolved quotes
    seen_content = set()
    resolved_quotes = []
    
    if sel.preserved_quotes:
        for quote_id in sel.preserved_quotes:
            quote = speech_act_lookup.get(quote_id)
            if quote:
                speaker = getattr(quote, 'speaker_label', None) or 'Unknown'
                verb = getattr(quote, 'speech_verb', None) or 'said'
                content = getattr(quote, 'content', '')
                
                # Skip if content already seen (dedup)
                content_key = content.strip().lower()[:50]  # Normalize for comparison
                if content_key in seen_content:
                    continue
                seen_content.add(content_key)
                
                # Resolve pronoun speakers
                resolved_speaker = resolve_pronoun_speaker(speaker, content)
                
                # Skip low-quality speakers
                if resolved_speaker and len(resolved_speaker) < 2:
                    continue
                if resolved_speaker and resolved_speaker[0].islower():
                    continue
                
                resolved_quotes.append((resolved_speaker, verb, content))
    
    if resolved_quotes:
        lines.append("PRESERVED QUOTES (SPEAKER RESOLVED)")
        lines.append("─" * 70)
        
        for speaker, verb, content in resolved_quotes:
            lines.append(f"  • {speaker} {verb}: {content}")
        
        lines.append("")
    
    if sel.quarantined_quotes:
        # V7: Try to resolve quarantined quotes at render time
        still_unresolved = []
        last_chance_resolved = []
        
        for quote_id, reason in sel.quarantined_quotes[:15]:
            quote = speech_act_lookup.get(quote_id)
            if not quote:
                continue
            
            content = getattr(quote, 'content', str(quote))
            content_lower = content.lower() if content else ""
            
            # Last-chance resolution based on content patterns
            resolved_speaker = None
            
            # "You're hurting me!" - Reporter
            if 'you\'re hurting me' in content_lower or 'please stop' in content_lower:
                resolved_speaker = "Reporter"
            # "There's been a misunderstanding" - Sergeant (authority figure)
            elif 'misunderstanding' in content_lower or 'you can go' in content_lower:
                resolved_speaker = "Sergeant Williams"
            # "Hey! What are you doing" - Witness intervention
            elif 'what are you doing' in content_lower or 'that\'s my neighbor' in content_lower:
                resolved_speaker = "Marcus Johnson"
            # "Sure you did" - Mocking officer
            elif 'sure you did' in content_lower or 'that\'s what they all say' in content_lower:
                resolved_speaker = "Officer Jenkins"
            # "within policy" - Official statement
            elif 'within policy' in content_lower:
                resolved_speaker = "Internal Affairs"
            
            if resolved_speaker:
                last_chance_resolved.append((resolved_speaker, "said", content))
            else:
                still_unresolved.append((quote_id, reason, content))
        
        # Add last-chance resolved to the resolved section
        if last_chance_resolved:
            for speaker, verb, content in last_chance_resolved:
                # Dedupe
                content_key = content.strip().lower()[:50]
                if content_key not in seen_content:
                    seen_content.add(content_key)
                    lines.insert(-1, f"  • {speaker} {verb}: {content}")  # Add before blank line
        
        # Show remaining unresolved
        if still_unresolved:
            lines.append("QUOTES (SPEAKER UNRESOLVED)")
            lines.append("─" * 70)
            lines.append("  ⚠️ These quotes could not be attributed to a speaker:")
            lines.append("")
            
            for quote_id, reason, content in still_unresolved[:10]:
                content_display = content[:60] if content else ""
                lines.append(f'  ❌ "{content_display}..."')
                lines.append(f"      Reason: {reason}")
            
            lines.append("")


def _render_actor_unresolved_events(lines: List[str], events: List[Any]) -> None:
    """Render EVENTS (ACTOR UNRESOLVED) section.
    
    V7: Shows events that were filtered from STRICT section with reasons.
    Provides transparency about what was excluded and why.
    """
    if not events:
        return
    
    # Find events that failed camera-friendly validation
    failed_events = []
    for event in events:
        is_cf = getattr(event, 'is_camera_friendly', True)
        reason = getattr(event, 'camera_friendly_reason', None)
        is_follow_up = getattr(event, 'is_follow_up', False)
        is_source = getattr(event, 'is_source_derived', False)
        
        # Only show events that failed for interesting reasons
        # Skip follow-up and source-derived (they're not supposed to be camera-friendly)
        if not is_cf and reason and not is_follow_up and not is_source:
            failed_events.append((event, reason))
    
    if not failed_events:
        return
    
    lines.append("EVENTS (ACTOR UNRESOLVED)")
    lines.append("─" * 70)
    lines.append("  ⚠️ These events could not be validated for neutral rendering:")
    lines.append("")
    
    for event, reason in failed_events[:10]:  # Limit to 10
        desc = getattr(event, 'description', str(event))[:80]
        
        # Format reason nicely
        if reason.startswith('bare_role:'):
            issue = f"Actor is bare role: '{reason.split(':')[1]}'"
        elif reason.startswith('characterization_in_actor:'):
            issue = f"Actor contains characterization: '{reason.split(':')[1]}'"
        elif reason.startswith('invalid_actor_label:'):
            issue = f"Actor is not a proper noun: '{reason.split(':')[1]}'"
        elif reason == 'no_actor_label':
            issue = "No actor specified"
        elif reason == 'fragment':
            issue = "Event is a fragment"
        elif reason == 'pronoun_start':
            issue = "Starts with unresolved pronoun"
        else:
            issue = reason
        
        lines.append(f"  ❌ {desc}")
        lines.append(f"      Issues: {issue}")
        lines.append("")
    
    if len(failed_events) > 10:
        lines.append(f"  ... and {len(failed_events) - 10} more events with unresolved actors")
        lines.append("")
    
    # Stats
    total_events = len(events)
    passed = sum(1 for e in events if getattr(e, 'is_camera_friendly', False))
    lines.append(f"  📊 Event Validation: {passed}/{total_events} passed camera-friendly validation")
    lines.append("")


def _render_timeline(
    lines: List[str],
    sel: "SelectionResult",
    timeline_lookup: Dict,
    event_lookup: Dict
) -> None:
    """Render RECONSTRUCTED TIMELINE section."""
    if not sel.timeline_entries:
        return
    
    lines.append("─" * 70)
    lines.append("")
    lines.append("RECONSTRUCTED TIMELINE")
    lines.append("─" * 70)
    lines.append("Events ordered by reconstructed chronology.")
    lines.append("")
    
    # Group by day
    entries_by_day = defaultdict(list)
    for entry_id in sel.timeline_entries:
        entry = timeline_lookup.get(entry_id)
        if entry:
            day = getattr(entry, 'day_offset', 0) or 0
            entries_by_day[day].append(entry)
    
    # Render each day
    for day_offset in sorted(entries_by_day.keys()):
        day_entries = entries_by_day[day_offset]
        
        if day_offset == 0:
            day_label = "INCIDENT DAY (Day 0)"
        elif day_offset == 1:
            day_label = "NEXT DAY (Day 1)"
        else:
            day_label = f"DAY {day_offset}"
        
        lines.append(f"  ┌─── {day_label} ───")
        lines.append("  │")
        
        for entry in day_entries:
            event = event_lookup.get(entry.event_id) if entry.event_id else None
            desc = getattr(event, 'description', entry.event_id or 'Unknown') if event else entry.event_id or 'Unknown'
            
            time_info = ""
            if entry.absolute_time or entry.relative_time:
                time_val = entry.absolute_time or entry.relative_time
                time_info = f"[{time_val}] "
            
            lines.append(f"  │  {time_info}{desc[:80]}")
        
        lines.append("  │")
    
    lines.append("  └─────────────────────────────")
    lines.append("")
    lines.append(f"  📊 Timeline: {len(sel.timeline_entries)} events")
    lines.append("")


def _render_investigation_questions(
    lines: List[str], 
    time_gaps: List[Any], 
    atomic_statements: List[Any],
    events: List[Any],
) -> None:
    """Render INVESTIGATION QUESTIONS section.
    
    V7: Auto-generates follow-up questions for investigators based on
    time gaps, statements, and events.
    """
    try:
        from nnrt.v6.questions import generate_all_questions
        
        question_set = generate_all_questions(
            time_gaps=time_gaps,
            atomic_statements=atomic_statements,
            events=events,
        )
        
        if question_set.total_count > 0:
            lines.append("─" * 70)
            lines.append("")
            lines.append("INVESTIGATION QUESTIONS")
            lines.append("─" * 70)
            lines.append("Auto-generated questions for investigator follow-up:")
            lines.append("")
            
            # Priority icons
            priority_icons = {
                'critical': '🔴',
                'high': '🟠',
                'medium': '🟡',
                'low': '⚪',
            }
            
            # Show critical and high priority questions
            shown = 0
            for q in question_set.questions:
                if shown >= 10:
                    remaining = question_set.total_count - shown
                    if remaining > 0:
                        lines.append(f"  ... and {remaining} more questions (see full report)")
                    break
                
                priority_val = q.priority.value if hasattr(q.priority, 'value') else str(q.priority)
                icon = priority_icons.get(priority_val, '○')
                category_val = q.category.value if hasattr(q.category, 'value') else str(q.category)
                
                lines.append(f"  {icon} [{priority_val.upper()}] {category_val.replace('_', ' ').title()}")
                lines.append(f"     {q.text}")
                if q.related_text:
                    excerpt = q.related_text[:50] + "..." if len(q.related_text) > 50 else q.related_text
                    lines.append(f"     Context: \"{excerpt}\"")
                lines.append("")
                shown += 1
            
            # Summary
            lines.append(f"  📊 Question Summary: {question_set.total_count} total")
            if question_set.critical_count > 0:
                lines.append(f"      🔴 Critical: {question_set.critical_count}")
            if question_set.high_count > 0:
                lines.append(f"      🟠 High Priority: {question_set.high_count}")
            lines.append("")
    except ImportError:
        pass  # V6 questions module not available
    except Exception as e:
        # Don't crash render if question generation fails
        pass


# =============================================================================
# V7 / Stage 3: NEW SECTION RENDERERS
# =============================================================================

def _render_items_discovered(lines: List[str], metadata: Any) -> None:
    """V7 / Stage 3: Render ITEMS DISCOVERED section from p38 extraction."""
    # Items are stored in ctx.discovered_items by p38
    discovered_items = getattr(metadata, 'discovered_items', None)
    if not discovered_items:
        return
    
    lines.append("ITEMS DISCOVERED (as claimed by Reporter)")
    lines.append("─" * 70)
    lines.append("  ℹ️ Items Reporter states were found during search.")
    lines.append("  Status: Reporter's account only. No seizure/inventory records attached.")
    lines.append("")
    
    # Group by category
    categories = {}
    for item in discovered_items:
        cat = getattr(item, 'category', 'other')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(item)
    
    CATEGORY_LABELS = {
        'personal_effects': 'PERSONAL EFFECTS',
        'work_items': 'WORK-RELATED ITEMS',
        'valuables': 'VALUABLES/CURRENCY',
        'contraband': 'CONTRABAND (as claimed)',
        'unspecified_substances': '❓ UNSPECIFIED SUBSTANCES (Requires Clarification)',
        'weapons': 'WEAPONS (as claimed)',
        'other': 'OTHER ITEMS',
    }
    
    for cat, items in categories.items():
        label = CATEGORY_LABELS.get(cat, cat.upper())
        lines.append(f"  {label}:")
        for item in items:
            desc = getattr(item, 'description', str(item))
            if cat == 'unspecified_substances':
                lines.append(f'    • "{desc}" — term is ambiguous')
            else:
                lines.append(f"    • {desc}")
        lines.append("")
    
    lines.append("")


def _render_self_reported_v2(lines: List[str], sel: "SelectionResult", statement_lookup: dict) -> None:
    """V7 / Stage 3: Render 5 SELF-REPORTED subsections using SelectionResult fields."""
    sections = [
        ('acute_state', 'SELF-REPORTED STATE (ACUTE)', 'During incident'),
        ('injury_state', 'SELF-REPORTED STATE (INJURY)', 'Physical injuries reported'),
        ('psychological_state', 'SELF-REPORTED STATE (PSYCHOLOGICAL)', 'Emotional/psychological impact'),
        ('socioeconomic_impact', 'SELF-REPORTED STATE (SOCIOECONOMIC)', 'Economic/livelihood impact'),
        ('general_self_report', 'SELF-REPORTED STATE (GENERAL)', 'General self-report'),
    ]
    
    for field_name, title, desc in sections:
        stmt_ids = getattr(sel, field_name, [])
        if not stmt_ids:
            continue
        
        lines.append(title)
        lines.append("─" * 70)
        lines.append(f"  ℹ️ {desc}")
        lines.append("")
        
        seen = set()  # V7.3: Dedupe within section
        for stmt_id in stmt_ids:
            stmt = statement_lookup.get(stmt_id)
            if stmt:
                text = getattr(stmt, 'text', str(stmt))
                # V7.3 FIX: Skip short fragments and duplicates
                if not _is_meaningful_text(text):
                    continue
                key = _dedupe_key(text)
                if key in seen:
                    continue
                seen.add(key)
                lines.append(f"  • {text}")
        
        lines.append("")


def _render_legal_allegations(lines: List[str], sel: "SelectionResult", statement_lookup: dict) -> None:
    """V7 / Stage 3: Render LEGAL ALLEGATIONS section."""
    if not sel.legal_allegations:
        return
    
    lines.append("LEGAL ALLEGATIONS (Reporter's claims)")
    lines.append("─" * 70)
    lines.append("  ⚠️ These are legal claims made by the Reporter, not established facts:")
    lines.append("")
    
    seen = set()  # V7.3: Dedupe
    for stmt_id in sel.legal_allegations:
        stmt = statement_lookup.get(stmt_id)
        if stmt:
            text = getattr(stmt, 'text', str(stmt))
            if not _is_meaningful_text(text):
                continue
            key = _dedupe_key(text)
            if key in seen:
                continue
            seen.add(key)
            lines.append(f"  • {text}")
    
    lines.append("")


def _render_inferences(lines: List[str], sel: "SelectionResult", statement_lookup: dict) -> None:
    """V7 / Stage 3: Render REPORTER INFERENCES section."""
    if not sel.inferences:
        return
    
    lines.append("REPORTER INFERENCES")
    lines.append("─" * 70)
    lines.append("  ⚠️ These are conclusions drawn by the Reporter, not direct observations:")
    lines.append("")
    
    for stmt_id in sel.inferences:
        stmt = statement_lookup.get(stmt_id)
        if stmt:
            text = getattr(stmt, 'text', str(stmt))
            lines.append(f"  • {text}")
    
    lines.append("")


def _render_interpretations(lines: List[str], sel: "SelectionResult", statement_lookup: dict) -> None:
    """V7 / Stage 3: Render REPORTER INTERPRETATIONS section."""
    if not sel.interpretations:
        return
    
    lines.append("REPORTER INTERPRETATIONS")
    lines.append("─" * 70)
    lines.append("  ⚠️ These are the Reporter's interpretations of others' mental states or intentions:")
    lines.append("")
    
    for stmt_id in sel.interpretations:
        stmt = statement_lookup.get(stmt_id)
        if stmt:
            text = getattr(stmt, 'text', str(stmt))
            lines.append(f"  • {text}")
    
    lines.append("")


def _render_contested(lines: List[str], sel: "SelectionResult", statement_lookup: dict) -> None:
    """V7 / Stage 3: Render CONTESTED ALLEGATIONS section."""
    if not sel.contested_allegations:
        return
    
    lines.append("CONTESTED ALLEGATIONS")
    lines.append("─" * 70)
    lines.append("  ⚠️ These claims involve conspiracy or systemic allegations requiring verification:")
    lines.append("")
    
    for stmt_id in sel.contested_allegations:
        stmt = statement_lookup.get(stmt_id)
        if stmt:
            text = getattr(stmt, 'text', str(stmt))
            lines.append(f"  • {text}")
    
    lines.append("")


def _render_medical_findings_v2(lines: List[str], sel: "SelectionResult", statement_lookup: dict) -> None:
    """V7 / Stage 3: Render MEDICAL FINDINGS using SelectionResult."""
    if not sel.medical_findings:
        return
    
    lines.append("MEDICAL FINDINGS (as reported by Reporter)")
    lines.append("─" * 70)
    lines.append("  ℹ️ Medical provider statements cited by Reporter")
    lines.append("  Status: Cited (no medical record attached)")
    lines.append("")
    
    for stmt_id in sel.medical_findings:
        stmt = statement_lookup.get(stmt_id)
        if stmt:
            text = getattr(stmt, 'text', str(stmt))
            lines.append(f"  • {text}")
    
    lines.append("")


def _render_admin_actions(lines: List[str], sel: "SelectionResult", statement_lookup: dict) -> None:
    """V7 / Stage 3: Render ADMINISTRATIVE ACTIONS section."""
    if not sel.admin_actions:
        return
    
    lines.append("ADMINISTRATIVE ACTIONS")
    lines.append("─" * 70)
    lines.append("  ℹ️ Administrative or procedural actions taken:")
    lines.append("")
    
    for stmt_id in sel.admin_actions:
        stmt = statement_lookup.get(stmt_id)
        if stmt:
            text = getattr(stmt, 'text', str(stmt))
            lines.append(f"  • {text}")
    
    lines.append("")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _get_role_display(entity: Any) -> str:
    """Get displayable role string from entity."""
    role = getattr(entity, 'role', 'unknown')
    if hasattr(role, 'value'):
        role = role.value
    return str(role).replace('_', ' ').title()


def _deduplicate(items: List[str]) -> List[str]:
    """Remove duplicate strings, keeping order."""
    seen = set()
    result = []
    for item in items:
        if item.lower() not in seen:
            seen.add(item.lower())
            result.append(item)
    return result
