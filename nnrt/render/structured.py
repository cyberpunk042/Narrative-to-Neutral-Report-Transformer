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


def _deduplicate_statements(statements: List[str]) -> List[str]:
    """
    Remove duplicate and subsument statements.
    
    If one statement is a substring of another, keep only the longer one.
    Also removes exact duplicates.
    
    Example:
        ["I froze in place", "I was so scared I froze in place"]
        -> ["I was so scared I froze in place"]
    """
    if not statements:
        return []
    
    # Normalize for comparison
    unique: List[str] = []
    seen_lower: Set[str] = set()
    
    # Sort by length descending - longer statements first
    sorted_stmts = sorted(statements, key=len, reverse=True)
    
    for stmt in sorted_stmts:
        stmt_lower = stmt.lower().strip()
        
        # Skip exact duplicates (case-insensitive)
        if stmt_lower in seen_lower:
            continue
        
        # Skip if this is a substring of something we've already kept
        is_substring = False
        for kept in seen_lower:
            if stmt_lower in kept:
                is_substring = True
                break
        
        if not is_substring:
            unique.append(stmt)
            seen_lower.add(stmt_lower)
    
    # Return in original order (longest first was just for processing)
    return unique


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
    # V9: Segments needed for event generator
    segments: List[Any] = None,
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
    
    # V7: Words to STRIP (not disqualify) - factual core remains
    INTERPRETIVE_STRIP_WORDS = [
        # Characterizing adverbs - remove but keep the verb
        'brutally', 'viciously', 'aggressively', 'menacingly', 'savagely',
        'deliberately', 'intentionally', 'obviously', 'clearly',
        'absolutely', 'completely', 'totally', 'definitely', 'certainly',
        'innocently', 'distressingly', 'horrifyingly', 'terrifyingly',
        # Characterizing adjectives - remove but keep the noun
        'brutal', 'vicious', 'psychotic', 'horrifying', 'horrific',
        'terrifying', 'shocking', 'excessive', 'innocent', 'menacing',
        'distressing', 'manic', 'maniacal',
        # Loaded phrases - remove entirely
        'like a maniac', 'like a criminal', 'for no reason', 'for absolutely no reason',
        'without any reason', 'with excessive force', 'without provocation',
    ]
    
    def neutralize_for_observed(text: str) -> str:
        """
        V7: Neutralize text by stripping interpretive words while keeping factual core.
        
        Example:
          "They brutally slammed me" -> "They slammed me"
          "innocently walking" -> "walking"
        """
        import re
        result = text
        
        # Strip interpretive words/phrases
        for word in INTERPRETIVE_STRIP_WORDS:
            # Match word with word boundaries and optional trailing comma/space
            pattern = r'\b' + re.escape(word) + r'\b[,]?\s*'
            result = re.sub(pattern, '', result, flags=re.IGNORECASE)
        
        # Clean up extra spaces
        result = ' '.join(result.split())
        
        # Fix article agreement after stripping
        result = re.sub(r'\ban\s+([bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ])', r'a \1', result)
        result = re.sub(r'\ba\s+([aeiouAEIOU])', r'an \1', result)
        
        # Clean up trailing punctuation artifacts
        result = re.sub(r'\s+\.', '.', result)  # " ." -> "."
        result = re.sub(r'\s+,', ',', result)   # " ," -> ","
        result = re.sub(r',\s*\.', '.', result)  # ", ." or ",." -> "."
        result = re.sub(r',\s*$', '', result)   # Trailing comma
        result = re.sub(r'\s+\.+$', '.', result)  # Trailing space+period(s)
        
        return result.strip()
    
    def is_strict_camera_friendly(text: str) -> tuple[bool, str]:
        """
        V8: STRICT camera-friendly check for OBSERVED EVENTS section.
        
        Returns (passed, failure_reason) tuple.
        
        V8.1: Fixed to check for named actors ANYWHERE in sentence, not just start.
        "His partner, Officer Rodriguez..." passes because Officer Rodriguez is named.
        """
        import re
        text_lower = text.lower().strip()
        words = text_lower.split()
        
        if not words or len(words) < 3:
            return (False, "too_short")
        
        first_word = words[0]
        
        # =====================================================================
        # Rule 1: No conjunction starts (dependent clause fragments)
        # =====================================================================
        CONJUNCTION_STARTS = [
            'but', 'and', 'when', 'which', 'although', 'while', 'because',
            'since', 'that', 'where', 'if', 'though', 'unless',
        ]
        if first_word in CONJUNCTION_STARTS:
            return (False, f"conjunction_start:{first_word}")
        
        # =====================================================================
        # Rule 2: No embedded quotes (should go to QUOTES section)
        # =====================================================================
        if '"' in text or '"' in text or '"' in text:
            return (False, "contains_quote")
        
        # =====================================================================
        # Rule 3: No verb-first fragments (missing actor entirely)
        # =====================================================================
        VERB_STARTS = [
            'twisted', 'grabbed', 'pushed', 'slammed', 'found', 'tried',
            'stepped', 'saw', 'also', 'put', 'cut', 'screamed',
            'yelled', 'shouted', 'told', 'called',
            'ran', 'walked', 'went', 'came', 'left', 'arrived',
            'started', 'began', 'stopped', 'continued', 'happened',
            'witnessed', 'watched', 'heard', 'felt', 'noticed', 'realized',
            'screeching', 'immediately',
        ]
        if first_word in VERB_STARTS:
            return (False, f"verb_start:{first_word}")
        
        # =====================================================================
        # Rule 4: Must have NAMED ACTOR anywhere in first clause
        # V8.1: Check ANYWHERE, not just at start
        # "His partner, Officer Rodriguez" -> Officer Rodriguez is the actor
        # =====================================================================
        
        # Named actor patterns to search for ANYWHERE in the text
        # V8.1: Case-sensitive for proper nouns, case-insensitive for titles
        
        # Check for named actor anywhere in the sentence
        has_named_actor = False
        
        # Pattern 1: Title + Name (case-insensitive for title, sensitive for name)
        title_pattern = r'\b(Officer|Sergeant|Detective|Captain|Lieutenant|Deputy|Dr\.?|Mr\.?|Mrs\.?|Ms\.?)\s+[A-Z][a-z]+'
        if re.search(title_pattern, text):
            has_named_actor = True
        
        # Pattern 2: Two-word proper nouns (CASE SENSITIVE - requires actual capitals)
        # This must NOT use IGNORECASE
        if not has_named_actor:
            proper_noun_pattern = r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b'
            match = re.search(proper_noun_pattern, text)  # NO IGNORECASE
            if match:
                # Verify it's not a common phrase like "He found", "My neighbor"
                matched = match.group()
                first_word = matched.split()[0].lower()
                skip_words = ['he', 'she', 'they', 'it', 'i', 'my', 'his', 'her', 'the', 'a', 'an', 'we', 'you']
                if first_word not in skip_words:
                    has_named_actor = True
        
        # Also check for valid actor patterns at START
        START_ACTOR_PATTERNS = [
            # Named persons at start
            r'^(officer|sergeant|detective|captain|lieutenant|deputy|dr\.?|mr\.?|mrs\.?|ms\.?)\s+\w+',
            # Entity classes at start (Another witness, The officers, This cruiser)
            r'^(the|a|an|this|that|another|one|two|three|four|five)\s+(officer|officers|sergeant|detective|witness|witnesses|neighbor|woman|man|person|vehicle|car|cruiser|people)',
            # Generic plurals (Officers approached, Witnesses saw)
            r'^(officers|witnesses|bystanders|paramedics)\s+',
        ]
        
        for pattern in START_ACTOR_PATTERNS:
            if re.match(pattern, text_lower):
                has_named_actor = True
                break
        
        # =====================================================================
        # Rule 5: Pronoun starts are OK only if named actor exists
        # "His partner, Officer Rodriguez" -> OK (Officer Rodriguez named)
        # "He found my wallet" -> NOT OK (who is He?)
        # =====================================================================
        PRONOUN_STARTS = [
            'he', 'she', 'they', 'it', 'we', 'i', 'you',
            'his', 'her', 'their', 'its', 'my', 'your', 'our',
            'him', 'them', 'us', 'me',
        ]
        
        if first_word in PRONOUN_STARTS:
            if not has_named_actor:
                return (False, f"pronoun_start:{first_word}")
            # Has pronoun start BUT also has named actor - check if actor is clear
            # "My neighbor, Marcus Johnson" -> actor is Marcus Johnson, OK
            # "His partner, Officer Rodriguez" -> actor is Officer Rodriguez, OK
        
        # If no named actor and not a valid start pattern, reject
        if not has_named_actor:
            return (False, f"no_valid_actor:{first_word}")
        
        # =====================================================================
        # Rule 6: No interpretive/legal content
        # =====================================================================
        INTERPRETIVE_BLOCKERS = [
            'assault', 'brutality', 'torture', 'violation', 'misconduct',
            'illegal', 'unlawful', 'criminal', 'guilty', 'innocent',
            'cover-up', 'conspiracy', 'corrupt', 'abuse', 'terrorize',
        ]
        for blocker in INTERPRETIVE_BLOCKERS:
            if blocker in text_lower:
                return (False, f"interpretive:{blocker}")
        
        # Passed all checks
        return (True, "passed")
    
    def is_camera_friendly(text: str, neutralized_text: str = None) -> bool:
        """
        Legacy check - now wraps is_strict_camera_friendly.
        Returns just boolean for backward compatibility.
        """
        check_text = neutralized_text if neutralized_text else text
        passed, _ = is_strict_camera_friendly(check_text)
        return passed
    
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
    # V7: Deduplicate all statement lists to remove fragments/substrings
    # =========================================================================
    MIN_STATEMENT_LENGTH = 10  # Filter out single-word fragments like "bruised"
    
    def clean_statement(text: str) -> str:
        """Clean up a statement: fix trailing punctuation, normalize whitespace."""
        import re as re_clean
        result = text.strip()
        result = re_clean.sub(r'\s+\.', '.', result)  # " ." -> "."
        result = re_clean.sub(r'\s+,', ',', result)   # " ," -> ","
        result = ' '.join(result.split())  # Normalize whitespace
        return result
    
    for key in statements_by_type:
        statements_by_type[key] = _deduplicate_statements(statements_by_type[key])
        # Clean and filter fragments
        statements_by_type[key] = [
            clean_statement(s) for s in statements_by_type[key] 
            if len(s.strip()) >= MIN_STATEMENT_LENGTH
        ]
    for key in statements_by_epistemic:
        statements_by_epistemic[key] = _deduplicate_statements(statements_by_epistemic[key])
        # Clean and filter fragments
        statements_by_epistemic[key] = [
            clean_statement(s) for s in statements_by_epistemic[key] 
            if len(s.strip()) >= MIN_STATEMENT_LENGTH
        ]
    
    # =========================================================================
    # V8.2: OBSERVED EVENTS - Extract camera-friendly facts from ALL types
    # Not just direct_event, but also characterization and legal_claim_direct
    # if they contain observable physical actions with named actors
    # =========================================================================
    
    strict_events = []       # Passed all strict checks
    narrative_excerpts = []  # Failed with reasons
    follow_up_events = []    # Post-incident actions
    source_derived = []      # Research/conclusions
    
    # V8.2: Process multiple epistemic types that might contain observable events
    # Order matters - direct_event first, then others
    OBSERVABLE_EPISTEMIC_TYPES = [
        'direct_event',        # Primary: observable events
        'characterization',    # May contain "Officer X did Y like a Z"
        'legal_claim_direct',  # May contain "Officer X grabbed with excessive force"
        'state_injury',        # May contain "Officer X put handcuffs on me"
    ]
    
    seen_in_strict = set()  # Tracks original text
    seen_neutralized = set()  # V8.2: Also track neutralized versions to catch duplicates
    
    for epistemic_type in OBSERVABLE_EPISTEMIC_TYPES:
        if not statements_by_epistemic.get(epistemic_type):
            continue
            
        for text in statements_by_epistemic[epistemic_type]:
            # Skip if original already seen
            if text in seen_in_strict:
                continue
            
            # V8.2: Neutralize the text first (strips characterization)
            neutralized = neutralize_for_observed(text)
            
            # V8.2: Skip if neutralized version already seen
            neutralized_key = ' '.join(neutralized.split()).strip().lower()
            if neutralized_key in seen_neutralized:
                seen_in_strict.add(text)  # Mark original as seen
                continue
            
            # Skip if neutralized version is too short
            if len(neutralized) < 15:
                if epistemic_type == 'direct_event':
                    narrative_excerpts.append((text, "too_short"))
                continue
            
            # Skip if neutralized version already seen
            if neutralized in seen_in_strict:
                continue
            
            # Check if follow-up (before strict check)
            if is_follow_up_event(neutralized):
                follow_up_events.append(neutralized)
                seen_in_strict.add(neutralized)
                seen_in_strict.add(text)
                continue
            
            # Check if source-derived
            if is_source_derived(neutralized):
                source_derived.append(neutralized)
                seen_in_strict.add(neutralized)
                seen_in_strict.add(text)
                continue
            
            # V8.2: Apply STRICT camera-friendly check to neutralized text
            passed, reason = is_strict_camera_friendly(neutralized)
            
            if passed:
                strict_events.append(neutralized)
                seen_in_strict.add(neutralized)
                seen_in_strict.add(text)
                seen_neutralized.add(neutralized_key)  # V8.2: Track neutralized version
            elif epistemic_type == 'direct_event':
                # Only track excerpts for direct_event (others go to their sections)
                narrative_excerpts.append((text, reason))
    
    # =========================================================================
    # SECTION 1: OBSERVED EVENTS (STRICT / CAMERA-FRIENDLY)
    # V9: Use event-based generation for higher quality
    # =========================================================================
    
    # V9: Import and use the new event generator
    from nnrt.render.event_generator import get_strict_event_sentences
    
    v9_strict_events = []
    if events:
        try:
            v9_strict_events = get_strict_event_sentences(
                events=events,
                segments=segments,
                atomic_statements=atomic_statements,
                entities=entities,
                max_events=25,
            )
        except Exception as e:
            # Fall back to V8 method if V9 fails
            pass
    
    # V9: Use V9 events if available, otherwise fall back to V8
    # Do NOT combine - V9 is strictly higher quality and avoids duplicates
    if v9_strict_events:
        # Use V9 events only
        final_strict_events = v9_strict_events
    else:
        # Fall back to V8 (atomic_statements-based)
        seen_normalized = set()
        final_strict_events = []
        for text in strict_events:
            normalized = ' '.join(text.split()).strip().lower()
            if normalized not in seen_normalized:
                seen_normalized.add(normalized)
                final_strict_events.append(text)
    
    if final_strict_events:
        lines.append("OBSERVED EVENTS (STRICT / CAMERA-FRIENDLY)")
        lines.append("─" * 70)
        
        # =================================================================
        # V10: Context Summary - neutralize and present opening context
        # =================================================================
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
            
            # Add self-reported state if available (acute)
            if statements_by_epistemic.get('state_acute'):
                # Get first emotional state, neutralized
                for stmt in statements_by_epistemic['state_acute'][:1]:
                    if 'terrified' in stmt.lower() or 'scared' in stmt.lower() or 'frightened' in stmt.lower() or 'shock' in stmt.lower():
                        context_summary += " Reporter reports feeling frightened during this encounter."
                        break
            
            lines.append(context_summary)
            lines.append("")
        
        lines.append("ℹ️ Fully normalized: Actor (entity/class) + action + object. No pronouns, quotes, or fragments.")
        lines.append("")
        for text in final_strict_events:
            lines.append(f"  • {text}")
        lines.append("")
    
    # FOLLOW-UP events (post-incident observable actions)
    if follow_up_events:
        lines.append("OBSERVED EVENTS (FOLLOW-UP ACTIONS)")
        lines.append("─" * 70)
        for text in follow_up_events:
            lines.append(f"  • {text}")
        lines.append("")
    
    # =========================================================================
    # SECTION 2: NARRATIVE EXCERPTS (UNNORMALIZED)
    # Items that couldn't be normalized, with documented reasons
    # =========================================================================
    if narrative_excerpts:
        # Group by reason for cleaner display (defaultdict is imported at module level)
        by_reason = defaultdict(list)
        for text, reason in narrative_excerpts:
            # Simplify reason codes for display
            reason_type = reason.split(':')[0] if ':' in reason else reason
            by_reason[reason_type].append(text)
        
        lines.append("NARRATIVE EXCERPTS (UNNORMALIZED)")
        lines.append("─" * 70)
        lines.append("⚠️ These excerpts couldn't be normalized. Listed by rejection reason:")
        lines.append("")
        
        # Nice labels for reason codes
        REASON_LABELS = {
            'pronoun_start': 'Pronoun start (actor unresolved)',
            'conjunction_start': 'Fragment (conjunction start)',
            'verb_start': 'Fragment (verb start, missing actor)',
            'no_valid_actor': 'Actor not explicit (needs resolution)',
            'contains_quote': 'Contains quote (see QUOTES section)',
            'too_short': 'Too short (fragment)',
            'interpretive': 'Contains interpretive language',
        }
        
        for reason_type, texts in by_reason.items():
            label = REASON_LABELS.get(reason_type, reason_type)
            lines.append(f"  [{label}]")
            for text in texts[:5]:  # Limit per category
                lines.append(f"    - {text[:80]}{'...' if len(text) > 80 else ''}")
            if len(texts) > 5:
                lines.append(f"    ... and {len(texts) - 5} more")
            lines.append("")

    
    # =========================================================================
    # V6: SOURCE-DERIVED INFORMATION with Provenance Validation
    # =========================================================================
    # Uses VERIFIED_HAS_EVIDENCE invariant to ensure honest status labels.
    # =========================================================================
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
            
            # V8.1: Expanded list of speech verbs
            SPEECH_VERBS = [
                ' said ', ' yelled ', ' shouted ', ' asked ', ' told ',
                ' screamed ', ' whispered ', ' replied ', ' answered ',
                ' explained ', ' stated ', ' mentioned ', ' demanded ',
                ' threatened ', ' warned ', ' muttered ', ' exclaimed ',
            ]
            
            speaker_found = False
            for verb in SPEECH_VERBS:
                if verb in text:
                    parts = text.split(verb, 1)
                    speaker_text = parts[0].strip()
                    
                    # V8.1: "I asked", "I tried to explain" -> Reporter
                    if speaker_text.lower() in ['i', 'i also', 'i then']:
                        MockQuote.speaker_label = "Reporter"
                    else:
                        MockQuote.speaker_label = speaker_text[:50]
                    MockQuote.content = parts[1] if len(parts) > 1 else text
                    speaker_found = True
                    break
            
            # V8.1: Handle "I tried to explain" pattern
            if not speaker_found:
                first_person_patterns = [
                    'I tried to explain',
                    'I explained',
                    'I asked him',
                    'I asked her',
                    'I asked them',
                    'I told him',
                    'I told her',
                    'I told them',
                ]
                for pattern in first_person_patterns:
                    if text.startswith(pattern):
                        MockQuote.speaker_label = "Reporter"
                        MockQuote.content = text
                        speaker_found = True
                        break
            
            if not speaker_found:
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
            
            # Track shown entries to avoid duplicates/fragments
            shown_descriptions = set()
            
            for entry in day_entries:
                # Get event description
                event = event_map.get(entry.event_id) if entry.event_id else None
                full_desc = getattr(event, 'description', entry.event_id or 'Unknown event') if event else entry.event_id or 'Unknown'
                
                # =============================================================
                # Filter out fragment events that aren't meaningful timeline entries
                # =============================================================
                desc_lower = full_desc.lower().strip()
                
                # Skip very short descriptions (likely fragments)
                if len(desc_lower) < 15:
                    continue
                
                # Skip descriptions that start with prepositions (clause fragments)
                fragment_starters = [
                    'to ', 'for ', 'with ', 'from ', 'at ', 'in ', 'on ', 'by ',
                    'where ', 'which ', 'who ', 'that ', 'when ', 'because ',
                    'while ', 'after ', 'before ', 'until ', 'unless ',
                    'what ', 'how ', 'why ', 'if ',
                ]
                if any(desc_lower.startswith(starter) for starter in fragment_starters):
                    continue
                
                # Skip if this is a substring of another shown description
                is_duplicate = False
                for shown in shown_descriptions:
                    if desc_lower in shown or shown in desc_lower:
                        is_duplicate = True
                        break
                if is_duplicate:
                    continue
                
                shown_descriptions.add(desc_lower)
                desc = full_desc[:50]
                
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
    
    # ==========================================================================
    # V6: INVESTIGATION QUESTIONS SECTION
    # ==========================================================================
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
    
    # V7: Final cleanup pass for the entire output
    result = "\n".join(lines)
    
    # Fix trailing spaces before punctuation
    import re
    result = re.sub(r'\s+\.', '.', result)  # " ." -> "."
    result = re.sub(r'\s+,', ',', result)   # " ," -> ","
    result = re.sub(r',\s*\.', '.', result)  # ",." -> "."
    
    return result
