"""
V9: Event-to-Sentence Generator

Generates clean, camera-friendly sentences from Event IR objects.
This module combines:
- Events (actor/verb/target structure from spaCy)
- Entities (for context and pronoun replacement)
- Atomic Statements (for epistemic filtering)

The goal is to produce sentences like:
    "Officer Jenkins grabbed Reporter's left arm."
    "Officer Rodriguez searched Reporter's pockets."
    "Sergeant Williams arrived at the scene."

From raw narrative like:
    "Officer Jenkins deliberately grabbed my left arm with excessive force"
"""

from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
import re


@dataclass
class GeneratedEvent:
    """A camera-friendly event sentence with metadata."""
    sentence: str           # The generated sentence
    actor: str             # Who performed the action
    verb: str              # What action
    target: Optional[str]  # Target of action (if any)
    confidence: float      # How confident we are in this generation
    source_segment: str    # Original segment ID
    original_text: str     # Original text for debugging
    exclusion_reason: Optional[str] = None  # If excluded, why


# =============================================================================
# Verb Conjugation
# =============================================================================

# Past tense mappings for irregular verbs
IRREGULAR_PAST_TENSE = {
    'grab': 'grabbed',
    'run': 'ran',
    'run over': 'ran over',
    'come': 'came',
    'come over': 'came over',
    'put': 'put',
    'get': 'got',
    'get out': 'got out',
    'say': 'said',
    'go': 'went',
    'see': 'saw',
    'hear': 'heard',
    'take': 'took',
    'give': 'gave',
    'find': 'found',
    'tell': 'told',
    'make': 'made',
    'think': 'thought',
    'know': 'knew',
    'feel': 'felt',
    'become': 'became',
    'begin': 'began',
    'break': 'broke',
    'bring': 'brought',
    'buy': 'bought',
    'catch': 'caught',
    'choose': 'chose',
    'do': 'did',
    'draw': 'drew',
    'drive': 'drove',
    'eat': 'ate',
    'fall': 'fell',
    'fight': 'fought',
    'fly': 'flew',
    'forget': 'forgot',
    'freeze': 'froze',
    'grow': 'grew',
    'have': 'had',
    'hide': 'hid',
    'hit': 'hit',
    'hold': 'held',
    'hurt': 'hurt',
    'keep': 'kept',
    'lay': 'laid',
    'lead': 'led',
    'leave': 'left',
    'lend': 'lent',
    'let': 'let',
    'lie': 'lay',
    'lose': 'lost',
    'mean': 'meant',
    'meet': 'met',
    'pay': 'paid',
    'read': 'read',
    'ride': 'rode',
    'ring': 'rang',
    'rise': 'rose',
    'send': 'sent',
    'set': 'set',
    'shake': 'shook',
    'shine': 'shone',
    'shoot': 'shot',
    'show': 'showed',
    'shut': 'shut',
    'sing': 'sang',
    'sit': 'sat',
    'sleep': 'slept',
    'speak': 'spoke',
    'spend': 'spent',
    'stand': 'stood',
    'steal': 'stole',
    'stick': 'stuck',
    'strike': 'struck',
    'swim': 'swam',
    'swing': 'swung',
    'teach': 'taught',
    'tear': 'tore',
    'throw': 'threw',
    'understand': 'understood',
    'wake': 'woke',
    'wear': 'wore',
    'win': 'won',
    'write': 'wrote',
    # Phrasal verbs  
    'jump out': 'jumped out',
    'step back': 'stepped back',
    'walk out': 'walked out',
    'pull over': 'pulled over',
    'run over': 'ran over',
    'come over': 'came over',
    'come out': 'came out',
    'get out': 'got out',
    'find out': 'found out',
    'go out': 'went out',
    'look at': 'looked at',
    'look for': 'looked for',
    # Common verbs that end in consonant
    'whisper': 'whispered',
    'threaten': 'threatened',
    'happen': 'happened',
    'open': 'opened',
    'listen': 'listened',
    'offer': 'offered',
    'answer': 'answered',
    'enter': 'entered',
    'order': 'ordered',
    'suffer': 'suffered',
    'wonder': 'wondered',
    'consider': 'considered',
    'discover': 'discovered',
    'remember': 'remembered',
    'cover': 'covered',
    'recover': 'recovered',
    # Common speech/action verbs
    'call': 'called',
    'pull': 'pulled',
    'push': 'pushed',
    'yell': 'yelled',
    'scream': 'screamed',
    'search': 'searched',
    'approach': 'approached',
    'arrive': 'arrived',
    'document': 'documented',
    'diagnose': 'diagnosed',
    'file': 'filed',
    'receive': 'received',
    'ask': 'asked',
    'start': 'started',
    'work': 'worked',
    'walk': 'walked',
    'laugh': 'laughed',
    'jump': 'jumped',
    'research': 'researched',
    'complain': 'complained',
    'charge': 'charged',
}


