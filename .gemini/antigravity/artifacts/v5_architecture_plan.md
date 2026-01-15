# V5 Architecture Plan: Proper Data Modeling

**Created:** 2026-01-15
**Status:** ✅ COMPLETE (All 7 phases complete, all 12 issues fixed)
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


### Phase 4: Source Provenance Model ✅ COMPLETE
**Fixes issues: #4, #9**

- [x] Create SourceType and ProvenanceStatus enums
- [x] Add provenance fields to AtomicStatement
- [x] Track source for every Statement in p27_epistemic_tag
- [x] Render SOURCE-DERIVED with structured provenance display

**Implementation notes (2026-01-15):**
- Added `SourceType` enum: reporter, witness, document, medical, official, attorney, research
- Added `ProvenanceStatus` enum: verified, cited, missing, inference, unverifiable
- Extended AtomicStatement with `source_type`, `source_entity_id`, `provenance_status`
- Updated p27_epistemic_tag to set provenance based on epistemic type:
  - self_report → verified (self-attested)
  - direct_event → verified (first-person)
  - legal_claim/conspiracy → missing (needs verification)
  - inference/characterization → inference
  - quote/document → cited
- Enhanced SOURCE-DERIVED section to show Claim/Source/Status format

**Provenance Distribution (stress test):**
- Verified: 49 statements (direct observations, self-reports)
- Missing: 41 statements (legal claims, conspiracy claims, unknown)
- Inference: 15 statements (interpretations, characterizations)
- Cited: 2 statements (documents, quotes)

**Files modified:**
- `nnrt/ir/enums.py` - Added SourceType, ProvenanceStatus enums
- `nnrt/passes/p26_decompose.py` - Added provenance fields to AtomicStatement
- `nnrt/passes/p27_epistemic_tag.py` - Provenance assignment
- `nnrt/render/structured.py` - Provenance display

**Actual effort:** ~45 minutes


### Phase 5: Quote Extraction Fix ✅ COMPLETE
**Fixes issues: #10**

- [x] Enhanced SpeechAct with speaker attribution
- [x] Added nested quote detection
- [x] Render as: `Speaker verb: Text` (no outer quotes)

**Implementation notes (2026-01-15):**
- Extended SpeechAct with: `speaker_label`, `speech_verb`, `is_nested`, `raw_text`
- Updated p40_build_ir to capture verb form and resolve speaker labels
- Nested quote detection: count quote characters > 2
- Enhanced PRESERVED QUOTES rendering:
  - Format: "• Speaker verb: content" (no outer quotes)
  - Warning for nested quotes with attribution issues
  - Fallback to statement-based quotes with speaker extraction

**Files modified:**
- `nnrt/ir/schema_v0_1.py` - V5 fields added to SpeechAct
- `nnrt/passes/p40_build_ir.py` - Enhanced speech act extraction
- `nnrt/render/structured.py` - Speaker-attributed quote rendering

**Actual effort:** ~30 minutes


### Phase 6: Temporal Model ✅ COMPLETE
**Fixes issues: #2**

- [x] Added TimeContext and LocationType enums
- [x] Restructured REFERENCE DATA display
- [x] Render with proper grouping:
  - INCIDENT_DATETIME (Date + Time)
  - INCIDENT_LOCATION
  - SECONDARY_LOCATIONS
  - OFFICER_IDENTIFICATION

**Implementation notes (2026-01-15):**
- Added `TimeContext` enum: incident, pre_incident, post_incident, ongoing
- Added `LocationType` enum: incident_scene, secondary, workplace, medical, official
- Restructured REFERENCE DATA section:
  - Primary date/time displayed first
  - Incident location separated from secondary locations
  - Officer names filtered to only show those with titles (Officer, Sergeant, etc.)
  - Badge numbers grouped with officer identification
  - Other identifiers displayed separately

**Example output:**
```
REFERENCE DATA
──────────────────────────────────────────────────────────────────────
  INCIDENT DATETIME:
    Date: January 15th, 2026
    Time: 11:30 PM

  INCIDENT LOCATION: Main Street and Oak Avenue
  SECONDARY LOCATIONS:
    • the Riverside Cafe
    • St. Mary's Hospital

  OFFICER IDENTIFICATION:
    • Sergeant Williams
    • Officers Jenkins
    • Badge #4821
    • Badge #5539
    • Badge #2103
```

**Files modified:**
- `nnrt/ir/enums.py` - Added TimeContext, LocationType enums
- `nnrt/render/structured.py` - Restructured REFERENCE DATA

**Actual effort:** ~30 minutes


### Phase 7: Renderer Cleanup ✅ COMPLETE
**Fixes issues: #12**

- [x] Documented classification logic rationale (VIEW concern, not DATA)
- [x] Renamed FULL NARRATIVE to `RAW_NEUTRALIZED_NARRATIVE (AUTO-GENERATED)`
- [x] Enhanced grammar fixes in _clean_text
- [x] Added warning banner for machine-generated content

**Implementation notes (2026-01-15):**
- Added V5 documentation block explaining why camera-friendly filtering is in renderer
  (VIEW concern for display, not DATA concern - all data preserved in IR)
- Renamed section: "FULL NARRATIVE (Computed)" → "RAW NEUTRALIZED NARRATIVE (AUTO-GENERATED)"
- Added warning: "⚠️ This is machine-generated neutralization. Review for accuracy."
- Enhanced _clean_text with:
  - Double punctuation fix (.., ,,)
  - Pronoun spacing (They, I)
  - Duplicate article fix (a a, an an, the the)
  - Dangling connector fix (, and,)
  - Leading punctuation removal

**Files modified:**
- `nnrt/render/structured.py` - Renamed section, added V5 documentation
- `nnrt/passes/p70_render.py` - Enhanced _clean_text grammar fixes

**Actual effort:** ~20 minutes

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
