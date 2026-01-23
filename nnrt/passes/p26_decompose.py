"""
Pass 25 — Statement Decomposition

Decomposes segments into atomic statements using dependency parsing.

Each atomic statement contains exactly ONE predicate (action/claim/interpretation).
Compound sentences are split at clause boundaries (and, because, but, etc.).

This is the foundation for proper NNRT structural decomposition.
"""

from dataclasses import dataclass, field
from typing import Optional

from nnrt.core.context import TransformContext
from nnrt.core.logging import get_pass_logger
from nnrt.ir.enums import StatementType
from nnrt.nlp.spacy_loader import get_nlp

PASS_NAME = "p26_decompose"
log = get_pass_logger(PASS_NAME)


@dataclass
class AtomicStatement:
    """
    An atomic statement extracted from a segment.
    
    Atomic = one predicate, one fact/claim/interpretation.
    
    V4 Alpha: Every statement carries full epistemic metadata:
    - source: who is speaking (reporter, witness, medical, investigator, document)
    - epistemic_type: what kind of content (event, self_report, interpretation, 
                      legal_claim, quote, admin_action, medical_finding)
    - polarity: asserted/denied/uncertain
    
    V5: Added provenance tracking with source_type, source_entity_id, provenance_status
    """
    id: str
    text: str
    segment_id: str
    
    # Position in original input
    span_start: int
    span_end: int
    
    # Classification (preliminary, refined in p30_classify)
    type_hint: StatementType = StatementType.UNKNOWN
    confidence: float = 0.5
    
    # Decomposition metadata
    clause_type: str = "root"  # root, conj, advcl, ccomp
    connector: Optional[str] = None  # "and", "because", "but", etc.
    
    # =========================================================================
    # V4 ALPHA: Epistemic Tagging
    # =========================================================================
    
    # Source: Who is making this statement?
    # Values: reporter, witness, medical, investigator, document, officer
    source: str = "reporter"
    
    # Epistemic Type: What kind of statement is this?
    # Values: direct_event, self_report, interpretation, legal_claim,
    #         quote, admin_action, medical_finding, documented_fact
    epistemic_type: str = "unknown"
    
    # Polarity: Is this asserted, denied, or uncertain?
    # Values: asserted, denied, uncertain, hypothetical
    polarity: str = "asserted"
    
    # Evidence Source: What type of evidence supports this?
    # Values: direct_observation, self_report, third_party, document, inference
    evidence_source: str = "self_report"
    
    # Flags
    flags: list[str] = field(default_factory=list)
    
    # For interpretations: what observations is this derived from?
    # (populated later in p35_link_provenance)
    derived_from: list[str] = field(default_factory=list)
    
    # =========================================================================
    # V5: Provenance Tracking
    # =========================================================================
    
    # Source Type: Who provided this information?
    # Values: reporter, witness, document, medical, official, attorney, research
    source_type: str = "reporter"
    
    # Source Entity ID: Link to the Entity who is the source (if applicable)
    # e.g., "ent_abc123" for a witness
    source_entity_id: Optional[str] = None
    
    # Provenance Status: Has this been verified?
    # Values: verified, cited, missing, inference, unverifiable
    provenance_status: str = "missing"
    
    # =========================================================================
    # V7.5: Sentence Completeness (for fragment detection)
    # =========================================================================
    
    # Is this a complete sentence with subject + predicate?
    # Used by renderer to filter out dependent clause fragments
    is_complete_sentence: bool = True
    

    # =========================================================================
    # V4 ALPHA: Attribution & Aberration
    # =========================================================================
    
    # Attributed text: The rewritten form in attributed voice
    # Example: "This was racial profiling" → "reporter characterizes the stop as racial profiling"
    attributed_text: Optional[str] = None
    
    # Aberration: Statement is quarantined (invective, conspiracy, etc.)
    # Aberrated statements are NEVER exposed as text, only metadata
    is_aberrated: bool = False
    aberration_reason: Optional[str] = None
    
    # Extracted claim: The core factual claim extracted for attribution
    # Example: "racial profiling" extracted from "This was clearly racial profiling"
    extracted_claim: Optional[str] = None
    
    # =========================================================================
    # V5: Actor Resolution
    # =========================================================================
    
    # Actor-resolved text: The statement with pronouns replaced by entity names
    # Example: "He grabbed my arm" → "Officer Jenkins grabbed reporter's arm"
    actor_resolved_text: Optional[str] = None



