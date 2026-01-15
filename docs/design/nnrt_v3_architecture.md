# NNRT v3 Architecture — Semantic Understanding Layer

**Date**: 2026-01-15
**Status**: RFC (Request for Comments)

---

## Vision

Transform NNRT from a **pattern-matching text transformer** into an **evidence structure analyzer** that:

1. **Groups** related statements into coherent clusters
2. **Tracks** entities across the entire narrative (coreference)
3. **Builds** a timeline of events
4. **Classifies** evidence by type and reliability
5. **Renders** structured output that answers investigative questions

---

## Current Architecture (v2)

```
Input Text
    ↓
┌─────────────────────────────────────────────────────────┐
│ SEGMENTATION LAYER (p00-p10)                            │
│   - Normalize text                                      │
│   - Split into sentences/segments                       │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│ ANNOTATION LAYER (p20-p28)                              │
│   - Tag spans (intent_attribution, legal_conclusion)    │
│   - Classify statements (claim/observation/interpret)   │
│   - Decompose into atomic statements                    │
│   - PROBLEM: Each statement processed in isolation!     │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│ EXTRACTION LAYER (p30-p40)                              │
│   - Extract identifiers (names, badges, dates)          │
│   - Extract entities (people, organizations)            │
│   - Extract events (actions, verbal, movement)          │
│   - PROBLEM: No cross-segment linking!                  │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│ TRANSFORM LAYER (p50-p80)                               │
│   - Apply policy rules                                  │
│   - Render neutral text                                 │
│   - Package output                                      │
└─────────────────────────────────────────────────────────┘
    ↓
Output
```

### Key Limitations
1. **No cross-segment understanding** — Each segment processed independently
2. **No coreference** — "Officer Jenkins" and "he" not linked
3. **No grouping** — Statements listed in order of appearance, not meaning
4. **No timeline** — Events extracted but not temporally ordered
5. **No evidence classification** — All statements treated equally

---

## Proposed Architecture (v3)

```
Input Text
    ↓
┌─────────────────────────────────────────────────────────┐
│ SEGMENTATION LAYER (p00-p10)                            │
│   Same as v2                                            │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│ ANNOTATION LAYER (p20-p28)                              │
│   Enhanced with:                                        │
│   - Expanded OBSERVATION patterns                       │
│   - Experiential state detection                        │
│   - Speech act classification                           │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│ ★ NEW: SEMANTIC UNDERSTANDING LAYER (p35-p45) ★         │
│                                                         │
│   p35_coreference:                                      │
│     - Link "he/she/they" to entities                    │
│     - Merge "Officer Jenkins" = "Jenkins" = "he"        │
│     - Build entity chains across segments               │
│                                                         │
│   p37_timeline:                                         │
│     - Extract temporal markers                          │
│     - Order events chronologically                      │
│     - Detect temporal relationships (before/after/dur)  │
│                                                         │
│   p38_group_statements:                                 │
│     - Cluster related atomic statements                 │
│     - Semantic similarity grouping                      │
│     - Actor-based grouping                              │
│     - Evidence-type grouping                            │
│                                                         │
│   p39_classify_evidence:                                │
│     - Direct observation vs reported                    │
│     - Physical evidence vs testimony                    │
│     - Official documentation vs narrative               │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│ EXTRACTION LAYER (p40-p50)                              │
│   Enhanced with coreference-aware extraction            │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│ TRANSFORM LAYER (p60-p80)                               │
│   Enhanced with:                                        │
│   - Group-aware rendering                               │
│   - Timeline-aware ordering                             │
│   - Evidence hierarchy in output                        │
└─────────────────────────────────────────────────────────┘
    ↓
Structured Evidence Report
```

---

## New IR Schema Elements

### 1. StatementGroup

```python
class StatementGroupType(str, Enum):
    ENCOUNTER_NARRATIVE = "encounter_narrative"
    WITNESS_ACCOUNT = "witness_account"
    PHYSICAL_EVIDENCE = "physical_evidence"
    MEDICAL_DOCUMENTATION = "medical_documentation"
    OFFICIAL_RECORD = "official_record"
    EMOTIONAL_IMPACT = "emotional_impact"
    TIMELINE_MARKER = "timeline_marker"

class StatementGroup(BaseModel):
    """A semantic cluster of related statements."""
    
    id: str = Field(default_factory=lambda: f"grp_{uuid4().hex[:8]}")
    type: StatementGroupType
    title: str  # Human-readable: "Initial Encounter", "Witness: Marcus Johnson"
    
    # Contents
    statement_ids: list[str] = []  # Links to AtomicStatement.id
    
    # Ordering
    temporal_anchor: Optional[str] = None  # "11:30 PM" or relative
    sequence_position: int = 0  # Order within narrative
    
    # Metadata
    primary_actor: Optional[str] = None  # Entity ID of main actor
    evidence_quality: float = 0.5  # 0=unreliable, 1=documented
```

