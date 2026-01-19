from __future__ import annotations
"""
Selection Models — Stage 2

V7 / Stage 2: Dataclasses for selection layer.

This module defines:
- SelectionMode: Output mode enum (STRICT, FULL, TIMELINE, etc.)
- SelectionResult: Which atoms are selected for which output sections
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SelectionMode(str, Enum):
    """Output mode determines selection criteria."""
    
    STRICT = "strict"
    # Only camera-friendly events with high confidence
    # Resolved entities and quotes only
    # Current default mode — matches existing output format
    
    FULL = "full"
    # All events with classification data
    # All entities  
    # All quotes (resolved and unresolved)
    # For debugging/analysis
    
    TIMELINE = "timeline"
    # Focus on timeline entries
    # Events ordered by time
    # For chronology-focused output
    
    EVENTS_ONLY = "events_only"
    # Just the event list
    # No quotes, no entities
    # For event extraction analysis
    
    RECOMPOSITION = "recomposition"
    # All atoms for narrative reconstruction
    # Preserves order and relationships
    # For future Stage 6


@dataclass
class SelectionResult:
    """
    Which atoms are selected for which output sections.
    
    This dataclass holds lists of IDs (not copies of atoms) pointing to 
    atoms that should be rendered in each section. The renderer uses these
    lists to know what to include without computing selection logic itself.
    """
    
    # Which mode was used
    mode: str = "strict"
    
    # === Event Selections ===
    
    observed_events: list[str] = field(default_factory=list)
    """Event IDs for OBSERVED EVENTS (STRICT) section."""
    
    follow_up_events: list[str] = field(default_factory=list)
    """Event IDs for FOLLOW-UP ACTIONS section."""
    
    source_derived_events: list[str] = field(default_factory=list)
    """Event IDs for SOURCE-DERIVED section."""
    
    narrative_excerpts: list[tuple[str, str]] = field(default_factory=list)
    """(Event ID, reason) tuples for NARRATIVE EXCERPTS section."""
    
    excluded_events: list[str] = field(default_factory=list)
    """Event IDs excluded entirely from output."""
    
    # === Quote Selections ===
    
    preserved_quotes: list[str] = field(default_factory=list)
    """SpeechAct IDs with resolved speakers — for PRESERVED QUOTES section."""
    
    quarantined_quotes: list[tuple[str, str]] = field(default_factory=list)
    """(SpeechAct ID, reason) tuples for QUARANTINE section."""
    
    # === Entity Selections ===
    
    incident_participants: list[str] = field(default_factory=list)
    """Entity IDs for INCIDENT PARTICIPANTS section."""
    
    post_incident_pros: list[str] = field(default_factory=list)
    """Entity IDs for POST-INCIDENT PROFESSIONALS section."""
    
    mentioned_contacts: list[str] = field(default_factory=list)
    """Entity IDs for MENTIONED CONTACTS section."""
    
    excluded_entities: list[str] = field(default_factory=list)
    """Entity IDs excluded entirely (bare role labels, etc.)."""
    
    # === Timeline Selections ===
    
    timeline_entries: list[str] = field(default_factory=list)
    """TimelineEntry IDs to include in RECONSTRUCTED TIMELINE."""
    
    excluded_timeline: list[tuple[str, str]] = field(default_factory=list)
    """(Entry ID, reason) tuples for excluded timeline entries."""
    
    # === V7 / Stage 2: Statement Selections (by epistemic_type) ===
    
    acute_state: list[str] = field(default_factory=list)
    """AtomicStatement IDs with epistemic_type='state_acute' — for SELF-REPORTED (ACUTE)."""
    
    injury_state: list[str] = field(default_factory=list)
    """AtomicStatement IDs with epistemic_type='state_injury' — for SELF-REPORTED (INJURY)."""
    
    psychological_state: list[str] = field(default_factory=list)
    """AtomicStatement IDs with epistemic_type='state_psychological' — for SELF-REPORTED (PSYCHOLOGICAL)."""
    
    socioeconomic_impact: list[str] = field(default_factory=list)
    """AtomicStatement IDs with epistemic_type='state_socioeconomic' — for SELF-REPORTED (SOCIOECONOMIC)."""
    
    general_self_report: list[str] = field(default_factory=list)
    """AtomicStatement IDs with epistemic_type='self_report' — for SELF-REPORTED (GENERAL)."""
    
    legal_allegations: list[str] = field(default_factory=list)
    """AtomicStatement IDs with epistemic_type='legal_claim' — for LEGAL ALLEGATIONS."""
    
    characterizations: list[str] = field(default_factory=list)
    """AtomicStatement IDs with epistemic_type='characterization' — for REPORTER CHARACTERIZATIONS."""
    
    inferences: list[str] = field(default_factory=list)
    """AtomicStatement IDs with epistemic_type='inference' — for REPORTER INFERENCES."""
    
    interpretations: list[str] = field(default_factory=list)
    """AtomicStatement IDs with epistemic_type='interpretation' — for REPORTER INTERPRETATIONS."""
    
    contested_allegations: list[str] = field(default_factory=list)
    """AtomicStatement IDs with epistemic_type='conspiracy_claim' — for CONTESTED ALLEGATIONS."""
    
    medical_findings: list[str] = field(default_factory=list)
    """AtomicStatement IDs for medical provider content — for MEDICAL FINDINGS."""
    
    admin_actions: list[str] = field(default_factory=list)
    """AtomicStatement IDs with epistemic_type='admin_action' — for ADMINISTRATIVE ACTIONS."""
    
    # === V7 / Stage 2: Identifier Selections ===
    
    identifiers_by_type: dict[str, list[str]] = field(default_factory=dict)
    """Identifier IDs grouped by type (date, time, location, etc.) — for REFERENCE DATA."""
    
    # === Statistics ===
    
    stats: dict = field(default_factory=dict)
    """Counts and metrics for logging/debugging."""
    
    def summary(self) -> str:
        """Get a summary string for logging."""
        return (
            f"Selection[{self.mode}]: "
            f"events={len(self.observed_events)}/{len(self.follow_up_events)}/{len(self.narrative_excerpts)} "
            f"(obs/followup/excerpt), "
            f"entities={len(self.incident_participants) + len(self.post_incident_pros) + len(self.mentioned_contacts)}, "
            f"quotes={len(self.preserved_quotes)}/{len(self.quarantined_quotes)} (pres/quar), "
            f"timeline={len(self.timeline_entries)}"
        )
