"""
V6 Multi-Narrative Comparison System.

This module compares multiple accounts of the same incident to identify:
1. Agreements - Facts/events that multiple accounts confirm
2. Contradictions - Conflicting statements between accounts
3. Unique claims - Information only in one account
4. Timeline discrepancies - Different event sequences

Usage:
    from nnrt.v6.comparison import compare_narratives, ComparisonResult
    
    result = compare_narratives([
        ("complainant", complainant_result),
        ("officer", officer_result),
        ("witness", witness_result),
    ])
"""

import re
import structlog
from enum import Enum
from typing import List, Optional, Tuple, Dict, Any
from pydantic import BaseModel, Field
from difflib import SequenceMatcher

log = structlog.get_logger("nnrt.v6.comparison")


class ComparisonType(str, Enum):
    """Type of comparison finding."""
    AGREEMENT = "agreement"           # Multiple sources agree
    CONTRADICTION = "contradiction"   # Sources contradict
    UNIQUE_CLAIM = "unique_claim"     # Only in one source
    TIMELINE_DISCREPANCY = "timeline_discrepancy"  # Different sequences
    OMISSION = "omission"             # One source omits something


class SeverityLevel(str, Enum):
    """Severity of a contradiction or discrepancy."""
    CRITICAL = "critical"   # Major factual contradiction
    SIGNIFICANT = "significant"  # Important difference
    MINOR = "minor"         # Small detail difference


class NarrativeSource(BaseModel):
    """A source narrative for comparison."""
    
    label: str = Field(..., description="Source identifier: 'complainant', 'officer', etc.")
    events: List[Any] = Field(default_factory=list, description="Extracted events")
    statements: List[Any] = Field(default_factory=list, description="Atomic statements")
    entities: List[Any] = Field(default_factory=list, description="Entities mentioned")
    timeline: List[Any] = Field(default_factory=list, description="Timeline entries")
    raw_text: Optional[str] = Field(None, description="Original narrative text")


class ComparisonFinding(BaseModel):
    """A single comparison finding between narratives."""
    
    id: str = Field(..., description="Finding ID")
    type: ComparisonType = Field(..., description="Type of finding")
    severity: SeverityLevel = Field(SeverityLevel.MINOR, description="Severity level")
    
    # What was compared
    topic: str = Field(..., description="What this is about: 'time of incident', 'use of force'")
    
    # Source information
    sources_involved: List[str] = Field(..., description="Labels of sources involved")
    source_excerpts: Dict[str, str] = Field(default_factory=dict, description="Relevant text from each source")
    
    # Analysis
    description: str = Field(..., description="What the finding means")
    details: Optional[str] = Field(None, description="Additional details")
    
    # For contradictions
    suggested_resolution: Optional[str] = Field(None, description="How to investigate this")


class ComparisonResult(BaseModel):
    """Complete comparison result between multiple narratives."""
    
    source_count: int = Field(0, description="Number of sources compared")
    source_labels: List[str] = Field(default_factory=list)
    
    # Findings by type
    findings: List[ComparisonFinding] = Field(default_factory=list)
    
    # Summary counts
    agreement_count: int = Field(0)
    contradiction_count: int = Field(0)
    unique_claim_count: int = Field(0)
    timeline_discrepancy_count: int = Field(0)
    
    # Critical issues
    critical_findings: List[str] = Field(default_factory=list, description="IDs of critical findings")
    
    # Overall assessment
    overall_consistency: float = Field(0.0, ge=0.0, le=1.0, description="0-1 consistency score")


# =============================================================================
# Similarity and Matching Functions
# =============================================================================

def _text_similarity(text1: str, text2: str) -> float:
    """Calculate similarity between two text strings."""
    if not text1 or not text2:
        return 0.0
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()


def _normalize_for_comparison(text: str) -> str:
    """Normalize text for comparison."""
    if not text:
        return ""
    # Lowercase, remove extra whitespace
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    # Remove punctuation
    text = re.sub(r'[^\w\s]', '', text)
    return text


def _extract_key_facts(statements: List[Any]) -> List[Tuple[str, str]]:
    """Extract key facts from statements as (normalized, original) pairs."""
    facts = []
    for stmt in statements:
        text = getattr(stmt, 'text', str(stmt))
        normalized = _normalize_for_comparison(text)
        if normalized:
            facts.append((normalized, text))
    return facts


def _find_matching_fact(fact: str, other_facts: List[Tuple[str, str]], 
                        threshold: float = 0.7) -> Optional[Tuple[str, float]]:
    """Find a matching fact in another source's facts."""
    best_match = None
    best_score = 0.0
    
    for other_norm, other_orig in other_facts:
        score = _text_similarity(fact, other_norm)
        if score > best_score and score >= threshold:
            best_score = score
            best_match = other_orig
    
    return (best_match, best_score) if best_match else None


