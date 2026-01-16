# NNRT V6 — Road to Verification and Analysis

## Status: 📋 PLANNING
## Created: 2026-01-16
## Target: V6 Alpha

---

## Executive Summary

V6 extends NNRT beyond single-narrative neutralization to become a **verification and analysis platform**. Three major features are planned:

| Feature | Priority | Complexity | Dependencies |
|---------|----------|------------|--------------|
| **Timeline Reconstruction** | P0 | Medium | p44_timeline (exists) |
| **Question Generation** | P1 | Medium | Timeline, Uncertainty |
| **Multi-Narrative Comparison** | P2 | High | Timeline, All V5 |

### Vision

```
V5: Narrative → Neutral Atomic Statements
V6: Multiple Narratives → Verified Timeline → Investigation Questions
```

---

## Feature 1: Timeline Reconstruction (Enhanced)

### Current State

- **`p44_timeline.py`** exists with basic functionality
- Builds `TimelineEntry` objects with sequence ordering
- Uses absolute times (DATE/TIME identifiers) as anchors
- Detects relative markers ("then", "later", "the next day")

### Gaps in Current Implementation

1. **No visualization output** - Timeline is built but not rendered
2. **Event-only focus** - Doesn't include atomic statements in timeline
3. **No time gap detection** - Doesn't flag unexplained gaps
4. **Single-day assumption** - Struggles with multi-day narratives
5. **No uncertainty propagation** - Doesn't flag uncertain temporal placements

### V6 Enhancements

#### 1.1 Timeline Data Model Expansion

```python
class TimelineEntry(BaseModel):
    # Existing fields...
    
    # V6 NEW: Gap Detection
    gap_before_minutes: Optional[int] = None  # Unexplained gap from previous
    gap_type: Optional[TimeGapType] = None    # EXPLAINED, UNEXPLAINED, CONTRADICTORY
    
    # V6 NEW: Multi-Day Support
    day_offset: int = 0  # 0 = incident day, 1 = next day, etc.
    
    # V6 NEW: Verification Status
    time_source: TimeSource = TimeSource.INFERRED  # EXPLICIT, RELATIVE, INFERRED
    requires_verification: bool = False
    
    # V6 NEW: Cross-Narrative Linking (for Feature 3)
    corroborating_entry_ids: list[str] = []  # From other narratives
    contradicting_entry_ids: list[str] = []
```

#### 1.2 Gap Detection Algorithm

```
For each pair of adjacent timeline entries:
  1. If both have absolute times:
     - Calculate gap in minutes
     - If gap > threshold AND no relative marker explains it:
       → Flag as UNEXPLAINED_GAP
       → Add to gaps_needing_investigation list
       
  2. If timeline has "the next day" marker:
     - Update day_offset for all subsequent entries
     - Recalculate gaps within each day
     
  3. If entry has low time_confidence:
     → Flag requires_verification = True
```

#### 1.3 Timeline Renderer

New output section in structured report:

```
══════════════════════════════════════════════════════════════════════
                         RECONSTRUCTED TIMELINE
══════════════════════════════════════════════════════════════════════

DAY 1: January 10, 2026
───────────────────────────────────────────────────────────────────────
  11:30 PM   Officer approached Reporter at Cedar Street
             Source: Explicit (identifier)
             
  ~11:35 PM  Officer grabbed Reporter's arm
             Source: Inferred (narrative sequence)
             
  ⚠️ GAP: ~20 minutes unaccounted for
             
  11:47 PM   Bystander began recording
             Source: Explicit (identifier)

DAY 2: January 11, 2026
───────────────────────────────────────────────────────────────────────
  Morning    Reporter went to emergency room
             Source: Relative ("the next day")
             Time: ⚠️ Needs verification
```

### Implementation Plan (Timeline)

| Step | Description | Effort |
|------|-------------|--------|
| 1.1 | Extend TimelineEntry model | 1 hr |
| 1.2 | Add gap detection to p44_timeline | 2 hr |
| 1.3 | Add multi-day support | 2 hr |
| 1.4 | Create timeline renderer | 2 hr |
| 1.5 | Add verification flags | 1 hr |
| 1.6 | Tests | 2 hr |
| **Total** | | **10 hr** |

---

## Feature 2: Question Generation

### Concept

Auto-generate follow-up questions based on:
1. **Gaps in timeline** - What happened during unexplained gaps?
2. **Missing information** - Who, what, where, when not specified
3. **Unresolved actors** - Pronouns without clear referents
4. **Low-confidence claims** - Statements needing verification
5. **Contradictions** - Internal inconsistencies

### Data Sources for Question Generation