### 2. CoreferenceChain

```python
class CoreferenceChain(BaseModel):
    """Links all mentions of the same entity across narrative."""
    
    id: str = Field(default_factory=lambda: f"coref_{uuid4().hex[:8]}")
    canonical_entity_id: str  # The Entity this refers to
    
    # All mentions (spans, pronouns, descriptors)
    mentions: list[MentionLink] = []
    
class MentionLink(BaseModel):
    """A single mention of an entity."""
    segment_id: str
    start_char: int
    end_char: int
    text: str
    mention_type: str  # "pronoun", "proper_name", "descriptor", "title"
```

### 3. TimelineEvent

```python
class TimelineEvent(BaseModel):
    """A temporally-anchored event."""
    
    id: str = Field(default_factory=lambda: f"tl_{uuid4().hex[:8]}")
    event_id: str  # Links to Event.id
    
    # Temporal information
    absolute_time: Optional[str] = None  # "11:30 PM"
    relative_time: Optional[str] = None  # "20 minutes later"
    temporal_relation: Optional[str] = None  # "before X", "during Y"
    
    # Sequence
    sequence_order: int = 0  # Computed order in timeline
    
    # Confidence
    time_confidence: float = 0.5
```

### 4. EvidenceClassification

```python
class EvidenceType(str, Enum):
    DIRECT_WITNESS = "direct_witness"  # Reporter saw/heard
    REPORTED = "reported"  # Someone told reporter
    PHYSICAL = "physical"  # Documented injury, etc.
    DOCUMENTARY = "documentary"  # Official records
    INFERENCE = "inference"  # Reporter's conclusion
    
class EvidenceClassification(BaseModel):
    """Evidence metadata for a statement."""
    
    statement_id: str
    evidence_type: EvidenceType
    source_entity_id: Optional[str] = None  # Who provided this info
    corroborating_ids: list[str] = []  # Other statements that support
    reliability_score: float = 0.5
```

---

## Updated TransformResult

```python
class TransformResult(BaseModel):
    # Existing fields...
    segments: list[Segment] = []
    spans: list[SemanticSpan] = []
    atomic_statements: list[AtomicStatement] = []
    entities: list[Entity] = []
    events: list[Event] = []
    
    # NEW: Semantic understanding
    statement_groups: list[StatementGroup] = []
    coreference_chains: list[CoreferenceChain] = []
    timeline: list[TimelineEvent] = []
    evidence_classifications: list[EvidenceClassification] = []
```

---

## New Pass Designs

### p35_coreference.py

**Purpose**: Link mentions across segments

**Algorithm**:
1. Collect all entity mentions from p32
2. Collect all pronouns from spaCy parse
3. For each pronoun:
   - Look back in recent_entities (recency-based)
   - Check gender/number agreement
   - Check syntactic constraints
4. Merge duplicate entity mentions:
   - "Officer Jenkins" + "Jenkins" + "he" → single chain

**Libraries**: Consider using neuralcoref or spaCy's native coref (v3.7+)

### p37_timeline.py

**Purpose**: Build temporal ordering

**Algorithm**:
1. Extract temporal markers:
   - Absolute: "11:30 PM", "January 15th"
   - Relative: "then", "after that", "20 minutes later"
   - Implicit: verb tense sequences
2. Detect temporal relationships:
   - "before X happened"
   - "while Y was going on"
   - "after Z"
3. Build DAG of temporal ordering
4. Assign sequence numbers

**Libraries**: Consider SUTime or custom temporal parser

### p38_group_statements.py

**Purpose**: Cluster related statements

**Algorithm**:
1. **Actor-based clustering**:
   - Group by primary entity (who is speaking/acting)
   - "What Jenkins did", "What Rodriguez did"
   
2. **Topic-based clustering**:
   - Semantic similarity via sentence embeddings
   - spaCy vectors or sentence-transformers
   
3. **Evidence-type clustering**:
   - Medical statements group together
   - Witness statements group together
   
4. **Timeline-based clustering**:
   - Events at same time group together

**Output**: Hierarchical groups with labels

### p39_classify_evidence.py

**Purpose**: Assess evidence reliability

**Algorithm**:
1. For each statement:
   - Is it first-person observation? → DIRECT_WITNESS
   - Is it "X told me..."? → REPORTED
   - Is it medical/official? → DOCUMENTARY
   - Is it "I think/believe"? → INFERENCE
   
