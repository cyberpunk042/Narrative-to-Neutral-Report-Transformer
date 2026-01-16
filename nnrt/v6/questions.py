"""
V6 Question Generation System.

This module generates investigation questions from:
1. Timeline gaps (unexplained periods)
2. Missing actors (unresolved subjects)
3. Vague statements (unclear details)
4. Missing context (locations, times, circumstances)

Questions are categorized by priority and type for investigator review.
"""

import re
import structlog
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

log = structlog.get_logger("nnrt.v6.questions")


class QuestionPriority(str, Enum):
    """Priority level for investigation questions."""
    CRITICAL = "critical"     # Memory gaps, use of force incidents
    HIGH = "high"             # Missing key details
    MEDIUM = "medium"         # Clarification needed
    LOW = "low"               # Nice-to-have context


class QuestionCategory(str, Enum):
    """Category of investigation question."""
    TIMELINE_GAP = "timeline_gap"           # Unexplained time period
    MISSING_ACTOR = "missing_actor"         # Who did this action?
    MISSING_TIME = "missing_time"           # When did this happen?
    MISSING_LOCATION = "missing_location"   # Where did this happen?
    VAGUE_DESCRIPTION = "vague_description" # Clarify what happened
    INJURY_DETAIL = "injury_detail"         # Medical/injury follow-up
    WITNESS = "witness"                     # Who else was present?
    EVIDENCE = "evidence"                   # What evidence exists?
    PRIOR_CONTACT = "prior_contact"         # Prior history/encounters
    OUTCOME = "outcome"                     # What was the result?


class InvestigationQuestion(BaseModel):
    """A generated investigation question."""
    
    id: str = Field(..., description="Unique question ID")
    
    # Question content
    text: str = Field(..., description="The question to ask")
    category: QuestionCategory = Field(..., description="Question type")
    priority: QuestionPriority = Field(..., description="Investigation priority")
    
    # Context
    source_id: Optional[str] = Field(None, description="ID of source object (gap, statement)")
    source_type: Optional[str] = Field(None, description="Type of source: 'gap', 'statement', 'event'")
    related_text: Optional[str] = Field(None, description="Relevant text excerpt")
    
    # Investigation guidance
    rationale: str = Field("", description="Why this question matters")
    follow_up_hints: List[str] = Field(default_factory=list, description="Suggested follow-ups")


class QuestionSet(BaseModel):
    """Collection of generated questions with summary."""
    
    questions: List[InvestigationQuestion] = Field(default_factory=list)
    
    # Summary counts
    total_count: int = Field(0)
    critical_count: int = Field(0)
    high_count: int = Field(0)
    
    # Coverage
    timeline_gap_questions: int = Field(0)
    missing_info_questions: int = Field(0)
    clarification_questions: int = Field(0)


# =============================================================================
# Question Templates
# =============================================================================

GAP_QUESTION_TEMPLATES = [
    "What happened during this period?",
    "Do you remember anything from this time?",
    "Is there anything else you can recall about what occurred between these events?",
]

MISSING_ACTOR_TEMPLATES = [
    "Who performed this action?",
    "Can you identify the person who did this?",
    "Who specifically {action}?",
]

MISSING_LOCATION_TEMPLATES = [
    "Where exactly did this occur?",
    "Can you describe the location?",
    "What was your position when this happened?",
]

VAGUE_TEMPLATES = [
    "Can you provide more detail about what happened?",
    "What specifically occurred?",
    "Can you describe this more precisely?",
]


# =============================================================================
# Pattern Detection for Question Generation
# =============================================================================

# Patterns indicating vague descriptions
VAGUE_PATTERNS = [
    (r'\bsomething\b', "What specifically?"),
    (r'\bsomeone\b', "Who specifically?"),
    (r'\bsomewhere\b', "Where specifically?"),
    (r'\bsomehow\b', "How specifically?"),
    (r'\bat some point\b', "When specifically?"),
    (r'\bI think\b', "What makes you uncertain?"),
    (r'\bI believe\b', "What makes you uncertain?"),
    (r'\bprobably\b', "What makes you uncertain?"),
    (r'\bmaybe\b', "What makes you uncertain?"),
    (r'\bI\'m not sure\b', "What do you recall?"),
]

