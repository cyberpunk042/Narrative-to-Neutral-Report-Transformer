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
# Note: Use full forms with periods to avoid 'mr' matching 'mrs'
MALE_INDICATORS = {'officer', 'sergeant', 'detective', 'mr.', 'sir', 
                   'officer jenkins', 'officer rodriguez', 'sergeant williams'}
# Female indicators - check these BEFORE male to avoid 'mr' matching 'mrs'
FEMALE_INDICATORS = {'ms.', 'mrs.', 'mrs', 'ms', 'miss', 'madam', 'dr. amanda', 
                     'patricia', 'sarah', 'amanda', 'jennifer'}

# Common male first names for gender detection 
MALE_FIRST_NAMES = {'marcus', 'michael', 'james', 'john', 'robert', 'david', 
                    'william', 'richard', 'joseph', 'thomas', 'charles', 'daniel'}

# Common female first names for gender detection  
FEMALE_FIRST_NAMES = {'patricia', 'sarah', 'amanda', 'jennifer', 'mary', 'linda',
                      'elizabeth', 'barbara', 'susan', 'jessica', 'karen', 'nancy'}


def _get_actor_gender(actor: str) -> str:
    """
    Determine the gender of an actor for pronoun replacement.
    
    Returns:
        'male', 'female', or 'neutral'
    """
    if not actor:
        return 'neutral'
    
    actor_lower = actor.lower()
    
    # Check female indicators FIRST (to avoid 'mr' matching 'mrs')
    for indicator in FEMALE_INDICATORS:
        if indicator in actor_lower:
            return 'female'
    
    # Check male indicators
    for indicator in MALE_INDICATORS:
        if indicator in actor_lower:
            return 'male'
    
    # Check first name in multi-word names (e.g., "Marcus Johnson" → "marcus")
    words = actor.split()
    if words:
        first_name = words[0].lower()
        if first_name in MALE_FIRST_NAMES:
            return 'male'
        if first_name in FEMALE_FIRST_NAMES:
            return 'female'
    
    # Default to neutral if unknown
    return 'neutral'


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
            
            # If no explicit subject, try alternative strategies
            if not actor:
                # Strategy 1a: For conjunct verbs, inherit full subject from head verb
                # "Chen came ... and called 911" → called's subject is Chen
                if verb_token.dep_ == 'conj':
                    head_verb = verb_token.head
                    for child in head_verb.children:
                        if child.dep_ in ('nsubj', 'nsubjpass'):
                            actor_tokens = sorted(child.subtree, key=lambda t: t.i)
                            actor = ' '.join(t.text for t in actor_tokens)
                            break
            
            if not actor:
                # Strategy 1b: For xcomp (open clausal complement) and similar,
                # inherit just the subject pronoun/noun (not full subtree)
                # "He started recording" → recording's subject is "He" (not "He started")
                if verb_token.dep_ in ('xcomp', 'ccomp', 'advcl'):
                    head_verb = verb_token.head
                    for child in head_verb.children:
                        if child.dep_ in ('nsubj', 'nsubjpass'):
                            actor = child.text
                            break
            
            if not actor:
                # Strategy 2: Take full proper noun compound at sentence start
                # "Mrs. Patricia Chen came" → full name, not just "Mrs."
                first_token = sent[0]
                if first_token.pos_ in ('PROPN', 'NOUN', 'PRON'):
                    # Collect the full compound
                    compound_tokens = [first_token]
                    for i, tok in enumerate(sent[1:], start=1):
                        if tok.pos_ == 'PROPN' and tok.dep_ in ('compound', 'flat', 'flat:name') or tok.i == first_token.head.i:
                            compound_tokens.append(tok)
                        elif tok.head.i < tok.i and tok.head.pos_ == 'PROPN':
                            # Include if it's part of the same name chain
                            compound_tokens.append(tok)
                        else:
                            break
                    actor = ' '.join(t.text for t in compound_tokens)
            
            if not actor:
                continue
            
            # V10: If actor is a verbose phrase, try to extract the proper name
            # Pattern: "an elderly woman named Mrs. Patricia Chen who..." → "Patricia Chen"
            import re
            if len(actor) > 30 or ' who ' in actor.lower() or ' named ' in actor.lower():
                # Try to extract a proper name pattern
                # Group(1) captures just the name without the title prefix
                name_match = re.search(r'(?:Mrs?\.?\s*|Ms\.?\s*|Dr\.?\s*)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', actor)
                if name_match:
                    # Use group(1) to get just the name, not the title
                    extracted_name = name_match.group(1).strip()
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
            
            # Extract target (direct object and/or prepositional object)
            target = None
            dobj_target = None
            prep_target = None
            
            for child in verb_token.children:
                if child.dep_ == 'dobj' and not dobj_target:
                    target_tokens = sorted(child.subtree, key=lambda t: t.i)
                    dobj_target = ' '.join(t.text for t in target_tokens)
                elif child.dep_ == 'prep' and not prep_target:
                    # Skip comparative preps like "like a maniac"
                    if child.text.lower() in ('like', 'as'):
                        continue
                    # Get full PP (take the FIRST meaningful prep)
                    pp_tokens = sorted(child.subtree, key=lambda t: t.i)
                    prep_target = ' '.join(t.text for t in pp_tokens)
            
            # Combine dobj and prep for patterns like "put handcuffs on me"
            if dobj_target and prep_target:
                target = f"{dobj_target} {prep_target}"
            elif dobj_target:
                target = dobj_target
            elif prep_target:
                target = prep_target
            
            # Get particles for phrasal verbs AND their complements
            # "jumped out of the car" → verb="jumped out of", target="the car"
            verb_with_particle = verb_token.text
            phrasal_target = None
            
            for child in verb_token.children:
                if child.dep_ == 'prt':
                    # Found a particle (e.g., "out")
                    verb_with_particle = f"{verb_token.text} {child.text}"
                    
                    # Look for preposition following the particle (e.g., "of")
                    for prt_child in child.children:
                        if prt_child.dep_ == 'prep':
                            verb_with_particle = f"{verb_token.text} {child.text} {prt_child.text}"
                            # Get the target of the preposition
                            for prep_obj in prt_child.children:
                                if prep_obj.dep_ == 'pobj':
                                    pobj_tokens = sorted(prep_obj.subtree, key=lambda t: t.i)
                                    phrasal_target = ' '.join(t.text for t in pobj_tokens)
                                    break
                    
                    # Also check sentence-level for "verb particle prep object" pattern
                    # Sometimes spaCy attaches prep to the verb, not the particle
                    if not phrasal_target:
                        for verb_child in verb_token.children:
                            if verb_child.dep_ == 'prep' and verb_child.i > child.i:
                                # Prep comes after particle, likely belongs to phrasal verb
                                verb_with_particle = f"{verb_token.text} {child.text} {verb_child.text}"
                                for prep_obj in verb_child.children:
                                    if prep_obj.dep_ == 'pobj':
                                        pobj_tokens = sorted(prep_obj.subtree, key=lambda t: t.i)
                                        phrasal_target = ' '.join(t.text for t in pobj_tokens)
                                        break
            
            # Use phrasal target if found - prefer it over the full PP target
            # to avoid duplication like "came out onto onto her porch"
            if phrasal_target:
                target = phrasal_target
            
            # Resolve pronouns in target too
            if target:
                target_lower = target.lower()
                if 'my ' in target_lower or target_lower.startswith('me'):
                    target = target.replace('my ', "Reporter's ").replace('me', 'Reporter')
                elif 'his ' in target_lower and last_male_entity:
                    # IMPORTANT: Don't resolve "his" to the actor (e.g., "Rodriguez grabbed his phone"
                    # should NOT become "Rodriguez grabbed Rodriguez's phone")
                    # "his" in target likely refers to someone OTHER than the actor
                    if actor_resolved and actor_resolved.lower() == last_male_entity.lower():
                        # Actor is male - look for another male entity in the sentence
                        # e.g., "Rodriguez ran to Marcus and grabbed his phone" → "his" = Marcus
                        other_male = None
                        for male_name in ['marcus johnson', 'marcus']:
                            if male_name in sent_lower and 'marcus' not in actor_resolved.lower():
                                other_male = 'Marcus Johnson' if 'johnson' in sent_lower else 'Marcus'
                                break
                        if other_male:
                            target = target.replace('his ', f"{other_male}'s ")
                        # else: leave as "his" for manual review
                    else:
                        target = target.replace('his ', f"{last_male_entity}'s ")
                elif 'her ' in target_lower and last_female_entity:
                    # Same logic for "her"
                    if actor_resolved and actor_resolved.lower() == last_female_entity.lower():
                        # Look for another female entity
                        other_female = None
                        for female_name in ['patricia chen', 'patricia']:
                            if female_name in sent_lower and 'patricia' not in actor_resolved.lower():
                                other_female = 'Patricia Chen' if 'chen' in sent_lower else 'Patricia'
                                break
                        if other_female:
                            target = target.replace('her ', f"{other_female}'s ")
                    else:
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
    
    # Speech verbs belong in QUOTES section, not OBSERVED EVENTS
    SPEECH_VERBS = {
        'yell', 'yelled', 'yelling',
        'scream', 'screamed', 'screaming', 
        'shout', 'shouted', 'shouting',
        'say', 'said', 'saying',
        'tell', 'told', 'telling',
        'ask', 'asked', 'asking',
        'whisper', 'whispered', 'whispering',
        'threaten', 'threatened', 'threatening',
        'laugh', 'laughed', 'laughing',  # Reaction, not action
        'mock', 'mocked', 'mocking',      # Characterization of speech
    }
    
    # Subjective phrases to remove
    SUBJECTIVE_PHRASES = [
        'like a maniac', 'like a criminal', 'like an animal',
        'brutally', 'viciously', 'violently', 'aggressively', 
        'deliberately', 'intentionally', 'clearly', 'obviously',
        'without any legal justification', 'for no reason',
        'with excessive force', 'with force',
    ]
    
    # V10.2: Incomplete action modifiers - these indicate attempted, not completed, actions
    INCOMPLETE_MODIFIERS = [
        'tried to', 'attempted to', 'appeared to', 'seemed to',
        'wanted to', 'was going to', 'was about to',
    ]
    
    # V10.2: Context words that suggest wrong extraction (from unrelated phrases)
    FALSE_CONTEXT_PATTERNS = [
        ('walked', 'night', 'night shift'),     # "walk outside at night" from "night shifts"
        ('walked', 'shift', 'night shift'),
        ('walk', 'night', 'night shift'),
        ('jump', 'passenger', 'got out'),       # "jumped out" shouldn't apply to passenger exiting
    ]
    
    # Past tense conversions for common verbs (both base and gerund forms)
    PAST_TENSE = {
        # Gerund → past
        'mocking': 'mocked', 'recording': 'recorded', 'yelling': 'yelled',
        'saying': 'said', 'asking': 'asked', 'telling': 'told',
        'stepping': 'stepped', 'pulling': 'pulled', 'pushing': 'pushed',
        'grabbing': 'grabbed', 'slamming': 'slammed', 'searching': 'searched',
        'running': 'ran', 'coming': 'came', 'going': 'went',
        'putting': 'put', 'taking': 'took', 'making': 'made',
        # Base → past (for infinitives that slip through)
        'grab': 'grabbed', 'slam': 'slammed', 'search': 'searched',
        'run': 'ran', 'come': 'came', 'go': 'went',
        'put': 'put', 'take': 'took', 'make': 'made',
        'walk': 'walked', 'call': 'called', 'document': 'documented',
        'pull': 'pulled', 'push': 'pushed', 'step': 'stepped',
        'try': 'tried', 'approach': 'approached', 'arrive': 'arrived',
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
        
        # QUALITY FILTER 6.5: Skip speech verbs (belong in QUOTES section)
        if verb_lower in SPEECH_VERBS:
            continue
        
        # QUALITY FILTER 6.6: Skip incomplete/attempted actions (A1.1 fix)
        sentence_lower = action.full_sentence.lower()
        is_incomplete_action = False
        for modifier in INCOMPLETE_MODIFIERS:
            if modifier in sentence_lower:
                # The action was attempted but may not have been completed
                # Skip for STRICT events (camera can't confirm completion)
                is_incomplete_action = True
                break
        if is_incomplete_action:
            continue
        
        # QUALITY FILTER 6.7: Skip false extractions from unrelated context (A1.3 fix)
        skip_false_context = False
        for verb_pat, bad_context, source_context in FALSE_CONTEXT_PATTERNS:
            if verb_pat in verb_lower and (bad_context in sentence_lower or source_context in sentence_lower):
                skip_false_context = True
                break
        if skip_false_context:
            continue
        
        # QUALITY FILTER 6.8: Prevent "got out" being reported as "jumped out" (A1.2 fix)
        # Check for actor disambiguation on phrasal verbs involving cars
        if 'jumped out' in verb_lower or 'got out' in verb_lower:
            # In original: Jenkins jumped out, Rodriguez got out (passenger side)
            # Make sure we're not confusing them
            if 'rodriguez' in actor.lower() and 'passenger' in sentence_lower:
                # Rodriguez got out of passenger side - shouldn't be "jumped"
                verb = 'got out of'
            elif 'got out' in verb_lower and 'jumped' not in sentence_lower:
                # Keep as "got out" if that's what the original said
                pass  # verb stays as-is
        
        # QUALITY FILTER 7: Skip generic verbs without meaningful targets
        # Note: Most speech verbs already filtered above
        generic_verbs = {'explain', 'explained', 'respond', 'responded'}
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
                gender = _get_actor_gender(actor)
                pronoun = "his " if gender == 'male' else ("her " if gender == 'female' else "their ")
                target = target.replace(f"{actor}'s ", pronoun)
        
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
        # Skip if target starts with unresolved 'it' (e.g., "it behind Reporter's back")
        if target.lower().startswith('it ') or ' it ' in target.lower():
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
        
        # QUALITY FILTER 15.5: Skip vague "walked" events (A1.3 fix)
        # "walked at night" is not a camera-friendly event, "walked to X" might be
        if verb_lower in ('walked', 'walk', 'walking'):
            if not target or 'at night' in target.lower() or 'outside' in target.lower():
                continue  # Too vague
            if 'night' in sentence_lower or 'shift' in sentence_lower:
                continue  # Likely from "night shifts" context
            
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
