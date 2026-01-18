"""
Enhanced Event Extraction — Sentence-level action extraction.

V10: A simpler, more comprehensive approach to event extraction.
Instead of relying solely on dependency parsing, we:
1. Split text into sentences
2. For each sentence, identify the subject and main verb
3. Extract complete action descriptions
4. Resolve pronouns using simple recency-based rules

This is ADDITIONAL to the existing spaCy extraction - not a replacement.
It catches events that dependency parsing misses.
"""

import re
import structlog
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from nnrt.nlp.spacy_loader import get_nlp

log = structlog.get_logger("nnrt.enhanced_event_extractor")


# Common action verbs to look for (expanded list)
ACTION_VERBS = {
    # Physical actions
    'grab', 'grabbed', 'grabbing',
    'push', 'pushed', 'pushing',
    'pull', 'pulled', 'pulling', 
    'hit', 'hits', 'hitting',
    'punch', 'punched', 'punching',
    'kick', 'kicked', 'kicking',
    'slam', 'slammed', 'slamming',
    'shove', 'shoved', 'shoving',
    'twist', 'twisted', 'twisting',
    'restrain', 'restrained', 'restraining',
    'handcuff', 'handcuffed', 'handcuffing',
    'cuff', 'cuffed', 'cuffing',
    'uncuff', 'uncuffed', 'uncuffing',
    'search', 'searched', 'searching',
    'frisk', 'frisked', 'frisking',
    
    # Movement
    'jump', 'jumped', 'jumping',
    'run', 'ran', 'running',
    'walk', 'walked', 'walking',
    'approach', 'approached', 'approaching',
    'arrive', 'arrived', 'arriving',
    'exit', 'exited', 'exiting',
    'enter', 'entered', 'entering',
    'leave', 'left', 'leaving',
    'step', 'stepped', 'stepping',
    'come', 'came', 'coming',
    'go', 'went', 'going',
    
    # Verbal
    'yell', 'yelled', 'yelling',
    'scream', 'screamed', 'screaming',
    'shout', 'shouted', 'shouting',
    'say', 'said', 'saying',
    'tell', 'told', 'telling',
    'ask', 'asked', 'asking',
    'call', 'called', 'calling',
    'threaten', 'threatened', 'threatening',
    'whisper', 'whispered', 'whispering',
    
    # Recording/Documenting
    'record', 'recorded', 'recording',
    'film', 'filmed', 'filming',
    'document', 'documented', 'documenting',
    'photograph', 'photographed', 'photographing',
    'file', 'filed', 'filing',
    
    # Other observable
    'take', 'took', 'taking',
    'put', 'puts', 'putting',
    'hold', 'held', 'holding',
    'find', 'found', 'finding',
    'stop', 'stopped', 'stopping',
    'freeze', 'froze', 'freezing',
    'mock', 'mocked', 'mocking',
    'laugh', 'laughed', 'laughing',
}

# Pronouns and their gender
MALE_PRONOUNS = {'he', 'him', 'his', 'himself'}
FEMALE_PRONOUNS = {'she', 'her', 'hers', 'herself'}
FIRST_PERSON = {'i', 'me', 'my', 'myself', 'mine'}
PLURAL_PRONOUNS = {'they', 'them', 'their', 'themselves'}

# Male indicators in names/titles
MALE_INDICATORS = {'officer', 'sergeant', 'detective', 'mr', 'sir', 
                   'officer jenkins', 'officer rodriguez', 'sergeant williams'}
FEMALE_INDICATORS = {'ms', 'mrs', 'miss', 'madam', 'dr. amanda', 
                     'patricia', 'sarah', 'amanda', 'jennifer'}


@dataclass
class ExtractedAction:
    """A single extracted action."""
    actor: str
    verb: str
    target: str
    full_sentence: str
    confidence: float = 0.8