def decompose(ctx: TransformContext) -> TransformContext:
    """
    Decompose segments into atomic statements.
    
    Uses spaCy dependency parsing to find clause boundaries:
    - ROOT: Main clause verb
    - conj: Coordinated clause (and, or)
    - advcl: Adverbial clause (because, although, when)
    - ccomp: Complement clause (that, whether)
    
    Each clause becomes an atomic statement.
    """
    if not ctx.segments:
        log.warning("no_segments", message="No segments to decompose")
        ctx.add_diagnostic(
            level="warning",
            code="NO_SEGMENTS",
            message="No segments to decompose",
            source=PASS_NAME,
        )
        return ctx
    
    log.verbose("starting_decomposition", segments=len(ctx.segments))
    
    nlp = get_nlp()
    all_statements: list[AtomicStatement] = []
    statement_counter = 0
    clause_type_counts = {}
    
    for segment in ctx.segments:
        # Skip segments that are pure quotes (preserve verbatim)
        if "direct_quote" in segment.contexts and segment.quote_depth > 0:
            # Create single statement for the whole quote
            stmt = AtomicStatement(
                id=f"stmt_{statement_counter:04d}",
                text=segment.text,
                segment_id=segment.id,
                span_start=segment.start_char,
                span_end=segment.end_char,
                type_hint=StatementType.QUOTE,
                confidence=1.0,
                clause_type="quote",
                flags=["quoted_content"],
            )
            all_statements.append(stmt)
            statement_counter += 1
            continue
        
        # Parse the segment
        doc = nlp(segment.text)
        
        # Find all clause heads (verbs that anchor clauses)
        clauses = _extract_clauses(doc, segment)
        
        if not clauses:
            # No clauses found - treat whole segment as one statement
            stmt = AtomicStatement(
                id=f"stmt_{statement_counter:04d}",
                text=segment.text,
                segment_id=segment.id,
                span_start=segment.start_char,
                span_end=segment.end_char,
                type_hint=_infer_type_hint(segment.text, doc),
                confidence=0.5,
                clause_type="root",
            )
            all_statements.append(stmt)
            statement_counter += 1
        else:
            # Create a statement for each clause
            for clause in clauses:
                stmt = AtomicStatement(
                    id=f"stmt_{statement_counter:04d}",
                    text=clause["text"],
                    segment_id=segment.id,
                    span_start=segment.start_char + clause["start"],
                    span_end=segment.start_char + clause["end"],
                    type_hint=clause["type_hint"],
                    confidence=clause["confidence"],
                    clause_type=clause["clause_type"],
                    connector=clause.get("connector"),
                    flags=clause.get("flags", []),
                    is_complete_sentence=clause.get("is_complete", True),
                )
                all_statements.append(stmt)
                statement_counter += 1
                clause_type_counts[clause["clause_type"]] = clause_type_counts.get(clause["clause_type"], 0) + 1
    
    # Store in context
    ctx.atomic_statements = all_statements
    
    log.info("decomposed",
        atomic_statements=len(all_statements),
        segments=len(ctx.segments),
        avg_per_segment=round(len(all_statements) / max(len(ctx.segments), 1), 2),
    )
    log.debug("clause_types", **clause_type_counts)
    
    ctx.add_trace(
        pass_name=PASS_NAME,
        action="decomposed_segments",
        after=f"{len(all_statements)} atomic statements from {len(ctx.segments)} segments",
    )
    
    return ctx


