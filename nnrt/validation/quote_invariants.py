"""
V6 Quote Invariants

Invariants for quote/speech act rendering:
- QUOTE_HAS_SPEAKER: Every quote has resolved speaker (not pronoun/unknown)
"""

from nnrt.validation.invariants import (
    Invariant,
    InvariantResult,
    InvariantSeverity,
    InvariantRegistry,
)

# Pronouns and placeholders that disqualify a speaker
INVALID_SPEAKERS = {
    "he", "she", "they", "him", "her", "them",
    "unknown", "speaker", "someone", "person",
    "individual", "voice", "unidentified"
}


def check_quote_has_speaker(speech_act) -> InvariantResult:
    """
    Invariant: Every quote must have a resolved speaker.
    
    Examples:
        ✅ Speaker: Officer Jenkins | "STOP RIGHT THERE!"
        ✅ Speaker: Reporter | "What's the problem?"
        ❌ Speaker: He | "Some quote" (pronoun)
        ❌ Speaker: Unknown | "Some quote" (placeholder)
        ❌ Speaker: None | "Some quote" (missing)
    """
    speaker = getattr(speech_act, 'speaker_label', None)
    content = getattr(speech_act, 'content', '')[:50]
    
    if not speaker:
        return InvariantResult(
            passes=False,
            invariant_id="QUOTE_HAS_SPEAKER",
            message="No speaker specified",
            failed_content=f'"{content}..."',
            quarantine_bucket="QUOTES_UNRESOLVED"
        )
    
    speaker_lower = speaker.lower().strip()
    
    if speaker_lower in INVALID_SPEAKERS:
        return InvariantResult(
            passes=False,
            invariant_id="QUOTE_HAS_SPEAKER",
            message=f"Speaker unresolved: '{speaker}'",
            failed_content=f'"{content}..."',
            quarantine_bucket="QUOTES_UNRESOLVED"
        )
    
    return InvariantResult(
        passes=True,
        invariant_id="QUOTE_HAS_SPEAKER",
        message=f"Speaker resolved: '{speaker}'"
    )


def check_quote_not_nested(speech_act) -> InvariantResult:
    """
    Invariant: Nested quotes should be flagged (soft warning).
    
    Nested quotes often have attribution issues.
    """
    is_nested = getattr(speech_act, 'is_nested', False)
    content = getattr(speech_act, 'content', '')[:50]
    
    if is_nested:
        return InvariantResult(
            passes=False,
            invariant_id="QUOTE_NOT_NESTED",
            message="Nested quote - may have attribution issues",
            failed_content=f'"{content}..."',
            quarantine_bucket="QUOTES_NEEDS_REVIEW"
        )
    
    return InvariantResult(
        passes=True,
        invariant_id="QUOTE_NOT_NESTED",
        message="Not nested"
    )


# Register all quote invariants
def _register_quote_invariants():
    """Register all quote invariants with the registry."""
    
    InvariantRegistry.register(Invariant(
        id="QUOTE_HAS_SPEAKER",
        description="Every quote has resolved speaker (not pronoun/unknown)",
        severity=InvariantSeverity.HARD,
        check_fn=check_quote_has_speaker,
        quarantine_bucket="QUOTES_UNRESOLVED"
    ))
    
    InvariantRegistry.register(Invariant(
        id="QUOTE_NOT_NESTED",
        description="Nested quotes flagged for review",
        severity=InvariantSeverity.SOFT,  # Warn but still render
        check_fn=check_quote_not_nested,
        quarantine_bucket="QUOTES_NEEDS_REVIEW"
    ))


# Auto-register on import
_register_quote_invariants()