| Source | Question Type | Example |
|--------|---------------|---------|
| Timeline gaps | Temporal | "What happened between 11:35 PM and 11:47 PM?" |
| Unresolved actors | Identity | "Who is 'he' in 'he grabbed my arm'?" |
| Missing times | Temporal | "What time did you arrive at the hospital?" |
| Missing locations | Spatial | "Where exactly did this occur?" |
| NEEDS_PROVENANCE | Evidence | "Can you provide the medical records?" |
| Intent claims | Verification | "How do you know he 'wanted to hurt you'?" |
| Conspiracy claims | Evidence | "What evidence supports this cover-up?" |

### Question Categories

```python
class QuestionCategory(str, Enum):
    """Types of investigative questions."""
    
    # Timeline/Sequence
    TIMELINE_GAP = "timeline_gap"           # Unexplained time gaps
    SEQUENCE_UNCLEAR = "sequence_unclear"   # Order of events unclear
    DURATION_MISSING = "duration_missing"   # How long did X take?
    
    # Identity/Actor
    ACTOR_UNRESOLVED = "actor_unresolved"   # Who did this?
    WITNESS_IDENTITY = "witness_identity"   # Who is this witness?
    
    # Location/Context
    LOCATION_MISSING = "location_missing"   # Where did this happen?
    LOCATION_VAGUE = "location_vague"       # "Near the corner" - which corner?
    
    # Evidence/Provenance
    EVIDENCE_REQUEST = "evidence_request"   # Can you provide documents?
    MEDICAL_RECORDS = "medical_records"     # Medical documentation
    WITNESS_CONTACT = "witness_contact"     # How to reach witness?
    
    # Verification
    INTENT_VERIFICATION = "intent_verify"   # How do you know their intent?
    CLAIM_VERIFICATION = "claim_verify"     # What supports this claim?
    CONTRADICTION = "contradiction"         # Resolve conflicting info
```

### Question Data Model

```python
class InvestigativeQuestion(BaseModel):
    """A generated question for investigation follow-up."""
    
    id: str
    category: QuestionCategory
    question_text: str
    
    # Source of the question
    source_statement_ids: list[str] = []     # Which statements triggered this
    source_timeline_entry_id: Optional[str]  # If timeline-based
    source_uncertainty_id: Optional[str]     # If uncertainty-based
    
    # Priority
    priority: QuestionPriority  # CRITICAL, HIGH, MEDIUM, LOW
    
    # For the investigator
    context: str                # Why this question matters
    suggested_evidence: list[str] = []  # What could answer this
    
    # Answer tracking (for interactive mode)
    answer: Optional[str] = None
    answered_at: Optional[datetime] = None
```

### Question Generation Pass

New pass: **`p80_generate_questions.py`**

```
Algorithm:
1. TIMELINE ANALYSIS
   - For each UNEXPLAINED_GAP: Generate TIMELINE_GAP question
   - For each low-confidence entry: Generate SEQUENCE_UNCLEAR question
   
2. ACTOR ANALYSIS  
   - For each ACTOR_UNRESOLVED event: Generate ACTOR_UNRESOLVED question
   - For each pronoun without resolved referent: Generate question
   
3. PROVENANCE ANALYSIS
   - For each statement with NEEDS_PROVENANCE: Generate EVIDENCE_REQUEST
   - For medical_finding without record: Generate MEDICAL_RECORDS question
   
4. DANGEROUS CONTENT ANALYSIS
   - For each INTENT_ATTRIBUTION: Generate skeptical question
   - For each CONSPIRACY_CLAIM: Generate evidence question
   
5. CONTRADICTION DETECTION
   - Compare statements, flag conflicts
   - Generate CONTRADICTION questions
   
6. COMPLETENESS CHECK
   - Check for missing: who, what, when, where
   - Generate questions for missing elements
```

### Implementation Plan (Questions)

| Step | Description | Effort |
|------|-------------|--------|
| 2.1 | Define QuestionCategory enum | 0.5 hr |
| 2.2 | Define InvestigativeQuestion model | 1 hr |
| 2.3 | Create p80_generate_questions pass | 4 hr |
| 2.4 | Timeline gap → questions | 2 hr |
| 2.5 | Actor analysis → questions | 2 hr |
| 2.6 | Provenance → questions | 2 hr |
| 2.7 | Contradiction detection | 3 hr |
| 2.8 | Question renderer | 2 hr |
| 2.9 | Tests | 3 hr |
| **Total** | | **19.5 hr** |

---

## Feature 3: Multi-Narrative Comparison

### Concept

Compare multiple accounts of the same incident:
- Reporter's narrative vs. Officer's statement
- Reporter's narrative vs. Witness account
- Multiple witness accounts

### Comparison Dimensions

| Dimension | What to Compare | Output |
|-----------|-----------------|--------|
| **Timeline** | Event ordering | Agreement/Disagreement markers |
| **Facts** | Observable events | Corroboration/Contradiction |
| **Actors** | Who did what | Role disagreements |
| **Quotes** | What was said | Matching/conflicting quotes |
| **Injuries** | Documented harm | Corroborated by both? |

