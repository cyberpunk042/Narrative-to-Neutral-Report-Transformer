"""
V6 Event Invariants

Invariants for event rendering:
- EVENT_HAS_ACTOR: Every event has resolved actor (not pronoun)
- EVENT_NOT_FRAGMENT: Event is complete clause, not fragment
- EVENT_HAS_VERB: Event has an action verb
"""

from nnrt.validation.invariants import (
    Invariant,
    InvariantResult,
    InvariantSeverity,
    InvariantRegistry,
)

# Pronouns that disqualify an actor
PRONOUNS = {
    "he", "she", "they", "him", "her", "them", 
    "i", "me", "we", "us", "it", "his", "hers"
}

# Common fragments that aren't complete events
FRAGMENT_STARTERS = {
    "and", "but", "or", "then", "which", "who", "that"
}


def check_event_has_actor(event) -> InvariantResult:
    """
    Invariant: Every event must have a resolved actor (not pronoun).
    
    Examples:
        ✅ "Officer Jenkins yelled at Reporter"
        ❌ "He yelled at Reporter" (pronoun)
        ❌ "yelled at Reporter" (no actor)
    """
    actor = getattr(event, 'actor_label', None)
    desc = getattr(event, 'description', str(event))[:100]
    
    if not actor:
        return InvariantResult(
            passes=False,
            invariant_id="EVENT_HAS_ACTOR",
            message="No actor specified",
            failed_content=desc,
            quarantine_bucket="EVENTS_UNRESOLVED"
        )
    
    actor_lower = actor.lower().strip()
    
    if actor_lower in PRONOUNS:
        return InvariantResult(
            passes=False,
            invariant_id="EVENT_HAS_ACTOR",
            message=f"Actor is pronoun: '{actor}'",
            failed_content=desc,
            quarantine_bucket="EVENTS_UNRESOLVED"
        )
    
    # Check for "Individual (Unidentified)" - also not resolved
    if "unidentified" in actor_lower or "unknown" in actor_lower:
        return InvariantResult(
            passes=False,
            invariant_id="EVENT_HAS_ACTOR",
            message=f"Actor is unidentified: '{actor}'",
            failed_content=desc,
            quarantine_bucket="EVENTS_UNRESOLVED"
        )
    
    return InvariantResult(
        passes=True,
        invariant_id="EVENT_HAS_ACTOR",
        message="Actor resolved"
    )


def check_event_not_fragment(event) -> InvariantResult:
    """
    Invariant: Event description must be complete clause (not fragment).
    
    Examples:
        ✅ "Officer Jenkins grabbed Reporter's arm"
        ❌ "immediately started" (fragment)
        ❌ "which caused" (dependent clause fragment)
    """
    desc = getattr(event, 'description', '')
    words = desc.split()
    
    # Too short = fragment
    if len(words) < 3:
        return InvariantResult(
            passes=False,
            invariant_id="EVENT_NOT_FRAGMENT",
            message=f"Too short ({len(words)} words)",
            failed_content=desc[:100],
            quarantine_bucket="EVENTS_UNRESOLVED"
        )
    
    # Starts with dependent clause marker = fragment
    first_word = words[0].lower().strip('",\'')
    if first_word in FRAGMENT_STARTERS:
        return InvariantResult(
            passes=False,
            invariant_id="EVENT_NOT_FRAGMENT",
            message=f"Starts with dependent marker: '{first_word}'",
            failed_content=desc[:100],
            quarantine_bucket="EVENTS_UNRESOLVED"
        )
    
    return InvariantResult(
        passes=True,
        invariant_id="EVENT_NOT_FRAGMENT",
        message="Complete clause"
    )


def check_event_has_verb(event) -> InvariantResult:
    """
    Invariant: Event must have an action verb.
    
    Examples:
        ✅ "Officer Jenkins grabbed Reporter's arm" (grabbed)
        ❌ "Officer Jenkins with a weapon" (no verb)
    """
    verb = getattr(event, 'action_verb', None)
    desc = getattr(event, 'description', str(event))[:100]
    
    if not verb:
        return InvariantResult(
            passes=False,
            invariant_id="EVENT_HAS_VERB",
            message="No action verb",
            failed_content=desc,
            quarantine_bucket="EVENTS_UNRESOLVED"
        )
    
    return InvariantResult(
        passes=True,
        invariant_id="EVENT_HAS_VERB",
        message=f"Has verb: '{verb}'"
    )


# Register all event invariants
def _register_event_invariants():
    """Register all event invariants with the registry."""
    
    InvariantRegistry.register(Invariant(
        id="EVENT_HAS_ACTOR",
        description="Every event has resolved actor (not pronoun/unidentified)",
        severity=InvariantSeverity.HARD,
        check_fn=check_event_has_actor,
        quarantine_bucket="EVENTS_UNRESOLVED"
    ))
    
    InvariantRegistry.register(Invariant(
        id="EVENT_NOT_FRAGMENT",
        description="Event is complete clause, not fragment",
        severity=InvariantSeverity.HARD,
        check_fn=check_event_not_fragment,
        quarantine_bucket="EVENTS_UNRESOLVED"
    ))
    
    InvariantRegistry.register(Invariant(
        id="EVENT_HAS_VERB",
        description="Event has an action verb",
        severity=InvariantSeverity.SOFT,  # Soft - warn but don't quarantine
        check_fn=check_event_has_verb,
        quarantine_bucket="EVENTS_UNRESOLVED"
    ))


# Auto-register on import
_register_event_invariants()
