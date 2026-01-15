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
    
    # === PARTIES ===
    if entities:
        entity_by_role = defaultdict(list)
        for e in entities:
            role = getattr(e, 'role', 'other') or 'other'
            # Normalize role names
            if role.lower() == 'authority':
                role = 'agent'
            label = getattr(e, 'label', 'Unknown')
            entity_by_role[role.upper()].append(label)
        
        lines.append("PARTIES")
        lines.append("─" * 70)
        for role, names in entity_by_role.items():
            lines.append(f"  {role}:".ljust(14) + ", ".join(names))
        lines.append("")
    
    # === REFERENCE DATA ===
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
            for ident_type, values in ident_by_type.items():
                label = ident_type.replace('_', ' ').title()
                lines.append(f"  {label}:".ljust(14) + ", ".join(values))
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
    
    # V4: Words that disqualify a statement from OBSERVED EVENTS
    # If a statement contains these, it's not "camera-friendly" and belongs elsewhere
    INTERPRETIVE_DISQUALIFIERS = [
        # Characterizations
        'horrifying', 'horrific', 'brutal', 'brutally', 'viciously', 'vicious',
        'psychotic', 'maniac', 'thug', 'aggressive', 'aggressively', 
        'menacing', 'menacingly', 'distressing', 'terrifying', 'shocking',
        'excessive', 'mocking', 'laughing at', 'fishing',  # V4.3
        # Legal conclusions
        'innocent', 'guilty', 'criminal', 'illegal', 'unlawful', 'assault',
        'assaulting', 'torture', 'terrorize', 'misconduct', 'violation',
        # Intent attributions
        'deliberately', 'intentionally', 'clearly', 'obviously', 'wanted to',
        # Certainty markers
        'absolutely', 'completely', 'totally', 'definitely', 'certainly',
        # Cover-up/conspiracy language
        'cover-up', 'coverup', 'whitewash', 'conspiracy', 'conspiring',
        'hiding more', 'protect their own', 'always protect',  # V4.3
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
        
        # V4.3: SOURCE-DERIVED INFORMATION (research, conclusions, comparisons)
        # These need provenance verification - not directly observable
        if source_derived:
            lines.append("SOURCE-DERIVED INFORMATION (PROVENANCE NEEDED)")
            lines.append("─" * 70)
            for text in source_derived:
                lines.append(f"  ⚠️ {text}")
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
    # V4: SELF-REPORTED STATE (internal: fear, pain, trauma)
    # NOT observations - reported internal experience
    # =========================================================================
    if statements_by_epistemic.get('self_report'):
        lines.append("SELF-REPORTED STATE")
        lines.append("─" * 70)
        for text in statements_by_epistemic['self_report']:
            lines.append(f"  • Reporter reports: {text}")
        lines.append("")
    
    # =========================================================================
    # V4: REPORTED CLAIMS (legal characterizations) - with proper attribution
    # These are legal conclusions made by the reporter
    # =========================================================================
    if statements_by_epistemic.get('legal_claim'):
        lines.append("REPORTED CLAIMS (legal characterizations)")
        lines.append("─" * 70)
        for text in statements_by_epistemic['legal_claim']:
            # Add attribution prefix
            lines.append(f"  • Reporter characterizes: {text}")
        lines.append("")
    
    # =========================================================================
    # V4: REPORTER INTERPRETATIONS - intent attributions, inferences
    # =========================================================================
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
    
    # === PRESERVED QUOTES ===
    if statements_by_type.get('quote'):
        lines.append("PRESERVED QUOTES")
        lines.append("─" * 70)
        for text in statements_by_type['quote']:
            lines.append(f'  "{text}"')
        lines.append("")
    
    # === RECORDED EVENTS ===
    # V4.3: Split events into camera-friendly vs interpretive (like statements)
    if events:
        # Light quality filter - only remove corrupted text
        def is_valid_event(desc: str) -> bool:
            """Light filter: only remove corrupt/fragment events."""
            if len(desc) < 10:
                return False
            
            desc_lower = desc.lower()
            desc_words = desc_lower.split()
            
            if len(desc_words) < 3:
                return False
            
            # Only filter clear text corruption (NLP parsing issues)
            corruption_markers = [
                'when innocently', 'when viciously', 'where work',
                'thug the', 'say what', 'saying what', 'the brutal when',
                'longer walk at', 'sergeant arrived after',
            ]
            if any(marker in desc_lower for marker in corruption_markers):
                return False
            
            # First word should be a valid start
            first_word = desc_words[0]
            valid_starts = {'i', 'he', 'she', 'they', 'we', 'officer', 'sergeant', 
                           'detective', 'the', 'a', 'my', 'his', 'her', 'their'}
            if not (first_word[0].isupper() or first_word in valid_starts):
                return False
            
            return True
        
        # Separate events: camera-friendly vs interpretive
        camera_friendly_by_type = defaultdict(list)
        interpretive_events = []
        seen_events = set()
        
        for event in events:
            desc = getattr(event, 'description', str(event))
            desc_normalized = ' '.join(desc.split())
            
            # Dedupe
            if desc_normalized in seen_events:
                continue
            seen_events.add(desc_normalized)
            
            if not is_valid_event(desc):
                continue
            
            # Get event type
            etype = getattr(event, 'type', None)
            if hasattr(etype, 'value'):
                etype = etype.value
            etype = str(etype) if etype else 'action'
            
            # Split by camera-friendliness (reuse existing function!)
            if is_camera_friendly(desc):
                camera_friendly_by_type[etype].append(desc)
            else:
                interpretive_events.append(desc)
        
        # Render camera-friendly events by type
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
                    for desc in camera_friendly_by_type[etype]:
                        lines.append(f"      • {desc}")
                    lines.append("")
            
            # Any other types not in our map
            for etype, descs in camera_friendly_by_type.items():
                if etype not in type_labels and descs:
                    lines.append(f"  📋 {etype.upper()}:")
                    for desc in descs:
                        lines.append(f"      • {desc}")
                    lines.append("")
        
        # Render interpretive events with attribution
        if interpretive_events:
            lines.append("REPORTER'S CHARACTERIZATIONS (of events)")
            lines.append("─" * 70)
            for desc in interpretive_events:
                lines.append(f"  • Reporter describes: {desc}")
            lines.append("")
    
    # === FULL NARRATIVE ===
    if rendered_text:
        lines.append("─" * 70)
        lines.append("")
        lines.append("FULL NARRATIVE (Computed)")
        lines.append("─" * 70)
        lines.append(rendered_text)
        lines.append("")
    
    lines.append("═" * 70)
    
    return "\n".join(lines)
