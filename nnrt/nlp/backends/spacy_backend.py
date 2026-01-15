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
        
        V4.2: Use VERBATIM text extraction instead of reconstruction.
        The key insight: use token.subtree to get the exact text span
        rather than reconstructing from dependency tree parts.
        
        This preserves:
        - Negations ("didn't", "won't")
        - Auxiliaries ("was", "were", "had been")
        - Word order
        - All connecting words
        """
        nlp = get_nlp()
        doc = nlp(text)
        
        results = []
        processed_verbs = set()
        
        # Find quoted regions to skip
        quote_regions = []
        in_quote = False
        quote_start = 0
        for i, char in enumerate(text):
            if char in '"\'':
                if not in_quote:
                    in_quote = True
                    quote_start = i
                else:
                    quote_regions.append((quote_start, i))
                    in_quote = False
        
        def is_in_quote(idx: int) -> bool:
            return any(start <= idx <= end for start, end in quote_regions)
        
        for token in doc:
            if token.pos_ != "VERB":
                continue
            
            # Skip if already processed
            if token.i in processed_verbs:
                continue
            processed_verbs.add(token.i)
            
            # Skip verbs inside quoted speech
            if is_in_quote(token.idx):
                continue
            
            # Skip ALL_CAPS verbs
            if token.text.isupper() and len(token.text) > 1:
                continue
            
            lemma = token.lemma_.lower()
            
            # Skip auxiliary and helper verbs
            if lemma in {"be", "have", "do", "will", "would", "could", "should", 
                         "can", "may", "might", "must", "don't", "dare"}:
                continue
            
            # Only process ROOT or main clause verbs
            if token.dep_ not in ("ROOT", "relcl", "advcl", "ccomp", "xcomp"):
                continue
            
            # V4.2: Get VERBATIM text from subtree instead of reconstruction
            subtree = list(token.subtree)
            if not subtree:
                continue
            
            # Get the span of text covered by the verb's subtree
            start_char = min(t.idx for t in subtree)
            end_char = max(t.idx + len(t.text) for t in subtree)
            
            # Extract verbatim text
            description = text[start_char:end_char].strip()
            
            # Clean up: remove trailing punctuation except for quoted text
            if description and description[-1] in '.!?,;:':
                description = description[:-1].strip()
            
            # Quality filter
            if len(description) < 10:
                continue
            words = description.split()
            if len(words) < 3:
                continue
            
            # Determine event type
            event_type = VERB_TYPE_MAP.get(lemma, EventType.ACTION)
            
            # V5: Extract actor with FULL noun phrase (not just head noun)
            nsubj = next((c for c in token.children if c.dep_ in ("nsubj", "nsubjpass")), None)
            actor_mention = None
            if nsubj:
                # Get full noun phrase by traversing subtree
                nsubj_tokens = sorted(nsubj.subtree, key=lambda t: t.i)
                actor_mention = " ".join(t.text for t in nsubj_tokens)
            
            # V5: Extract action verb (may include particle)
            action_verb = token.lemma_
            prt = next((c for c in token.children if c.dep_ == "prt"), None)
            if prt:
                action_verb = f"{token.lemma_} {prt.text}"
            
            # V5: Extract target with full noun phrase
            dobj = next((c for c in token.children if c.dep_ == "dobj"), None)
            target_mention = None
            if dobj:
                dobj_tokens = sorted(dobj.subtree, key=lambda t: t.i)
                target_mention = " ".join(t.text for t in dobj_tokens)
            
            # V5: Get source sentence for pronoun resolution
            source_sentence = token.sent.text.strip()
            
            # Confidence based on completeness
            confidence = 0.7
            if actor_mention and target_mention:
                confidence = 0.9
            elif actor_mention:
                confidence = 0.8
            
            results.append(EventExtractResult(
                description=description,
                type=event_type,
                confidence=confidence,
                source_start=start_char,
                source_end=end_char,
                actor_mention=actor_mention,
                action_verb=action_verb,
                target_mention=target_mention,
                source_sentence=source_sentence,
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