# =============================================================================
# Key Claim Patterns (for detecting important facts)
# =============================================================================

# Patterns for different types of claims
TIME_PATTERNS = [
    r'\b\d{1,2}:\d{2}\s*(?:am|pm|AM|PM)?\b',
    r'\bat\s+approximately\b',
    r'\bat\s+about\b',
]

LOCATION_PATTERNS = [
    r'\bon\s+\w+\s+(?:street|avenue|road|blvd|boulevard)\b',
    r'\bat\s+the\s+\w+\b',
    r'\bin\s+the\s+\w+\b',
]

FORCE_PATTERNS = [
    r'\b(grabbed|pushed|shoved|hit|struck|kicked|punched|threw)\b',
    r'\b(handcuffed|restrained|detained|arrested)\b',
    r'\b(taser|pepper spray|baton)\b',
]

INJURY_PATTERNS = [
    r'\b(hurt|injured|pain|bleeding|bruise)\b',
    r'\b(hospital|emergency room|ambulance)\b',
]


def _categorize_claim(text: str) -> Optional[str]:
    """Categorize a claim by type."""
    lower = text.lower()
    
    for pattern in TIME_PATTERNS:
        if re.search(pattern, lower, re.I):
            return "time"
    
    for pattern in FORCE_PATTERNS:
        if re.search(pattern, lower, re.I):
            return "force"
    
    for pattern in INJURY_PATTERNS:
        if re.search(pattern, lower, re.I):
            return "injury"
    
    for pattern in LOCATION_PATTERNS:
        if re.search(pattern, lower, re.I):
            return "location"
    
    return None


# =============================================================================
# Comparison Functions
# =============================================================================

def _compare_events(sources: List[NarrativeSource]) -> List[ComparisonFinding]:
    """Compare events across sources."""
    findings = []
    finding_counter = 0
    
    if len(sources) < 2:
        return findings
    
    # Extract event descriptions from each source
    source_events: Dict[str, List[str]] = {}
    for source in sources:
        descs = []
        for event in source.events:
            desc = getattr(event, 'description', str(event))
            if desc:
                descs.append(desc)
        source_events[source.label] = descs
    
    # Compare first source's events against others
    primary = sources[0]
    primary_descs = source_events.get(primary.label, [])
    
    for desc in primary_descs:
        normalized = _normalize_for_comparison(desc)
        category = _categorize_claim(desc)
        
        # Check if this event appears in other sources
        matches = {}
        for source in sources[1:]:
            other_descs = source_events.get(source.label, [])
            for other_desc in other_descs:
                similarity = _text_similarity(normalized, _normalize_for_comparison(other_desc))
                if similarity > 0.6:
                    matches[source.label] = (other_desc, similarity)
                    break
        
        if matches:
            # Agreement found
            all_labels = [primary.label] + list(matches.keys())
            excerpts = {primary.label: desc[:100]}
            for label, (match_text, _) in matches.items():
                excerpts[label] = match_text[:100]
            
            finding = ComparisonFinding(
                id=f"cf_{finding_counter:04d}",
                type=ComparisonType.AGREEMENT,
                severity=SeverityLevel.MINOR,  # Agreements are positive
                topic=category or "event",
                sources_involved=all_labels,
                source_excerpts=excerpts,
                description=f"Multiple sources agree on: {desc[:50]}...",
            )
            findings.append(finding)
            finding_counter += 1
        else:
            # Unique claim - only in primary source
            severity = SeverityLevel.SIGNIFICANT if category == "force" else SeverityLevel.MINOR
            
            finding = ComparisonFinding(
                id=f"cf_{finding_counter:04d}",
                type=ComparisonType.UNIQUE_CLAIM,
                severity=severity,
                topic=category or "event",
                sources_involved=[primary.label],
                source_excerpts={primary.label: desc[:100]},
                description=f"Only {primary.label} mentions: {desc[:50]}...",
                suggested_resolution="Verify with other evidence or follow-up interview",
            )
            findings.append(finding)
            finding_counter += 1
    
    return findings


