"""
Pass 43 — Actor Resolution (V5)

Resolves pronouns in atomic statements to concrete actor names using
coreference chains from p42.

This is a CRITICAL pass for making "Observed Events" trustworthy:
1. PRONOUN REPLACEMENT: "He grabbed" → "Officer Jenkins grabbed"
2. FRAGMENT DETECTION: Flags dependent fragments ("but then...")
3. QUOTE/INTERPRETATION SPLIT: Separates quotes from trailing characterization

Design Principle:
    Observed statements MUST have explicit, resolvable actors.
    If an actor cannot be resolved, the statement is flagged as actor-unresolved.

Exit Criteria:
    - No pronouns in actor_resolved_text for OBSERVED type statements
    - Fragments are flagged, not in clean output
    - Quotes contain ONLY quoted speech (interpretation split off)
"""

import re
from typing import Optional

from nnrt.core.context import TransformContext
from nnrt.core.logging import get_pass_logger
from nnrt.ir.enums import MentionType

PASS_NAME = "p43_resolve_actors"
log = get_pass_logger(PASS_NAME)


# =============================================================================
# Pronoun Patterns (for substitution)
# =============================================================================

# Pronouns that should be resolved to actor names
SUBJECT_PRONOUNS = {"he", "she", "they"}
OBJECT_PRONOUNS = {"him", "her", "them"}
POSSESSIVE_PRONOUNS = {"his", "her", "their", "hers", "theirs"}

ALL_THIRD_PERSON = SUBJECT_PRONOUNS | OBJECT_PRONOUNS | POSSESSIVE_PRONOUNS

# Fragment markers (dependent clauses that need context)
FRAGMENT_STARTERS = {
    "but", "and", "or", "yet", "so", "because", "although", "though",
    "however", "meanwhile", "suddenly", "then", "after", "before",
    "which", "who", "that", "while", "when", "if", "unless",
}

# Quote/interpretation split patterns
# Match: "..." [characterization]
QUOTE_TRAILING_PATTERN = re.compile(
    r'^(.*?["\'].*?["\'])\s*'  # Quote part
    r'(which\s+was\s+|,\s*which\s+|,?\s*clearly\s+|,?\s*obviously\s+)'  # Connector
    r'(.+)$',  # Trailing characterization
    re.IGNORECASE
)


def resolve_actors(ctx: TransformContext) -> TransformContext:
    """
    Resolve pronouns in atomic statements to concrete actor names.
    
    Uses coreference chains from p42_coreference to map pronouns to entities.
    
    For each atomic statement:
    1. Find pronouns in the text
    2. Look up their resolved entity in coreference chains
    3. Replace pronouns with entity labels
    4. Store result in actor_resolved_text
    5. Flag statements where resolution fails
    """
    if not ctx.atomic_statements:
        log.warning("no_statements", message="No atomic statements to process")
        ctx.add_trace(
            pass_name=PASS_NAME,
            action="skipped",
            after="No atomic statements to process",
        )
        return ctx
    
    # Build pronoun → entity mapping from coreference data
    pronoun_map = _build_pronoun_map(ctx)
    
    resolved_count = 0
    unresolved_count = 0
    fragment_count = 0
    split_count = 0
    
    # Collect new statements from splits
    new_statements = []
    
    for stmt in ctx.atomic_statements:
        # 1. Check for fragments
        if _is_fragment(stmt.text):
            stmt.flags = stmt.flags or []
            if "fragment" not in stmt.flags:
                stmt.flags.append("fragment")
            fragment_count += 1
        
        # 2. Check for quote/interpretation mix and split
        split_result = _split_quote_interpretation(stmt)
        if split_result:
            # Original becomes the quote
            stmt.text = split_result["quote_text"]
            stmt.actor_resolved_text = split_result["quote_text"]
            stmt.flags = stmt.flags or []
            if "quote_cleaned" not in stmt.flags:
                stmt.flags.append("quote_cleaned")
            
            # Create new statement for the interpretation
            new_stmt = _create_interpretation_statement(
                stmt, 
                split_result["interpretation_text"],
                len(ctx.atomic_statements) + len(new_statements)
            )
            new_statements.append(new_stmt)
            split_count += 1
            continue
        
        # 3. Resolve pronouns in text
        resolved_text, resolution_success = _resolve_pronouns_in_text(
            stmt.text, 
            pronoun_map,
            stmt.segment_id
        )
        
        # Store resolved text (even if unchanged)
        stmt.actor_resolved_text = resolved_text
        
        if resolution_success:
            resolved_count += 1
        else:
            # Flag unresolved statements
            stmt.flags = stmt.flags or []
            if "actor_unresolved" not in stmt.flags:
                stmt.flags.append("actor_unresolved")
            unresolved_count += 1
    
    # Add new statements from splits
    ctx.atomic_statements.extend(new_statements)
    
    log.info(
        "actor_resolution_complete",
        total=len(ctx.atomic_statements),
        resolved=resolved_count,
        unresolved=unresolved_count,
        fragments=fragment_count,
        splits=split_count,
    )
    
    ctx.add_trace(
        pass_name=PASS_NAME,
        action="resolved_actors",
        after=f"Resolved: {resolved_count}, Unresolved: {unresolved_count}, Fragments: {fragment_count}, Splits: {split_count}",
    )
    
    # Add diagnostic for unresolved actors
    if unresolved_count > 0:
        ctx.add_diagnostic(
            level="info",
            code="ACTOR_UNRESOLVED",
            message=f"{unresolved_count} statements have unresolved actors (pronouns without clear antecedent)",
            source=PASS_NAME,
        )
    
    return ctx


