# NNRT v3 Implementation Plan — Clean Architecture Approach

**Date**: 2026-01-15
**Philosophy**: Infrastructure first, test-driven, incremental validation

---

## The "Clean and Perfect" Approach

### Phase 0: Deep Analysis (Before Any Code)

To get v3 right the first time, we need to understand:

1. **What data exists at each pipeline stage?**
   - What does each pass produce?
   - What can each new pass consume?
   - What are the data dependencies?

2. **What are the semantic boundaries?**
   - Where does "understanding" end and "transformation" begin?
   - What should be computed once vs. derived on-demand?

3. **What are the interface contracts?**
   - What does each new pass promise to produce?
   - What invariants must be maintained?

---

## Current Pipeline Data Flow Analysis

```
Input Text
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ p00_normalize                                                        │
│   INPUT:  raw text                                                   │
│   OUTPUT: cleaned text (encoding normalized)                         │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ p10_segment                                                          │
│   INPUT:  cleaned text                                               │
│   OUTPUT: ctx.segments = [Segment]                                   │
│           Each segment has: id, text, start_char, end_char           │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ p20_tag_spans                                                        │
│   INPUT:  ctx.segments                                               │
│   OUTPUT: ctx.spans = [SemanticSpan]                                 │
│           Spans: intent_attribution, legal_conclusion, etc.          │
│           Each span linked to segment_id                             │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ p22_classify_statements                                              │
│   INPUT:  ctx.segments                                               │
│   OUTPUT: segment.statement_type = observation|claim|interpretation  │
│           segment.statement_confidence = 0.0-1.0                     │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ p25_annotate_context                                                 │
│   INPUT:  ctx.segments, ctx.spans                                    │
│   OUTPUT: segment.contexts = ["timeline", "direct_quote", etc.]      │
│           ctx.uncertainty = [UncertaintyMarker]                      │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ p26_decompose                                                        │
│   INPUT:  ctx.segments                                               │
│   OUTPUT: ctx.atomic_statements = [AtomicStatement]                  │
│           Each atomic has: id, text, segment_id, clause_type         │
│           CRITICAL: This is where we get individual facts            │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ p27_classify_atomic                                                  │
│   INPUT:  ctx.atomic_statements                                      │
│   OUTPUT: atomic.type_hint = observation|claim|interpretation|quote  │
│           atomic.confidence, atomic.flags                            │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ p28_link_provenance                                                  │
│   INPUT:  ctx.atomic_statements                                      │
│   OUTPUT: atomic.derived_from = [stmt_id, ...]                       │
│           Links interpretations to source observations               │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ p30_extract_identifiers                                              │
│   INPUT:  ctx.segments                                               │
│   OUTPUT: ctx.identifiers = [Identifier]                             │
│           Types: badge_number, date, time, location, name            │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ p32_extract_entities                                                 │
│   INPUT:  ctx.segments, ctx.identifiers                              │
│   OUTPUT: ctx.entities = [Entity]                                    │
│           Roles: reporter, authority, witness, subject               │
│           Has: mentions (span IDs)                                   │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ p34_extract_events                                                   │
│   INPUT:  ctx.segments, ctx.entities                                 │
│   OUTPUT: ctx.events = [Event]                                       │
│           Types: action, verbal, movement                            │
│           Has: actor_id, target_id, description                      │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ p40_build_ir                                                         │
│   INPUT:  all above                                                  │
│   OUTPUT: ctx.speech_acts (optional), validation                     │
│           Assembles final IR structure                               │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  │ ← ★ NEW PASSES INSERT HERE ★
                                  │
┌─────────────────────────────────────────────────────────────────────┐
│ p50_policy → p80_package (transformation & output)                   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Where Do New Passes Fit?

The new semantic understanding passes should go **after extraction, before policy**:

```
p40_build_ir
    │
    ▼
┌── p42_coreference ──┐   ← Link "he/she" to entities
│                       │
├── p44_timeline ──────┤   ← Order events temporally
│                       │
├── p46_group_statements┤   ← Cluster related statements
│                       │
└── p48_classify_evidence┘   ← Assess reliability
    │
    ▼
p50_policy
```

**Why here?**
1. All raw extraction is complete (entities, events, identifiers)
2. We have atomic statements with classifications
3. We haven't started transformation yet
4. Groups and timeline can inform rendering order

---

## IR Schema Additions — Precise Definitions

### 1. CoreferenceChain

```python
class MentionType(str, Enum):
    """How an entity is mentioned in text."""
    PROPER_NAME = "proper_name"    # "Officer Jenkins"
    PRONOUN = "pronoun"            # "he", "she", "they"
    DESCRIPTOR = "descriptor"      # "the officer", "the man"
    TITLE = "title"                # "Jenkins", "Officer"

