"""
Domain Loader — Stage 5

Load and validate domain configurations from YAML files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

from nnrt.domain.schema import Domain


# Domain cache
_domains: dict[str, Domain] = {}


def load_domain(path: Path | str, validate: bool = True) -> Domain:
    """
    Load a domain configuration from a YAML file.
    
    Args:
        path: Path to the domain YAML file
        validate: Whether to validate the configuration
        
    Returns:
        Domain configuration
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValidationError: If validation fails
    """
    path = Path(path)
    
    if not path.exists():
        raise FileNotFoundError(f"Domain file not found: {path}")
    
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    
    # Parse with Pydantic (validates automatically)
    domain = Domain.model_validate(data)
    
    # Handle inheritance if extends is set
    if domain.domain.extends:
        base = get_domain(domain.domain.extends)
        domain = _merge_domains(base, domain)
    
    return domain


def get_domain(domain_id: str) -> Domain:
    """
    Get a domain by ID, loading from standard location if needed.
    
    Args:
        domain_id: Domain ID (e.g., 'law_enforcement')
        
    Returns:
        Domain configuration
        
    Raises:
        FileNotFoundError: If domain file not found
    """
    if domain_id in _domains:
        return _domains[domain_id]
    
    # Look in standard location
    domain_path = _get_domain_path(domain_id)
    domain = load_domain(domain_path)
    
    # Cache it
    _domains[domain_id] = domain
    
    return domain


def clear_domain_cache() -> None:
    """Clear the domain cache."""
    global _domains
    _domains = {}


def _get_domain_path(domain_id: str) -> Path:
    """Get the path to a domain file by ID."""
    # First try new location
    new_path = Path(__file__).parent.parent / "domain" / "configs" / f"{domain_id}.yaml"
    if new_path.exists():
        return new_path
    
    # Try old location (policy/rulesets/domains)
    old_path = Path(__file__).parent.parent / "policy" / "rulesets" / "domains" / f"{domain_id}.yaml"
    if old_path.exists():
        return old_path
    
    raise FileNotFoundError(
        f"Domain '{domain_id}' not found. Checked:\n"
        f"  - {new_path}\n"
        f"  - {old_path}"
    )


def _merge_domains(base: Domain, overlay: Domain) -> Domain:
    """
    Merge an overlay domain onto a base domain.
    
    The overlay takes precedence for conflicting items.
    
    Args:
        base: Base domain configuration
        overlay: Overlay domain configuration
        
    Returns:
        Merged domain configuration
    """
    # Start with base data
    merged_data = base.model_dump()
    overlay_data = overlay.model_dump()
    
    # Override domain info
    merged_data['domain'] = overlay_data['domain']
    
    # Merge vocabulary (overlay wins for conflicts)
    for category in ['actors', 'actions', 'locations', 'modifiers']:
        base_vocab = merged_data.get('vocabulary', {}).get(category, {})
        overlay_vocab = overlay_data.get('vocabulary', {}).get(category, {})
        base_vocab.update(overlay_vocab)
        merged_data.setdefault('vocabulary', {})[category] = base_vocab
    
    # Merge lists (append overlay to base)
    for list_field in ['entity_roles', 'event_types', 'transformations']:
        base_list = merged_data.get(list_field, [])
        overlay_list = overlay_data.get(list_field, [])
        # Remove duplicates based on role/type/id
        existing_ids = set()
        for item in base_list:
            if 'role' in item:
                existing_ids.add(item['role'])
            elif 'type' in item:
                existing_ids.add(item['type'])
            elif 'id' in item:
                existing_ids.add(item['id'])
        
        for item in overlay_list:
            item_id = item.get('role') or item.get('type') or item.get('id')
            if item_id in existing_ids:
                # Replace base item
                base_list = [i for i in base_list if (
                    i.get('role') != item_id and 
                    i.get('type') != item_id and 
                    i.get('id') != item_id
                )]
            base_list.append(item)
        
        merged_data[list_field] = base_list
    
    # Override classification
    if overlay_data.get('classification'):
        merged_data['classification'] = overlay_data['classification']
    
    # Override diagnostics
    if overlay_data.get('diagnostics'):
        merged_data['diagnostics'] = overlay_data['diagnostics']
    
    # Override metadata
    if overlay_data.get('metadata'):
        merged_data['metadata'] = overlay_data['metadata']
    
    return Domain.model_validate(merged_data)


def create_domain_template(domain_id: str, name: str) -> str:
    """
    Create a template YAML for a new domain.
    
    Args:
        domain_id: Domain ID (e.g., 'medical_malpractice')
        name: Human-readable name
        
    Returns:
        YAML template string
    """
    template = f'''# {name} Domain Configuration
# Stage 5 Domain System

domain:
  id: {domain_id}
  name: "{name}"
  version: "1.0"
  description: "TODO: Add description"
  # extends: base  # Uncomment to inherit from base domain

# ============================================================================
# VOCABULARY
# ============================================================================
vocabulary:
  actors:
    # example_role:
    #   synonyms: ["synonym1", "synonym2"]
    #   derogatory: ["derogatory_term"]
    #   neutral_form: "neutral term"
  
  actions:
    # example_action:
    #   synonyms: ["synonym1"]
    #   neutral_form: "neutral action"
  
  locations:
    # example_location:
    #   synonyms: ["synonym1"]
    #   neutral_form: "neutral location"

# ============================================================================
# ENTITY ROLES
# ============================================================================
entity_roles:
  # - role: EXAMPLE_ROLE
  #   patterns:
  #     - "Pattern {{name}}"
  #   keywords:
  #     - "keyword"
  #   participation: incident
  #   is_primary: false

# ============================================================================
# EVENT TYPES
# ============================================================================
event_types:
  # - type: EXAMPLE_EVENT
  #   verbs: ["example_verb"]
  #   requires_actor: true
  #   is_camera_friendly: true
  #   participation: incident

# ============================================================================
# CLASSIFICATION
# ============================================================================
classification:
  camera_friendly:
    required:
      - has_named_actor
      - has_physical_action
    disqualifying:
      - contains_internal_state
  
  follow_up:
    actor_roles: []
    time_contexts:
      - "later"
      - "afterward"

# ============================================================================
# TRANSFORMATIONS
# ============================================================================
transformations:
  # - id: {domain_id}_example
  #   match: ["inflammatory term"]
  #   replace: "neutral term"
  #   priority: 60

# ============================================================================
# DIAGNOSTICS
# ============================================================================
diagnostics:
  flags: []

# ============================================================================
# METADATA
# ============================================================================
metadata:
  typical_actors: []
  typical_locations: []
  typical_timeline:
    - incident
    - aftermath
'''
    return template
