# V5 Architecture Plan: Proper Data Modeling

**Created:** 2026-01-15
**Status:** In Progress (Phases 1, 2 & 3 complete)
**Goal:** Address the 12 structural issues identified in the critical review

---

## Core Problem

V4 put classification logic in the **renderer** instead of the **data model**.
The result: mixing event/state/quote/source/assessment at render time.

V5 must:
1. Define proper **typed data structures** at extraction time
2. Enforce **actor/action/target** schema for events
3. Track **provenance** for all claims
4. Resolve **pronouns** to entities before rendering
5. Make the renderer **dumb** - it just formats, doesn't classify

---

## Proposed Data Model (V5 Core Types)

```python
# === ENTITIES ===
@dataclass
class Entity:
    id: str
    canonical_name: str  # "Officer Marcus Jenkins"
    mentions: list[str]  # ["Jenkins", "Officer Jenkins", "he"]
    role: EntityRole
    participation: Participation  # INCIDENT, POST_INCIDENT, MENTIONED_ONLY

class Participation(Enum):
    INCIDENT = "incident"           # Present at scene
    POST_INCIDENT = "post_incident" # Medical/legal/investigator
    MENTIONED_ONLY = "mentioned"    # Referenced but not present


# === EVENTS (Actor/Action/Target) ===
@dataclass
class Event:
    id: str
    actor_id: str         # Entity ID - WHO
    action: str           # Verb phrase - DID WHAT
    target_id: str | None # Entity ID or None - TO WHOM
    target_object: str | None  # Object if not entity
    
    # Qualifiers
    time_expression: str | None  # "at 11:30 PM"
    location: str | None
    
    # Epistemic
    source: Source          # Who reported this
    uncertainty: Uncertainty
    event_type: EventType   # PHYSICAL, VERBAL, MOVEMENT


# === STATEMENTS (Non-Event Content) ===
@dataclass
class Statement:
    id: str
    text: str
    statement_type: StatementType
    source: Source
    uncertainty: Uncertainty

class StatementType(Enum):
    STATE_ACUTE = "state_acute"          # Fear during incident
    STATE_INJURY = "state_injury"        # Physical after-effects
    STATE_PSYCHOLOGICAL = "state_psych"  # PTSD, anxiety
    STATE_SOCIOECONOMIC = "state_socio"  # Job loss, etc.
    
    LEGAL_ALLEGATION = "legal_allegation"  # Assault, false imprisonment
    INFERENCE = "inference"                 # "looking for trouble"
    CHARACTERIZATION = "characterization"   # "thug", "psychotic"
    
    QUOTE = "quote"                # Verbatim speech
    MEDICAL_FINDING = "medical"   # Dr. documented X
    ADMIN_ACTION = "admin"        # IA letter, complaint filed


# === SOURCE PROVENANCE ===
@dataclass
class Source:
    source_type: SourceType
    entity_id: str | None     # Who provided this
    document_id: str | None   # If from document
    confidence: float
    status: ProvenanceStatus

class SourceType(Enum):
    REPORTER = "reporter"         # Person filing report
    WITNESS = "witness"           # Third-party observer  
    DOCUMENT = "document"         # Letter, record
    MEDICAL_RECORD = "medical"    # ER records
    OFFICIAL = "official"         # Police, IA
    UNKNOWN = "unknown"

class ProvenanceStatus(Enum):
    VERIFIED = "verified"       # Corroborated
    MISSING = "missing"         # Needs provenance
    UNVERIFIABLE = "unverifiable"


# === QUOTES (Proper Attribution) ===
@dataclass
class Quote:
    speaker_id: str       # Entity ID
    text: str             # Raw quote, no outer quotes
    context: str | None   # "yelled", "whispered"
    source: Source


# === TEMPORAL ===
@dataclass
class TimeReference:
    type: TimeType
    value: str
    normalized: str | None  # ISO if absolute

class TimeType(Enum):
    ABSOLUTE = "absolute"     # "January 15, 2026, 11:30 PM"
    RELATIVE = "relative"     # "three months later"
    DURATION = "duration"     # "about 20 minutes"
    APPROXIMATE = "approx"    # "after dark"
```

