"""
IR Enums — All semantic labels, roles, and codes.

No stringly-typed constants scattered across passes.
"""

from enum import Enum


# ============================================================================
# Phase 1: Statement Classification
# ============================================================================

class StatementType(str, Enum):
    """
    Classification of statement epistemic status.
    
    This tells us HOW the narrator knows what they're claiming:
    - OBSERVATION: Directly witnessed ("I saw him grab me")
    - CLAIM: Asserted without explicit witness ("He grabbed me")  
    - INTERPRETATION: Inference/opinion ("He wanted to hurt me")
    - QUOTE: Direct speech preserved verbatim
    """
    
    OBSERVATION = "observation"      # "I saw/heard/felt..."
    CLAIM = "claim"                  # Assertion without explicit witness
    INTERPRETATION = "interpretation"  # Inference, opinion, intent
    QUOTE = "quote"                  # Direct speech
    UNKNOWN = "unknown"              # Unable to classify


class SpanLabel(str, Enum):
    """Semantic labels for spans."""

    # Factual content
    OBSERVATION = "observation"
    ACTION = "action"
    STATEMENT = "statement"

    # Interpretive content (flagged, not removed)
    INTERPRETATION = "interpretation"
    INFERENCE = "inference"
    EMOTIONAL = "emotional"

    # Structural
    TEMPORAL = "temporal"
    SPATIAL = "spatial"
    REFERENCE = "reference"

    # Problematic (require attention)
    LEGAL_CONCLUSION = "legal_conclusion"
    INTENT_ATTRIBUTION = "intent_attribution"
    INFLAMMATORY = "inflammatory"

    # Uncertain
    AMBIGUOUS = "ambiguous"
    UNKNOWN = "unknown"


class SegmentContext(str, Enum):
    """
    High-level context classification for segments.
    
    This tells downstream passes HOW to interpret content,
    enabling context-aware transformation decisions.
    """
    
    # Speech contexts
    DIRECT_QUOTE = "direct_quote"          # Exact words spoken (must preserve)
    REPORTED_SPEECH = "reported_speech"    # Paraphrased speech
    
    # Legal/Accusation contexts
    CHARGE_DESCRIPTION = "charge"          # "charged me with X" - preserve X
    ACCUSATION = "accusation"              # "accused me of X" - preserve X
    OFFICIAL_REPORT = "official_report"    # Police report language
    
    # Physical description
    PHYSICAL_FORCE = "physical_force"      # Observable physical actions
    PHYSICAL_ATTEMPT = "physical_attempt"  # "tried to move/say/breathe"
    INJURY_DESCRIPTION = "injury"          # Description of injuries
    
    # Narrator contexts
    EMOTIONAL_IMPACT = "emotional"         # Narrator's emotional state
    TIMELINE = "timeline"                  # Temporal sequence
    OBSERVATION = "observation"            # Factual observation
    INTERPRETATION = "interpretation"      # Narrator's interpretation
    
    # Meta contexts
    CREDIBILITY_ASSERTION = "credibility"  # "I swear I'm telling the truth"
    SARCASM = "sarcasm"                    # Detected sarcasm/irony
    
    # M3: Meta-detection contexts
    ALREADY_NEUTRAL = "already_neutral"    # No biased language detected
    OPINION_ONLY = "opinion_only"          # No verifiable facts
    AMBIGUOUS = "ambiguous"                # Unclear references
    CONTRADICTS_PREVIOUS = "contradiction" # Conflicts with earlier statement
    
    # Neutral
    NEUTRAL = "neutral"                    # Already neutral content
    UNKNOWN = "unknown"


class EntityRole(str, Enum):
    """Roles entities can play in a narrative."""

    REPORTER = "reporter"
    SUBJECT = "subject"
    WITNESS = "witness"
    AUTHORITY = "authority"
    INSTITUTION = "institution"
    OBJECT = "object"
    UNKNOWN = "unknown"

class EntityType(str, Enum):
    """Refined type of an entity."""
    
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    VEHICLE = "vehicle"
    OBJECT = "object"
    UNKNOWN = "unknown"

class IdentifierType(str, Enum):
    """Types of identifiers that can be extracted."""

    NAME = "name"
    BADGE_NUMBER = "badge_number"
    EMPLOYEE_ID = "employee_id"
    VEHICLE_PLATE = "vehicle_plate"
    LOCATION = "location"
    DATE = "date"
    TIME = "time"
    OTHER = "other"