# Keywords suggesting injury/medical questions needed
INJURY_KEYWORDS = [
    'pain', 'hurt', 'injured', 'injury', 'bleeding', 'bruise', 'swelling',
    'broken', 'sprain', 'ache', 'hospital', 'emergency room', 'doctor',
    'medical', 'treatment', 'ambulance',
]

# Action verbs without clear subjects
ACTION_PATTERNS = [
    r'\b(was|were)\s+(grabbed|pushed|shoved|hit|struck|kicked|punched|thrown)',
    r'\b(was|were)\s+(handcuffed|restrained|detained|arrested)',
    r'\b(got|received)\s+(a|an)?\s*(punch|kick|hit|blow)',
]


def generate_questions_from_gaps(
    time_gaps: List,
    events: List,
) -> List[InvestigationQuestion]:
    """Generate questions from detected timeline gaps."""
    questions = []
    q_counter = 0
    
    # Map event IDs to descriptions
    event_map = {e.id: e for e in events} if events else {}
    
    for gap in time_gaps:
        if not getattr(gap, 'requires_investigation', False):
            continue
        
        # Use suggested question if available
        suggested = getattr(gap, 'suggested_question', None)
        if suggested:
            question_text = suggested
        else:
            question_text = "What happened during this unaccounted period?"
        
        # Determine priority based on gap type
        gap_type = getattr(gap, 'gap_type', None)
        gap_type_val = gap_type.value if hasattr(gap_type, 'value') else str(gap_type)
        
        if gap_type_val == 'uncertain':
            priority = QuestionPriority.CRITICAL  # Memory gaps are critical
            rationale = "This gap suggests a possible memory discontinuity that may indicate significant events occurred."
        elif gap_type_val == 'day_boundary':
            priority = QuestionPriority.HIGH
            rationale = "Events occurred on different days without explanation of what happened in between."
        else:
            priority = QuestionPriority.MEDIUM
            rationale = "There is an unexplained time period that may contain relevant information."
        
        # Get related event descriptions
        related = ""
        after_id = getattr(gap, 'after_entry_id', None)
        before_id = getattr(gap, 'before_entry_id', None)
        # These are timeline entry IDs, not event IDs, but include for context
        
        question = InvestigationQuestion(
            id=f"iq_{q_counter:04d}",
            text=question_text,
            category=QuestionCategory.TIMELINE_GAP,
            priority=priority,
            source_id=gap.id,
            source_type="gap",
            rationale=rationale,
            follow_up_hints=[
                "Ask about sensory details (sounds, sights, sensations)",
                "Check for physical evidence of this period",
                "Review any medical or witness statements",
            ],
        )
        questions.append(question)
        q_counter += 1
    
    return questions


def generate_questions_from_statements(
    atomic_statements: List,
) -> List[InvestigationQuestion]:
    """Generate questions from vague or incomplete statements."""
    questions = []
    q_counter = 0
    
    for stmt in atomic_statements:
        text = getattr(stmt, 'text', str(stmt))
        stmt_id = getattr(stmt, 'id', f"stmt_{q_counter}")
        
        # Check for vague patterns
        for pattern, follow_up in VAGUE_PATTERNS:
            if re.search(pattern, text, re.I):
                question = InvestigationQuestion(
                    id=f"iq_v_{q_counter:04d}",
                    text=follow_up,
                    category=QuestionCategory.VAGUE_DESCRIPTION,
                    priority=QuestionPriority.MEDIUM,
                    source_id=stmt_id,
                    source_type="statement",
                    related_text=text[:100],
                    rationale="This statement contains vague language that should be clarified.",
                )
                questions.append(question)
                q_counter += 1
                break  # One question per statement
        
        # Check for passive voice actions without actors
        for pattern in ACTION_PATTERNS:
            if re.search(pattern, text, re.I):
                question = InvestigationQuestion(
                    id=f"iq_a_{q_counter:04d}",
                    text="Who performed this action?",
                    category=QuestionCategory.MISSING_ACTOR,
                    priority=QuestionPriority.HIGH,
                    source_id=stmt_id,
                    source_type="statement", 
                    related_text=text[:100],
                    rationale="This action lacks a clear subject/actor identification.",
                    follow_up_hints=[
                        "Can you describe the person who did this?",
                        "Do you know their name, badge number, or description?",
                    ],
                )
                questions.append(question)
                q_counter += 1
                break
        
        # Check for injury-related statements needing follow-up
        for keyword in INJURY_KEYWORDS:
            if keyword in text.lower():
                question = InvestigationQuestion(
                    id=f"iq_i_{q_counter:04d}",
                    text="Can you describe the injury and any medical treatment received?",
                    category=QuestionCategory.INJURY_DETAIL,
                    priority=QuestionPriority.HIGH,
                    source_id=stmt_id,
                    source_type="statement",
                    related_text=text[:100],
                    rationale="Medical details may be important for documentation.",
                    follow_up_hints=[
                        "Were photos taken of injuries?",
                        "Were medical records obtained?",
                        "What was the diagnosis?",
                    ],
                )
                questions.append(question)
                q_counter += 1
                break
    
    return questions