### Multi-Narrative Data Model

```python
class NarrativeSource(BaseModel):
    """A single narrative being compared."""
    
    id: str
    label: str                    # "Reporter", "Officer Jenkins", "Witness Chen"
    role: NarrativeRole          # REPORTER, SUBJECT, WITNESS, OFFICIAL
    transform_result: TransformResult
    
    # Metadata
    collected_at: Optional[datetime]
    collected_by: Optional[str]


class NarrativeComparison(BaseModel):
    """Comparison of multiple narratives about the same incident."""
    
    id: str
    narratives: list[NarrativeSource]
    
    # Merged timeline
    unified_timeline: list[TimelineEntry]
    
    # Analysis results
    corroborations: list[FactCorroboration]
    contradictions: list[FactContradiction]
    unique_claims: list[UniqueClaim]  # Only one source mentions this
    
    # Summary
    agreement_score: float  # 0.0-1.0
    key_disagreements: list[str]


class FactCorroboration(BaseModel):
    """Multiple sources agree on a fact."""
    
    id: str
    fact_text: str
    
    # Which narratives mention this
    source_ids: list[str]  # NarrativeSource IDs
    statement_ids: dict[str, list[str]]  # narrative_id → statement_ids
    
    # Strength
    strength: CorroborationStrength  # STRONG, MODERATE, WEAK


class FactContradiction(BaseModel):
    """Sources disagree on a fact."""
    
    id: str
    topic: str  # What they disagree about
    
    # The conflicting claims
    claims: list[ContradictingClaim]
    
    # Analysis
    contradiction_type: ContradictionType
    # SEQUENCE (order disagreement)
    # ACTOR (who did it)
    # OCCURRENCE (did it happen at all)
    # CHARACTERIZATION (how to describe it)
    
    # For investigation
    resolution_needed: bool
    suggested_evidence: list[str]
```

### Comparison Algorithm

```
PHASE 1: TIMELINE ALIGNMENT
  1. Build timeline from each narrative
  2. Find anchor events (mentioned in multiple narratives)
  3. Align timelines at anchor points
  4. Identify sequence disagreements
  
PHASE 2: ENTITY MAPPING
  1. Extract entities from each narrative
  2. Match entities across narratives (same person, different names)
  3. Build unified entity registry
  
PHASE 3: FACT COMPARISON
  For each atomic statement in Narrative A:
    1. Find semantically similar statements in Narrative B, C, ...
    2. If match found with SAME epistemic type:
       → Add to corroborations
    3. If match found with DIFFERENT claims:
       → Add to contradictions
    4. If no match found:
       → Add to unique_claims
       
PHASE 4: SPECIAL COMPARISONS
  - Compare quotes (exact match, partial match, conflicting)
  - Compare injury descriptions
  - Compare legal characterizations (who's at fault)
  
PHASE 5: GENERATE UNIFIED VIEW
  - Build unified timeline with all sources
  - Mark corroborated facts with ✓
  - Mark contradictions with ⚠️
  - Flag unique claims with 🔎
```

### Comparison Output

```
══════════════════════════════════════════════════════════════════════
                    MULTI-NARRATIVE COMPARISON
══════════════════════════════════════════════════════════════════════

NARRATIVES ANALYZED:
  1. Reporter (Marcus Johnson)
  2. Subject Officer (Officer Jenkins)  
  3. Witness (Patricia Chen)

AGREEMENT SCORE: 68%

══════════════════════════════════════════════════════════════════════
                         CORROBORATED FACTS
══════════════════════════════════════════════════════════════════════

✓ All 3 sources agree:
  • Incident occurred on Cedar Street corner
  • Time was approximately 11:30 PM
  • Physical contact occurred between Officer and Reporter

✓ Reporter + Witness agree:
  • Reporter was grabbed without warning
  • Bystander began recording

✓ Officer + Reporter agree:
  • Reporter was placed in handcuffs
  • Incident lasted approximately 15 minutes

══════════════════════════════════════════════════════════════════════
                          CONTRADICTIONS
══════════════════════════════════════════════════════════════════════

⚠️ SEQUENCE DISAGREEMENT: Who acted first
   Reporter:  "Officer approached me without provocation"
   Officer:   "Subject was behaving erratically, I approached to check welfare"
   
⚠️ CHARACTERIZATION: Use of force
   Reporter:  "Slammed me against the patrol car"
   Officer:   "Guided subject to vehicle for search"
   Witness:   "Pushed him pretty hard against the car"
   
⚠️ OCCURRENCE: Verbal threat
   Reporter:  "He said he would make my life hell"
   Officer:   [Not mentioned]
   Witness:   [Not present for this portion]

══════════════════════════════════════════════════════════════════════
                         UNIQUE CLAIMS
══════════════════════════════════════════════════════════════════════

🔎 Only Reporter mentions:
  • "My glasses fell and broke"
  • "I saw his hand on his weapon"
  • Estimate of 15 other citizens with complaints
  
🔎 Only Officer mentions:
  • Suspected intoxication
  • Subject refused to provide ID
  
🔎 Only Witness mentions:
  • Second officer arrived during incident
```

