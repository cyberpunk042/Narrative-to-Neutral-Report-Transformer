"""
p46_group_statements — Semantic clustering of atomic statements.

This pass organizes atomic statements into meaningful groups based on
their semantic content. Groups make the narrative easier to understand
and present in a structured format.

Algorithm:
1. CLASSIFY EACH STATEMENT
   - Use keyword patterns to identify group type
   - Use entity roles (WITNESS → WITNESS_ACCOUNT, medical titles → MEDICAL)
   - Use statement type (QUOTE → QUOTE group)

2. CLUSTER CONSECUTIVE STATEMENTS
   - Group adjacent statements of the same type
   - Allow overlapping keywords to influence grouping

3. ASSIGN GROUP METADATA
   - Generate descriptive titles
   - Track primary entity for each group
   - Calculate evidence strength

Group Types:
- ENCOUNTER: Physical actions during the incident
- WITNESS_ACCOUNT: Third-party observations  
- MEDICAL: Medical treatment, documented injuries
- OFFICIAL: Complaints, investigations, official records
- EMOTIONAL: Psychological/emotional impact
- BACKGROUND: Context before the incident
- AFTERMATH: Events after the incident
- QUOTE: Direct speech preserved
"""

import re
import structlog
from typing import Optional
from collections import defaultdict

from nnrt.core.context import TransformContext
from nnrt.ir.schema_v0_1 import StatementGroup, Entity
from nnrt.ir.enums import GroupType, EntityRole, StatementType
from nnrt.policy.engine import get_policy_engine

log = structlog.get_logger("nnrt.p46_group_statements")

PASS_NAME = "p46_group_statements"

# V7 / Stage 4: Use YAML rules for classification (set to True to enable)
USE_YAML_RULES = True

# ============================================================================
# DEPRECATED: Keyword Patterns for Group Classification
# V7 / Stage 4: These patterns are now in _grouping/statement_groups.yaml
# They remain here for backwards compatibility but will be removed.
# ============================================================================

# DEPRECATED: Use _grouping/statement_groups.yaml instead
# ENCOUNTER: Physical actions, confrontation
ENCOUNTER_PATTERNS = [
    r'\b(grabbed|pushed|shoved|hit|struck|punched|kicked)',
    r'\b(arrested|handcuffed|detained|restrained)',
    r'\b(approached|confronted|stopped)',
    r'\b(pulled|dragged|threw|slammed)',
    r'\b(choked|tased|sprayed|shot)',
    r'\b(force|assault|attack)',
]

# DEPRECATED: Use _grouping/statement_groups.yaml instead
# MEDICAL: Treatment, injuries, hospitals
MEDICAL_PATTERNS = [
    r'\b(hospital|emergency room|clinic|urgent care)',
    r'\b(doctor|physician|nurse|paramedic|emt)',
    r'\b(treated|examined|diagnosed|documented)',
    r'\b(injury|injuries|wound|bruise|fracture)',
    r'\b(x-ray|ct scan|mri|medical record)',
    r'\b(pain|hurt|bleeding|swelling)',
    r'\bdr\.\s+\w+',  # Dr. Name
]

# DEPRECATED: Use _grouping/statement_groups.yaml instead
# WITNESS: Third-party observations
WITNESS_PATTERNS = [
    r'\b(witness|bystander|onlooker)',
    r'\b(saw|watched|observed|noticed)\s+(the|what|him|her|them)',
    r'\b(recording|filmed|videotaped|photographed)',
    r'\b(told|said|reported|stated)\s+(that|he|she|they)',
]

# DEPRECATED: Use _grouping/statement_groups.yaml instead
# OFFICIAL: Administrative, legal
OFFICIAL_PATTERNS = [
    r'\b(complaint|report|investigation)',
    r'\b(filed|submitted|reported)',
    r'\b(internal affairs|IA|police department)',
    r'\b(case number|badge number|report number)',
    r'\b(hearing|trial|court|judge)',
    r'\b(policy|procedure|within policy)',
    r'\b(letter|notice|notification)',
]