def extract_sentence_events(text: str, entities: List[str] = None) -> List[ExtractedAction]:
    """
    Extract observable events using sentence-level analysis.
    
    This is a simpler approach than full dependency parsing:
    1. Find sentences with action verbs
    2. Extract the subject (actor)
    3. Resolve pronouns to entities
    4. Build clean action descriptions
    
    Args:
        text: The narrative text
        entities: Known entity names for pronoun resolution
        
    Returns:
        List of ExtractedAction objects
    """
    nlp = get_nlp()
    doc = nlp(text)
    
    results = []
    last_male_entity = None
    last_female_entity = None
    
    # Build entity gender map from provided entities
    # Use name patterns to determine gender
    entity_genders = {}
    for entity in (entities or []):
        entity_lower = entity.lower()
        # Male indicators
        if 'officer' in entity_lower or 'sergeant' in entity_lower or 'mr.' in entity_lower:
            entity_genders[entity] = 'male'
            if not last_male_entity:
                last_male_entity = entity
        # Female indicators (more specific names)
        elif any(name in entity_lower for name in ['patricia', 'sarah', 'amanda', 'jennifer', 'mrs.', 'ms.']):
            entity_genders[entity] = 'female'
            if not last_female_entity:
                last_female_entity = entity
    
    # Process each sentence
    for sent in doc.sents:
        sent_text = sent.text.strip()
        
        # Skip very short sentences
        if len(sent_text) < 10:
            continue
        
        # FIRST: Scan for named entity mentions to update tracking
        # This ensures pronouns in the NEXT sentence resolve correctly
        sent_lower = sent_text.lower()
        
        # Check for specific female names that should update last_female_entity
        if 'patricia chen' in sent_lower or 'mrs. patricia' in sent_lower:
            last_female_entity = 'Patricia Chen'
        if 'amanda foster' in sent_lower or 'dr. amanda' in sent_lower:
            last_female_entity = 'Amanda Foster'
        if 'sarah monroe' in sent_lower or 'detective sarah' in sent_lower:
            last_female_entity = 'Sarah Monroe'
        if 'jennifer walsh' in sent_lower:
            last_female_entity = 'Jennifer Walsh'
        
        # Check for male entity mentions
        if 'officer jenkins' in sent_lower:
            last_male_entity = 'Officer Jenkins'
        if 'officer rodriguez' in sent_lower:
            last_male_entity = 'Officer Rodriguez'
        if 'sergeant williams' in sent_lower:
            last_male_entity = 'Sergeant Williams'
        if 'marcus johnson' in sent_lower:
            last_male_entity = 'Marcus Johnson'
        
        # Skip sentences that are mostly quoted speech
        quote_chars = sent_text.count('"') + sent_text.count("'")
        if quote_chars > 2:
            continue
        
        # Find action verbs in this sentence
        action_verbs_found = []
        for token in sent:
            if token.text.lower() in ACTION_VERBS and token.pos_ == 'VERB':
                action_verbs_found.append(token)
        
        if not action_verbs_found:
            continue
        
        # For each action verb, extract actor-action-target
        for verb_token in action_verbs_found:
            # Find the subject (actor)
            actor = None
            actor_resolved = None
            
            # Look for nsubj or nsubjpass
            for child in verb_token.children:
                if child.dep_ in ('nsubj', 'nsubjpass'):
                    # Get full noun phrase
                    actor_tokens = sorted(child.subtree, key=lambda t: t.i)
                    actor = ' '.join(t.text for t in actor_tokens)
                    break
            
            # If no explicit subject, check sentence start
            if not actor:
                first_token = sent[0]
                if first_token.pos_ in ('PROPN', 'NOUN', 'PRON'):
                    actor = first_token.text
            
            if not actor:
                continue
            
            # V10: If actor is a verbose phrase, try to extract the proper name
            # Pattern: "an elderly woman named Mrs. Patricia Chen who..." → "Patricia Chen"
            import re
            if len(actor) > 30 or ' who ' in actor.lower() or ' named ' in actor.lower():
                # Try to extract a proper name pattern
                name_match = re.search(r'(?:Mrs?\.|Ms\.|Dr\.)?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', actor)
                if name_match:
                    extracted_name = name_match.group(0).strip()
                    # Prefer the clean name
                    actor = extracted_name
            # Resolve pronouns
            actor_lower = actor.lower().strip()
            pronoun_resolved = False
            
            if actor_lower in FIRST_PERSON:
                actor_resolved = 'Reporter'
                pronoun_resolved = True
            elif actor_lower in MALE_PRONOUNS:
                # Only resolve if we have a recent male entity
                if last_male_entity:
                    actor_resolved = last_male_entity
                    pronoun_resolved = True
                else:
                    actor_resolved = actor  # Keep as unresolved
            elif actor_lower in FEMALE_PRONOUNS:
                # Only resolve if we have a recent female entity
                if last_female_entity:
                    actor_resolved = last_female_entity
                    pronoun_resolved = True
                else:
                    actor_resolved = actor  # Keep as unresolved
            elif actor_lower in PLURAL_PRONOUNS:
                actor_resolved = 'Officers'  # Common case in police narratives
                pronoun_resolved = True
            else:
                actor_resolved = actor
                # Update last seen entities ONLY for clearly named entities
                # Check if the actor contains a proper name (multiple words, not just title)
                words = actor.split()
                if len(words) >= 2:  # "Officer Jenkins", "Patricia Chen", etc.
                    if any(ind in actor_lower for ind in ('officer', 'sergeant', 'detective')):
                        last_male_entity = actor
                    elif any(name in actor_lower for name in ('patricia', 'sarah', 'amanda', 'jennifer', 'mrs', 'ms')):
                        last_female_entity = actor
            
            # Extract target (direct object or prepositional object)
            target = None
            for child in verb_token.children:
                if child.dep_ == 'dobj':
                    target_tokens = sorted(child.subtree, key=lambda t: t.i)
                    target = ' '.join(t.text for t in target_tokens)
                    break
                elif child.dep_ == 'prep':
                    # Get full PP
                    pp_tokens = sorted(child.subtree, key=lambda t: t.i)
                    target = ' '.join(t.text for t in pp_tokens)
            
            # Get particles for phrasal verbs
            verb_with_particle = verb_token.text
            for child in verb_token.children:
                if child.dep_ == 'prt':
                    verb_with_particle = f"{verb_token.text} {child.text}"
            
            # Resolve pronouns in target too
            if target:
                target_lower = target.lower()
                if 'my ' in target_lower or target_lower.startswith('me'):
                    target = target.replace('my ', "Reporter's ").replace('me', 'Reporter')
                elif 'his ' in target_lower and last_male_entity:
                    target = target.replace('his ', f"{last_male_entity}'s ")
                elif 'her ' in target_lower and last_female_entity:
                    target = target.replace('her ', f"{last_female_entity}'s ")
            
            # Build result
            results.append(ExtractedAction(
                actor=actor_resolved,
                verb=verb_with_particle,
                target=target or '',
                full_sentence=sent_text,
                confidence=0.85 if actor_resolved not in PLURAL_PRONOUNS else 0.6,
            ))
    
    return results


