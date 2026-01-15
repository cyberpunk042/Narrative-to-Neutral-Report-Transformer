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
    """
    Roles entities play in a narrative.
    
    V4: Expanded taxonomy for proper role classification.
    Replaces the oversimplified AUTHORITY/WITNESS dichotomy.
    """
    
    # The narrator
    REPORTER = "reporter"                # The person telling the narrative (I/me/my)
    
    # Law enforcement involved in incident
    SUBJECT_OFFICER = "subject_officer"  # Officer(s) being described/complained about
    SUPERVISOR = "supervisor"            # Sergeants, commanding officers
    WITNESS_OFFICIAL = "witness_official"  # Other officers present but not subjects
    
    # Civilians
    WITNESS_CIVILIAN = "witness_civilian"  # Third-party civilian observers
    BYSTANDER = "bystander"               # Present but minimal involvement
    
    # Professional roles
    MEDICAL_PROVIDER = "medical_provider" # Doctors, nurses, EMTs, therapists
    LEGAL_COUNSEL = "legal_counsel"       # Attorneys, public defenders
    INVESTIGATOR = "investigator"         # IA detectives, oversight investigators
    WORKPLACE_CONTACT = "workplace_contact"  # Managers, coworkers
    
    # Entities mentioned but not actors
    SUBJECT = "subject"                   # Deprecated: use specific role
    INSTITUTION = "institution"           # Organizations (use EntityType.ORGANIZATION)
    
    # Backward compatibility aliases (DEPRECATED - use specific roles)
    AUTHORITY = "authority"               # DEPRECATED: Use SUBJECT_OFFICER/SUPERVISOR/INVESTIGATOR
    WITNESS = "witness"                   # DEPRECATED: Use WITNESS_CIVILIAN/WITNESS_OFFICIAL
    OBJECT = "object"                     # DEPRECATED
    
    # Fallback
    OTHER = "other"
    UNKNOWN = "unknown"


class Participation(str, Enum):
    """
    V5: When/how an entity participated in the events.
    
    This separates incident participants from post-incident professionals
    and people merely mentioned in the narrative.
    """
    
    # Present at the incident scene
    INCIDENT = "incident"
    # Examples: Reporter, Officers Jenkins/Rodriguez/Williams, Marcus Johnson, Patricia Chen
    
    # Involved after the incident (professional capacity)
    POST_INCIDENT = "post_incident"
    # Examples: Dr. Foster (ER), Detective Monroe (IA), Dr. Thompson (therapist), Attorney Walsh
    
    # Mentioned but not present (reference/verification)
    MENTIONED_ONLY = "mentioned"
    # Examples: Sarah Mitchell (manager for verification), robbery suspect (description)
    
    UNKNOWN = "unknown"


class EntityType(str, Enum):
    """
    What kind of entity this is.
    
    V4: Added BADGE_NUMBER as distinct type, and FACILITY separate from LOCATION.
    """
    
    PERSON = "person"               # Named individuals
    ORGANIZATION = "organization"   # Departments, foundations, divisions
    FACILITY = "facility"           # Hospitals, police stations, cafes
    LOCATION = "location"           # Geographic locations (streets, corners)
    VEHICLE = "vehicle"             # Cars, patrol cars
    BADGE_NUMBER = "badge_number"   # Identifier attached to an officer
    OBJECT = "object"               # Physical objects
    UNKNOWN = "unknown"


class EntitySubtype(str, Enum):
    """
    Subtype classification to detect invalid extractions.
    
    V4: Used to REJECT bare titles, roles, and descriptors that
    should not be treated as entities.
    """
    
    # Valid subtypes
    NAMED_INDIVIDUAL = "named_individual"     # "Officer Jenkins", "Dr. Foster"
    ORGANIZATION_PROPER = "organization_proper"  # "Internal Affairs Division"
    FACILITY_PROPER = "facility_proper"       # "St. Mary's Hospital"
    
    # INVALID - should be rejected or attached
    BARE_TITLE = "bare_title"           # "Officer", "Detective", "sergeant"
    BARE_ROLE = "bare_role"             # "partner", "passenger", "suspect", "manager"
    DESCRIPTOR = "descriptor"           # "male", "person", "man", "woman"
    PARTIAL_NAME = "partial_name"       # "Jenkins" (may need full name resolution)
    BADGE_ONLY = "badge_only"           # Badge number without officer attachment


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


