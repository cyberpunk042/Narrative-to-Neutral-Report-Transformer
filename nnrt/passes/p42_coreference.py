"""
p42_coreference — Pronoun and mention resolution.

Ultra-top solution for linking pronouns to entities:

Algorithm:
1. EXHAUSTIVE MENTION DETECTION
   - Direct text search for entity labels (not just spaCy NER)
   - Search for full names AND individual words
   - Handles cases spaCy misses

2. PRONOUN COLLECTION
   - Use spaCy POS tagging (reliable) not NER
   - Classify by gender/number

3. UNIFIED TIMELINE RESOLUTION
   - Merge all mentions into position-sorted timeline
   - Pronouns resolve to most recent gender-matching entity
   - First person always resolves to REPORTER

4. CHAIN ASSEMBLY
   - Group mentions by resolved entity
   - Calculate confidence metrics

Design principles:
- Never rely solely on spaCy NER for mention detection
- Use word boundaries for accurate matching
- Position-based recency is the primary resolution signal
"""

import re
import structlog
from typing import Optional

from nnrt.core.context import TransformContext
from nnrt.ir.schema_v0_1 import Mention, CoreferenceChain, Entity
from nnrt.ir.enums import MentionType, EntityRole, EntityType
from nnrt.nlp.spacy_loader import get_nlp

log = structlog.get_logger("nnrt.p42_coreference")

PASS_NAME = "p42_coreference"

# ============================================================================
# Pronoun Classification
# ============================================================================

# First-person pronouns (resolve to REPORTER)
FIRST_PERSON = {"i", "me", "my", "myself", "mine", "we", "us", "our", "ourselves", "ours"}

# Third-person pronouns by likely gender
MALE_PRONOUNS = {"he", "him", "his", "himself"}
FEMALE_PRONOUNS = {"she", "her", "hers", "herself"}
NEUTRAL_PRONOUNS = {"they", "them", "their", "theirs", "themselves"}

ALL_PRONOUNS = FIRST_PERSON | MALE_PRONOUNS | FEMALE_PRONOUNS | NEUTRAL_PRONOUNS

# Gender inference from names (expandable)
MALE_INDICATORS = {
    "officer", "sergeant", "detective", "captain", "mr", "sir",
    "james", "john", "robert", "michael", "william", "david", "marcus", 
    "jenkins", "rodriguez", "williams", "johnson", "smith", "brown"
}
FEMALE_INDICATORS = {
    "ms", "mrs", "miss", "madam",
    "mary", "patricia", "jennifer", "linda", "sarah", "amanda", 
    "foster", "chen", "lisa", "nancy"
}