---

## Implementation Phases

### Phase 1: Entity Model Refactor (PARTIES fix) ✅ COMPLETE
**Fixes issues: #1**

- [x] Add `Participation` enum to Entity model
- [x] Split entity extraction to categorize:
  - INCIDENT_PARTICIPANTS
  - POST_INCIDENT_PROFESSIONALS
  - MENTIONED_CONTACTS
- [x] Fix name normalization ("Officers Jenkins" → "Officer Jenkins")
- [x] Filter bare role labels (partner, suspect, manager) from output
- [x] Classify workplace contacts properly (Sarah Mitchell)

**Implementation notes (2026-01-15):**
- Added `Participation` enum with INCIDENT, POST_INCIDENT, MENTIONED_ONLY values
- Added `participation` field to Entity model
- Updated renderer to display three-tier PARTIES structure
- Added WORKPLACE_CONTACT role detection pattern for managers/coworkers
- Filter out bare role labels that aren't properly named entities

**Files modified:**
- `nnrt/ir/enums.py` - Added Participation enum
- `nnrt/ir/schema_v0_1.py` - Added participation field to Entity
- `nnrt/passes/p32_extract_entities.py` - WORKPLACE_CONTACT patterns
- `nnrt/render/structured.py` - Three-tier PARTIES rendering

**Actual effort:** ~1 hour


### Phase 2: Event Schema Enforcement ✅ COMPLETE
**Fixes issues: #3, #11**

- [x] Create Event dataclass with Actor/Action/Target
- [x] Modify spaCy extractor to populate all fields
- [x] Add pronoun resolution pass (he→Jenkins)
- [x] Enforce schema in renderer: `[ACTOR] [ACTION] [TARGET]`

**Implementation notes (2026-01-15):**
- Extended `EventExtractResult` with `action_verb`, `source_sentence` fields
- Extended `Event` IR with `actor_label`, `action_verb`, `target_label`, `target_object`
- Added pronoun resolution using `source_sentence` context matching
- Renderer now displays events as `[Actor] [action]` format
- Unresolved pronouns go to "EVENTS (ACTOR UNRESOLVED)" bucket
- Verbatim text extraction preserves negations, auxiliaries, word order

**Files modified:**
- `nnrt/nlp/interfaces.py` - Extended EventExtractResult
- `nnrt/nlp/backends/spacy_backend.py` - Full event extraction with V5 fields
- `nnrt/passes/p34_extract_events.py` - Pronoun resolution
- `nnrt/ir/schema_v0_1.py` - Extended Event model
- `nnrt/render/structured.py` - Schema-based event rendering

**Actual effort:** ~2 hours


### Phase 3: Statement Type Hierarchy ✅ COMPLETE
**Fixes issues: #5, #6, #7, #8**

- [x] Split SELF-REPORTED into 4 sub-buckets
- [x] Split REPORTER content into 3 sub-buckets:
  - CHARACTERIZATIONS (adjectives: thug, psychotic)
  - INFERENCES (intent: looking for trouble)
  - REPORTER-REPORTED EVENTS (factual claims)
- [x] Renamed REPORTED CLAIMS to LEGAL ALLEGATIONS
- [x] Updated all unit tests for new type names

**Implementation notes (2026-01-15):**
- Added `STATE_ACUTE_PATTERNS`, `STATE_INJURY_PATTERNS`, `STATE_PSYCHOLOGICAL_PATTERNS`, `STATE_SOCIOECONOMIC_PATTERNS`
- Added `CHARACTERIZATION_PATTERNS` (adjectives/insults) separate from `INFERENCE_PATTERNS` (intent)
- Updated `_classify_epistemic()` to return fine-grained sub-types
- Updated renderer to display 4 self-report sub-sections and 2 interpretation sub-sections
- Renamed "REPORTED CLAIMS" → "LEGAL ALLEGATIONS (as asserted by Reporter)"
- Renamed "REPORTER INTERPRETATIONS" → "REPORTER CHARACTERIZATIONS" + "REPORTER INFERENCES"