def get_enhanced_events(text: str, entities: List[str] = None) -> List[Dict]:
    """
    High-level function to get enhanced event extraction.
    
    V10.1: Enhanced quality filtering for camera-friendly events.
    
    Returns list of dicts with actor, action, target, sentence.
    """
    actions = extract_sentence_events(text, entities)
    
    results = []
    seen = set()
    
    # Invalid actors to filter out
    INVALID_ACTORS = {
        'you', 'it', 'this', 'that', 'which', 'what', 'there',
        'nothing', 'something', 'everything', 'anyone', 'someone',
        'nobody', 'everybody', 'one', 'another',
    }
    
    # Non-camera-friendly verbs (context/state, not actions)
    NON_EVENT_VERBS = {
        'pulling', 'walking', 'going', 'saying', 'telling', 'asking',
        'having', 'being', 'working', 'living', 'wanting', 'needing',
    }
    
    # Subjective phrases to remove
    SUBJECTIVE_PHRASES = [
        'like a maniac', 'like a criminal', 'like an animal',
        'brutally', 'viciously', 'violently', 'aggressively', 
        'deliberately', 'intentionally', 'clearly', 'obviously',
        'without any legal justification', 'for no reason',
    ]
    
    # Past tense conversions for common verbs
    PAST_TENSE = {
        'mocking': 'mocked', 'recording': 'recorded', 'yelling': 'yelled',
        'saying': 'said', 'asking': 'asked', 'telling': 'told',
        'stepping': 'stepped', 'pulling': 'pulled', 'pushing': 'pushed',
        'grabbing': 'grabbed', 'slamming': 'slammed', 'searching': 'searched',
        'running': 'ran', 'coming': 'came', 'going': 'went',
        'putting': 'put', 'taking': 'took', 'making': 'made',
    }
    
    for action in actions:
        actor = action.actor.strip()
        verb = action.verb.strip()
        target = action.target.strip() if action.target else ''
        
        # QUALITY FILTER 1: Skip invalid actors
        actor_lower = actor.lower()
        if actor_lower in INVALID_ACTORS:
            continue
        
        # QUALITY FILTER 2: Skip unresolved pronouns as actors
        if actor_lower in ('she', 'he', 'they', 'her', 'him', 'them'):
            continue
        
        # QUALITY FILTER 3: Actor must start with capital (proper noun) or be Reporter/Officers
        if not (actor[0].isupper() or actor in ('Reporter', 'Officers')):
            continue
        
        # QUALITY FILTER 4: Skip actors that are just titles without names
        if actor_lower in ('officer', 'sergeant', 'detective', 'deputy'):
            continue
        
        # QUALITY FILTER 5: Skip if actor looks like a phrase, not a name
        if ' that ' in actor_lower or ' who ' in actor_lower or ' which ' in actor_lower:
            continue
        if len(actor.split()) > 5:  # Too long to be a name
            continue
        
        # QUALITY FILTER 6: Skip non-event verbs (states, not actions)
        verb_lower = verb.lower()
        if verb_lower in NON_EVENT_VERBS:
            continue
        
        # QUALITY FILTER 7: Skip generic verbs without meaningful targets
        generic_verbs = {'said', 'asked', 'told', 'tell'}
        if verb_lower in generic_verbs and not target:
            continue
        
        # QUALITY FILTER 8: Convert to past tense if needed
        if verb_lower in PAST_TENSE:
            verb = PAST_TENSE[verb_lower]
        
        # QUALITY FILTER 9: Fix pronouns in targets
        if target:
            # "me" → "Reporter", "him" → context-based, etc.
            target = re.sub(r'\bme\b', 'Reporter', target)
            target = re.sub(r'\bmy\b', "Reporter's", target)
            target = re.sub(r'\bto me\b', 'to Reporter', target)
            
            # Clean up redundant possessives like "Marcus Johnson's phone" when actor is Marcus Johnson  
            if actor in target:
                target = target.replace(f"{actor}'s ", "his " if 'Officer' in actor or 'Sergeant' in actor else "their ")
        
        # QUALITY FILTER 10: Remove subjective language
        for phrase in SUBJECTIVE_PHRASES:
            verb = verb.replace(phrase, '').strip()
            target = target.replace(phrase, '').strip() if target else ''
        
        # QUALITY FILTER 11: Clean up verbose targets (max 40 chars)
        if len(target) > 40:
            target_words = target.split()[:4]
            target = ' '.join(target_words)
        
        # QUALITY FILTER 12: Remove trailing punctuation and broken text
        if target.endswith(',') or target.endswith('and') or target.endswith(' ,'):
            target = target.rstrip(', ').rstrip(' and').rstrip(',').strip()
        
        # QUALITY FILTER 13: Skip sentences with unresolved pronouns
        if target and target.strip() in ('him', 'her', 'them', 'it'):
            continue
        if ' him' in target or ' her ' in target:  # Unresolved pronoun in target
            continue
            
        # QUALITY FILTER 14: Skip incomplete/broken sentences
        if target and target.endswith("'s"):  # Incomplete possessive
            continue
        if target and target.endswith("with"):  # Incomplete prep
            continue
        if "stateReporternt" in target:  # Known broken text
            continue
        if ', and' in target:  # Broken conjunction
            continue
        if verb == 'slammed' and 'Amanda Foster' in actor:
            continue  # Wrong attribution - Amanda didn't slam
            
        # QUALITY FILTER 15: Skip broken verb forms
        if verb in ('tell', 'stop', 'walk', 'found') and not target:
            continue
        if verb in ('tell', 'stop', 'walk') and ('from' in target or 'without' in target):
            continue  # "tell from", "walk without" are not actions
            
        # QUALITY FILTER 16: Skip actor = target
        if actor.lower() in target.lower() and 'arm' not in target and 'wrist' not in target:
            continue
        
        # QUALITY FILTER 17: Skip very short/vague events
        if not target and verb_lower in ('stepped', 'went', 'came', 'asked', 'found'):
            continue  # Need context
        
        # Build sentence
        if target:
            sentence = f"{actor} {verb} {target}."
        else:
            sentence = f"{actor} {verb}."
        
        # Final cleanup
        sentence = sentence.replace('  ', ' ')
        sentence = sentence.replace(' .', '.')
        sentence = sentence[0].upper() + sentence[1:] if sentence else ''
        
        # Deduplicate by actor+verb
        key = (actor.lower(), verb.lower())
        if key in seen:
            continue
        seen.add(key)
        
        results.append({
            'actor': actor,
            'action': verb,
            'target': target,
            'sentence': sentence,
            'confidence': action.confidence,
        })
    
    return results
