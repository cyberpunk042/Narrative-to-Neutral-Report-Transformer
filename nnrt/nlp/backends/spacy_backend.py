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
        """
        Extract entities from text using spaCy.
        
        V4: Uses doc.ents for proper multi-token entity extraction.
        """
        nlp = get_nlp()
        doc = nlp(text)
        
        results = []
        processed_spans = set()  # Track processed character spans
        
        # =======================================================================
        # FIRST: Process spaCy NER entities (multi-token aware)
        # =======================================================================
        for ent in doc.ents:
            if ent.label_ != "PERSON":
                continue
            
            # Track this span
            span_key = (ent.start_char, ent.end_char)
            processed_spans.add(span_key)
            
            ent_text = ent.text.strip()
            ent_lower = ent_text.lower()
            mention = (ent.start_char, ent.end_char, ent_text)
            
            # Classify role based on context around the entity
            role = EntityRole.UNKNOWN
            context_start = max(0, ent.start_char - 50)
            context = text[context_start:ent.start_char].lower()
            
            # Check for role indicators in preceding context
            if "dr." in context or "doctor" in context or "nurse" in context:
                role = EntityRole.WITNESS  # Will be upgraded to MEDICAL_PROVIDER in pass
            elif "attorney" in context or "lawyer" in context:
                role = EntityRole.WITNESS  # Will be upgraded to LEGAL_COUNSEL in pass
            elif "sergeant" in ent_lower or "sgt" in ent_lower:
                role = EntityRole.AUTHORITY
            elif "officer" in ent_lower or "deputy" in ent_lower:
                role = EntityRole.AUTHORITY
            elif "detective" in ent_lower:
                role = EntityRole.AUTHORITY
            
            results.append(EntityExtractResult(
                label=ent_text,
                type=EntityType.PERSON,
                role=role,
                confidence=0.80,
                mentions=[mention],
                is_new=True,
            ))
        
        # =======================================================================
        # SECOND: Process pronouns and special tokens (not covered by NER)
        # =======================================================================
        for token in doc:
            # Skip if already processed as part of an entity span
            token_span = (token.idx, token.idx + len(token.text))
            if any(s[0] <= token.idx < s[1] for s in processed_spans):
                continue
            
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
        
        # =======================================================================
        # THIRD: V4 Pattern-based extraction for compound names spaCy misses
        # =======================================================================
        # Handle patterns like "Officers Jenkins and Rodriguez"
        import re
        
        # Pattern: "Officer(s) Name and Name"
        compound_pattern = r'\b(?:Officer|Officers|Deputy|Deputies|Detective|Detectives)\s+([A-Z][a-z]+)\s+and\s+([A-Z][a-z]+)\b'
        for match in re.finditer(compound_pattern, text):
            name1, name2 = match.group(1), match.group(2)
            
            # Check if these names are already extracted
            existing_labels = {r.label.lower() for r in results if r.label}
            
            # Add Officer Name1 if not exists
            if f"officer {name1.lower()}" not in existing_labels and name1.lower() not in existing_labels:
                results.append(EntityExtractResult(
                    label=f"Officer {name1}",
                    type=EntityType.PERSON,
                    role=EntityRole.AUTHORITY,
                    confidence=0.85,
                    mentions=[(match.start(1), match.end(1), name1)],
                    is_new=True,
                ))
            
            # Add Officer Name2 if not exists (this is the one spaCy typically misses)
            if f"officer {name2.lower()}" not in existing_labels and name2.lower() not in existing_labels:
                results.append(EntityExtractResult(
                    label=f"Officer {name2}",
                    type=EntityType.PERSON,
                    role=EntityRole.AUTHORITY,
                    confidence=0.85,
                    mentions=[(match.start(2), match.end(2), name2)],
                    is_new=True,
                ))
        
        return results


# =============================================================================
# Event Extractor
# =============================================================================