**New epistemic types:**
- `state_acute` - Fear during incident
- `state_injury` - Physical after-effects
- `state_psychological` - PTSD, anxiety
- `state_socioeconomic` - Job loss, lifestyle impact
- `characterization` - Subjective adjectives
- `inference` - Intent/motive claims

**Files modified:**
- `nnrt/passes/p27_epistemic_tag.py` - Pattern splitting and classification
- `nnrt/render/structured.py` - New section rendering
- `scripts/stress_test.py` - Updated expected types/sections
- `tests/test_p27_epistemic_tag.py` - Updated tests

**Actual effort:** ~1.5 hours


### Phase 4: Source Provenance Model
**Fixes issues: #4, #9**

- [ ] Create Source dataclass with provenance fields
- [ ] Track source for every Statement/Event
- [ ] Add ProvenanceStatus enum
- [ ] Render SOURCE-DERIVED with proper fields:
  ```
  Claim: ...
  Source: [type] [id]
  Status: missing provenance
  ```

**Files to modify:**
- `nnrt/core/types.py` - Source, ProvenanceStatus
- `nnrt/passes/p27b_attribute_statements.py` - Source tracking
- `nnrt/render/structured.py` - Provenance rendering

**Estimated effort:** 2-3 hours


### Phase 5: Quote Extraction Fix
**Fixes issues: #10**

- [ ] Create Quote dataclass with speaker attribution
- [ ] Fix nested quote handling
- [ ] Render as: `Speaker: Text` (no outer quotes)

**Files to modify:**
- `nnrt/core/types.py` - Quote dataclass
- `nnrt/nlp/backends/spacy_backend.py` - Quote extraction
- `nnrt/render/structured.py` - Quote rendering

**Estimated effort:** 2 hours


### Phase 6: Temporal Model
**Fixes issues: #2**

- [ ] Create TimeReference dataclass
- [ ] Extract and categorize time expressions
- [ ] Render REFERENCE DATA with:
  - INCIDENT_DATETIME
  - INCIDENT_LOCATION
  - SECONDARY_LOCATIONS
  - TIME_EXPRESSIONS

**Files to modify:**
- `nnrt/core/types.py` - TimeReference
- `nnrt/passes/p33_temporal.py` - Time extraction
- `nnrt/render/structured.py` - Time rendering

**Estimated effort:** 2 hours


### Phase 7: Renderer Cleanup
**Fixes issues: #12**

- [ ] Remove classification logic from renderer
- [ ] Rename FULL NARRATIVE to `RAW_NEUTRALIZED_NARRATIVE (AUTO)`
- [ ] Fix grammar issues in neutralization passes
- [ ] Make renderer strictly format, not classify

**Files to modify:**
- `nnrt/render/structured.py` - Simplify
- `nnrt/passes/p50_neutralize.py` - Fix grammar

**Estimated effort:** 2 hours

---

## Priority Order

Based on impact and dependencies:

1. **Phase 2: Event Schema** (biggest correctness win)
2. **Phase 3: Statement Hierarchy** (fixes overlap/leakage)
3. **Phase 1: Entity Model** (fixes PARTIES)
4. **Phase 4: Provenance** (enables verification)
5. **Phase 5: Quotes** (cleaner output)
6. **Phase 6: Temporal** (reference data quality)
7. **Phase 7: Renderer** (polish)

---

## Success Criteria

After V5:

- [ ] Every event has: Actor + Action + Target (optional)
- [ ] No pronouns in output - all resolved to entity names
- [ ] No fragments - every line is a complete statement
- [ ] No bucket leakage - types are mutually exclusive
- [ ] All claims have source provenance (even if "missing")
- [ ] Quotes attributed with speaker labels
- [ ] Time expressions normalized or labeled
- [ ] Renderer has zero classification logic

---

## Test Strategy

- [ ] Update stress test for new sections
- [ ] Add schema validation tests (event has actor)
- [ ] Add pronoun resolution tests
- [ ] Add provenance completeness tests
- [ ] Add mutual exclusivity tests (no overlap between buckets)