2. Compute reliability:
   - Direct + corroborated = high
   - Reported + uncorroborated = low
   
3. Flag potential issues:
   - Contradictions
   - Impossible sequences
   - Unusual claims

---

## Structured Output (v3)

```json
{
  "summary": {
    "encounter_date": "January 15, 2026",
    "encounter_time": "approximately 11:30 PM",
    "location": "Corner of Main Street and Oak Avenue",
    "parties_involved": [
      {"role": "reporter", "label": "Reporter"},
      {"role": "authority", "label": "Officer Jenkins", "badge": "4821"},
      {"role": "authority", "label": "Officer Rodriguez", "badge": "5539"},
      {"role": "witness", "label": "Marcus Johnson"}
    ]
  },
  
  "evidence_groups": [
    {
      "type": "encounter_narrative",
      "title": "Initial Contact",
      "statements": [...],
      "timeline_position": 1
    },
    {
      "type": "witness_account",
      "title": "Marcus Johnson's Account", 
      "statements": [...],
      "evidence_quality": 0.8
    },
    {
      "type": "medical_documentation",
      "title": "Medical Evidence",
      "statements": [
        "Treated at St. Mary's Hospital by Dr. Amanda Foster",
        "Documented: bruises on both wrists, sprained left shoulder"
      ],
      "evidence_quality": 0.95
    }
  ],
  
  "timeline": [
    {"time": "11:30 PM", "event": "Police cruiser approached Reporter"},
    {"time": "11:31 PM", "event": "Officer Jenkins exited vehicle, yelled commands"},
    {"time": "~11:35 PM", "event": "Reporter handcuffed against patrol car"},
    {"time": "~11:55 PM", "event": "Sergeant Williams arrived"},
    {"time": "~12:00 AM", "event": "Reporter released without charges"}
  ]
}
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2)
1. Add new IR schema types (StatementGroup, etc.)
2. Create empty pass stubs (p35-p39)
3. Update TransformResult
4. Add to pipeline registration

### Phase 2: Coreference (Week 2-3)
1. Implement basic pronoun resolution
2. Implement entity mention merging
3. Build coreference chains
4. Update entity output with chains

### Phase 3: Grouping (Week 3-4)
1. Implement actor-based grouping
2. Implement evidence-type grouping
3. Add group labels
4. Update structured output

### Phase 4: Timeline (Week 4-5)
1. Extract temporal markers
2. Build temporal ordering
3. Assign sequence positions
4. Add timeline to output

### Phase 5: Evidence Classification (Week 5-6)
1. Implement evidence type detection
2. Compute reliability scores
3. Detect corroboration
4. Add to structured output

### Phase 6: Enhanced Rendering (Week 6+)
1. Group-aware prose rendering
2. Timeline-aware ordering
3. Evidence hierarchy display
4. GUI updates for new sections

---

## Dependencies & Tools

### Coreference
- **Option A**: spaCy + neuralcoref (older but simple)
- **Option B**: spaCy Coref (v3.7+ experimental)
- **Option C**: allennlp/coref-spanbert (heavy but accurate)

### Sentence Embeddings (for similarity)
- **Option A**: spaCy vectors (already have)
- **Option B**: sentence-transformers (more accurate, heavier)
- **Option C**: OpenAI embeddings (API call)

### Timeline Parsing
- **Custom**: Build on spaCy DATE/TIME entities
- **External**: SUTime (Java, requires setup)

---

## Questions for Discussion

1. **Coreference depth**: Full neural coref or simpler rule-based?
2. **Grouping strategy**: User-configurable or automatic?
3. **Timeline precision**: Exact times only or infer from order?
4. **Evidence scoring**: Binary or gradient reliability?
5. **Performance budget**: How much slower is acceptable?

---

## Success Metrics

After v3, the example input should produce:

1. **OBSERVATIONS**: 15+ (not just 1)
   - "I was terrified", "I froze", "I screamed"...
   
2. **ENTITIES**: Clean, no duplicates
   - Officer Jenkins (badge: 4821, role: AUTHORITY)
   - NOT: "4821" as separate entity
   
3. **LOCATIONS**: Only real places
   - Main Street, Oak Avenue, Riverside Cafe
   - NOT: "me", "their", "his"
   
4. **GROUPS**: 5-7 semantic clusters
   - Initial Encounter
   - Use of Force
   - Witness Accounts
   - Medical Documentation
   - Official Response
   
5. **TIMELINE**: Ordered events with times

---

*Document Version: 0.1*
*Author: NNRT Team*