def conjugate_past_tense(verb: str) -> str:
    """
    Convert verb to past tense.
    
    Examples:
        grab -> grabbed
        run over -> ran over
        search -> searched
    """
    if not verb:
        return verb
    
    verb_lower = verb.lower().strip()
    
    # Check irregular verbs first
    if verb_lower in IRREGULAR_PAST_TENSE:
        return IRREGULAR_PAST_TENSE[verb_lower]
    
    # Regular verb conjugation
    if verb_lower.endswith('e'):
        return verb_lower + 'd'
    elif verb_lower.endswith('y') and len(verb_lower) > 1 and verb_lower[-2] not in 'aeiou':
        return verb_lower[:-1] + 'ied'
    elif verb_lower.endswith('er') or verb_lower.endswith('en'):
        # Verbs ending in -er or -en: whisper->whispered, threaten->threatened
        return verb_lower + 'ed'
    elif len(verb_lower) > 2 and verb_lower[-1] not in 'aeiouwy' and verb_lower[-2] in 'aeiou' and verb_lower[-3] not in 'aeiou':
        # Double consonant only for CVC pattern (stop->stopped)
        # But not for words like 'search' where last vowel isn't stressed
        if verb_lower[-1] in 'bdfgklmnprst' and len(verb_lower) <= 5:
            return verb_lower + verb_lower[-1] + 'ed'
        return verb_lower + 'ed'
    else:
        return verb_lower + 'ed'


# =============================================================================
# Pronoun Replacement
# =============================================================================

def replace_pronouns_in_target(target: str, reporter_label: str = "Reporter") -> str:
    """
    Replace pronouns in target with proper nouns.
    
    Examples:
        "my left arm" -> "Reporter's left arm"
        "his phone" -> "the phone"  (ambiguous possessive)
        "me" -> "Reporter"
    """
    if not target:
        return target
    
    target = target.strip()
    
    # First-person possessives -> Reporter's
    target = re.sub(r'\bmy\b', f"{reporter_label}'s", target, flags=re.IGNORECASE)
    target = re.sub(r'\bmine\b', f"{reporter_label}'s", target, flags=re.IGNORECASE)
    
    # First-person object pronouns -> Reporter
    target = re.sub(r'\bme\b', reporter_label, target, flags=re.IGNORECASE)
    
    # Third-person possessives (ambiguous - make neutral)
    target = re.sub(r'\bhis\b(?!\s+\w+\')', 'the', target, flags=re.IGNORECASE)
    target = re.sub(r'\bher\b(?!\s+\w+\')', 'the', target, flags=re.IGNORECASE)
    target = re.sub(r'\btheir\b', 'the', target, flags=re.IGNORECASE)
    
    # Clean up any double spaces
    target = ' '.join(target.split())
    
    return target


# =============================================================================
# Text Cleaning
# =============================================================================

# Words/phrases that indicate subjective characterization
CHARACTERIZATION_PATTERNS = [
    r'\bdeliberately\b',
    r'\bintentionally\b', 
    r'\bpurposefully\b',
    r'\bmaliciously\b',
    r'\bviciously\b',
    r'\bbrutally\b',
    r'\baggressively\b',
    r'\bviolently\b',
    r'\bexcessive(?:ly)?\b',
    r'\bwithout (?:any )?(?:legal )?justification\b',
    r'\bwithout (?:my )?consent\b',
    r'\blike a (?:maniac|criminal|thug)\b',
    r'\bso tightly that\b',
    r'\bwith (?:excessive )?force\b',
    r'\bfor (?:absolutely )?no reason\b',
]