### Implementation Plan (Comparison)

| Step | Description | Effort |
|------|-------------|--------|
| 3.1 | Define comparison data models | 2 hr |
| 3.2 | Timeline alignment algorithm | 4 hr |
| 3.3 | Entity mapping across narratives | 4 hr |
| 3.4 | Semantic similarity for statements | 6 hr |
| 3.5 | Corroboration detection | 3 hr |
| 3.6 | Contradiction detection | 4 hr |
| 3.7 | Comparison renderer | 4 hr |
| 3.8 | Unified timeline generation | 3 hr |
| 3.9 | Tests | 4 hr |
| **Total** | | **34 hr** |

---

## Implementation Roadmap

### Phase 1: Timeline Enhancement (Week 1)
- [ ] Extend TimelineEntry model
- [ ] Implement gap detection
- [ ] Add multi-day support
- [ ] Create timeline renderer
- [ ] Tests

### Phase 2: Question Generation (Week 2-3)
- [ ] Define question models
- [ ] Create p80_generate_questions pass
- [ ] Implement all question generators
- [ ] Question renderer
- [ ] Tests

### Phase 3: Multi-Narrative (Week 4-6)
- [ ] Define comparison models
- [ ] Timeline alignment
- [ ] Entity mapping
- [ ] Semantic comparison
- [ ] Comparison renderer
- [ ] Integration tests

### Phase 4: UI Integration (Week 7)
- [ ] Timeline visualization panel
- [ ] Questions panel
- [ ] Multi-narrative mode
- [ ] Comparison view

---

## Dependencies & Prerequisites

### For Timeline Enhancement
- None (builds on existing p44_timeline)

### For Question Generation
- Enhanced timeline (Phase 1)
- UncertaintyMarker population (may need enhancement)

### For Multi-Narrative Comparison
- Enhanced timeline (Phase 1)
- Semantic similarity (may need NLP enhancement)
- Entity disambiguation
- Full V5 pipeline working

---

## Open Questions

1. **Semantic Similarity**: Use embeddings or rule-based matching?
   - Embeddings: More flexible, requires model
   - Rules: More predictable, labor-intensive

2. **Multi-Narrative Input Format**: How do users provide multiple narratives?
   - Separate text inputs?
   - File upload?
   - API batch mode?

3. **Question Prioritization**: How to rank questions?
   - By uncertainty level?
   - By legal relevance?
   - By timeline criticality?

4. **Interactive Mode**: Should questions be answerable in the UI?
   - If yes, how do answers update the analysis?

---

## Success Criteria

### Timeline Enhancement
- [ ] 90% of test narratives have complete timeline
- [ ] All time gaps > 10 minutes are flagged
- [ ] Multi-day narratives handled correctly

### Question Generation
- [ ] All UNEXPLAINED_GAP entries generate questions
- [ ] All ACTOR_UNRESOLVED events generate questions
- [ ] All NEEDS_PROVENANCE statements generate questions
- [ ] Questions are grammatically correct

### Multi-Narrative Comparison
- [ ] Timeline alignment works for 2+ narratives
- [ ] Contradictions correctly identified in 90% of test cases
- [ ] Corroborations correctly identified
- [ ] Output is clear and actionable

---

## Appendix: Existing Implementation Details

### p44_timeline.py (Current)
- **Lines**: 359
- **Functions**: `build_timeline`, `_find_relative_marker_before_position`, `_parse_time_for_sort`
- **Patterns Detected**: SEQUENCE_PATTERNS, BEFORE_PATTERNS, TIME_GAP_PATTERNS, DURING_PATTERNS

### TimelineEntry (Current Schema)
```python
class TimelineEntry(BaseModel):
    id: str
    event_id: Optional[str]
    statement_id: Optional[str]
    group_id: Optional[str]
    absolute_time: Optional[str]
    date: Optional[str]
    relative_time: Optional[str]
    sequence_order: int
    before_entry_ids: list[str]
    after_entry_ids: list[str]
    time_confidence: float
```

### UncertaintyType (Current)
```python
class UncertaintyType(str, Enum):
    AMBIGUOUS_REFERENCE = "ambiguous_reference"
    MISSING_CONTEXT = "missing_context"
    LOW_CONFIDENCE = "low_confidence"
    CONTRADICTORY = "contradictory"
    INCOMPLETE = "incomplete"
```