# DEPRECATED: Use _grouping/statement_groups.yaml instead
# EMOTIONAL: Psychological impact
EMOTIONAL_PATTERNS = [
    r'\b(terrified|scared|afraid|fear)',
    r'\b(angry|frustrated|humiliated|embarrassed)',
    r'\b(anxious|anxiety|panic|ptsd)',
    r'\b(couldn\'t sleep|nightmares|flashbacks)',
    r'\b(traumat|shock|distress)',
    r'\b(crying|screamed|sobbed)',
]

# DEPRECATED: Use _grouping/statement_groups.yaml instead
# BACKGROUND: Context before incident
BACKGROUND_PATTERNS = [
    r'\b(before|prior to|earlier that)',
    r'\b(was walking|was driving|was standing)',
    r'\b(on my way|heading)',
]

# DEPRECATED: Use _grouping/statement_groups.yaml instead
# AFTERMATH: Events after incident
AFTERMATH_PATTERNS = [
    r'\b(released|let go|freed)',
    r'\b(the next day|days later|weeks later|months later)',
    r'\b(after that|subsequently|eventually)',
    r'\b(still|continue to|ongoing)',
]


def group_statements(ctx: TransformContext) -> TransformContext:
    """
    Group atomic statements into semantic clusters.
    
    This pass:
    1. Classifies each statement by semantic content
    2. Clusters related statements
    3. Assigns metadata (title, primary entity)
    """
    if not ctx.atomic_statements:
        log.info("no_statements", pass_name=PASS_NAME, message="No statements to group")
        ctx.add_trace(PASS_NAME, "skipped", after="No statements")
        return ctx
    
    # =========================================================================
    # Phase 1: Classify Each Statement
    # =========================================================================
    
    # Map statement_id -> group_type
    statement_groups_map: dict[str, GroupType] = {}
    
    for stmt in ctx.atomic_statements:
        group_type = _classify_statement(stmt, ctx.entities)
        statement_groups_map[stmt.id] = group_type
    
    # =========================================================================
    # Phase 2: Cluster Consecutive Statements
    # =========================================================================
    
    # Group adjacent statements of the same type
    groups: list[StatementGroup] = []
    
    # Track statements by group type for building groups
    current_type: Optional[GroupType] = None
    current_statements: list[str] = []
    current_entity_id: Optional[str] = None
    
    for stmt in ctx.atomic_statements:
        stmt_type = statement_groups_map[stmt.id]
        
        # Check if this statement continues the current group
        if stmt_type == current_type:
            current_statements.append(stmt.id)
        else:
            # Save current group if exists
            if current_statements and current_type:
                group = _create_group(
                    current_type, 
                    current_statements, 
                    len(groups),
                    current_entity_id,
                    ctx
                )
                groups.append(group)
            
            # Start new group
            current_type = stmt_type
            current_statements = [stmt.id]
            current_entity_id = _find_primary_entity(stmt, ctx.entities)
    
    # Don't forget the last group
    if current_statements and current_type:
        group = _create_group(
            current_type, 
            current_statements, 
            len(groups),
            current_entity_id,
            ctx
        )
        groups.append(group)
    
    # =========================================================================
    # Phase 3: Merge Small Adjacent Groups
    # =========================================================================
    
    # Optionally merge very small groups of the same type
    merged_groups: list[StatementGroup] = []
    for group in groups:
        if merged_groups and _should_merge(merged_groups[-1], group):
            # Merge into previous group
            merged_groups[-1].statement_ids.extend(group.statement_ids)
        else:
            merged_groups.append(group)
    
    # Store results
    ctx.statement_groups = merged_groups
    
    # Log summary
    type_counts = defaultdict(int)
    for g in merged_groups:
        type_counts[g.group_type.value] += 1
    
    log.info(
        "grouped",
        pass_name=PASS_NAME,
        channel="SEMANTIC",
        total_groups=len(merged_groups),
        total_statements=len(ctx.atomic_statements),
        **dict(type_counts),
    )
    
    ctx.add_trace(
        PASS_NAME,
        "statements_grouped",
        after=f"{len(merged_groups)} groups from {len(ctx.atomic_statements)} statements",
    )
    
    return ctx