def _compare_timelines(sources: List[NarrativeSource]) -> List[ComparisonFinding]:
    """Compare timeline sequences across sources."""
    findings = []
    finding_counter = 0
    
    if len(sources) < 2:
        return findings
    
    # Compare event sequences
    primary = sources[0]
    primary_events = [getattr(e, 'description', str(e))[:30] for e in primary.events[:5]]
    
    for source in sources[1:]:
        other_events = [getattr(e, 'description', str(e))[:30] for e in source.events[:5]]
        
        # Simple sequence comparison - check if order differs
        # This is a simplified check; full implementation would use timeline entries
        if len(primary_events) >= 2 and len(other_events) >= 2:
            # Check if any events appear in different order
            for i, evt1 in enumerate(primary_events):
                for j, evt2 in enumerate(primary_events):
                    if i < j:  # evt1 comes before evt2 in primary
                        # Check if order is reversed in other
                        try:
                            idx1_other = next((k for k, e in enumerate(other_events) 
                                             if _text_similarity(evt1, e) > 0.5), -1)
                            idx2_other = next((k for k, e in enumerate(other_events) 
                                             if _text_similarity(evt2, e) > 0.5), -1)
                            
                            if idx1_other >= 0 and idx2_other >= 0 and idx1_other > idx2_other:
                                finding = ComparisonFinding(
                                    id=f"cf_tl_{finding_counter:04d}",
                                    type=ComparisonType.TIMELINE_DISCREPANCY,
                                    severity=SeverityLevel.SIGNIFICANT,
                                    topic="event_sequence",
                                    sources_involved=[primary.label, source.label],
                                    source_excerpts={
                                        primary.label: f"{evt1} → {evt2}",
                                        source.label: f"{evt2} → {evt1}",
                                    },
                                    description=f"Event sequence differs between {primary.label} and {source.label}",
                                    suggested_resolution="Clarify the actual order of events",
                                )
                                findings.append(finding)
                                finding_counter += 1
                        except StopIteration:
                            pass
    
    return findings


def _find_contradictions(sources: List[NarrativeSource]) -> List[ComparisonFinding]:
    """Find contradicting statements between sources."""
    findings = []
    finding_counter = 0
    
    if len(sources) < 2:
        return findings
    
    # Extract facts from each source
    source_facts: Dict[str, List[Tuple[str, str]]] = {}
    for source in sources:
        source_facts[source.label] = _extract_key_facts(source.statements)
    
    # Look for potential contradictions
    # This is a simplified implementation - real contradictions require semantic understanding
    
    # Examples of contradiction patterns:
    contradiction_pairs = [
        (r'\bI was standing\b', r'\bI was sitting\b'),
        (r'\bI did not resist\b', r'\b(he|she|they)\s+resisted\b'),
        (r'\bno weapon\b', r'\bweapon\b'),
        (r'\bone officer\b', r'\b(two|three|multiple) officers\b'),
        (r'\bbefore\s+midnight\b', r'\bafter\s+midnight\b'),
    ]
    
    for source1 in sources:
        facts1 = source_facts.get(source1.label, [])
        
        for source2 in sources:
            if source2.label <= source1.label:
                continue  # Avoid duplicate comparisons
            
            facts2 = source_facts.get(source2.label, [])
            
            for norm1, orig1 in facts1:
                for pattern1, pattern2 in contradiction_pairs:
                    if re.search(pattern1, orig1, re.I):
                        # Check if other source has contradicting pattern
                        for norm2, orig2 in facts2:
                            if re.search(pattern2, orig2, re.I):
                                finding = ComparisonFinding(
                                    id=f"cf_ctr_{finding_counter:04d}",
                                    type=ComparisonType.CONTRADICTION,
                                    severity=SeverityLevel.CRITICAL,
                                    topic="factual_claim",
                                    sources_involved=[source1.label, source2.label],
                                    source_excerpts={
                                        source1.label: orig1[:100],
                                        source2.label: orig2[:100],
                                    },
                                    description=f"Potential contradiction between {source1.label} and {source2.label}",
                                    suggested_resolution="Interview both parties about this discrepancy",
                                )
                                findings.append(finding)
                                finding_counter += 1
    
    return findings