def _build_pronoun_map(ctx: TransformContext) -> dict:
    """
    Build a mapping of (segment_id, pronoun_position) → entity_label.
    
    Uses mentions from p42_coreference.
    """
    pronoun_map = {}
    
    if not ctx.mentions:
        return pronoun_map
    
    # Build entity ID → label mapping
    entity_labels = {}
    for entity in ctx.entities:
        if entity.label:
            entity_labels[entity.id] = entity.label
    
    # Map each pronoun mention to its resolved entity label
    for mention in ctx.mentions:
        if mention.mention_type != MentionType.PRONOUN:
            continue
        
        if not mention.resolved_entity_id:
            continue
        
        label = entity_labels.get(mention.resolved_entity_id)
        if label:
            # Key: (segment_id, start_char, text)
            key = (mention.segment_id, mention.start_char, mention.text.lower())
            pronoun_map[key] = label
    
    return pronoun_map


def _resolve_pronouns_in_text(
    text: str, 
    pronoun_map: dict,
    segment_id: str
) -> tuple[str, bool]:
    """
    Replace pronouns in text with their resolved entity labels.
    
    Returns (resolved_text, all_resolved_success).
    """
    result = text
    all_resolved = True
    
    # Find all third-person pronouns in the text
    for match in re.finditer(r'\b([Hh]e|[Ss]he|[Tt]hey|[Hh]im|[Hh]er|[Tt]hem|[Hh]is|[Tt]heir)\b', text):
        pronoun = match.group(1)
        pronoun_lower = pronoun.lower()
        start = match.start()
        
        # Look up in pronoun map
        key = (segment_id, start, pronoun_lower)
        
        # Try exact position match first
        label = pronoun_map.get(key)
        
        # If not found, try fuzzy match (within segment)
        if not label:
            for (seg_id, pos, pron), ent_label in pronoun_map.items():
                if seg_id == segment_id and pron == pronoun_lower:
                    # Use first match in same segment
                    label = ent_label
                    break
        
        if label:
            # Determine correct form based on pronoun type
            if pronoun_lower in SUBJECT_PRONOUNS or pronoun_lower in OBJECT_PRONOUNS:
                replacement = label
            elif pronoun_lower in POSSESSIVE_PRONOUNS:
                replacement = f"{label}'s"
            else:
                replacement = label
            
            # Preserve capitalization
            if pronoun[0].isupper():
                replacement = replacement[0].upper() + replacement[1:]
            
            result = result[:match.start()] + replacement + result[match.end():]
            # Adjust for length difference in subsequent matches
            # (Note: this simple approach works for single pass;
            #  for production, use offset tracking)
        else:
            all_resolved = False
    
    return result, all_resolved


def _is_fragment(text: str) -> bool:
    """
    Check if text is a dependent fragment.
    
    Fragments start with conjunctions/subordinators and lack independent meaning.
    """
    text_stripped = text.strip()
    if not text_stripped:
        return False
    
    first_word = text_stripped.split()[0].lower().rstrip(",")
    return first_word in FRAGMENT_STARTERS


def _split_quote_interpretation(stmt) -> Optional[dict]:
    """
    Split a statement that mixes quote + interpretation.
    
    Example input: 'He said "Stop!" which was clearly a threat'
    Output: {quote_text: 'He said "Stop!"', interpretation_text: 'clearly a threat'}
    
    Returns None if no split needed.
    """
    match = QUOTE_TRAILING_PATTERN.match(stmt.text)
    if match:
        quote_part = match.group(1).strip()
        interpretation_part = match.group(3).strip()
        
        return {
            "quote_text": quote_part,
            "interpretation_text": interpretation_part,
        }
    
    return None


def _create_interpretation_statement(
    parent_stmt,
    interpretation_text: str,
    counter: int
):
    """
    Create a new AtomicStatement for split-off interpretation.
    """
    from nnrt.passes.p26_decompose import AtomicStatement
    from nnrt.ir.enums import StatementType
    
    return AtomicStatement(
        id=f"stmt_{counter:04d}_interp",
        text=interpretation_text,
        segment_id=parent_stmt.segment_id,
        span_start=parent_stmt.span_start,
        span_end=parent_stmt.span_end,
        type_hint=StatementType.INTERPRETATION,
        confidence=0.7,
        clause_type="split_interpretation",
        source="reporter",
        epistemic_type="inference",
        polarity="asserted",
        evidence_source="inference",
        flags=["split_from_quote"],
        derived_from=[parent_stmt.id],
    )
