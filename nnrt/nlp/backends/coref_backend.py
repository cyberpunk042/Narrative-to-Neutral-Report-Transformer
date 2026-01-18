"""
FastCoref Backend — Enhanced coreference resolution for pronoun handling.

V9: Uses FastCoref to resolve pronouns (he, she, they) to actual entities
BEFORE event extraction, giving us better actor attribution.

Usage:
    from nnrt.nlp.backends.coref_backend import CorefResolver
    
    resolver = CorefResolver()
    resolved_text = resolver.resolve(text)
    # "She called 911" → "Patricia Chen called 911"
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import structlog

log = structlog.get_logger(__name__)


@dataclass
class CorefCluster:
    """A cluster of coreferent mentions."""
    main_mention: str  # The main/canonical mention (usually a named entity)
    mentions: List[Tuple[int, int, str]]  # (start, end, text) for each mention
    is_named: bool = False  # True if main_mention is a named entity


class CorefResolver:
    """
    Coreference resolver using FastCoref.
    
    Provides:
    1. resolve(text) → text with pronouns replaced by entity names
    2. get_clusters(text) → list of coreference clusters
    """
    
    _model = None
    _available = None
    
    def __init__(self):
        self._ensure_model()
    
    @classmethod
    def _ensure_model(cls):
        """Lazy-load the FastCoref model."""
        if cls._available is not None:
            return
        
        try:
            from fastcoref import FCoref
            cls._model = FCoref(device='cpu')  # Use CPU for compatibility
            cls._available = True
            log.info("fastcoref_loaded", status="success")
        except ImportError:
            log.warning("fastcoref_not_available", 
                       message="Install with: pip install fastcoref")
            cls._available = False
        except Exception as e:
            log.warning("fastcoref_load_failed", error=str(e))
            cls._available = False
    
    @property
    def available(self) -> bool:
        """Check if FastCoref is available."""
        return self._available or False
    
    def get_clusters(self, text: str) -> List[CorefCluster]:
        """
        Get coreference clusters from text.
        
        Returns list of clusters, each containing:
        - main_mention: The canonical entity name (extracted from descriptions)
        - mentions: All mentions (including pronouns) that refer to it
        """
        if not self.available:
            return []
        
        try:
            preds = self._model.predict(texts=[text])
            clusters = []
            
            for cluster_spans in preds[0].get_clusters(as_strings=False):
                mentions = []
                main_mention = None
                is_named = False
                
                for start, end in cluster_spans:
                    mention_text = text[start:end]
                    mentions.append((start, end, mention_text))
                    
                    # Try to extract a clean named entity from this mention
                    extracted = self._extract_named_entity(mention_text)
                    
                    if extracted:
                        if not main_mention or not is_named:
                            main_mention = extracted
                            is_named = True
                    elif not main_mention:
                        main_mention = mention_text
                
                if main_mention:
                    clusters.append(CorefCluster(
                        main_mention=main_mention,
                        mentions=mentions,
                        is_named=is_named,
                    ))
            
            return clusters
            
        except Exception as e:
            log.warning("coref_extraction_failed", error=str(e))
            return []
    
    def _extract_named_entity(self, text: str) -> Optional[str]:
        """
        Extract a clean named entity from a mention.
        
        Examples:
            "an elderly woman named Mrs. Patricia Chen who lives..."
            → "Mrs. Patricia Chen"
            
            "Officer Jenkins, badge number 4821"
            → "Officer Jenkins"
        """
        text = text.strip()
        
        # Pattern 1: "named X" or "called X"
        named_match = re.search(r'\b(?:named|called)\s+([A-Z][^\s,]*(?:\s+[A-Z][^\s,]*)*)', text)
        if named_match:
            return named_match.group(1).strip()
        
        # Pattern 2: "Title Name" at start or standalone
        title_pattern = r'^((?:Officer|Sergeant|Detective|Deputy|Mrs?\.|Ms\.|Dr\.)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'
        title_match = re.search(title_pattern, text)
        if title_match:
            # Remove trailing badge number etc
            name = title_match.group(1)
            name = re.sub(r',?\s*badge.*$', '', name, flags=re.IGNORECASE)
            return name.strip()
        
        # Pattern 3: Simple "Firstname Lastname" 
        if len(text) < 30:  # Short mentions only
            name_match = re.match(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*(?:,|$)', text)
            if name_match:
                return name_match.group(1).strip()
        
        # Check if entire text is a pronoun (not a named entity)
        if text.lower() in {'he', 'she', 'they', 'him', 'her', 'them', 'his', 'her', 'their'}:
            return None
        
        return None
    
    def _is_named_entity(self, text: str) -> bool:
        """Check if text looks like a named entity (not a pronoun)."""
        text_lower = text.lower().strip()
        
        # Pronouns
        pronouns = {
            'he', 'she', 'it', 'they', 'him', 'her', 'them',
            'his', 'her', 'its', 'their', 'hers', 'theirs',
            'i', 'me', 'my', 'we', 'us', 'our'
        }
        if text_lower in pronouns:
            return False
        
        # Generic terms
        generic = {
            'the man', 'the woman', 'the officer', 'the suspect',
            'the victim', 'a man', 'a woman'
        }
        if text_lower in generic:
            return False
        
        # Looks like a name (capitalized, not too short)
        words = text.split()
        if len(words) >= 1 and words[0][0].isupper():
            # Check for title + name pattern
            titles = {'officer', 'sergeant', 'deputy', 'detective', 'dr.', 'mr.', 'mrs.', 'ms.'}
            if words[0].lower() in titles and len(words) >= 2:
                return True
            # Regular name (capitalized, multi-word)
            if len(text) > 3:
                return True
        
        return False
    
    def resolve(self, text: str, entity_map: Dict[str, str] = None) -> str:
        """
        Resolve pronouns in text to their antecedents.
        
        Args:
            text: The text to process
            entity_map: Optional mapping of mention → preferred name
                       e.g. {"Patricia": "Patricia Chen"}
        
        Returns:
            Text with pronouns replaced by entity names
        
        Example:
            "Patricia Chen came out. She called 911."
            → "Patricia Chen came out. Patricia Chen called 911."
        """
        if not self.available:
            return text
        
        entity_map = entity_map or {}
        
        try:
            clusters = self.get_clusters(text)
            
            # Build replacement map: pronoun positions → replacement text
            replacements = []  # (start, end, replacement)
            
            for cluster in clusters:
                if not cluster.is_named:
                    continue  # Skip clusters without a named entity
                
                # Get the canonical name for this cluster
                canonical = cluster.main_mention
                
                # Check if we have a preferred name in entity_map
                for key, preferred in entity_map.items():
                    if key.lower() in canonical.lower():
                        canonical = preferred
                        break
                
                # Replace pronouns in this cluster
                for start, end, mention_text in cluster.mentions:
                    mention_lower = mention_text.lower()
                    
                    # V9 Safety: Skip plural pronouns referring to singular entities
                    # "They slammed me" → refers to multiple officers, not a single entity
                    if mention_lower in {'they', 'them', 'their', 'themselves'}:
                        # Only replace if canonical looks like a group (e.g., "Officers Jenkins and Rodriguez")
                        if not (' and ' in canonical.lower() or 'officers' in canonical.lower()):
                            continue  # Skip - would create weird text like "Officer Jenkins slammed"
                    
                    # Handle possessive pronouns (his, her)
                    if mention_lower in {'his', 'her'}:
                        # Add possessive 's to the canonical form
                        possessive = canonical + "'s" if not canonical.endswith("s") else canonical + "'"
                        replacements.append((start, end, possessive))
                    # Handle subject/object pronouns (singular only)
                    elif mention_lower in {'he', 'she', 'him', 
                                         'himself', 'herself'}:
                        replacements.append((start, end, canonical))
            
            # Apply replacements in reverse order (to preserve positions)
            replacements.sort(key=lambda x: x[0], reverse=True)
            
            result = text
            for start, end, replacement in replacements:
                result = result[:start] + replacement + result[end:]
            
            return result
            
        except Exception as e:
            log.warning("coref_resolution_failed", error=str(e))
            return text


def get_coref_resolver() -> CorefResolver:
    """Get the singleton coreference resolver."""
    return CorefResolver()


# =============================================================================
# Fallback: Rule-based coreference (when FastCoref not available)
# =============================================================================

class RuleBasedCorefResolver:
    """
    Simple rule-based coreference for when FastCoref isn't available.
    
    Uses heuristics:
    - Track the last mentioned entity of each gender
    - "She" → last female entity, "He" → last male entity
    """
    
    FEMALE_INDICATORS = {'mrs', 'ms', 'miss', 'woman', 'lady', 'girl', 'mother', 'wife'}
    MALE_INDICATORS = {'mr', 'sir', 'man', 'gentleman', 'boy', 'father', 'husband', 
                       'officer', 'sergeant', 'deputy', 'detective'}
    FEMALE_NAMES = {
        'patricia', 'amanda', 'sarah', 'jennifer', 'maria', 'linda', 'susan',
        'karen', 'nancy', 'lisa', 'betty', 'margaret', 'sandra', 'ashley',
        'dorothy', 'elizabeth', 'helen', 'samantha', 'katherine', 'christine'
    }
    
    def __init__(self):
        self.last_female = None
        self.last_male = None
    
    def resolve(self, text: str, entity_map: Dict[str, str] = None) -> str:
        """
        Rule-based pronoun resolution.
        
        Tracks entities as they appear and replaces pronouns.
        """
        import re
        
        result = text
        
        # Find all named entities and their genders
        # Pattern: "Officer/Mrs./etc. Name" or just "Name"
        entity_pattern = r'\b((?:Officer|Sergeant|Deputy|Detective|Mrs?\.|Ms\.|Dr\.)\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b'
        
        for match in re.finditer(entity_pattern, text):
            title = match.group(1) or ''
            name = match.group(2)
            full = (title + name).strip()
            
            # Determine gender
            title_lower = title.lower().strip()
            name_lower = name.lower().split()[0]  # First name
            
            if any(ind in title_lower for ind in self.FEMALE_INDICATORS):
                self.last_female = full
            elif any(ind in title_lower for ind in self.MALE_INDICATORS):
                self.last_male = full
            elif name_lower in self.FEMALE_NAMES:
                self.last_female = full
            else:
                # Default to male for officers without female indicator
                self.last_male = full
        
        # Now replace pronouns
        # We need to do this sentence by sentence, forward order
        sentences = re.split(r'(?<=[.!?])\s+', text)
        resolved_sentences = []
        
        for sent in sentences:
            resolved = sent
            
            # Replace "She" at start of sentence
            if self.last_female:
                resolved = re.sub(r'^She\b', self.last_female, resolved)
                resolved = re.sub(r'^Her\b', self.last_female + "'s", resolved)
            
            # Replace "He" at start of sentence  
            if self.last_male:
                resolved = re.sub(r'^He\b', self.last_male, resolved)
                resolved = re.sub(r'^His\b', self.last_male + "'s", resolved)
            
            # Update gender tracking based on this sentence
            for match in re.finditer(entity_pattern, sent):
                title = match.group(1) or ''
                name = match.group(2)
                full = (title + name).strip()
                title_lower = title.lower().strip()
                name_lower = name.lower().split()[0]
                
                if any(ind in title_lower for ind in self.FEMALE_INDICATORS):
                    self.last_female = full
                elif name_lower in self.FEMALE_NAMES:
                    self.last_female = full
                elif any(ind in title_lower for ind in self.MALE_INDICATORS):
                    self.last_male = full
                else:
                    self.last_male = full
            
            resolved_sentences.append(resolved)
        
        return ' '.join(resolved_sentences)


def get_resolver() -> CorefResolver:
    """Get the best available coreference resolver."""
    resolver = CorefResolver()
    if resolver.available:
        return resolver
    else:
        log.info("using_rule_based_coref", reason="fastcoref_not_available")
        return RuleBasedCorefResolver()