def compare_narratives(
    sources: List[Tuple[str, Any]],
) -> ComparisonResult:
    """
    Compare multiple narrative accounts.
    
    Args:
        sources: List of (label, TransformResult) tuples
        
    Returns:
        ComparisonResult with all findings
    """
    # Convert to NarrativeSource objects
    narrative_sources = []
    for label, result in sources:
        source = NarrativeSource(
            label=label,
            events=getattr(result, 'events', []),
            statements=getattr(result, 'atomic_statements', []),
            entities=getattr(result, 'entities', []),
            timeline=getattr(result, 'timeline', []),
            raw_text=getattr(result, 'raw_text', None),
        )
        narrative_sources.append(source)
    
    # Run comparisons
    all_findings = []
    
    # Compare events (agreements, unique claims)
    event_findings = _compare_events(narrative_sources)
    all_findings.extend(event_findings)
    
    # Compare timelines (sequence discrepancies)
    timeline_findings = _compare_timelines(narrative_sources)
    all_findings.extend(timeline_findings)
    
    # Find contradictions
    contradiction_findings = _find_contradictions(narrative_sources)
    all_findings.extend(contradiction_findings)
    
    # Calculate summary
    agreements = [f for f in all_findings if f.type == ComparisonType.AGREEMENT]
    contradictions = [f for f in all_findings if f.type == ComparisonType.CONTRADICTION]
    unique_claims = [f for f in all_findings if f.type == ComparisonType.UNIQUE_CLAIM]
    timeline_discrepancies = [f for f in all_findings if f.type == ComparisonType.TIMELINE_DISCREPANCY]
    
    # Critical findings
    critical = [f.id for f in all_findings if f.severity == SeverityLevel.CRITICAL]
    
    # Overall consistency (simplified)
    total_comparisons = len(all_findings) or 1
    consistent = len(agreements)
    inconsistent = len(contradictions) + len(timeline_discrepancies)
    consistency_score = consistent / total_comparisons if total_comparisons > 0 else 0.5
    
    result = ComparisonResult(
        source_count=len(sources),
        source_labels=[label for label, _ in sources],
        findings=all_findings,
        agreement_count=len(agreements),
        contradiction_count=len(contradictions),
        unique_claim_count=len(unique_claims),
        timeline_discrepancy_count=len(timeline_discrepancies),
        critical_findings=critical,
        overall_consistency=round(consistency_score, 2),
    )
    
    log.info(
        "narratives_compared",
        sources=len(sources),
        findings=len(all_findings),
        agreements=len(agreements),
        contradictions=len(contradictions),
        consistency=result.overall_consistency,
    )
    
    return result


def format_comparison_report(result: ComparisonResult) -> str:
    """Format a comparison result as a readable report."""
    lines = []
    
    lines.append("═" * 70)
    lines.append("              MULTI-NARRATIVE COMPARISON REPORT")
    lines.append("═" * 70)
    lines.append("")
    
    # Summary
    lines.append(f"📊 SUMMARY")
    lines.append(f"   Sources Compared: {result.source_count} ({', '.join(result.source_labels)})")
    lines.append(f"   Total Findings: {len(result.findings)}")
    lines.append(f"   Overall Consistency: {result.overall_consistency:.0%}")
    lines.append("")
    
    # Stats by type
    lines.append(f"   ✅ Agreements: {result.agreement_count}")
    lines.append(f"   ❌ Contradictions: {result.contradiction_count}")
    lines.append(f"   ⚠️ Unique Claims: {result.unique_claim_count}")
    lines.append(f"   🔄 Timeline Discrepancies: {result.timeline_discrepancy_count}")
    lines.append("")
    
    # Critical issues first
    if result.critical_findings:
        lines.append("─" * 70)
        lines.append("🔴 CRITICAL ISSUES")
        lines.append("─" * 70)
        for finding_id in result.critical_findings:
            finding = next((f for f in result.findings if f.id == finding_id), None)
            if finding:
                lines.append(f"")
                lines.append(f"  [{finding.type.value.upper()}] {finding.topic}")
                lines.append(f"  {finding.description}")
                for source, excerpt in finding.source_excerpts.items():
                    lines.append(f"    • {source}: \"{excerpt[:60]}...\"")
                if finding.suggested_resolution:
                    lines.append(f"  💡 {finding.suggested_resolution}")
        lines.append("")
    
    # All findings by type
    for finding_type, icon in [
        (ComparisonType.CONTRADICTION, "❌"),
        (ComparisonType.TIMELINE_DISCREPANCY, "🔄"),
        (ComparisonType.UNIQUE_CLAIM, "⚠️"),
        (ComparisonType.AGREEMENT, "✅"),
    ]:
        type_findings = [f for f in result.findings if f.type == finding_type]
        if type_findings and finding_type != ComparisonType.AGREEMENT:  # Skip agreements in detail
            lines.append("─" * 70)
            lines.append(f"{icon} {finding_type.value.upper().replace('_', ' ')}S ({len(type_findings)})")
            lines.append("─" * 70)
            
            for finding in type_findings[:5]:  # Limit display
                lines.append(f"")
                lines.append(f"  {finding.description}")
                for source, excerpt in finding.source_excerpts.items():
                    lines.append(f"    • {source}: \"{excerpt[:50]}...\"")
            
            if len(type_findings) > 5:
                lines.append(f"  ... and {len(type_findings) - 5} more")
            lines.append("")
    
    lines.append("═" * 70)
    
    return "\n".join(lines)
