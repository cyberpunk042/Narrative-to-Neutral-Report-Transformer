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
    # V4: OBSERVED EVENTS (physical, third-party observable)
    # CRITICAL INVARIANT: Must be externally observable by camera/witness
    # =========================================================================
    if statements_by_epistemic.get('direct_event'):
        lines.append("OBSERVED EVENTS")
        lines.append("─" * 70)
        for text in statements_by_epistemic['direct_event']:
            lines.append(f"  • {text}")
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
    
    # === CLAIMS ===
    if statements_by_type.get('claim'):
        lines.append("CLAIMS")
        lines.append("─" * 70)
        for text in statements_by_type['claim']:
            lines.append(f"  • {text}")
        lines.append("")
    
    # === STATEMENTS (Interpretations) ===
    if statements_by_type.get('interpretation'):
        lines.append("STATEMENTS")
        lines.append("─" * 70)
        for text in statements_by_type['interpretation']:
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
    if events:
        lines.append("RECORDED EVENTS")
        lines.append("─" * 70)
        for event in events:
            desc = getattr(event, 'description', str(event))
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