def resolve_coreference(ctx: TransformContext) -> TransformContext:
    """
    Resolve pronouns and build coreference chains.
    
    This is the ultra-top solution using exhaustive mention detection
    and position-based recency resolution.
    """
    if not ctx.entities:
        log.info("no_entities", pass_name=PASS_NAME, message="No entities to resolve")
        ctx.add_trace(PASS_NAME, "skipped", after="No entities")
        return ctx
    
    all_mentions: list[Mention] = []
    mention_counter = 0
    
    nlp = get_nlp()
    
    # =========================================================================
    # PHASE 1: Exhaustive Mention Detection
    # =========================================================================
    # For each entity, search for all occurrences in text
    
    for segment in ctx.segments:
        text = segment.text
        text_lower = text.lower()
        
        # Track positions we've already created mentions for (avoid duplicates)
        covered_ranges: list[tuple[int, int]] = []
        
        # A) Search for each entity's label in the text
        for entity in ctx.entities:
            if not entity.label:
                continue
            
            # Search for full label
            positions = _find_all_occurrences(text, entity.label)
            for start, end in positions:
                if not _overlaps_any(start, end, covered_ranges):
                    mention = Mention(
                        id=f"m_{mention_counter:04d}",
                        segment_id=segment.id,
                        start_char=start,
                        end_char=end,
                        text=text[start:end],
                        mention_type=MentionType.PROPER_NAME,
                        resolved_entity_id=entity.id,
                        resolution_confidence=0.95,
                    )
                    all_mentions.append(mention)
                    covered_ranges.append((start, end))
                    mention_counter += 1
            
            # Search for individual significant words (skip common titles)
            label_words = entity.label.split()
            for word in label_words:
                if len(word) < 3:  # Skip short words
                    continue
                if word.lower() in {"the", "officer", "sergeant", "dr", "mr", "ms", "mrs"}:
                    continue  # Skip common titles
                    
                positions = _find_all_occurrences(text, word)
                for start, end in positions:
                    if not _overlaps_any(start, end, covered_ranges):
                        # This is a partial match (e.g., "Jenkins" for "Officer Jenkins")
                        mention = Mention(
                            id=f"m_{mention_counter:04d}",
                            segment_id=segment.id,
                            start_char=start,
                            end_char=end,
                            text=text[start:end],
                            mention_type=MentionType.TITLE,  # Partial name
                            resolved_entity_id=entity.id,
                            resolution_confidence=0.85,
                        )
                        all_mentions.append(mention)
                        covered_ranges.append((start, end))
                        mention_counter += 1
        
        # B) Also collect spaCy PERSON entities (as supplement)
        doc = nlp(text)
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                if not _overlaps_any(ent.start_char, ent.end_char, covered_ranges):
                    # Try to match to our entities
                    matched = _match_entity_by_name(ent.text, ctx.entities)
                    mention = Mention(
                        id=f"m_{mention_counter:04d}",
                        segment_id=segment.id,
                        start_char=ent.start_char,
                        end_char=ent.end_char,
                        text=ent.text,
                        mention_type=MentionType.PROPER_NAME,
                        resolved_entity_id=matched.id if matched else None,
                        resolution_confidence=0.9 if matched else 0.0,
                    )
                    all_mentions.append(mention)
                    covered_ranges.append((ent.start_char, ent.end_char))
                    mention_counter += 1
        
        # =====================================================================
        # PHASE 2: Pronoun Collection (using POS tagging, not NER)
        # =====================================================================
        for token in doc:
            # Use POS tagging for reliable pronoun detection
            if token.pos_ == "PRON" or token.text.lower() in ALL_PRONOUNS:
                text_lower_tok = token.text.lower()
                
                if text_lower_tok not in ALL_PRONOUNS:
                    continue  # Not a pronoun we handle
                
                if _overlaps_any(token.idx, token.idx + len(token.text), covered_ranges):
                    continue  # Already covered
                
                # Classify pronoun
                if text_lower_tok in FIRST_PERSON:
                    gender = "first_person"
                    number = "singular" if text_lower_tok in {"i", "me", "my", "myself", "mine"} else "plural"
                elif text_lower_tok in MALE_PRONOUNS:
                    gender = "male"
                    number = "singular"
                elif text_lower_tok in FEMALE_PRONOUNS:
                    gender = "female"
                    number = "singular"
                else:
                    gender = "neutral"
                    number = "plural" if text_lower_tok in {"they", "them", "their", "theirs", "themselves"} else "singular"
                
                mention = Mention(
                    id=f"m_{mention_counter:04d}",
                    segment_id=segment.id,
                    start_char=token.idx,
                    end_char=token.idx + len(token.text),
                    text=token.text,
                    mention_type=MentionType.PRONOUN,
                    gender=gender,
                    number=number,
                )
                all_mentions.append(mention)
                covered_ranges.append((token.idx, token.idx + len(token.text)))
                mention_counter += 1
    
    # =========================================================================
    # PHASE 3: Unified Timeline Resolution
    # =========================================================================
    
    # Find reporter entity (for first-person pronouns)
    reporter = next((e for e in ctx.entities if e.role == EntityRole.REPORTER), None)
    
    # Build unified timeline: all mentions sorted by position
    # For proper names, we already have resolved_entity_id
    timeline: list[tuple[int, Mention]] = [
        (m.start_char, m) for m in all_mentions
    ]
    timeline.sort(key=lambda x: x[0])
    
    # Track the most recent entity mention at each point
    # As we iterate through timeline, we know which entity was last mentioned
    recent_entity_by_gender: dict[str, str] = {}  # gender -> entity_id
    recent_entity_any: Optional[str] = None  # Most recent entity regardless of gender
    
    for pos, mention in timeline:
        if mention.mention_type == MentionType.PRONOUN:
            # This is a pronoun - resolve it
            if mention.gender == "first_person":
                if reporter:
                    mention.resolved_entity_id = reporter.id
                    mention.resolution_confidence = 0.95
            else:
                # Third-person pronoun - use recency
                if mention.gender == "neutral":
                    # "They" can refer to any entity
                    if recent_entity_any:
                        mention.resolved_entity_id = recent_entity_any
                        mention.resolution_confidence = 0.7
                else:
                    # Gender-specific pronoun
                    if mention.gender in recent_entity_by_gender:
                        mention.resolved_entity_id = recent_entity_by_gender[mention.gender]
                        mention.resolution_confidence = 0.8
                    elif recent_entity_any:
                        # Fallback to most recent if no gender match
                        mention.resolved_entity_id = recent_entity_any
                        mention.resolution_confidence = 0.5
        else:
            # This is a proper name or title - update recency tracking
            if mention.resolved_entity_id:
                entity = next((e for e in ctx.entities if e.id == mention.resolved_entity_id), None)
                if entity:
                    recent_entity_any = entity.id
                    # Infer gender and update gender-specific tracker
                    inferred_gender = _infer_entity_gender(entity)
                    if inferred_gender:
                        recent_entity_by_gender[inferred_gender] = entity.id
    
    # =========================================================================
    # PHASE 4: Chain Assembly
    # =========================================================================
    chains: list[CoreferenceChain] = []
    
    for entity in ctx.entities:
        # Collect all mentions for this entity
        entity_mentions = [m for m in all_mentions if m.resolved_entity_id == entity.id]
        
        if not entity_mentions:
            continue
        
        # Sort by position
        entity_mentions.sort(key=lambda m: m.start_char)
        entity_mention_ids = [m.id for m in entity_mentions]
        
        # Check if chain has proper name
        has_proper = any(m.mention_type == MentionType.PROPER_NAME for m in entity_mentions)
        
        # Calculate confidence
        proper_count = sum(1 for m in entity_mentions if m.mention_type == MentionType.PROPER_NAME)
        pronoun_count = sum(1 for m in entity_mentions if m.mention_type == MentionType.PRONOUN)
        
        if proper_count >= 2:
            confidence = 0.95
        elif proper_count == 1 and pronoun_count > 0:
            confidence = 0.85
        elif proper_count == 1:
            confidence = 0.8
        else:
            confidence = 0.6
        
        chain = CoreferenceChain(
            id=f"coref_{entity.id}",
            entity_id=entity.id,
            mention_ids=entity_mention_ids,
            mention_count=len(entity_mentions),
            has_proper_name=has_proper,
            confidence=confidence,
        )
        chains.append(chain)
    
    # Store results
    ctx.mentions = all_mentions
    ctx.coreference_chains = chains
    
    # Log summary
    resolved_count = sum(1 for m in all_mentions if m.resolved_entity_id)
    proper_mentions = sum(1 for m in all_mentions if m.mention_type in {MentionType.PROPER_NAME, MentionType.TITLE})
    pronoun_mentions = sum(1 for m in all_mentions if m.mention_type == MentionType.PRONOUN)
    
    log.info(
        "resolved",
        pass_name=PASS_NAME,
        channel="SEMANTIC",
        total_mentions=len(all_mentions),
        proper_names=proper_mentions,
        pronouns=pronoun_mentions,
        resolved=resolved_count,
        chains=len(chains),
    )
    
    ctx.add_trace(
        PASS_NAME,
        "coreference_resolved",
        after=f"{len(all_mentions)} mentions ({proper_mentions} proper, {pronoun_mentions} pronouns), {len(chains)} chains",
    )
    
    return ctx


