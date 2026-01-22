"""
Pass 35 — Event Classification

V7 / Stage 1: Event classification using Policy Engine rules.

This pass classifies events with:
- is_camera_friendly + confidence + reason + source
- is_follow_up
- is_fragment
- is_source_derived
- contains_quote
- contains_interpretive
- neutralized_description

Uses PolicyEngine classification rules (CLASSIFY, DISQUALIFY, DETECT, STRIP).
All patterns are defined in YAML files under _classification/.
"""

import re
from typing import Any, List

from nnrt.core.context import TransformContext
from nnrt.core.logging import get_pass_logger
from nnrt.policy.engine import get_policy_engine
from nnrt.policy.models import RuleAction

PASS_NAME = "p35_classify_events"
log = get_pass_logger(PASS_NAME)


# =============================================================================
# Verb Conjugation Helper
# =============================================================================

# Irregular verbs: base -> past
IRREGULAR_VERBS = {
    'be': 'was', 'am': 'was', 'is': 'was', 'are': 'were',
    'begin': 'began', 'break': 'broke', 'bring': 'brought',
    'build': 'built', 'buy': 'bought', 'catch': 'caught',
    'choose': 'chose', 'come': 'came', 'do': 'did',
    'drink': 'drank', 'drive': 'drove', 'eat': 'ate',
    'fall': 'fell', 'feel': 'felt', 'find': 'found',
    'freeze': 'froze', 'get': 'got', 'give': 'gave',
    'go': 'went', 'grab': 'grabbed', 'have': 'had',
    'hear': 'heard', 'hit': 'hit', 'hold': 'held',
    'jump': 'jumped', 'keep': 'kept', 'know': 'knew',
    'leave': 'left', 'lose': 'lost', 'make': 'made',
    'put': 'put', 'read': 'read', 'run': 'ran',
    'say': 'said', 'see': 'saw', 'search': 'searched',
    'send': 'sent', 'set': 'set', 'sit': 'sat',
    'slam': 'slammed', 'speak': 'spoke', 'stand': 'stood',
    'take': 'took', 'tell': 'told', 'think': 'thought',
    'throw': 'threw', 'twist': 'twisted', 'understand': 'understood',
    'walk': 'walked', 'write': 'wrote', 'yell': 'yelled',
    # Added: more common verbs
    'attack': 'attacked', 'start': 'started', 'pull': 'pulled',
    'push': 'pushed', 'step': 'stepped', 'record': 'recorded',
}


def _conjugate_past_tense(verb: str) -> str:
    """
    Conjugate verb to past tense.
    
    Handles:
    - Single verbs: run -> ran
    - Phrasal verbs: run over -> ran over, come out -> came out
    
    Uses irregular verb lookup first, then applies regular -ed rules.
    """
    if not verb:
        return verb
    
    verb = verb.strip()
    
    # Handle phrasal verbs (e.g., "run over", "come out")
    parts = verb.split()
    if len(parts) > 1:
        # Conjugate only the main verb (first word)
        main_verb = parts[0]
        particle = ' '.join(parts[1:])
        conjugated_main = _conjugate_past_tense(main_verb)
        return f"{conjugated_main} {particle}"
    
    verb_lower = verb.lower()
    
    # Already past tense (common forms)
    if verb_lower.endswith('ed') or verb_lower in {'went', 'came', 'ran', 'saw', 'took', 'got', 'had', 'said', 'made', 'froze', 'gave'}:
        return verb
    
    # Check irregular
    if verb_lower in IRREGULAR_VERBS:
        return IRREGULAR_VERBS[verb_lower]
    
    # Regular conjugation
    if verb_lower.endswith('e'):
        return verb_lower + 'd'
    elif verb_lower.endswith('y') and len(verb_lower) > 2 and verb_lower[-2] not in 'aeiou':
        return verb_lower[:-1] + 'ied'
    elif len(verb_lower) > 2 and verb_lower[-1] not in 'aeiouwxy' and verb_lower[-2] in 'aeiou' and verb_lower[-3] not in 'aeiou':
        # Double final consonant (stop -> stopped)
        return verb_lower + verb_lower[-1] + 'ed'
    else:
        return verb_lower + 'ed'