class Mention(BaseModel):
    """A single mention of an entity in the narrative."""
    
    id: str = Field(default_factory=lambda: f"m_{uuid4().hex[:8]}")
    
    # Location
    segment_id: str
    start_char: int
    end_char: int
    text: str
    
    # Classification
    mention_type: MentionType
    
    # Resolution
    resolved_entity_id: Optional[str] = None  # Which entity this refers to
    resolution_confidence: float = 0.0

class CoreferenceChain(BaseModel):
    """All mentions that refer to the same entity."""
    
    id: str = Field(default_factory=lambda: f"coref_{uuid4().hex[:8]}")
    
    # The canonical entity
    entity_id: str
    
    # All mentions (in narrative order)
    mention_ids: list[str] = []
    
    # Chain confidence (how sure are we these all refer to same entity?)
    confidence: float = 0.5
```

### 2. StatementGroup

```python
class GroupType(str, Enum):
    """Semantic category of a statement group."""
    ENCOUNTER = "encounter"              # What happened during the incident
    WITNESS_ACCOUNT = "witness_account"  # What a witness reported
    MEDICAL = "medical"                  # Medical treatment/evidence
    OFFICIAL = "official"                # Official records, complaints
    EMOTIONAL = "emotional"              # Psychological impact
    BACKGROUND = "background"            # Context before incident
    AFTERMATH = "aftermath"              # Events after incident

class StatementGroup(BaseModel):
    """A semantic cluster of related statements."""
    
    id: str = Field(default_factory=lambda: f"grp_{uuid4().hex[:8]}")
    
    # Classification
    group_type: GroupType
    title: str  # Human-readable: "Initial Contact", "Marcus Johnson's Account"
    
    # Contents (ordered by narrative position)
    statement_ids: list[str] = []  # Links to AtomicStatement.id
    
    # Primary actor (if applicable)
    primary_entity_id: Optional[str] = None
    
    # Temporal anchor
    temporal_anchor: Optional[str] = None  # "11:30 PM"
    sequence_in_narrative: int = 0  # Order this group appears
    
    # Quality
    evidence_strength: float = 0.5  # 0=weak, 1=documented
```

### 3. TimelineEntry

```python
class TemporalRelation(str, Enum):
    """How events relate temporally."""
    BEFORE = "before"
    AFTER = "after"
    DURING = "during"
    SIMULTANEOUS = "simultaneous"
    UNKNOWN = "unknown"

class TimelineEntry(BaseModel):
    """A temporally-positioned element."""
    
    id: str = Field(default_factory=lambda: f"tl_{uuid4().hex[:8]}")
    
    # What this entry represents
    event_id: Optional[str] = None  # Link to Event
    statement_id: Optional[str] = None  # Or link to AtomicStatement
    
    # Time information
    absolute_time: Optional[str] = None  # "11:30 PM"
    relative_time: Optional[str] = None  # "20 minutes later"
    date: Optional[str] = None  # "January 15th, 2026"
    
    # Ordering
    sequence_order: int = 0  # Computed order in timeline
    confidence: float = 0.5
    
    # Relations
    before_ids: list[str] = []  # Timeline entries that come before
    after_ids: list[str] = []   # Timeline entries that come after
```

### 4. EvidenceClassification

```python
class EvidenceType(str, Enum):
    """Source/reliability of evidence."""
    DIRECT_WITNESS = "direct_witness"  # Reporter saw/experienced
    REPORTED = "reported"              # Someone told reporter
    DOCUMENTARY = "documentary"        # Official records
    PHYSICAL = "physical"              # Physical evidence (injuries, etc.)
    INFERENCE = "inference"            # Reporter's conclusion

class EvidenceClassification(BaseModel):
    """Evidence metadata for a statement."""
    
    statement_id: str
    
    # Classification
    evidence_type: EvidenceType
    
    # Source
    source_entity_id: Optional[str] = None  # Who provided this
    
    # Corroboration
    corroborating_ids: list[str] = []  # Other statements that support
    contradicting_ids: list[str] = []  # Statements that conflict
    
    # Quality
    reliability: float = 0.5  # 0=unreliable, 1=documented
```

---

## Implementation Order (Dependency-Driven)

```
Week 1: Schema Foundation ✅ COMPLETE
├── Add all new models to schema_v0_1.py ✅
├── Add fields to TransformContext ✅
├── Add fields to TransformResult ✅
└── Write schema tests ✅ (19 tests passing)

Week 2: p42_coreference ✅ COMPLETE
├── Collect all pronouns from spaCy ✅
├── Collect all entity mentions ✅ (exhaustive text search + spaCy NER)
├── Rule-based pronoun resolution ✅ (recency + gender agreement)
├── Build CoreferenceChains ✅
└── Write coreference tests ✅ (11 tests passing)