def _find_all_occurrences(text: str, pattern: str) -> list[tuple[int, int]]:
    """
    Find all occurrences of pattern in text (case-insensitive, word boundaries).
    
    Returns list of (start, end) tuples.
    """
    results = []
    # Escape regex special characters in pattern
    escaped = re.escape(pattern)
    # Use word boundaries for accurate matching
    regex = rf'\b{escaped}\b'
    
    for match in re.finditer(regex, text, re.IGNORECASE):
        results.append((match.start(), match.end()))
    
    return results


def _overlaps_any(start: int, end: int, ranges: list[tuple[int, int]]) -> bool:
    """Check if [start, end) overlaps with any range in the list."""
    for r_start, r_end in ranges:
        if start < r_end and end > r_start:
            return True
    return False


def _match_entity_by_name(name_text: str, entities: list) -> Optional[Entity]:
    """Try to match a name mention to an existing entity."""
    name_lower = name_text.lower()
    
    for entity in entities:
        if not entity.label:
            continue
        label_lower = entity.label.lower()
        
        # Exact match
        if name_lower == label_lower:
            return entity
        
        # Name is part of label
        if name_lower in label_lower:
            return entity
        
        # Label is part of name
        if label_lower in name_lower:
            return entity
        
        # Check individual words
        name_words = set(name_lower.split())
        label_words = set(label_lower.split())
        if name_words & label_words:
            return entity
    
    return None


def _infer_entity_gender(entity: Entity) -> Optional[str]:
    """
    Infer gender from entity label.
    
    Returns "male", "female", or None if unknown.
    """
    if not entity.label:
        return None
    
    label_lower = entity.label.lower()
    words = label_lower.split()
    
    for word in words:
        if word in MALE_INDICATORS:
            return "male"
        if word in FEMALE_INDICATORS:
            return "female"
    
    return None