def _classify_statement(stmt, entities: list[Entity]) -> GroupType:
    """
    Classify a statement into a group type based on content and context.
    
    V7 / Stage 4: Uses PolicyEngine YAML rules if USE_YAML_RULES is True.
    """
    # Check statement type first (QUOTE is preserved)
    if hasattr(stmt, 'type_hint') and stmt.type_hint == StatementType.QUOTE:
        return GroupType.QUOTE
    
    # V7 / Stage 4: Use YAML rules for classification
    if USE_YAML_RULES:
        return _classify_statement_yaml(stmt, entities)
    
    # Legacy: Use Python patterns
    return _classify_statement_legacy(stmt, entities)


def _classify_statement_yaml(stmt, entities: list[Entity]) -> GroupType:
    """
    V7 / Stage 4: Classify using PolicyEngine YAML rules.
    
    Uses apply_group_rules() which reads from _grouping/statement_groups.yaml.
    """
    text = stmt.text if hasattr(stmt, 'text') else ""
    
    # Try PolicyEngine classification
    engine = get_policy_engine()
    group_name = engine.apply_group_rules(text)
    
    if group_name:
        # Map YAML group names to GroupType enum
        group_map = {
            "encounter": GroupType.ENCOUNTER,
            "medical": GroupType.MEDICAL,
            "official": GroupType.OFFICIAL,
            "emotional": GroupType.EMOTIONAL,
            "witness_account": GroupType.WITNESS_ACCOUNT,
            "background": GroupType.BACKGROUND,
            "aftermath": GroupType.AFTERMATH,
        }
        return group_map.get(group_name, GroupType.ENCOUNTER)
    
    # Fallback: Check witness entity mentions (entity-based, not pattern-based)
    text_lower = text.lower()
    for entity in entities:
        if entity.role == EntityRole.WITNESS:
            if entity.label and entity.label.lower() in text_lower:
                return GroupType.WITNESS_ACCOUNT
    
    # Default: ENCOUNTER (most common for incident narratives)
    return GroupType.ENCOUNTER


def _classify_statement_legacy(stmt, entities: list[Entity]) -> GroupType:
    """
    DEPRECATED: Legacy classification using Python patterns.
    
    This function will be removed once YAML rules are fully validated.
    """
    text = stmt.text.lower() if hasattr(stmt, 'text') else ""
    
    # Check for pattern matches (priority order)
    
    # MEDICAL has high priority - clear indicators
    if _matches_any(text, MEDICAL_PATTERNS):
        return GroupType.MEDICAL
    
    # OFFICIAL - administrative/legal language
    if _matches_any(text, OFFICIAL_PATTERNS):
        return GroupType.OFFICIAL
    
    # EMOTIONAL - psychological impact
    if _matches_any(text, EMOTIONAL_PATTERNS):
        return GroupType.EMOTIONAL
    
    # WITNESS - check for witness entity mentions
    for entity in entities:
        if entity.role == EntityRole.WITNESS:
            if entity.label and entity.label.lower() in text:
                return GroupType.WITNESS_ACCOUNT
    
    # WITNESS - pattern matching
    if _matches_any(text, WITNESS_PATTERNS):
        return GroupType.WITNESS_ACCOUNT
    
    # BACKGROUND - before incident
    if _matches_any(text, BACKGROUND_PATTERNS):
        return GroupType.BACKGROUND
    
    # AFTERMATH - after incident
    if _matches_any(text, AFTERMATH_PATTERNS):
        return GroupType.AFTERMATH
    
    # ENCOUNTER - default for physical actions
    if _matches_any(text, ENCOUNTER_PATTERNS):
        return GroupType.ENCOUNTER
    
    # Default: ENCOUNTER (most common for incident narratives)
    return GroupType.ENCOUNTER