class EventType(str, Enum):
    """Types of events that can be extracted."""

    ACTION = "action"
    VERBAL = "verbal"
    MOVEMENT = "movement"
    OBSERVATION = "observation"
    STATE_CHANGE = "state_change"
    UNKNOWN = "unknown"


class SpeechActType(str, Enum):
    """Types of speech acts."""

    STATEMENT = "statement"
    COMMAND = "command"
    QUESTION = "question"
    THREAT = "threat"
    UNKNOWN = "unknown"


class UncertaintyType(str, Enum):
    """Types of uncertainty."""

    AMBIGUOUS_REFERENCE = "ambiguous_reference"
    MISSING_CONTEXT = "missing_context"
    LOW_CONFIDENCE = "low_confidence"
    CONTRADICTORY = "contradictory"
    INCOMPLETE = "incomplete"


class PolicyAction(str, Enum):
    """Actions a policy rule can take."""

    ACCEPT = "accept"
    FLAG = "flag"
    TRANSFORM = "transform"
    MODIFY = "modify"
    STRIP = "strip"
    REMOVE = "remove"
    PRESERVE = "preserve"
    REFUSE = "refuse"
    WARN = "warn"


class DiagnosticLevel(str, Enum):
    """Diagnostic severity levels."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class TransformStatus(str, Enum):
    """Overall transformation status."""

    SUCCESS = "success"
    PARTIAL = "partial"
    REFUSED = "refused"
    ERROR = "error"


# ============================================================================
# Phase 3: Semantic Understanding (v3)
# ============================================================================

class MentionType(str, Enum):
    """
    How an entity is mentioned in text.
    
    Used by coreference resolution to track different forms of reference
    to the same entity across the narrative.
    """
    
    PROPER_NAME = "proper_name"    # Full name: "Officer Jenkins"
    PRONOUN = "pronoun"            # Personal pronoun: "he", "she", "they"  
    DESCRIPTOR = "descriptor"      # Descriptive phrase: "the officer", "the man"
    TITLE = "title"                # Title/partial name: "Jenkins", "the sergeant"
    POSSESSIVE = "possessive"      # Possessive reference: "his", "her", "my"


class GroupType(str, Enum):
    """
    Semantic category of a statement group.
    
    Groups cluster related atomic statements for coherent presentation.
    Each group has a clear semantic purpose.
    """
    
    ENCOUNTER = "encounter"              # Events during the incident
    WITNESS_ACCOUNT = "witness_account"  # Third party's observations
    MEDICAL = "medical"                  # Medical treatment, documented injuries
    OFFICIAL = "official"                # Official records, complaints, investigations
    EMOTIONAL = "emotional"              # Psychological/emotional impact
    BACKGROUND = "background"            # Context before the incident
    AFTERMATH = "aftermath"              # Events after the incident
    QUOTE = "quote"                      # Direct speech preserved
    UNKNOWN = "unknown"


class TemporalRelation(str, Enum):
    """
    How events relate to each other in time.
    
    Used to build the timeline DAG and determine event ordering.
    """
    
    BEFORE = "before"           # This happened before another event
    AFTER = "after"             # This happened after another event
    DURING = "during"           # Concurrent with another event
    SIMULTANEOUS = "simultaneous"  # At exactly the same time
    IMMEDIATELY_BEFORE = "immediately_before"  # Right before
    IMMEDIATELY_AFTER = "immediately_after"    # Right after
    UNKNOWN = "unknown"


class EvidenceType(str, Enum):
    """
    Source and reliability classification of evidence.
    
    Enables assessment of how reliable a statement is based on
    its provenance and corroboration.
    """
    
    # Direct evidence (highest reliability)
    DIRECT_WITNESS = "direct_witness"  # Reporter directly saw/heard/felt
    PHYSICAL = "physical"              # Physical evidence (injuries, damage)
    DOCUMENTARY = "documentary"        # Official documents, medical records
    
    # Indirect evidence (medium reliability)
    REPORTED = "reported"              # Someone told the reporter
    VIDEO_AUDIO = "video_audio"        # Recorded but not by reporter
    
    # Interpretive (lower reliability)
    INFERENCE = "inference"            # Reporter's conclusion/interpretation
    OPINION = "opinion"                # Reporter's opinion
    
    UNKNOWN = "unknown"

