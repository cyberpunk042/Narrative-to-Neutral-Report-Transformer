"""
Pass 28: Provenance Linking

Links interpretations to their source observations/claims.

Uses the clause structure from decomposition to establish provenance:
- advcl clauses (because/since) are derived from their parent clauses
- conj clauses share context with the root clause
- Statements in the same segment share implicit context

This creates the "derived_from" links essential for proper NNRT output.
"""

from typing import Optional

from nnrt.core.context import TransformContext
from nnrt.ir.enums import StatementType

PASS_NAME = "p28_link_provenance"

# Clause types that indicate derivation from parent
DERIVED_CLAUSE_TYPES = {"advcl", "ccomp", "relcl"}

# Connectors that signal causal/evidential relationships
CAUSAL_CONNECTORS = {"because", "since", "as", "so", "therefore", "thus"}
CONTRAST_CONNECTORS = {"but", "however", "although", "though", "despite"}
RESULT_CONNECTORS = {"so", "therefore", "thus", "hence"}


def link_provenance(ctx: TransformContext) -> TransformContext:
    """
    Establish provenance links between atomic statements.
    
    Interpretations are linked to the observations/claims they interpret.
    This uses the clause structure already captured during decomposition.
    """
    if not ctx.atomic_statements:
        ctx.add_trace(
            pass_name=PASS_NAME,
            action="skipped",
            after="No atomic statements to link",
        )
        return ctx
    
    # Build index of statements by segment
    statements_by_segment: dict[str, list] = {}
    for stmt in ctx.atomic_statements:
        seg_id = stmt.segment_id
        if seg_id not in statements_by_segment:
            statements_by_segment[seg_id] = []
        statements_by_segment[seg_id].append(stmt)
    
    links_created = 0
    
    # Process each segment's statements
    for seg_id, statements in statements_by_segment.items():
        if len(statements) < 2:
            continue  # Need at least 2 statements to link
        
        # Find root and conj clauses (potential sources)
        source_statements = [
            s for s in statements 
            if s.clause_type in ("root", "conj")
        ]
        
        # Find derived clauses (interpretations, advcl, etc.)
        for stmt in statements:
            if stmt.clause_type in DERIVED_CLAUSE_TYPES:
                # This statement is derived from the source statements
                derived_from = _find_sources(stmt, source_statements, statements)
                
                if derived_from:
                    stmt.derived_from = derived_from
                    links_created += 1
            
            # Also link interpretations even if clause_type is different
            elif stmt.type_hint == StatementType.INTERPRETATION:
                # Interpretations without clear clause structure
                # Link to all preceding claims/observations in same segment
                derived_from = _find_preceding_sources(stmt, statements)
                
                if derived_from and not stmt.derived_from:
                    stmt.derived_from = derived_from
                    links_created += 1
    
    ctx.add_trace(
        pass_name=PASS_NAME,
        action="linked_provenance",
        after=f"{links_created} provenance links created",
    )
    
    return ctx


def _find_sources(
    target: "AtomicStatement", 
    source_candidates: list, 
    all_statements: list
) -> list[str]:
    """
    Find source statements for a derived statement.
    
    For advcl (because) clauses, sources are:
    1. The root clause
    2. Any conj clauses before the advcl
    
    For ccomp (that) clauses, source is usually the root.
    """
    sources = []
    
    # Get position of target statement
    target_idx = all_statements.index(target)
    
    for candidate in source_candidates:
        # Source must come before (or be) the target's structural parent
        candidate_idx = all_statements.index(candidate)
        
        if candidate_idx < target_idx:
            # Candidate is before target - likely a source
            if candidate.clause_type == "root":
                sources.append(candidate.id)
            elif candidate.clause_type == "conj":
                sources.append(candidate.id)
    
    # If we have causal connector, all preceding sources are valid
    if target.connector and target.connector in CAUSAL_CONNECTORS:
        # Already have the sources
        pass
    
    return sources


def _find_preceding_sources(
    target: "AtomicStatement",
    all_statements: list
) -> list[str]:
    """
    Find sources for interpretations without clear clause structure.
    
    Links to preceding claims/observations in the same segment.
    """
    sources = []
    target_idx = all_statements.index(target)
    
    for i, stmt in enumerate(all_statements):
        if i >= target_idx:
            break  # Only look at preceding statements
        
        if stmt.type_hint in (StatementType.CLAIM, StatementType.OBSERVATION):
            sources.append(stmt.id)
    
    return sources