class SpacyEventExtractor(EventExtractor):
    """
    spaCy-based event extraction.
    
    V4: Enhanced extraction with:
    - Fuller description from verb subtree
    - Better actor/target detection
    - Filtering for quality events
    """

    @property
    def name(self) -> str:
        return "spacy_event"

    def extract(self, text: str, spans: list[SpanTagResult] = None) -> list[EventExtractResult]:
        """
        Extract events from text using spaCy dependency parsing.
        
        V4: Builds richer descriptions and filters noise.
        """
        nlp = get_nlp()
        doc = nlp(text)
        
        results = []
        processed_verbs = set()  # Avoid duplicates
        
        for token in doc:
            if token.pos_ != "VERB":
                continue
            
            # Skip if already processed
            if token.i in processed_verbs:
                continue
            processed_verbs.add(token.i)
            
            lemma = token.lemma_.lower()
            
            # V4: Skip auxiliary and helper verbs
            if lemma in {"be", "have", "do", "will", "would", "could", "should", "can", "may", "might", "must"}:
                continue
            
            # V4: Skip very common low-info verbs unless they have good context
            if lemma in {"get", "go", "come", "make", "take", "put", "give", "keep", "let", "seem"}:
                # Only keep if there's a direct object
                if not any(c.dep_ == "dobj" for c in token.children):
                    continue
            
            # Determine event type
            event_type = VERB_TYPE_MAP.get(lemma, EventType.ACTION)
            
            # V4: Enhanced actor detection - include compounds
            actor_mention = None
            nsubj = next((c for c in token.children if c.dep_ in ("nsubj", "nsubjpass")), None)
            if nsubj:
                # Get the full noun phrase, not just the head
                actor_parts = [nsubj.text]
                # Include preceding modifiers
                for child in nsubj.children:
                    if child.dep_ in ("compound", "amod", "det") and child.i < nsubj.i:
                        actor_parts.insert(0, child.text)
                    elif child.dep_ in ("compound", "flat") and child.i > nsubj.i:
                        actor_parts.append(child.text)
                actor_mention = " ".join(actor_parts)
            
            # V4: Enhanced target detection - follow prep phrases too
            target_mention = None
            dobj = next((c for c in token.children if c.dep_ == "dobj"), None)
            if dobj:
                target_parts = [dobj.text]
                for child in dobj.children:
                    if child.dep_ in ("compound", "amod"):
                        target_parts.insert(0, child.text)
                target_mention = " ".join(target_parts)
            else:
                # Check for prepositional object
                prep = next((c for c in token.children if c.dep_ == "prep"), None)
                if prep:
                    pobj = next((c for c in prep.children if c.dep_ == "pobj"), None)
                    if pobj:
                        target_mention = f"{prep.text} {pobj.text}"
            
            # V4: Build fuller description from subtree
            # Get relevant parts of the verb phrase
            desc_parts = []
            
            # Add subject
            if actor_mention:
                desc_parts.append(actor_mention)
            
            # Add any adverbs before the verb
            for child in token.children:
                if child.dep_ == "advmod" and child.i < token.i:
                    desc_parts.append(child.text)
            
            # Add the verb (possibly with particle)
            verb_phrase = token.text
            prt = next((c for c in token.children if c.dep_ == "prt"), None)
            if prt:
                verb_phrase = f"{token.text} {prt.text}"
            desc_parts.append(verb_phrase)
            
            # Add direct object
            if dobj:
                desc_parts.append(target_mention or dobj.text)
            
            # Add key prepositional phrases
            for child in token.children:
                if child.dep_ == "prep":
                    prep_text = child.text
                    pobj = next((c for c in child.children if c.dep_ == "pobj"), None)
                    if pobj:
                        prep_text += f" {pobj.text}"
                    if len(prep_text) > 3:  # Skip tiny preps
                        desc_parts.append(prep_text)
                        break  # Only add first prep phrase
            
            description = " ".join(desc_parts)
            
            # V4: Quality filter - skip very short or low-value events
            if len(description) < 5:
                continue
            if description.lower() in {"it is", "is", "was", "were", "be"}:
                continue
            
            # V4: Higher confidence for events with both actor and target
            confidence = 0.7
            if actor_mention and target_mention:
                confidence = 0.9
            elif actor_mention or target_mention:
                confidence = 0.8
            
            results.append(EventExtractResult(
                description=description,
                type=event_type,
                confidence=confidence,
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
