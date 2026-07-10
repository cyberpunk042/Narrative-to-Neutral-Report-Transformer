"""
Domain Module — Stage 5

Provides domain configuration system for NNRT.

A domain contains:
- Vocabulary (synonyms, canonical forms)
- Entity role patterns
- Event type definitions
- Classification rules
- Transformation rules
"""

from nnrt.domain.integration import (
    domain_to_ruleset,
    get_camera_friendly_verbs,
    get_domain_ruleset,
    get_entity_role_keywords,
    get_event_type_verbs,
    get_vocabulary_replacements,
)
from nnrt.domain.loader import get_domain, load_domain
from nnrt.domain.schema import (
    ClassificationConfig,
    Domain,
    DomainVocabulary,
    EntityRolePattern,
    EventTypeDefinition,
    TransformationRule,
    VocabularyTerm,
)

__all__ = [
    # Schema
    "Domain",
    "DomainVocabulary",
    "VocabularyTerm",
    "EntityRolePattern",
    "EventTypeDefinition",
    "ClassificationConfig",
    "TransformationRule",
    # Loader
    "load_domain",
    "get_domain",
    # Integration
    "domain_to_ruleset",
    "get_domain_ruleset",
    "get_vocabulary_replacements",
    "get_entity_role_keywords",
    "get_event_type_verbs",
    "get_camera_friendly_verbs",
]