class TemporalMarkerType(str, Enum):
    """
    Classification of temporal markers.
    
    V4: Proper typing of time references to prevent artifacts.
    """
    
    # Valid timestamps
    TIMESTAMP = "timestamp"       # "11:30 PM" - specific clock time
    DATE = "date"                 # "January 15th, 2026" - specific date
    DATETIME = "datetime"         # Combined date and time
    
    # Durations
    DURATION = "duration"         # "about 20 minutes", "three hours"
    
    # Relative markers
    RELATIVE = "relative"         # "next day", "three months later"
    SEQUENCE = "sequence"         # "then", "after that", "afterwards"
    
    # Vague (low confidence)
    VAGUE = "vague"               # "night", "hours", "later" (without specifics)
    
    # Invalid (should be rejected)
    ARTIFACT = "artifact"         # "30 PM" - parsing error
    NOT_TEMPORAL = "not_temporal" # "40s" as age, not decade


class TimeContext(str, Enum):
    """
    V5: When in the narrative timeline did this time reference occur?
    
    Separates incident time from post-incident time for proper rendering.
    """
    
    INCIDENT = "incident"           # During the main incident
    PRE_INCIDENT = "pre_incident"   # Before the incident (background)
    POST_INCIDENT = "post_incident" # After the incident (follow-up)
    ONGOING = "ongoing"             # Continuing effect (PTSD, lost job)
    UNKNOWN = "unknown"


class LocationType(str, Enum):
    """
    V5: Relevance of a location in the narrative.
    
    Separates incident scene from other mentioned locations.
    """
    
    INCIDENT_SCENE = "incident"     # Where the main incident occurred
    SECONDARY = "secondary"         # Other relevant locations
    WORKPLACE = "workplace"         # Reporter's workplace
    MEDICAL = "medical"             # Hospital, ER, clinic
    OFFICIAL = "official"           # Police station, IA office
    UNKNOWN = "unknown"


class EventType(str, Enum):
    """
    Types of events that can be extracted.
    
    V4: Expanded with structured event types for law enforcement contexts.
    """
    
    # Physical actions
    ACTION = "action"                    # Generic action
    APPROACH = "approach"                # Officer approached
    PHYSICAL_RESTRAINT = "physical_restraint"  # Grabbed, pushed, slammed
    SEARCH = "search"                    # Searched pockets, vehicle
    HANDCUFF = "handcuff"                # Handcuffing
    RELEASE = "release"                  # Released from custody
    
    # Verbal
    VERBAL = "verbal"                    # Generic verbal
    VERBAL_COMMAND = "verbal_command"    # "Stop!", "Get down!"
    VERBAL_THREAT = "verbal_threat"      # Threatening statement
    VERBAL_QUESTION = "verbal_question"  # Asked a question
    
    # Witness actions
    WITNESS_RECORDING = "witness_recording"      # Bystander recording
    WITNESS_INTERVENTION = "witness_intervention"  # Bystander spoke up
    
    # Procedural
    ARREST = "arrest"                    # Formal arrest
    COMPLAINT_FILED = "complaint_filed"  # Filed complaint
    INVESTIGATION = "investigation"      # Investigation action
    DISPOSITION = "disposition"          # Investigation outcome
    
    # Medical
    MEDICAL_TREATMENT = "medical_treatment"  # Hospital/doctor visit
    INJURY_DOCUMENTATION = "injury_documentation"  # Injuries documented
    
    # Movement
    MOVEMENT = "movement"                # Movement/travel
    VEHICLE_STOP = "vehicle_stop"        # Traffic stop
    
    # Other
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


class SourceType(str, Enum):
    """
    V5: Who provided the information.
    
    Tracks the original source of each statement for provenance.
    """
    
    REPORTER = "reporter"           # The person filing the narrative
    WITNESS = "witness"             # Third-party observer
    DOCUMENT = "document"           # Official document (letter, record)
    MEDICAL_RECORD = "medical"      # ER records, medical documentation
    OFFICIAL = "official"           # Police, IA, official findings
    ATTORNEY = "attorney"           # Legal counsel statement
    RESEARCH = "research"           # Reporter's own research
    UNKNOWN = "unknown"


class ProvenanceStatus(str, Enum):
    """
    V5: Verification status of a claim's provenance.
    
    Indicates whether the source has been verified or is missing.
    """
    
    VERIFIED = "verified"           # Source is documented/corroborated
    CITED = "cited"                 # Source is named but not verified
    MISSING = "missing"             # No source provided (NEEDS provenance)
    INFERENCE = "inference"         # Derived by reporter, not external source
    UNVERIFIABLE = "unverifiable"   # Cannot be independently verified