Week 3: p44_timeline ✅ COMPLETE
├── Extract temporal markers (from identifiers) ✅
├── Extract relative time phrases ✅ ("then", "later", "the next day", "X minutes later")
├── Build ordering DAG ✅ (narrative order primary, times as anchors)
├── Assign sequence numbers ✅
└── Write timeline tests ✅ (12 tests passing)

Week 4: p46_group_statements
├── Group by actor (who is primary subject)
├── Group by topic (semantic clustering)
├── Group by evidence type
├── Assign group titles
└── Write grouping tests

Week 5: p48_classify_evidence
├── Classify each statement by evidence type
├── Compute reliability scores
├── Detect corroboration/contradiction
└── Write evidence tests

Week 6: Integration
├── Update structured output
├── Update GUI rendering
├── End-to-end testing
└── Documentation
```

---

## Test-Driven Development: Example Tests

```python
# tests/test_coreference.py

def test_pronoun_resolution_basic():
    """Pronouns should resolve to nearest matching entity."""
    text = "Officer Jenkins grabbed my arm. He then pushed me."
    
    result = transform(text)
    
    # "He" should resolve to "Officer Jenkins"
    chain = result.coreference_chains[0]
    assert "Officer Jenkins" in chain.mentions
    assert "He" in chain.mentions

def test_coreference_gender_agreement():
    """Pronouns should match entity gender."""
    text = "Officer Jenkins arrested John. She was aggressive."
    
    result = transform(text)
    
    # "She" should NOT resolve to "John"
    john_chain = find_chain_for("John", result)
    assert "She" not in john_chain.mentions

# tests/test_grouping.py

def test_medical_statements_grouped():
    """Medical statements should be in MEDICAL group."""
    text = "Dr. Foster treated my injuries. She documented bruises."
    
    result = transform(text)
    
    medical_group = find_group_by_type(GroupType.MEDICAL, result)
    assert len(medical_group.statement_ids) >= 2

def test_witness_statements_grouped():
    """Each witness's statements should be grouped."""
    text = "Marcus saw the incident. He started recording."
    
    result = transform(text)
    
    witness_group = find_group_by_type(GroupType.WITNESS_ACCOUNT, result)
    assert witness_group.primary_entity_id is not None
```

---

## Decision Points (Require Your Input)

### 1. Coreference Scope
- **Option A**: Only resolve pronouns to named entities
- **Option B**: Also resolve descriptors ("the officer" → Jenkins)
- **Recommendation**: A first, then expand to B

### 2. Timeline Granularity
- **Option A**: Only events with explicit times
- **Option B**: All events, infer order from narrative
- **Recommendation**: Both, with confidence flags

### 3. Grouping Algorithm
- **Option A**: Rule-based (keywords, actors)
- **Option B**: Embedding similarity clustering
- **Recommendation**: A first (simpler, debuggable)

### 4. Evidence Source Tracking
- **Option A**: Binary (direct vs. reported)
- **Option B**: Full provenance chain
- **Recommendation**: B (more useful for legal)

---

## Files to Create/Modify

### New Files
```
nnrt/passes/p42_coreference.py
nnrt/passes/p44_timeline.py
nnrt/passes/p46_group_statements.py
nnrt/passes/p48_classify_evidence.py

tests/passes/test_coreference.py
tests/passes/test_timeline.py
tests/passes/test_grouping.py
tests/passes/test_evidence.py
```

### Modified Files
```
nnrt/ir/schema_v0_1.py          # Add new models
nnrt/core/context.py            # Add new fields to TransformContext
nnrt/cli/main.py                # Register new passes
nnrt/output/structured.py       # Add new sections to output
web/server.py                   # Include new data in response
web/app.js                      # Render new sections
```

---

## Success Criteria

After v3, the example input should produce:

### Coreference
```
Chain 1: "Officer Jenkins" → "Jenkins" → "he" (3 mentions)
Chain 2: "Marcus Johnson" → "Marcus" → "he" (2 mentions)  
Chain 3: "Reporter" → "I" → "me" → "my" (many mentions)
```

### Groups
```
Group 1: "Initial Encounter" (type=ENCOUNTER)
  - Police cruiser approached
  - Officer Jenkins exited vehicle
  - Jenkins yelled commands

Group 2: "Marcus Johnson's Account" (type=WITNESS_ACCOUNT)
  - Marcus witnessed the assault
  - Marcus started recording

Group 3: "Medical Documentation" (type=MEDICAL)
  - Treated at St. Mary's Hospital
  - Dr. Foster documented injuries
```

### Timeline
```
1. [11:30 PM] Police cruiser approached
2. [11:31 PM] Officer Jenkins exited, yelled
3. [~11:35 PM] Reporter handcuffed
4. [~11:55 PM] Sergeant Williams arrived
5. [~12:00 AM] Reporter released
6. [Next day] Filed complaint with IA
7. [3 months later] Received "within policy" letter
```

---

*Document Version: 1.0*
*Status: Ready for Implementation*