def classify_events(ctx: TransformContext) -> TransformContext:
    """
    Classify events for camera-friendliness and other properties.
    
    V7 / Stage 1: Uses PolicyEngine classification rules.
    """
    if not ctx.events:
        log.debug("no_events", message="No events to classify")
        return ctx
    
    engine = get_policy_engine()
    
    camera_friendly_count = 0
    disqualified_count = 0
    
    for event in ctx.events:
        # Get description to classify
        text = event.description or ""
        
        # Start with optimistic defaults
        event.is_camera_friendly = True
        event.camera_friendly_confidence = 0.9
        event.camera_friendly_reason = "passed_all_rules"
        event.camera_friendly_source = PASS_NAME
        event.is_fragment = False
        event.is_follow_up = False
        event.is_source_derived = False
        event.contains_quote = False
        event.contains_interpretive = False
        
        # =====================================================================
        # Step 1: Apply classification rules from PolicyEngine
        # =====================================================================
        
        classification_results = engine.apply_classification_rules(text, "event")
        
        for result in classification_results:
            field = result["field"]
            value = result["value"]
            reason = result["reason"]
            confidence = result["confidence"]
            
            # Handle is_camera_friendly specially
            if field == "is_camera_friendly" and value == False:
                event.is_camera_friendly = False
                event.camera_friendly_confidence = confidence
                event.camera_friendly_reason = reason
                
                # Also set category flags based on reason
                if "conjunction" in reason or "verb_start" in reason:
                    event.is_fragment = True
                elif "follow_up" in reason:
                    event.is_follow_up = True
                elif "source_derived" in reason:
                    event.is_source_derived = True
            
            # Handle boolean detection flags
            elif field == "contains_quote" and value == True:
                event.contains_quote = True
            elif field == "contains_interpretive" and value == True:
                event.contains_interpretive = True
                # Track which terms were found
                if "matched_text" in result:
                    if not event.interpretive_terms_found:
                        event.interpretive_terms_found = []
                    event.interpretive_terms_found.append(result["matched_text"])
        
        # =====================================================================
        # Step 2: Named Actor Detection (V1 Rules 4 & 5) - based on text
        # =====================================================================
        
        if event.is_camera_friendly:
            words = text.split()
            first_word = words[0].lower() if words else ""
            
            # -----------------------------------------------------------------
            # Rule 4: Must have NAMED ACTOR anywhere in the text
            # V8.1: Check ANYWHERE, not just at start
            # V7.4: Also check event.actor_label (set by extraction pass)
            # -----------------------------------------------------------------
            
            has_named_actor = False
            
            # V7.4: Check if actor_label is already a named actor (from extraction)
            # This handles compound verbs like "twisted" inheriting actor from "grabbed"
            if event.actor_label:
                actor_lower = event.actor_label.lower()
                # Check if it's a Title + Name pattern
                if re.match(r'^(officer|sergeant|detective|captain|lieutenant|deputy|dr\.?|mr\.?|mrs\.?|ms\.?)\s+\w+', actor_lower):
                    has_named_actor = True
                # Or a proper name (two capitalized words)
                elif re.match(r'^[A-Z][a-z]+\s+[A-Z][a-z]+$', event.actor_label):
                    has_named_actor = True
                # Or Reporter
                elif actor_lower == 'reporter':
                    has_named_actor = True
            
            # Pattern 1: Title + Name in TEXT (e.g., "Officer Jenkins")
            if not has_named_actor:
                title_pattern = r'\b(Officer|Sergeant|Detective|Captain|Lieutenant|Deputy|Dr\.?|Mr\.?|Mrs\.?|Ms\.?)\s+[A-Z][a-z]+'
                if re.search(title_pattern, text):
                    has_named_actor = True
            
            # Pattern 2: Two-word proper nouns (CASE SENSITIVE)
            # e.g., "Marcus Johnson", "Patricia Chen"
            if not has_named_actor:
                proper_noun_pattern = r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b'
                match = re.search(proper_noun_pattern, text)  # NO IGNORECASE
                if match:
                    # Verify it's not a common phrase like "He found", "My neighbor"
                    matched = match.group()
                    matched_first = matched.split()[0].lower()
                    skip_words = {'he', 'she', 'they', 'it', 'i', 'my', 'his', 'her', 'the', 'a', 'an', 'we', 'you'}
                    if matched_first not in skip_words:
                        has_named_actor = True
            
            # Pattern 3: Valid START patterns (entity classes, plurals)
            text_lower = text.lower()
            START_ACTOR_PATTERNS = [
                # Named persons at start
                r'^(officer|sergeant|detective|captain|lieutenant|deputy|dr\.?|mr\.?|mrs\.?|ms\.?)\s+\w+',
                # Entity classes at start (Another witness, The officers, This cruiser)
                r'^(the|a|an|this|that|another|one|two|three|four|five)\s+(officer|officers|sergeant|detective|witness|witnesses|neighbor|woman|man|person|vehicle|car|cruiser|people)',
                # Generic plurals (Officers approached, Witnesses saw)
                r'^(officers|witnesses|bystanders|paramedics)\s+',
            ]
            
            for pattern in START_ACTOR_PATTERNS:
                if re.match(pattern, text_lower):
                    has_named_actor = True
                    break
            
            # -----------------------------------------------------------------
            # Rule 5: Pronoun starts are OK ONLY if named actor exists elsewhere
            # "His partner, Officer Rodriguez" -> OK (Officer Rodriguez named)
            # "He found my wallet" -> NOT OK (who is He?)
            # -----------------------------------------------------------------
            
            PRONOUN_STARTS = {
                'he', 'she', 'they', 'it', 'we', 'i', 'you',
                'his', 'her', 'their', 'its', 'my', 'your', 'our',
                'him', 'them', 'us', 'me',
            }
            
            if first_word in PRONOUN_STARTS:
                if not has_named_actor:
                    event.is_camera_friendly = False
                    event.camera_friendly_confidence = 0.85
                    event.camera_friendly_reason = f"pronoun_start_no_named_actor:{first_word}"
                    event.actor_resolved = False
                else:
                    # Pronoun start with named actor elsewhere - OK but mark as needing resolution
                    event.actor_resolved = False
                    event.actor_resolution_method = "needs_context"
            elif not has_named_actor:
                # No valid actor pattern found at all
                event.is_camera_friendly = False
                event.camera_friendly_confidence = 0.80
                event.camera_friendly_reason = f"no_valid_actor:{first_word}"
                event.actor_resolved = False
            else:
                # Has named actor, mark as resolved
                event.actor_resolved = True
                event.actor_resolution_method = "direct"
        
        # =====================================================================
        # Step 2.5: Validate actor_label directly (V7 FIX)
        # 
        # Even if text-based checks pass, verify actor_label is valid.
        # Filter out: bare roles, characterizations, fragments, None
        # =====================================================================
        
        if event.is_camera_friendly:
            actor = event.actor_label
            
            # List of bare roles that should NOT be camera-friendly
            BARE_ROLES = {
                'partner', 'passenger', 'suspect', 'manager', 'driver',
                'victim', 'witness', 'officer', 'the partner', 'his partner',
                'the suspect', 'a suspect', 'the manager', 'my manager',
                'cops', 'the cops', 'police', 'it', 'it all', 'they',
            }
            
            # Check 1: actor_label must exist
            if not actor:
                event.is_camera_friendly = False
                event.camera_friendly_confidence = 0.75
                event.camera_friendly_reason = "no_actor_label"
            
            # Check 2: actor_label must not be a bare role
            elif actor.lower().strip() in BARE_ROLES:
                event.is_camera_friendly = False
                event.camera_friendly_confidence = 0.75
                event.camera_friendly_reason = f"bare_role:{actor}"
            
            # Check 3: actor_label must not contain characterizations
            elif re.search(r'\b(brutal|psychotic|thug|violent|corrupt|evil|crazy)\b', actor, re.IGNORECASE):
                event.is_camera_friendly = False
                event.camera_friendly_confidence = 0.70
                event.camera_friendly_reason = f"characterization_in_actor:{actor[:30]}"
            
            # Check 4: actor_label should be a proper named entity
            # Must have either Title+Name pattern OR be known entity like "Reporter"
            elif actor != "Reporter":
                title_match = re.match(r'^(Officer|Sergeant|Detective|Captain|Lieutenant|Deputy|Dr\.?|Mr\.?|Mrs\.?|Ms\.?)\s+[A-Z][a-z]+', actor)
                proper_name = re.match(r'^[A-Z][a-z]+\s+[A-Z][a-z]+$', actor)  # Two-word proper noun
                if not title_match and not proper_name:
                    event.is_camera_friendly = False
                    event.camera_friendly_confidence = 0.70
                    event.camera_friendly_reason = f"invalid_actor_label:{actor[:30]}"
        
        # =====================================================================
        # Step 3: Construct neutralized_description from resolved components
        # 
        # This is the KEY step for camera-friendly events. We want:
        # - Actor resolved to name (not "I" or "he")
        # - Verb in past tense
        # - Target resolved or kept as object
        # - Interpretive language stripped
        # =====================================================================
        
        # Build neutralized description from components if we have a resolved actor
        if event.actor_label and event.action_verb:
            # Conjugate verb to past tense
            verb = event.action_verb
            verb_past = _conjugate_past_tense(verb)
            
            # Build sentence: Actor + Verb + Target/Object
            parts = [event.actor_label, verb_past]
            
            if event.target_label:
                # Replace first-person pronouns in target_label
                target = event.target_label
                target = re.sub(r"\bmy\b", "Reporter's", target, flags=re.IGNORECASE)
                target = re.sub(r"\bme\b", "Reporter", target, flags=re.IGNORECASE)
                parts.append(target)
            elif event.target_object:
                # Replace first-person pronouns in target_object
                target = event.target_object
                target = re.sub(r"\bmy\b", "Reporter's", target, flags=re.IGNORECASE)
                target = re.sub(r"\bme\b", "Reporter", target, flags=re.IGNORECASE)
                parts.append(target)
            
            constructed = " ".join(parts)
            
            # Ensure ends with period
            if not constructed.endswith('.'):
                constructed += '.'
            
            # Apply strip rules to remove remaining interpretive language
            neutralized = engine.apply_strip_rules(constructed)
            
            # Clean up any artifacts
            neutralized = re.sub(r'\s+\.', '.', neutralized)
            neutralized = re.sub(r'\s{2,}', ' ', neutralized)
            
            event.neutralized_description = neutralized.strip()
            event.neutralization_applied = True
        
        elif event.contains_interpretive and event.is_camera_friendly:
            # Fallback: If no resolved components, apply strip rules to original
            neutralized = engine.apply_strip_rules(text)
            if neutralized != text:
                event.neutralized_description = neutralized
                event.neutralization_applied = True
        
        # =====================================================================
        # Step 4: Update quality score based on classification
        # =====================================================================
        
        if event.is_camera_friendly:
            camera_friendly_count += 1
            # Base quality from confidence
            event.quality_score = event.camera_friendly_confidence
            
            # Penalize if neutralization was needed
            if event.neutralization_applied:
                event.quality_score = max(0.5, event.quality_score - 0.1)
        else:
            disqualified_count += 1
            event.quality_score = 0.3
    
    log.info(
        "classified_events",
        total=len(ctx.events),
        camera_friendly=camera_friendly_count,
        disqualified=disqualified_count,
    )
    
    ctx.add_trace(
        pass_name=PASS_NAME,
        action="classify_events",
        after=f"Classified {len(ctx.events)} events: {camera_friendly_count} camera-friendly, {disqualified_count} disqualified",
    )
    
    return ctx