class EpistemicType(str, Enum):
    """
    V4: Fine-grained epistemic classification.
    
    This is the CRITICAL enum for fixing statement classification.
    Every atomic statement must be tagged with its epistemic status
    to enable proper neutralization and flagging.
    """
    
    # =========================================================================
    # DIRECTLY PERCEIVABLE (High confidence, preserve)
    # =========================================================================
    
    DIRECT_OBSERVATION = "direct_observation"
    # Observable external events: "He grabbed my arm"
    # CAN be neutralized but preserved as fact
    
    SENSORY_EXPERIENCE = "sensory_experience"
    # Physical sensation: "I felt pain", "I heard him yell"
    # Subjective but grounded in perception
    
    # =========================================================================
    # INTERNAL STATES (Medium confidence, flag as self-report)
    # =========================================================================
    
    EMOTIONAL_STATE = "emotional_state"
    # "I was terrified", "I felt scared"
    # Valid self-report but not externally verifiable
    
    PHYSICAL_SYMPTOM = "physical_symptom"
    # "My wrists were bleeding", "I couldn't breathe"
    # Self-reported physical state
    
    PSYCHOLOGICAL_CLAIM = "psychological_claim"
    # "I now suffer from PTSD", "I have panic attacks"
    # Medical claim requiring documentation
    
    # =========================================================================
    # REPORTER INTERPRETATION (Low confidence, MUST flag)
    # =========================================================================
    
    INFERENCE = "inference"
    # "She wasn't going to do anything about it"
    # Conclusion based on observation
    
    INTENT_ATTRIBUTION = "intent_attribution"
    # "He wanted to inflict maximum damage" ⚠️ DANGEROUS
    # "clearly looking for trouble" ⚠️ DANGEROUS
    # MUST be flagged - attributes mental state to another
    
    LEGAL_CHARACTERIZATION = "legal_characterization"
    # "This was racial profiling" ⚠️ DANGEROUS
    # "obstruction of justice" ⚠️ DANGEROUS
    # Legal conclusion by non-attorney
    
    CONSPIRACY_CLAIM = "conspiracy_claim"
    # "proves there's a cover-up" ⚠️ DANGEROUS
    # "they were conspiring"
    # Unfalsifiable allegation
    
    # =========================================================================
    # EXTERNAL SOURCES (Variable confidence)
    # =========================================================================
    
    REPORTED_SPEECH = "reported_speech"
    # "He said 'You can go'"
    # Attributed to another speaker
    
    DOCUMENT_CLAIM = "document_claim"
    # "The medical report shows..."
    # Referenced to a document
    
    WITNESS_CLAIM = "witness_claim"
    # "Marcus said he saw..."
    # Attributed to a witness
    
    # =========================================================================
    # DISCARDABLE (No semantic value)
    # =========================================================================
    
    NARRATIVE_GLUE = "narrative_glue"
    # "It all started", "Out of nowhere"
    # Transition phrases, rhetorical connectors
    
    RHETORICAL_EMPHASIS = "rhetorical_emphasis"
    # "which proves", "obviously", "clearly"
    # Persuasion markers, not facts
    
    UNKNOWN = "unknown"


# ============================================================================
# V4: Forbidden Phrases for Neutral Layer
# ============================================================================

# These patterns MUST trigger INTENT_ATTRIBUTION classification
INTENT_ATTRIBUTION_PATTERNS = [
    r"clearly (looking for|wanting|trying to|ready to)",
    r"obviously (wanted|didn't care|enjoying)",
    r"(wanted|intended|meant) to (inflict|hurt|harm|damage|kill)",
    r"(enjoyed?|enjoying|relished?) (my |the )?(suffering|pain|fear)",
    r"looking for trouble",
    r"ready to (shoot|attack|assault|hurt)",
    r"it was (obvious|clear) they were",
]

# These patterns trigger LEGAL_CHARACTERIZATION
LEGAL_CHARACTERIZATION_PATTERNS = [
    r"racial profiling",
    r"police brutality",
    r"civil rights violation",
    r"excessive force",
    r"false imprisonment",
    r"obstruction of justice",
    r"witness intimidation",
    r"illegal (arrest|search|seizure|assault)",
]

# These patterns trigger NARRATIVE_GLUE (can be discarded)
NARRATIVE_GLUE_PATTERNS = [
    r"^it all started",
    r"^out of nowhere",
    r"^the next thing I knew",
    r"^suddenly",
    r"which proves",
    r"which shows",
    r"this is (clearly|obviously)",
]

