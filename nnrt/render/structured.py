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
        # Legal conclusions
        'innocent', 'guilty', 'criminal', 'illegal', 'unlawful', 'assault',
        'assaulting', 'torture', 'terrorize', 'misconduct', 'violation',
        # Intent attributions
        'deliberately', 'intentionally', 'clearly', 'obviously', 'wanted to',
        # Certainty markers
        'absolutely', 'completely', 'totally', 'definitely', 'certainly',
        # Cover-up language
        'cover-up', 'coverup', 'whitewash', 'conspiracy', 'conspiring',
    ]
    
    # V4: Patterns that indicate "later discovered" facts (not incident-scene)
    FOLLOW_UP_PATTERNS = [
        'later found', 'later learned', 'turned out', 'found out',
        'three months later', 'the next day', 'afterward', 'afterwards',
        'went to the emergency', 'went to the hospital', 'filed a complaint',
        'filed a formal', 'received a letter', 'therapist', 'diagnosed',
        'internal affairs', 'detective', 'investigated', 'pursuing legal',
        'my attorney', 'researched',
    ]
    
    def is_camera_friendly(text: str) -> bool:
        """Check if statement is purely observational (no interpretive content)."""
        text_lower = text.lower()
        for word in INTERPRETIVE_DISQUALIFIERS:
            if word in text_lower:
                return False
        return True
    
    def is_follow_up_event(text: str) -> bool:
        """Check if event is follow-up (not incident-scene)."""
        text_lower = text.lower()
        return any(pattern in text_lower for pattern in FOLLOW_UP_PATTERNS)
    
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
        excluded_events = []  # Statements with interpretive content
        
        for text in statements_by_epistemic['direct_event']:
            if not is_camera_friendly(text):
                # Contains interpretive words - exclude from OBSERVED EVENTS
                excluded_events.append(text)
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
        
        # FOLLOW-UP events (post-incident)
        if follow_up_events:
            lines.append("OBSERVED EVENTS (FOLLOW-UP ACTIONS)")
            lines.append("─" * 70)
            for text in follow_up_events:
                lines.append(f"  • {text}")
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
    # V4.1: Apply comprehensive quality filter to events
    if events:
        # V4.1: Event quality validation
        def is_quality_event(desc: str) -> bool:
            """Check if event description meets quality standards."""
            # Minimum length
            if len(desc) < 20:
                return False
            
            desc_lower = desc.lower()
            desc_words = desc_lower.split()
            
            # Minimum word count
            if len(desc_words) < 4:
                return False
            
            # Interpretive words that disqualify the event
            interpretive_words = [
                'brutal', 'brutally', 'viciously', 'psychotic', 'maniac', 'thug',
                'clearly', 'obviously', 'deliberately', 'innocent', 'criminal',
                'horrifying', 'terrifying', 'illegal', 'proves', 'cover-up',
                'intentionally', 'mocking', 'fishing', 'excessive'
            ]
            if any(word in desc_lower for word in interpretive_words):
                return False
            
            # Detect text corruption patterns
            # (words appearing in wrong positions due to NLP parsing issues)
            corruption_markers = [
                'when innocently', 'when viciously', 'where work',
                'obviously care', 'thug the', 'say what', 'hurting me',
                'the brutal when',
            ]
            if any(marker in desc_lower for marker in corruption_markers):
                return False
            
            # First word should be a proper subject (capitalized or pronoun)
            first_word = desc_words[0]
            valid_pronouns = {'i', 'he', 'she', 'they', 'we', 'officer', 'sergeant', 'detective'}
            if not (first_word[0].isupper() or first_word in valid_pronouns):
                return False
            
            # Must contain a verb-like word (not just fragments)
            verb_indicators = ['ed ', 'ing ', 'ran ', 'put ', 'saw ', 'said ', 'came ', 'went ']
            if not any(vi in desc_lower + ' ' for vi in verb_indicators):
                # Allow if it ends with common verb endings
                if not desc_lower.endswith(('ed', 'ing')):
                    return False
            
            return True
        
        quality_events = []
        seen_events = set()  # Deduplicate
        for event in events:
            desc = getattr(event, 'description', str(event))
            # Normalize and dedupe
            desc_normalized = ' '.join(desc.split())
            if desc_normalized in seen_events:
                continue
            seen_events.add(desc_normalized)
            
            if is_quality_event(desc):
                quality_events.append(desc)
        
        if quality_events:
            lines.append("RECORDED EVENTS")
            lines.append("─" * 70)
            for desc in quality_events:
                lines.append(f"  • {desc}")
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