# Compile patterns for efficiency
CHARACTERIZATION_REGEX = [re.compile(p, re.IGNORECASE) for p in CHARACTERIZATION_PATTERNS]


# =============================================================================
# Phrasal Verb Extraction
# =============================================================================

# Phrasal verbs that should be kept together with their preposition
PHRASAL_VERB_PATTERNS = {
    'jump': [
        (r'jumped?\s+out\s+of\s+(.+?)(?:\s+like|\s+and|$)', 'jumped out of'),
    ],
    'get': [
        (r'got\s+out\s+of\s+(.+?)(?:\s+and|$)', 'got out of'),
    ],
    'come': [
        (r'cam?e?\s+over\s+to\s+(.+?)(?:\s+and|$)', 'came over to'),
        (r'cam?e?\s+out\s+of\s+(.+?)(?:\s+and|$)', 'came out of'),
        (r'cam?e?\s+out\s+onto\s+(.+?)(?:\s+and|$)', 'came out onto'),
    ],
    'run': [
        (r'ran?\s+over\s+to\s+(.+?)(?:\s+and|$)', 'ran over to'),
    ],
    'pull': [
        (r'pull(?:ed)?\s+(.+?)\s+aside', 'pulled {target} aside'),  # Special: target in middle
    ],
    'step': [
        (r'step(?:ped)?\s+out\s+of\s+(.+?)(?:\s+and|$)', 'stepped out of'),
    ],
}


