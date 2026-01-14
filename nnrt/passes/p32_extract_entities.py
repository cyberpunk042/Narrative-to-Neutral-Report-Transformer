"""
Pass 32 — Entity Extraction

Extracts and resolves entities (people, vehicles, objects) from the narrative.
Resolves pronouns and links mentions to canonical entities.
Replaces the legacy entity logic in p40.
"""

from collections import defaultdict
from typing import Optional, Dict, List
from uuid import uuid4

from nnrt.core.context import TransformContext
from nnrt.ir.enums import EntityRole, EntityType, IdentifierType, UncertaintyType
from nnrt.ir.schema_v0_1 import Entity, UncertaintyMarker
from nnrt.nlp.spacy_loader import get_nlp

PASS_NAME = "p32_extract_entities"

# -----------------------------------------------------------------------------
# Constants & Patterns
# -----------------------------------------------------------------------------

REPORTER_PRONOUNS = {"i", "me", "my", "mine", "myself", "we", "us", "our", "ours"}

# Pronouns to resolve
RESOLVABLE_PRONOUNS = {
    "he", "him", "his", "himself",
    "she", "her", "hers", "herself",
    "they", "them", "their", "theirs", "themselves"
}

# Generic terms that usually map to new entities if not determining
GENERIC_SUBJECTS = {"subject", "suspect", "individual", "male", "female", "driver", "passenger", "partner", "manager", "employee"}
AUTHORITY_TITLES = {"officer", "deputy", "sergeant", "detective", "lieutenant", "chief", "sheriff", "trooper"}

# -----------------------------------------------------------------------------
# Pass Implementation
# -----------------------------------------------------------------------------


def extract_entities(ctx: TransformContext) -> TransformContext:
    nlp = get_nlp()
    
    # 1. Initialize Canonical Entities
    entities: List[Entity] = []
    
    # Always exist: Reporter
    reporter = Entity(
        id=f"ent_{uuid4().hex[:8]}",
        type=EntityType.PERSON,
        role=EntityRole.REPORTER,
        label="Reporter",
        mentions=[]
    )
    entities.append(reporter)
    
    # 2. Seed from Identifiers (p30)
    # Map Identifier ID -> Entity
    identifier_map: Dict[str, Entity] = {}
    
    for ident in ctx.identifiers:
        if ident.type in (IdentifierType.NAME, IdentifierType.BADGE_NUMBER, IdentifierType.EMPLOYEE_ID):
            # Create Authority/Person entity
            # Check if likely authority
            is_authority = (
                ident.type != IdentifierType.NAME or 
                any(t in ident.value.lower() for t in AUTHORITY_TITLES)
            )
            role = EntityRole.AUTHORITY if is_authority else EntityRole.WITNESS # Default, refinement later
            
            # Simple deduplication by value (e.g. Badge #123)
            # Find existing entity with same label?
            existing = next((e for e in entities if e.label == ident.value), None)
            
            if existing:
                ent = existing
            else:
                ent = Entity(
                    id=f"ent_{uuid4().hex[:8]}",
                    type=EntityType.PERSON,
                    role=role,
                    label=ident.value,
                    mentions=[]
                )
                entities.append(ent)
                
            identifier_map[ident.id] = ent

    # 3. Sequential Processing (for Resolution)
    # We maintain a "focus" history for pronoun resolution
    recent_entities: List[Entity] = [] 
    
    for segment in ctx.segments:
        doc = nlp(segment.text)
        
        # We need to map spans in this segment to SemanticSpan IDs eventually,
        # but for resolution we just need offsets.
        
        # Iterate noun chunks and pronouns
        for token in doc:
            text_lower = token.text.lower()
            
            # Skip non-nominal
            if token.pos_ not in ("PRON", "PROPN", "NOUN"):
                continue
                
            match_entity = None
            
            # A. Check Reporter
            if text_lower in REPORTER_PRONOUNS:
                match_entity = reporter
            
            # B. Check Pronoun Resolution
            elif text_lower in RESOLVABLE_PRONOUNS:
                # Find most recent compatible entity
                # He/Him -> Person, not Reporter (usually)
                candidates = [e for e in reversed(recent_entities) if e != reporter and e.type == EntityType.PERSON]
                if candidates:
                    # Detect Ambiguity (Multiple valid candidates)
                    if len(candidates) > 1:
                        lbls = [c.label or "Unknown" for c in candidates[:3]]
                        marker = UncertaintyMarker(
                            id=f"unc_{uuid4().hex[:8]}",
                            type=UncertaintyType.AMBIGUOUS_REFERENCE,
                            text=token.text,
                            description=f"Ambiguous pronoun '{token.text}' could refer to: {', '.join(lbls)}",
                            affected_ids=[segment.id],
                            source=PASS_NAME,
                        )
                        ctx.uncertainty.append(marker)
                        
                    match_entity = candidates[0]
                else:
                    # If no candidate, create a generic "Individual"
                    # But wait, maybe it refers to a new Subject?
                    # For now, create a new Subject
                    match_entity = Entity(
                        id=f"ent_{uuid4().hex[:8]}",
                        type=EntityType.PERSON,
                        role=EntityRole.SUBJECT,
                        label="Individual (Unidentified)",
                        mentions=[]
                    )
                    entities.append(match_entity)
            
            # C. Check Named Entities / Nouns
            elif token.pos_ in ("PROPN", "NOUN"):
                # Check for overlap with Identifiers
                # TODO: This requires span mapping which is complex here.
                # Simplified: Label matching
                
                # Check labels of existing entities
                for ent in entities:
                    if ent.label and ent.label.lower() in text_lower: # "Smith" in "Officer Smith"
                         match_entity = ent
                         break
                
                if not match_entity:
                    # New Entity?
                    # If "Officer", "The Officer" -> Authority
                    if text_lower in AUTHORITY_TITLES:
                         # Link to most recent Authority?
                         candidates = [e for e in reversed(recent_entities) if e.role == EntityRole.AUTHORITY]
                         if candidates:
                             match_entity = candidates[0]
                         else:
                             # New Authority
                             match_entity = Entity(
                                 id=f"ent_{uuid4().hex[:8]}",
                                 type=EntityType.PERSON,
                                 role=EntityRole.AUTHORITY,
                                 label=token.text,
                                 mentions=[]
                             )
                             entities.append(match_entity)
                    elif text_lower in GENERIC_SUBJECTS:
                        # Create New Subject (Do not merge distinct generic terms)
                        match_entity = Entity(
                            id=f"ent_{uuid4().hex[:8]}",
                            type=EntityType.PERSON,
                            role=EntityRole.SUBJECT,
                            label=token.text,
                            mentions=[]
                        )
                        entities.append(match_entity)

            # If we found or created an entity
            if match_entity:
                # Add mention text (temporary, IR expects span IDs)
                match_entity.mentions.append(token.text) # Placeholder
                if match_entity not in recent_entities:
                    recent_entities.append(match_entity)
                # Keep history short-ish
                if len(recent_entities) > 5:
                    recent_entities.pop(0)

    # 4. Final Cleanup
    # Deduplicate entities with same label? Done during creation.
    # Convert 'mentions' which are currently texts to span IDs? 
    # Current IR expects span IDs. This pass logic doesn't easily map token->span_id without re-scanning ctx.spans.
    # We will settle for just having the entity list populated for now, matching p40's level of 'mentions' (which p40 did by checking overlap).

    ctx.entities = entities
    
    ctx.add_trace(
        pass_name=PASS_NAME,
        action="extracted_entities",
        after=f"{len(entities)} entities extracted",
    )
    
    return ctx
