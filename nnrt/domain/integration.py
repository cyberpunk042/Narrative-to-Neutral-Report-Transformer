"""
Domain Integration — Stage 5 Phase 4

Bridge between Domain configurations and PolicyEngine.

This module converts Domain transformation rules to PolicyRules
that the PolicyEngine can use.
"""

from __future__ import annotations

from typing import Optional

from nnrt.domain.schema import Domain, TransformationRule
from nnrt.domain.loader import get_domain
from nnrt.policy.models import (
    MatchType,
    PolicyRule,
    PolicyRuleset,
    PolicySettings,
    RuleAction,
    RuleMatch,
)


def domain_to_ruleset(domain: Domain) -> PolicyRuleset:
    """
    Convert a Domain's transformations to a PolicyRuleset.
    
    This allows the PolicyEngine to use domain-defined rules.
    
    Args:
        domain: The domain configuration
        
    Returns:
        PolicyRuleset with converted rules
    """
    rules = []
    
    for transformation in domain.transformations:
        rule = _convert_transformation(transformation)
        if rule:
            rules.append(rule)
    
    # Sort by priority (descending)
    rules.sort(key=lambda r: r.priority, reverse=True)
    
    return PolicyRuleset(
        version="2.0",
        name=domain.domain.id,
        description=f"Domain: {domain.domain.name}",
        rules=rules,
        validation=[],
        settings=PolicySettings(
            min_confidence=0.7,
            always_diagnose=True,
        ),
    )


def _convert_transformation(trans: TransformationRule) -> Optional[PolicyRule]:
    """
    Convert a domain TransformationRule to a PolicyRule.
    
    Args:
        trans: The domain transformation rule
        
    Returns:
        PolicyRule or None if conversion fails
    """
    if not trans.match:
        return None
    
    # Determine action
    if trans.preserve:
        action = RuleAction.PRESERVE
        replacement = None
    elif trans.remove:
        action = RuleAction.REMOVE
        replacement = None
    elif trans.replace:
        action = RuleAction.REPLACE
        replacement = trans.replace
    else:
        # Default to flag
        action = RuleAction.FLAG
        replacement = None
    
    # Determine match type based on patterns
    # Single words = keyword, multiple words = phrase
    has_phrase = any(' ' in p for p in trans.match)
    match_type = MatchType.PHRASE if has_phrase else MatchType.KEYWORD
    
    # Create RuleMatch object
    rule_match = RuleMatch(
        type=match_type,
        patterns=trans.match,
        context=trans.context if trans.context else [],
    )
    
    return PolicyRule(
        id=trans.id,
        category="domain",
        priority=trans.priority,
        description=f"Domain rule: {trans.id}",
        match=rule_match,
        action=action,
        replacement=replacement,
    )


def get_domain_ruleset(domain_id: str) -> PolicyRuleset:
    """
    Get a PolicyRuleset for a domain by ID.
    
    Args:
        domain_id: The domain ID (e.g., 'law_enforcement')
        
    Returns:
        PolicyRuleset with domain rules
    """
    domain = get_domain(domain_id)
    return domain_to_ruleset(domain)


def get_vocabulary_replacements(domain: Domain) -> dict[str, str]:
    """
    Build a vocabulary replacement map from a domain.
    
    This maps derogatory/synonym terms to their neutral forms.
    
    Args:
        domain: The domain configuration
        
    Returns:
        Dict mapping terms to neutral forms
    """
    replacements = {}
    
    for category_name in ['actors', 'actions', 'locations', 'modifiers']:
        category = getattr(domain.vocabulary, category_name, {})
        for term_id, term in category.items():
            # Map derogatory terms
            for derog in term.derogatory:
                if term.neutral_form:  # Only if there's a replacement
                    replacements[derog.lower()] = term.neutral_form
            
            # Map synonyms (optional - could keep synonyms as-is)
            # For now, only map derogatory terms
    
    return replacements


def get_entity_role_keywords(domain: Domain) -> dict[str, list[str]]:
    """
    Get entity role detection keywords from a domain.
    
    Args:
        domain: The domain configuration
        
    Returns:
        Dict mapping role names to their detection keywords
    """
    roles = {}
    
    for entity_role in domain.entity_roles:
        roles[entity_role.role] = entity_role.keywords
    
    return roles


def get_event_type_verbs(domain: Domain) -> dict[str, list[str]]:
    """
    Get event type verbs from a domain.
    
    Args:
        domain: The domain configuration
        
    Returns:
        Dict mapping event types to their verbs
    """
    event_types = {}
    
    for evt_type in domain.event_types:
        event_types[evt_type.type] = evt_type.verbs
    
    return event_types


def get_camera_friendly_verbs(domain: Domain) -> set[str]:
    """
    Get all verbs that indicate camera-friendly events.
    
    Args:
        domain: The domain configuration
        
    Returns:
        Set of verbs for camera-friendly events
    """
    verbs = set()
    
    for evt_type in domain.event_types:
        if evt_type.is_camera_friendly:
            verbs.update(evt_type.verbs)
    
    return verbs