def extract_phrasal_verb_and_target(verb: str, description: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract phrasal verb and its target from description.
    
    Example:
        verb="jump", description="jumped out of the car like a maniac"
        -> ("jumped out of", "the car")
    
    Returns:
        (phrasal_verb_past_tense, target) or (None, None) if not a phrasal verb
    """
    if not verb or not description:
        return None, None
    
    verb_lower = verb.lower().strip()
    desc_lower = description.lower()
    
    # Check if this verb has phrasal patterns
    if verb_lower not in PHRASAL_VERB_PATTERNS:
        return None, None
    
    for pattern, phrasal_form in PHRASAL_VERB_PATTERNS[verb_lower]:
        match = re.search(pattern, desc_lower, re.IGNORECASE)
        if match:
            target = match.group(1).strip()
            # Clean target
            target = re.sub(r'\s*(,|\.)\s*$', '', target)
            target = re.sub(r'\s+like\s+.*$', '', target)  # Remove "like a maniac"
            
            if len(target) > 2 and len(target) < 40:
                # Handle special case where target goes in middle
                if '{target}' in phrasal_form:
                    return phrasal_form.replace('{target}', target), None
                return phrasal_form, target
    
    return None, None


def clean_description_for_target(description: str) -> Optional[str]:
    """
    Extract target from event description if not provided.
    
    Example:
        "Officer Jenkins grabbed my left arm with excessive force"
        -> extract "my left arm" as target
    """
    if not description:
        return None
    
    # Common patterns for extracting target
    patterns = [
        # Physical actions
        r'grabbed\s+(.+?)(?:\s+with|\s+and|$)',
        r'searched\s+(?:through\s+)?(.+?)(?:\s+without|\s+and|$)',
        r'put\s+(.+?)\s+on',
        r'slammed\s+(.+?)\s+against',
        r'twisted\s+(.+?)(?:\s+behind|$)',
        r'pushed\s+(.+?)(?:\s+against|\s+into|$)',
        # Movement with destination
        r'ran\s+(?:over\s+)?to\s+(.+?)(?:\s+and|$)',
        r'came\s+(?:over\s+)?to\s+(.+?)(?:\s+and|$)',
        r'walked\s+(?:over\s+)?to\s+(.+?)(?:\s+and|$)',
        # Phrasal verbs with prepositions
        r'jumped\s+out\s+of\s+(.+?)(?:\s+and|\s+like|$)',
        r'got\s+out\s+of\s+(.+?)(?:\s+and|$)',
        r'stepped\s+(?:out\s+of|back\s+from)\s+(.+?)(?:\s+and|$)',
        # Taking/giving actions
        r'took\s+(.+?)(?:\s+from|,|$)',
        r'gave\s+(.+?)\s+to',
        r'handed\s+(.+?)\s+to',
        # Documentation/filing
        r'documented\s+(.+?)(?:\s+from|\s+and|,|$)',
        r'filed\s+(.+?)(?:\s+with|\s+against|$)',
        # Speaking to someone
        r'said\s+(?:to\s+)?(.+?)(?:\s+that|,|\"|$)',
        r'yelled\s+(?:to\s+|at\s+)?(.+?)(?:\s+that|,|\"|$)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            target = match.group(1).strip()
            # Clean up target
            target = re.sub(r'\s*(,|\.)\s*$', '', target)  # Remove trailing punctuation
            target = re.sub(r'^["\']+|["\']+$', '', target)  # Remove quotes
            target = re.sub(r'\s+like\s+.*$', '', target)  # Remove "like a..."
            
            # Reject if target looks like quote content
            if '"' in target or "'" in target:
                continue  # Quote contamination
            if len(target) > 50:  # Too long, likely sentence fragment
                continue
            if target.lower().startswith(('you', 'i ', 'we ')):
                continue  # Likely quote content
                
            if len(target) > 2 and len(target) < 50:  # Sanity check
                return target
    
    return None


def strip_characterization(text: str) -> str:
    """
    Remove characterization language from text.
    
    Example:
        "deliberately grabbed with excessive force" 
        -> "grabbed"
    """
    if not text:
        return text
    
    result = text
    for pattern in CHARACTERIZATION_REGEX:
        result = pattern.sub('', result)
    
    # Clean up whitespace
    result = ' '.join(result.split())
    
    return result


# =============================================================================
# Actor Validation
# =============================================================================

# Named person patterns that are valid actors
VALID_ACTOR_PATTERNS = [
    r'^Officer\s+\w+',
    r'^Sergeant\s+\w+',
    r'^Detective\s+\w+',
    r'^Deputy\s+\w+',
    r'^Dr\.\s+\w+',
    r'^Mrs?\.\s+\w+',
    r'^Reporter$',
    r'^[A-Z][a-z]+\s+[A-Z][a-z]+',  # Two-word proper noun (First Last)
]

# Patterns that are NOT valid actors
INVALID_ACTOR_PATTERNS = [
    r'^(he|she|they|it|we|i|you|who|that|this|these|those)$',  # Pronouns
    r'^(he|she|they|it|we|i|you|who)\s',  # Pronouns followed by space
    r'^the\s+',  # Definite articles (the officer, the cop)
    r'^a\s+',    # Indefinite articles
    r'^an\s+',   # Indefinite articles
    r'^my\s+',   # Possessives
    r'^his\s+',
    r'^her\s+',
    r'^their\s+',
    r'^this\s+',  # Demonstratives
    r'^that\s+',
    r'^these\s+',
    r'^those\s+',
    r'^it\s+',   # "It all started"
    r'\ball$',   # "they all", "It all"
    r'cops?$',   # Generic terms
    r'officers?$',
    r'police$',
    r'^police\s+officers?$',
    r'^at\s+least',  # "at least 12 other citizens"
    r'^\d+',  # Numbers at start
]

VALID_ACTOR_REGEX = [re.compile(p, re.IGNORECASE) for p in VALID_ACTOR_PATTERNS]
INVALID_ACTOR_REGEX = [re.compile(p, re.IGNORECASE) for p in INVALID_ACTOR_PATTERNS]


def is_valid_actor(actor: str) -> Tuple[bool, Optional[str]]:
    """
    Check if actor is a valid named person for STRICT events.
    
    Returns:
        (is_valid, reason_if_invalid)
    """
    if not actor:
        return False, "No actor specified"
    
    actor = actor.strip()
    
    # Check invalid patterns first
    for pattern in INVALID_ACTOR_REGEX:
        if pattern.search(actor):
            return False, f"Actor is pronoun or generic: '{actor}'"
    
    # Check for valid patterns
    for pattern in VALID_ACTOR_REGEX:
        if pattern.match(actor):
            return True, None
    
    # If no pattern matched, it's likely invalid
    return False, f"Actor not recognized as named person: '{actor}'"


# =============================================================================
# Epistemic Filtering
# =============================================================================

# Epistemic types that should be EXCLUDED from STRICT
EXCLUDE_EPISTEMIC_TYPES = {
    'inference',           # Reporter's conclusions about intent
    'characterization',    # Subjective descriptions
    'conspiracy_claim',    # Unverifiable conspiracy claims
    'interpretation',      # Reporter's interpretation of events
}


# =============================================================================
# Verb Quality Filtering
# =============================================================================

# Verbs that are meaningless without a target/complement
VERBS_REQUIRING_TARGET = {
    # Speech verbs (base and past) - should go to QUOTES section
    'say', 'said', 'ask', 'asked', 'tell', 'told', 'explain', 'explained',
    'state', 'stated', 'yell', 'yelled', 'scream', 'screamed',
    'whisper', 'whispered', 'shout', 'shouted', 'laugh', 'laughed', 
    'threaten', 'threatened',
    # Intention verbs (base and past)
    'try', 'tried', 'attempt', 'attempted', 'want', 'wanted',
    # Generic verbs that need context
    'start', 'started', 'begin', 'began', 'continue', 'continued',
    'work', 'worked', 'walk', 'walked',  # Too generic without destination
    'go', 'went', 'come', 'came',  # Need destination
    'think', 'thought', 'believe', 'believed', 'feel', 'felt',  # Mental states
    'know', 'knew', 'understand', 'understood',  # Knowledge states
    # Witness actions that need context
    'see', 'saw', 'hear', 'heard', 'notice', 'noticed', 
    'observe', 'observed', 'witness', 'witnessed',
    # Generic actions
    'show up', 'showed up', 'find out', 'found out',
    'suffer', 'suffered', 'charge', 'charged', 'complain', 'complained',
    'pursue', 'pursued', 'refuse', 'refused', 'research', 'researched',
}

# Verbs that are always meaningful (even without target)
STANDALONE_VERBS = {
    'arrive', 'arrived', 'depart', 'departed', 'leave', 'left',  # Location changes
    'freeze', 'froze',  # Physical state (for officers, meaningful)
    'run', 'ran', 'jump', 'jumped', 'fall', 'fell',  # Physical movements
}


def is_verb_meaningful(verb: str, target: Optional[str], actor: str) -> Tuple[bool, Optional[str]]:
    """
    Check if verb+target combination is meaningful enough for STRICT section.
    
    Returns:
        (is_meaningful, reason_if_not)
    """
    if not verb:
        return False, "No verb"
    
    verb_lower = verb.lower().strip()
    
    # Speech/communication verbs should NEVER be in STRICT - they belong in QUOTES
    # Include both base form and past tense
    # NOTE: 'call' is NOT included as "called 911" is an observable action
    SPEECH_VERBS = {
        # Base forms
        'say', 'ask', 'tell', 'yell', 'scream', 'shout', 'whisper', 'laugh', 
        'threaten', 'state', 'explain', 'respond', 'reply', 'answer',
        # Past tense
        'said', 'asked', 'told', 'yelled', 'screamed', 'shouted', 'whispered', 
        'laughed', 'threatened', 'stated', 'explained', 'responded',
        'replied', 'answered',
    }
    if verb_lower in SPEECH_VERBS:
        return False, f"Speech verb '{verb}' belongs in QUOTES section"
    
    # If verb requires target and no target, reject
    if verb_lower in VERBS_REQUIRING_TARGET and not target:
        return False, f"Verb '{verb}' requires target/complement"
    
    # Check target quality - reject quote contamination
    if target:
        target_lower = target.lower()
        # Reject if target contains actual quotes (not possessive 's)
        # Check for paired quotes or standalone quotes that aren't possessive
        if '"' in target:
            return False, "Target contains quote content"
        # Check for quotes that aren't possessive 's
        if "'" in target and "'s " not in target and not target.endswith("'s"):
            return False, "Target contains quote content"
        if target_lower.startswith(('you ', "i ", "we ", "what", "sure ", "there")):
            return False, "Target looks like quote content"
        if "reporter's complaint" in target_lower:
            return False, "Target contains self-referential content"
    
    # Special case: Reporter's generic actions are less useful in STRICT section
    REPORTER_GENERIC_VERBS = {
        # Base forms
        'freeze', 'scream', 'try', 'work', 'walk', 'research', 
        'go', 'hear', 'complain', 'charge', 'suffer', 'pursue', 'refuse',
        # Past forms
        'froze', 'screamed', 'tried', 'worked', 'walked', 'researched', 
        'went', 'heard', 'complained', 'charged', 'suffered', 'pursued', 'refused',
    }
    if actor == "Reporter" and verb_lower in REPORTER_GENERIC_VERBS:
        if not target or len(target) < 5:
            return False, f"Reporter's action '{verb}' needs context"
    
    # Generic verbs that are always meaningless
    GENERIC_VERBS = {'happen', 'happened', 'occur', 'occurred', 'be', 'was', 'were'}
    if verb_lower in GENERIC_VERBS:
        return False, f"Verb '{verb}' is too generic"
    
    return True, None


def should_exclude_by_epistemic(
    segment_text: str,
    atomic_statements: list,
) -> Tuple[bool, Optional[str]]:
    """
    Check if segment should be excluded based on epistemic type.
    
    Returns:
        (should_exclude, reason)
    """
    for stmt in atomic_statements:
        # Match by text overlap
        if hasattr(stmt, 'text') and segment_text[:25] in stmt.text:
            epistemic = getattr(stmt, 'epistemic_type', None)
            if epistemic in EXCLUDE_EPISTEMIC_TYPES:
                return True, f"Excluded by epistemic type: {epistemic}"
    
    return False, None


# =============================================================================
# Main Generator
# =============================================================================

def generate_strict_events(
    events: list,
    segments: list,
    atomic_statements: list,
    entities: list = None,
) -> List[GeneratedEvent]:
    """
    Generate clean, camera-friendly event sentences.
    
    This is the main entry point for V9 event generation.
    
    Args:
        events: Event IR objects with actor/verb/target
        segments: Segment objects for context
        atomic_statements: For epistemic filtering
        entities: Entity objects for context
    
    Returns:
        List of GeneratedEvent objects (both included and excluded with reasons)
    """
    results: List[GeneratedEvent] = []
    seen_sentences: Set[str] = set()
    
    # Build segment lookup for context
    segment_lookup = {seg.id: seg for seg in segments}
    
    # Build segment -> events mapping
    seg_to_events: Dict[str, list] = {}
    for ev in events:
        for seg_id in (ev.source_spans or []):
            if seg_id not in seg_to_events:
                seg_to_events[seg_id] = []
            seg_to_events[seg_id].append(ev)
    
    # Process each event
    for ev in events:
        # Get source segment
        seg_id = ev.source_spans[0] if ev.source_spans else None
        seg = segment_lookup.get(seg_id) if seg_id else None
        original_text = seg.text if seg else ev.description
        
        # 1. Validate actor
        actor = ev.actor_label
        is_valid, actor_reason = is_valid_actor(actor)
        
        if not is_valid:
            results.append(GeneratedEvent(
                sentence="",
                actor=actor or "",
                verb=ev.action_verb or "",
                target=ev.target_object,
                confidence=0.0,
                source_segment=seg_id or "",
                original_text=original_text[:80] if original_text else "",
                exclusion_reason=actor_reason,
            ))
            continue
        
        # 2. Check epistemic exclusion
        if seg:
            should_exclude, epistemic_reason = should_exclude_by_epistemic(
                seg.text, atomic_statements
            )
            # Note: We DON'T exclude based on epistemic alone anymore
            # We use it as a flag but still generate the event if actor is valid
        
        # 3. Get verb and conjugate
        verb = ev.action_verb
        if not verb:
            results.append(GeneratedEvent(
                sentence="",
                actor=actor,
                verb="",
                target=ev.target_object,
                confidence=0.0,
                source_segment=seg_id or "",
                original_text=original_text[:80] if original_text else "",
                exclusion_reason="No action verb",
            ))
            continue
        
        verb_past = conjugate_past_tense(verb)
        
        # 3.5. Check for phrasal verbs (e.g., "jumped out of" instead of "jumped")
        phrasal_verb, phrasal_target = extract_phrasal_verb_and_target(verb, ev.description)
        if phrasal_verb:
            verb_past = phrasal_verb
            # Use phrasal target if no explicit target
            if not ev.target_object and phrasal_target:
                target = phrasal_target
            else:
                target = ev.target_object
        else:
            # 4. Get target (from event or parse from description)
            target = ev.target_object
            if not target:
                target = clean_description_for_target(ev.description)
        
        # 5. Replace pronouns in target
        if target:
            target = replace_pronouns_in_target(target)
            target = strip_characterization(target)
        
        # 5.5. Check verb quality (some verbs need targets to be meaningful)
        is_meaningful, verb_reason = is_verb_meaningful(verb, target, actor)
        if not is_meaningful:
            results.append(GeneratedEvent(
                sentence="",
                actor=actor,
                verb=verb,
                target=target,
                confidence=0.0,
                source_segment=seg_id or "",
                original_text=original_text[:80] if original_text else "",
                exclusion_reason=verb_reason,
            ))
            continue
        
        # 6. Generate sentence
        if target:
            sentence = f"{actor} {verb_past} {target}."
        else:
            sentence = f"{actor} {verb_past}."
        
        # Clean up sentence
        sentence = sentence.strip()
        sentence = re.sub(r'\s+', ' ', sentence)
        sentence = re.sub(r'\s+\.', '.', sentence)
        
        # 7. Deduplicate
        sentence_key = sentence.lower()
        if sentence_key in seen_sentences:
            continue
        seen_sentences.add(sentence_key)
        
        # 8. Calculate confidence
        confidence = 0.9 if target else 0.7
        if actor and 'Officer' in actor or 'Sergeant' in actor:
            confidence += 0.05  # Boost for clear authority figures
        
        results.append(GeneratedEvent(
            sentence=sentence,
            actor=actor,
            verb=verb,
            target=target,
            confidence=confidence,
            source_segment=seg_id or "",
            original_text=original_text[:80] if original_text else "",
            exclusion_reason=None,
        ))
    
    # Sort by confidence (highest first)
    results.sort(key=lambda x: (x.exclusion_reason is None, x.confidence), reverse=True)
    
    return results


def get_strict_event_sentences(
    events: list,
    segments: list,
    atomic_statements: list,
    entities: list = None,
    max_events: int = 25,
) -> List[str]:
    """
    Convenience function to get just the sentence strings for STRICT section.
    
    Args:
        events: Event IR objects
        segments: Segment objects
        atomic_statements: For context
        entities: Entity objects
        max_events: Maximum number of events to return
    
    Returns:
        List of clean sentence strings
    """
    generated = generate_strict_events(events, segments, atomic_statements, entities)
    
    # Filter to only valid (non-excluded) events
    valid_events = [g for g in generated if g.exclusion_reason is None and g.sentence]
    
    # Return sentences up to max
    return [g.sentence for g in valid_events[:max_events]]


def get_excluded_events_summary(
    events: list,
    segments: list,
    atomic_statements: list,
) -> Dict[str, List[str]]:
    """
    Get summary of excluded events grouped by reason.
    
    Returns:
        Dict mapping exclusion reason to list of original texts
    """
    generated = generate_strict_events(events, segments, atomic_statements)
    
    excluded: Dict[str, List[str]] = {}
    for g in generated:
        if g.exclusion_reason:
            reason = g.exclusion_reason.split(':')[0]  # Simplify reason
            if reason not in excluded:
                excluded[reason] = []
            excluded[reason].append(g.original_text)
    
    return excluded
