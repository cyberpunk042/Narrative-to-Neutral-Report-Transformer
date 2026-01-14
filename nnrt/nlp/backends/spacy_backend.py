"""
SpaCy Backend — NLP interface implementations using spaCy.

These implementations wrap spaCy functionality behind the defined
NLP interfaces for pluggable backend support.
"""

from typing import Optional

from nnrt.ir.enums import EntityRole, EntityType, EventType, SpanLabel
from nnrt.nlp.interfaces import (
    EntityExtractResult,
    EntityExtractor,
    EventExtractResult,
    EventExtractor,
    SpanTagResult,
)
from nnrt.nlp.spacy_loader import get_nlp


# =============================================================================
# Constants
# =============================================================================

REPORTER_PRONOUNS = {"i", "me", "my", "mine", "myself", "we", "us", "our", "ours"}
RESOLVABLE_PRONOUNS = {
    "he", "him", "his", "himself",
    "she", "her", "hers", "herself",
    "they", "them", "their", "theirs", "themselves"
}
GENERIC_SUBJECTS = {
    "subject", "suspect", "individual", "male", "female",
    "driver", "passenger", "partner", "manager", "employee"
}
AUTHORITY_TITLES = {
    "officer", "deputy", "sergeant", "detective",
    "lieutenant", "chief", "sheriff", "trooper"
}

# Verb type mappings
VERB_TYPE_MAP = {
    # Physical actions
    "grab": EventType.ACTION,
    "hit": EventType.ACTION,
    "punch": EventType.ACTION,
    "push": EventType.ACTION,
    "shove": EventType.ACTION,
    "strike": EventType.ACTION,
    "kick": EventType.ACTION,
    "tackle": EventType.ACTION,
    "restrain": EventType.ACTION,
    "cuff": EventType.ACTION,
    "handcuff": EventType.ACTION,
    "resist": EventType.ACTION,
    # Movement
    "walk": EventType.MOVEMENT,
    "run": EventType.MOVEMENT,
    "drive": EventType.MOVEMENT,
    "approach": EventType.MOVEMENT,
    "leave": EventType.MOVEMENT,
    "arrive": EventType.MOVEMENT,
    "enter": EventType.MOVEMENT,
    "exit": EventType.MOVEMENT,
    "flee": EventType.MOVEMENT,
    # Verbal
    "say": EventType.VERBAL,
    "yell": EventType.VERBAL,
    "scream": EventType.VERBAL,
    "shout": EventType.VERBAL,
    "tell": EventType.VERBAL,
    "ask": EventType.VERBAL,
    "command": EventType.VERBAL,
    "order": EventType.VERBAL,
}


# =============================================================================
# Entity Extractor
# =============================================================================

class SpacyEntityExtractor(EntityExtractor):
    """
    spaCy-based entity extraction.
    
    Extracts entities by analyzing:
    - Named entities (NER)
    - Pronouns (with resolution hints)
    - Noun phrases matching known patterns
    """

    @property
    def name(self) -> str:
        return "spacy_entity"

    def extract(self, text: str, existing_entities: list = None) -> list[EntityExtractResult]:
        """Extract entities from text using spaCy."""
        nlp = get_nlp()
        doc = nlp(text)
        
        results = []
        
        for token in doc:
            if token.pos_ not in ("PRON", "PROPN", "NOUN"):
                continue
            
            text_lower = token.text.lower()
            mention = (token.idx, token.idx + len(token.text), token.text)
            
            # Check for reporter pronouns
            if text_lower in REPORTER_PRONOUNS:
                results.append(EntityExtractResult(
                    label="Reporter",
                    type=EntityType.PERSON,
                    role=EntityRole.REPORTER,
                    confidence=0.95,
                    mentions=[mention],
                    is_new=False,  # Reporter always exists
                ))
            
            # Check for resolvable pronouns
            elif text_lower in RESOLVABLE_PRONOUNS:
                # Mark as needing resolution
                results.append(EntityExtractResult(
                    label="Individual (Unidentified)",
                    type=EntityType.PERSON,
                    role=EntityRole.SUBJECT,
                    confidence=0.6,
                    mentions=[mention],
                    is_new=True,
                ))
            
            # Check for authority titles
            elif text_lower in AUTHORITY_TITLES:
                results.append(EntityExtractResult(
                    label=token.text,
                    type=EntityType.PERSON,
                    role=EntityRole.AUTHORITY,
                    confidence=0.85,
                    mentions=[mention],
                    is_new=True,
                ))
            
            # Check for generic subjects
            elif text_lower in GENERIC_SUBJECTS:
                results.append(EntityExtractResult(
                    label=token.text,
                    type=EntityType.PERSON,
                    role=EntityRole.SUBJECT,
                    confidence=0.80,
                    mentions=[mention],
                    is_new=True,
                ))
            
            # Check spaCy NER
            elif token.ent_type_ == "PERSON":
                results.append(EntityExtractResult(
                    label=token.text,
                    type=EntityType.PERSON,
                    role=EntityRole.UNKNOWN,
                    confidence=0.75,
                    mentions=[mention],
                    is_new=True,
                ))
        
        return results


# =============================================================================
# Event Extractor
# =============================================================================

class SpacyEventExtractor(EventExtractor):
    """
    spaCy-based event extraction.
    
    Extracts events by analyzing:
    - Verbs and their dependencies
    - Actor (subject) and target (object) relationships
    """

    @property
    def name(self) -> str:
        return "spacy_event"

    def extract(self, text: str, spans: list[SpanTagResult] = None) -> list[EventExtractResult]:
        """Extract events from text using spaCy dependency parsing."""
        nlp = get_nlp()
        doc = nlp(text)
        
        results = []
        
        for token in doc:
            if token.pos_ != "VERB":
                continue
            
            lemma = token.lemma_.lower()
            
            # Determine event type
            event_type = VERB_TYPE_MAP.get(lemma, EventType.ACTION)
            
            # Find actor (subject)
            actor_mention = None
            nsubj = next((c for c in token.children if c.dep_ in ("nsubj", "nsubjpass")), None)
            if nsubj:
                actor_mention = nsubj.text
            
            # Find target (object)
            target_mention = None
            dobj = next((c for c in token.children if c.dep_ in ("dobj", "pobj")), None)
            if dobj:
                target_mention = dobj.text
            
            # Build description
            desc_parts = []
            if nsubj:
                desc_parts.append(nsubj.text)
            desc_parts.append(token.text)
            if dobj:
                desc_parts.append(dobj.text)
            description = " ".join(desc_parts) if desc_parts else token.text
            
            # Only include events with actors or known verb types
            if actor_mention or lemma in VERB_TYPE_MAP:
                results.append(EventExtractResult(
                    description=description,
                    type=event_type,
                    confidence=0.8,
                    source_start=token.idx,
                    source_end=token.idx + len(token.text),
                    actor_mention=actor_mention,
                    target_mention=target_mention,
                ))
        
        return results


# =============================================================================
# Factory Functions
# =============================================================================

def get_entity_extractor() -> EntityExtractor:
    """Get the default entity extractor."""
    return SpacyEntityExtractor()


def get_event_extractor() -> EventExtractor:
    """Get the default event extractor."""
    return SpacyEventExtractor()