def _is_complete_clause(tokens: list) -> bool:
    """
    V7.5: Check if a clause is a complete sentence (has subject + verb).
    
    Uses spaCy dependency labels to detect:
    - Subject: nsubj, nsubjpass, expl (expletive 'it'/'there')
    - Verb: Any VERB that isn't just an auxiliary, OR an AUX as ROOT (copular)
    - Dependent: Starts with subordinating conjunction (that, which, who, etc.)
    
    This replaces the brittle FRAGMENT_PATTERNS string matching approach.
    """
    if not tokens:
        return False
    
    # Check for subject
    subject_deps = {'nsubj', 'nsubjpass', 'expl', 'csubj', 'csubjpass'}
    has_subject = any(tok.dep_ in subject_deps for tok in tokens)
    
    # Check for main verb (not just auxiliary)
    # V7.5.1: Also accept AUX as ROOT (copular sentences like "I was scared")
    has_main_verb = any(
        (tok.pos_ == 'VERB' and tok.dep_ not in ('aux', 'auxpass')) or
        (tok.pos_ == 'AUX' and tok.dep_ == 'ROOT')  # Copular sentences
        for tok in tokens
    )
    
    # V7.5.1: Check for subordinating conjunction (makes it a dependent clause)
    # E.g., "that they cut into my wrists" starts with SCONJ
    has_subordinator = any(tok.dep_ == 'mark' and tok.pos_ == 'SCONJ' for tok in tokens)
    if has_subordinator:
        return False  # Dependent clause, not a standalone sentence
    
    # V7.5.2: Check for relative pronouns at start (which, who, whom, whose)
    # E.g., "which proves they used excessive force" - starts with relative pronoun
    relative_pronouns = {'which', 'who', 'whom', 'whose'}
    if tokens and tokens[0].text.lower() in relative_pronouns:
        return False  # Relative clause, not a standalone sentence
    
    return has_subject and has_main_verb