def _matches_any(text: str, patterns: list[str]) -> bool:
    """Check if text matches any of the regex patterns."""
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def _find_primary_entity(stmt, entities: list[Entity]) -> Optional[str]:
    """Find the primary entity mentioned in a statement."""
    text = stmt.text.lower() if hasattr(stmt, 'text') else ""
    
    for entity in entities:
        if entity.label and entity.label.lower() in text:
            return entity.id
    
    return None


def _create_group(
    group_type: GroupType,
    statement_ids: list[str],
    sequence: int,
    primary_entity_id: Optional[str],
    ctx: TransformContext,
) -> StatementGroup:
    """Create a StatementGroup with appropriate metadata."""
    
    # Generate title based on group type
    title = _generate_title(group_type, sequence, primary_entity_id, ctx)
    
    # Calculate evidence strength
    evidence_strength = _calculate_evidence_strength(statement_ids, ctx)
    
    return StatementGroup(
        id=f"grp_{sequence:04d}",
        group_type=group_type,
        title=title,
        statement_ids=list(statement_ids),
        primary_entity_id=primary_entity_id,
        sequence_in_narrative=sequence,
        evidence_strength=evidence_strength,
    )


def _generate_title(
    group_type: GroupType, 
    sequence: int, 
    primary_entity_id: Optional[str],
    ctx: TransformContext,
) -> str:
    """Generate a human-readable title for a group."""
    
    # Try to get entity name for personalized title
    entity_name = None
    if primary_entity_id:
        entity = next((e for e in ctx.entities if e.id == primary_entity_id), None)
        if entity and entity.label:
            entity_name = entity.label
    
    titles = {
        GroupType.ENCOUNTER: "Incident Description",
        GroupType.WITNESS_ACCOUNT: f"{entity_name}'s Account" if entity_name else "Witness Account",
        GroupType.MEDICAL: "Medical Documentation",
        GroupType.OFFICIAL: "Official Records",
        GroupType.EMOTIONAL: "Psychological Impact",
        GroupType.BACKGROUND: "Background Context",
        GroupType.AFTERMATH: "Aftermath",
        GroupType.QUOTE: "Direct Quote",
        GroupType.UNKNOWN: "Other",
    }
    
    base_title = titles.get(group_type, "Details")
    
    # Add sequence indicator if multiple groups of same type
    # (This would require scanning all groups, simplified for now)
    return base_title


def _calculate_evidence_strength(statement_ids: list[str], ctx: TransformContext) -> float:
    """
    Calculate evidence strength based on statement characteristics.
    
    Higher strength for:
    - More statements (more detail)
    - OBSERVATION type statements (direct witness)
    - Presence of documentary evidence
    """
    if not statement_ids:
        return 0.5
    
    # Base score
    score = 0.5
    
    # More statements = more detail
    if len(statement_ids) >= 3:
        score += 0.1
    if len(statement_ids) >= 5:
        score += 0.1
    
    # Check for observation-type statements
    for stmt in ctx.atomic_statements:
        if stmt.id in statement_ids:
            if hasattr(stmt, 'type_hint') and stmt.type_hint == StatementType.OBSERVATION:
                score += 0.1
                break
    
    return min(score, 1.0)


def _should_merge(group1: StatementGroup, group2: StatementGroup) -> bool:
    """Determine if two groups should be merged."""
    # Only merge if same type and both small
    if group1.group_type != group2.group_type:
        return False
    
    # Don't merge if combined would be too large
    if len(group1.statement_ids) + len(group2.statement_ids) > 10:
        return False
    
    # Merge small adjacent groups of same type
    if len(group1.statement_ids) <= 2 and len(group2.statement_ids) <= 2:
        return True
    
    return False