def generate_questions_from_events(
    events: List,
) -> List[InvestigationQuestion]:
    """Generate questions from events missing key details."""
    questions = []
    q_counter = 0
    
    for event in events:
        desc = getattr(event, 'description', '')
        event_id = getattr(event, 'id', f"evt_{q_counter}")
        event_type = getattr(event, 'type', None)
        event_type_val = event_type.value if hasattr(event_type, 'value') else str(event_type)
        
        # Check for use of force events without witness info
        if event_type_val in ('use_of_force', 'restraint', 'detention'):
            question = InvestigationQuestion(
                id=f"iq_w_{q_counter:04d}",
                text="Were there any witnesses to this event?",
                category=QuestionCategory.WITNESS,
                priority=QuestionPriority.HIGH,
                source_id=event_id,
                source_type="event",
                related_text=desc[:100] if desc else None,
                rationale="Use of force incidents often have witnesses whose accounts should be obtained.",
                follow_up_hints=[
                    "Were there bystanders?",
                    "Was this captured on body camera or surveillance?",
                    "Did anyone intervene?",
                ],
            )
            questions.append(question)
            q_counter += 1
    
    return questions


def generate_all_questions(
    time_gaps: List = None,
    atomic_statements: List = None,
    events: List = None,
) -> QuestionSet:
    """
    Generate a complete set of investigation questions.
    
    Args:
        time_gaps: TimeGap objects from timeline analysis
        atomic_statements: AtomicStatement objects
        events: Event objects
        
    Returns:
        QuestionSet with all generated questions and summary
    """
    all_questions = []
    
    # Generate from gaps
    if time_gaps:
        gap_questions = generate_questions_from_gaps(time_gaps, events or [])
        all_questions.extend(gap_questions)
    
    # Generate from statements
    if atomic_statements:
        stmt_questions = generate_questions_from_statements(atomic_statements)
        all_questions.extend(stmt_questions)
    
    # Generate from events
    if events:
        event_questions = generate_questions_from_events(events)
        all_questions.extend(event_questions)
    
    # Sort by priority
    priority_order = {
        QuestionPriority.CRITICAL: 0,
        QuestionPriority.HIGH: 1,
        QuestionPriority.MEDIUM: 2,
        QuestionPriority.LOW: 3,
    }
    all_questions.sort(key=lambda q: priority_order.get(q.priority, 99))
    
    # Build summary
    question_set = QuestionSet(
        questions=all_questions,
        total_count=len(all_questions),
        critical_count=sum(1 for q in all_questions if q.priority == QuestionPriority.CRITICAL),
        high_count=sum(1 for q in all_questions if q.priority == QuestionPriority.HIGH),
        timeline_gap_questions=sum(1 for q in all_questions if q.category == QuestionCategory.TIMELINE_GAP),
        missing_info_questions=sum(1 for q in all_questions 
                                   if q.category in (QuestionCategory.MISSING_ACTOR, 
                                                     QuestionCategory.MISSING_TIME,
                                                     QuestionCategory.MISSING_LOCATION)),
        clarification_questions=sum(1 for q in all_questions 
                                   if q.category == QuestionCategory.VAGUE_DESCRIPTION),
    )
    
    log.info(
        "questions_generated",
        total=question_set.total_count,
        critical=question_set.critical_count,
        high=question_set.high_count,
    )
    
    return question_set