def _extract_clauses(doc, segment) -> list[dict]:
    """
    Extract clause boundaries using dependency parsing.
    
    Returns list of clause dicts with:
    - text: clause text
    - start/end: character offsets within segment
    - clause_type: root, conj, advcl, etc.
    - connector: the word linking this clause (and, because, etc.)
    - type_hint: preliminary statement type
    """
    clauses = []
    
    # Find all clause heads
    clause_heads = []
    for token in doc:
        if token.dep_ == "ROOT":
            clause_heads.append({
                "token": token,
                "type": "root",
                "connector": None,
            })
        elif token.dep_ == "conj" and token.pos_ == "VERB":
            # Find the connector (cc)
            connector = None
            for child in token.head.children:
                if child.dep_ == "cc" and child.i < token.i:
                    connector = child.text.lower()
                    break
            clause_heads.append({
                "token": token,
                "type": "conj",
                "connector": connector,
            })
        elif token.dep_ == "advcl":
            # Find the marker (because, although, etc.)
            connector = None
            for child in token.children:
                if child.dep_ == "mark":
                    connector = child.text.lower()
                    break
            clause_heads.append({
                "token": token,
                "type": "advcl",
                "connector": connector,
            })
        elif token.dep_ == "ccomp":
            clause_heads.append({
                "token": token,
                "type": "ccomp",
                "connector": None,
            })
    
    if not clause_heads:
        return []
    
    if len(clause_heads) == 1:
        # Single clause - return the whole segment
        head = clause_heads[0]
        # V7.5: Check sentence completeness using NLP
        is_complete = _is_complete_clause(list(doc))
        return [{
            "text": doc.text,
            "start": 0,
            "end": len(doc.text),
            "clause_type": head["type"],
            "connector": head["connector"],
            "type_hint": _infer_type_hint_from_head(head),
            "confidence": 0.7,
            "flags": [],
            "is_complete": is_complete,
        }]
    
    # Multiple clauses - split at clause boundaries
    # Sort by position
    clause_heads.sort(key=lambda x: x["token"].i)
    
    # Build exclusion sets for each clause type
    # advcl tokens are excluded from everything else
    # conj tokens (minus advcl) are excluded from root
    advcl_tokens: set[int] = set()
    for head in clause_heads:
        if head["type"] == "advcl":
            for tok in head["token"].subtree:
                advcl_tokens.add(tok.i)
    
    conj_tokens: set[int] = set()  # conj tokens excluding advcl
    for head in clause_heads:
        if head["type"] == "conj":
            for tok in head["token"].subtree:
                if tok.i not in advcl_tokens:
                    conj_tokens.add(tok.i)
    
    for i, head in enumerate(clause_heads):
        if head["type"] == "root":
            # For ROOT: exclude conj, advcl, and cc
            clause_tokens = []
            for tok in head["token"].subtree:
                if tok.i not in conj_tokens and tok.i not in advcl_tokens:
                    if tok.dep_ != "cc":
                        clause_tokens.append(tok)
            
            if not clause_tokens:
                clause_tokens = [head["token"]]
            
            # Sort by position and reconstruct text
            clause_tokens.sort(key=lambda t: t.i)
            
            # Use text_with_ws to preserve original spacing (handles contractions)
            # text_with_ws includes the whitespace after each token
            clause_text = "".join(t.text_with_ws for t in clause_tokens).strip()
            
            # Use first token's start and last token's end for span tracking
            start_idx = clause_tokens[0].idx
            end_idx = clause_tokens[-1].idx + len(clause_tokens[-1].text)
            
        elif head["type"] == "conj":
            # For CONJ: exclude advcl tokens and connector
            clause_tokens = []
            for tok in head["token"].subtree:
                if tok.i not in advcl_tokens:
                    if head["connector"] and tok.text.lower() == head["connector"]:
                        continue  # Skip connector
                    clause_tokens.append(tok)
            
            if not clause_tokens:
                clause_tokens = [head["token"]]
            
            # Sort by position and reconstruct text
            clause_tokens.sort(key=lambda t: t.i)
            # Use text_with_ws to preserve original spacing (contractions)
            clause_text = "".join(t.text_with_ws for t in clause_tokens).strip()
            start_idx = clause_tokens[0].idx
            end_idx = clause_tokens[-1].idx + len(clause_tokens[-1].text)
            
        else:
            # For advcl and others: use subtree but exclude connector
            subtree = list(head["token"].subtree)
            
            # Exclude the connector word itself
            if head["connector"]:
                subtree = [t for t in subtree if t.text.lower() != head["connector"]]
            
            if not subtree:
                subtree = [head["token"]]
            
            # Sort by position and reconstruct text
            subtree.sort(key=lambda t: t.i)
            # Use text_with_ws to preserve original spacing (contractions)
            clause_text = "".join(t.text_with_ws for t in subtree).strip()
            start_idx = subtree[0].idx
            end_idx = subtree[-1].idx + len(subtree[-1].text)
        
        # clause_text is now set in each branch above
        
        # Infer type hint
        type_hint = _infer_type_hint_from_head(head)
        
        # Check for intent-related clauses (causal)
        flags = []
        subtree_for_check = list(head["token"].subtree)
        if head["type"] == "advcl" and head["connector"] in ("because", "since", "as"):
            flags.append("causal_clause")
            # Causal clauses often contain interpretations
            if any(tok.lemma_ in ("want", "intend", "try", "mean", "plan") for tok in subtree_for_check):
                type_hint = StatementType.INTERPRETATION
                flags.append("intent_attribution")
        
        # V7.5: Check sentence completeness using NLP
        is_complete = _is_complete_clause(subtree_for_check)
        
        clauses.append({
            "text": clause_text,
            "start": start_idx,
            "end": end_idx,
            "clause_type": head["type"],
            "connector": head["connector"],
            "type_hint": type_hint,
            "confidence": 0.6,
            "flags": flags,
            "is_complete": is_complete,
        })
    
    return clauses


def _infer_type_hint_from_head(head: dict) -> StatementType:
    """Infer statement type from clause head characteristics."""
    token = head["token"]
    
    # Causal clauses with certain verbs are often interpretations
    if head["type"] == "advcl" and head["connector"] in ("because", "since"):
        # Check for intent verbs
        if token.lemma_ in ("want", "intend", "try", "mean", "plan", "decide"):
            return StatementType.INTERPRETATION
    
    # Default to claim for now (will be refined in p30_classify)
    return StatementType.CLAIM


def _infer_type_hint(text: str, doc) -> StatementType:
    """Infer statement type from text content."""
    text_lower = text.lower()
    
    # Check for intent language
    intent_markers = ["wanted to", "tried to", "meant to", "deliberately", "intentionally", "on purpose"]
    if any(marker in text_lower for marker in intent_markers):
        return StatementType.INTERPRETATION
    
    # Check for quote markers
    if '"' in text or "'" in text:
        return StatementType.QUOTE
    
    # Default to claim
    return StatementType.CLAIM
