"""
Domain Schema — Stage 5

Pydantic models for domain configuration.

A complete domain configuration contains:
- Metadata (id, name, version)
- Vocabulary (synonyms, canonical forms)
- Entity role patterns
- Event type definitions
- Classification rules
- Transformation rules
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Participation(str, Enum):
    """When an entity participated in the narrative."""
    INCIDENT = "incident"
    POST_INCIDENT = "post_incident"
    MENTIONED = "mentioned"


# ============================================================================
# Vocabulary Models
# ============================================================================

class VocabularyTerm(BaseModel):
    """A term with its synonyms and canonical form."""
    
    synonyms: list[str] = Field(default_factory=list, description="Alternative forms of the term")
    derogatory: list[str] = Field(default_factory=list, description="Derogatory forms to replace")
    neutral_form: str = Field(..., description="The neutral/canonical form")
    context: Optional[str] = Field(None, description="Usage context hint")


class VocabularyCategory(BaseModel):
    """A category of vocabulary terms."""
    
    terms: dict[str, VocabularyTerm] = Field(
        default_factory=dict,
        description="Map of term_id -> VocabularyTerm"
    )


class DomainVocabulary(BaseModel):
    """Complete vocabulary for a domain."""
    
    actors: dict[str, VocabularyTerm] = Field(
        default_factory=dict,
        description="Actor terms (officer, witness, etc.)"
    )
    actions: dict[str, VocabularyTerm] = Field(
        default_factory=dict,
        description="Action terms (arrest, use_of_force, etc.)"
    )
    locations: dict[str, VocabularyTerm] = Field(
        default_factory=dict,
        description="Location terms (patrol_car, precinct, etc.)"
    )
    modifiers: dict[str, VocabularyTerm] = Field(
        default_factory=dict,
        description="Modifier terms (violent, aggressive, etc.)"
    )
    
    def get_synonyms(self, term_id: str) -> list[str]:
        """Get all synonyms for a term ID."""
        for category in [self.actors, self.actions, self.locations, self.modifiers]:
            if term_id in category:
                term = category[term_id]
                return term.synonyms + term.derogatory
        return []
    
    def get_neutral_form(self, term_id: str) -> Optional[str]:
        """Get the neutral form for a term ID."""
        for category in [self.actors, self.actions, self.locations, self.modifiers]:
            if term_id in category:
                return category[term_id].neutral_form
        return None


# ============================================================================
# Entity Role Models
# ============================================================================

class EntityRolePattern(BaseModel):
    """Pattern for identifying entity roles."""
    
    role: str = Field(..., description="Role enum value (SUBJECT_OFFICER, REPORTER, etc.)")
    patterns: list[str] = Field(
        default_factory=list,
        description="Text patterns to match, use {name} for name capture"
    )
    keywords: list[str] = Field(
        default_factory=list,
        description="Single keywords that indicate this role"
    )
    badge_linkable: bool = Field(False, description="Can be linked to a badge number")
    participation: Participation = Field(
        Participation.INCIDENT,
        description="When this role typically participates"
    )
    is_primary: bool = Field(False, description="Is this a primary entity (reporter)")


# ============================================================================
# Event Type Models
# ============================================================================

class EventTypeDefinition(BaseModel):
    """Definition of an event type."""
    
    type: str = Field(..., description="Event type (USE_OF_FORCE, ARREST, etc.)")
    verbs: list[str] = Field(default_factory=list, description="Verbs that indicate this event")
    requires_actor: bool = Field(False, description="Must have an actor")
    requires_target: bool = Field(False, description="Must have a target")
    is_camera_friendly: bool = Field(True, description="Observable by camera")
    typical_actor_role: Optional[str] = Field(None, description="Expected actor role")
    participation: Participation = Field(
        Participation.INCIDENT,
        description="When this event type typically occurs"
    )


# ============================================================================
# Classification Models
# ============================================================================

class CameraFriendlyConfig(BaseModel):
    """What makes an event camera-friendly (observable)."""
    
    required: list[str] = Field(
        default_factory=list,
        description="All conditions required (has_named_actor, has_physical_action)"
    )
    disqualifying: list[str] = Field(
        default_factory=list,
        description="Any of these disqualifies (contains_internal_state)"
    )


class FollowUpConfig(BaseModel):
    """What makes an event a follow-up action."""
    
    actor_roles: list[str] = Field(
        default_factory=list,
        description="Roles that typically do follow-up (MEDICAL_PROVIDER)"
    )
    time_contexts: list[str] = Field(
        default_factory=list,
        description="Time markers (later, afterward, subsequently)"
    )


class ClassificationConfig(BaseModel):
    """Classification rules for the domain."""
    
    camera_friendly: CameraFriendlyConfig = Field(
        default_factory=CameraFriendlyConfig,
        description="Camera-friendly criteria"
    )
    follow_up: FollowUpConfig = Field(
        default_factory=FollowUpConfig,
        description="Follow-up action criteria"
    )


# ============================================================================
# Transformation Models
# ============================================================================

class TransformationRule(BaseModel):
    """A transformation rule for neutralization."""
    
    id: str = Field(..., description="Rule ID (le_cop_to_officer)")
    match: list[str] = Field(default_factory=list, description="Patterns to match")
    replace: Optional[str] = Field(None, description="Replacement text")
    remove: bool = Field(False, description="Remove match entirely")
    preserve: bool = Field(False, description="Preserve match (no transformation)")
    context: list[str] = Field(
        default_factory=list,
        description="Required context (before_officer, in_quote)"
    )
    priority: int = Field(50, description="Rule priority (higher = earlier)")


# ============================================================================
# Diagnostic Models
# ============================================================================

class DiagnosticFlag(BaseModel):
    """A diagnostic flag configuration."""
    
    code: str = Field(..., description="Diagnostic code (PHYSICAL_ACTION_DESCRIBED)")
    on_match: list[str] = Field(default_factory=list, description="Patterns that trigger")
    level: str = Field("info", description="Severity level (info, warning, error)")
    message: str = Field(..., description="Human-readable message")


class DiagnosticsConfig(BaseModel):
    """Diagnostics configuration for the domain."""
    
    flags: list[DiagnosticFlag] = Field(
        default_factory=list,
        description="Diagnostic flags to emit"
    )


# ============================================================================
# Domain Metadata
# ============================================================================

class DomainMetadata(BaseModel):
    """Metadata about the domain."""
    
    typical_actors: list[str] = Field(
        default_factory=list,
        description="Common actor roles in this domain"
    )
    typical_locations: list[str] = Field(
        default_factory=list,
        description="Common locations"
    )
    typical_timeline: list[str] = Field(
        default_factory=list,
        description="Common timeline phases"
    )


# ============================================================================
# Complete Domain Model
# ============================================================================

class DomainInfo(BaseModel):
    """Domain identification."""
    
    id: str = Field(..., description="Domain ID (law_enforcement)")
    name: str = Field(..., description="Human-readable name")
    version: str = Field("1.0", description="Domain version")
    description: Optional[str] = Field(None, description="Domain description")
    extends: Optional[str] = Field(None, description="Base domain to extend")


class Domain(BaseModel):
    """Complete domain configuration."""
    
    domain: DomainInfo = Field(..., description="Domain identification")
    
    vocabulary: DomainVocabulary = Field(
        default_factory=DomainVocabulary,
        description="Domain vocabulary (synonyms, canonical forms)"
    )
    
    entity_roles: list[EntityRolePattern] = Field(
        default_factory=list,
        description="Entity role patterns"
    )
    
    event_types: list[EventTypeDefinition] = Field(
        default_factory=list,
        description="Event type definitions"
    )
    
    classification: ClassificationConfig = Field(
        default_factory=ClassificationConfig,
        description="Classification rules"
    )
    
    transformations: list[TransformationRule] = Field(
        default_factory=list,
        description="Transformation rules"
    )
    
    diagnostics: DiagnosticsConfig = Field(
        default_factory=DiagnosticsConfig,
        description="Diagnostic configuration"
    )
    
    metadata: DomainMetadata = Field(
        default_factory=DomainMetadata,
        description="Domain metadata"
    )
    
    def get_entity_role_pattern(self, role: str) -> Optional[EntityRolePattern]:
        """Get entity role pattern by role name."""
        for pattern in self.entity_roles:
            if pattern.role == role:
                return pattern
        return None
    
    def get_event_type(self, type_name: str) -> Optional[EventTypeDefinition]:
        """Get event type definition by type name."""
        for evt_type in self.event_types:
            if evt_type.type == type_name:
                return evt_type
        return None
    
    def get_transformation_rules(self, priority_min: int = 0) -> list[TransformationRule]:
        """Get transformation rules sorted by priority (descending)."""
        return sorted(
            [r for r in self.transformations if r.priority >= priority_min],
            key=lambda r: r.priority,
            reverse=True
        )
