# NNRT V4 Remediation Plan — Critical Fixes

**Based on stress test analysis: January 15, 2026**

---

## Executive Summary

The stress test narrative exposed fundamental issues in NNRT's extraction and classification pipeline. This document outlines specific failures and their required fixes.

---

## 1. ENTITY EXTRACTION FAILURES

### 1.1 Current Output (BROKEN)

```
[reporter    ] person       | Reporter
[authority   ] person       | 4821        ← WRONG: Badge number as person
[authority   ] person       | Jenkins     ← OK
[authority   ] person       | 5539        ← WRONG: Badge number as person
[authority   ] person       | Sarah Mitchell  ← WRONG: She's a manager
[witness     ] person       | Marcus Johnson  ← OK
[witness     ] person       | Patricia Chen   ← OK
[authority   ] person       | 2103        ← WRONG: Badge number as person
[authority   ] person       | Sergeant Williams ← OK
[authority   ] person       | Amanda Foster    ← WRONG: She's medical
[authority   ] person       | Sarah Monroe     ← OK (IA investigator)
[authority   ] person       | Michael Thompson ← WRONG: He's a therapist
[authority   ] person       | Officers Jenkins ← WRONG: Duplicate of Jenkins
[authority   ] person       | Jennifer Walsh   ← WRONG: She's an attorney
[authority   ] person       | Officer     ← WRONG: Title, not entity
[authority   ] person       | partner     ← WRONG: Role, not entity
[authority   ] person       | passenger   ← WRONG: Role, not entity
[authority   ] person       | suspect     ← WRONG: Role, not entity
[authority   ] person       | manager     ← WRONG: Role, not entity
[authority   ] person       | sergeant    ← WRONG: Title, not entity
[authority   ] person       | Detective   ← WRONG: Title, not entity
[authority   ] person       | male        ← WRONG: Descriptor, not entity
```

### 1.2 Required Entity Taxonomy

```python
class EntityRole(str, Enum):
    REPORTER = "reporter"              # The narrative author (I/me/my)
    SUBJECT_OFFICER = "subject_officer" # Officers being described
    WITNESS_CIVILIAN = "witness_civilian" # Third-party observers
    WITNESS_OFFICIAL = "witness_official" # Other officers present
    MEDICAL_PROVIDER = "medical_provider" # Doctors, nurses, EMTs
    LEGAL_COUNSEL = "legal_counsel"     # Attorneys
    INVESTIGATOR = "investigator"       # IA, oversight
    SUPERVISOR = "supervisor"           # Sergeants, commanding officers
    WORKPLACE_CONTACT = "workplace_contact" # Managers, coworkers
    INSTITUTION = "institution"         # Departments, hospitals
    UNKNOWN = "unknown"

class EntityType(str, Enum):
    PERSON = "person"                   # Named individuals only
    BADGE_NUMBER = "badge_number"       # Attached to person entities
    ORGANIZATION = "organization"       # City PD, Internal Affairs Division
    FACILITY = "facility"               # St. Mary's Hospital
    TITLE = "title"                     # "Officer", "Detective" (NOT entity)
    DESCRIPTOR = "descriptor"           # "male", "partner" (NOT entity)
```

### 1.3 Correct Output

```
PERSON (subject_officer)  | Officer Jenkins
  └── BADGE: 4821
PERSON (subject_officer)  | Officer Rodriguez
  └── BADGE: 5539
PERSON (supervisor)       | Sergeant Williams
  └── BADGE: 2103
PERSON (witness_civilian) | Marcus Johnson
PERSON (witness_civilian) | Mrs. Patricia Chen
PERSON (workplace_contact)| Sarah Mitchell
PERSON (medical_provider) | Dr. Amanda Foster
PERSON (medical_provider) | Dr. Michael Thompson
PERSON (investigator)     | Detective Sarah Monroe
PERSON (legal_counsel)    | Jennifer Walsh
ORGANIZATION              | City Police Department
ORGANIZATION              | Internal Affairs Division
ORGANIZATION              | Civil Rights Legal Foundation
FACILITY                  | St. Mary's Hospital
FACILITY                  | Riverside Cafe
```

### 1.4 Fix Required

✅ **COMPLETED (V4 Phase 1)** - `p32_extract_entities.py` updated:

- ✅ Reject bare titles ("Officer", "Detective", "sergeant")
- ✅ Reject descriptors ("male", "female")
- ✅ Badge numbers no longer extracted as person entities
- ✅ Role-based references ("partner", "manager") tracked as contextual entities
- ✅ New role taxonomy: SUBJECT_OFFICER, SUPERVISOR, MEDICAL_PROVIDER, LEGAL_COUNSEL, INVESTIGATOR
- ⏳ Merge badge numbers with their officers (future)
- ⏳ Combine "Officer Jenkins" when spaCy extracts separately (future)

---

## 2. IDENTIFIER EXTRACTION FAILURES

### 2.1 Current Time Output (BROKEN)

```
[time      ] 11:30 PM     ← OK
[time      ] 30 PM        ← WRONG: Parsing artifact
[time      ] 11:30 PM     ← DUPLICATE
[time      ] hours        ← WRONG: Duration descriptor
[time      ] about 20 minutes ← Should be DURATION type
[time      ] night        ← WRONG: Vague temporal
[time      ] night        ← DUPLICATE
```

### 2.2 Required Temporal Types

```python
class TemporalType(str, Enum):
    TIMESTAMP = "timestamp"     # 11:30 PM
    DATE = "date"               # January 15th, 2026
    DURATION = "duration"       # about 20 minutes
    RELATIVE = "relative"       # next day, three months later
    VAGUE = "vague"             # night, hours (low confidence)
```

### 2.3 Current Date Output (BROKEN)

```
[date      ] January 15th, 2026  ← OK
[date      ] today               ← WRONG: Not a date marker
[date      ] 40s                 ← WRONG: Age range
[date      ] next day            ← Should be RELATIVE type
[date      ] Three months later  ← Should be RELATIVE type
```

### 2.4 Location Output (BROKEN)

```
[location  ] Main Street and Oak Avenue  ← OK
[location  ] Riverside Cafe              ← OK (should be WORKPLACE)
[location  ] Marcus                      ← WRONG: Person name
[location  ] Officers Jenkins            ← WRONG: Person name
[location  ] St. Mary's Hospital         ← OK (should be MEDICAL_FACILITY)
```

### 2.5 Fix Required

✅ **COMPLETED (V4 Phase 2)** - `p30_extract_identifiers.py` updated:

- ✅ Reject parsing artifacts ("30 PM") via `_is_valid_time()` validation
- ✅ Reject age decade patterns ("40s") as dates
- ✅ Add deduplication via `_deduplicate_identifiers()`
- ✅ Confidence-adjusted for vague temporal markers ("night", "hours")
- ⏳ Add DURATION type classification (future)
- ⏳ Fix person names appearing in locations (NER limitation)

---

## 3. STATEMENT CLASSIFICATION FAILURES

### 3.1 Current INFERENCE Bucket Contains Intent Attribution

These are classified as INFERENCE but should be REPORTER_INTERPRETATION:

```
- "The thug cop behind the wheel was clearly looking for trouble"
- "he wanted to inflict maximum damage"
- "clearly enjoying my suffering"
- "it was obvious they were conspiring"
- "which proves they are hiding even more evidence"
```

### 3.2 Current DIRECT_WITNESS Contains Conclusions

These are classified as DIRECT_WITNESS but are actually LEGAL_CHARACTERIZATION:

```
- "This was clearly racial profiling and harassment"
- "This is clearly obstruction of justice"
- "This is an obvious whitewash and cover-up"
```

### 3.3 Required Epistemic Classification

```python
class EpistemicType(str, Enum):
    # Directly observable
    DIRECT_OBSERVATION = "direct_observation"     # "He grabbed my arm"
    SENSORY_EXPERIENCE = "sensory_experience"     # "I felt pain"
    
    # Self-reported internal states
    EMOTIONAL_STATE = "emotional_state"           # "I was terrified"
    PHYSICAL_SYMPTOM = "physical_symptom"         # "My wrists were bleeding"
    
    # Reporter's conclusions
    INFERENCE = "inference"                       # "she wasn't going to do anything"
    INTENT_ATTRIBUTION = "intent_attribution"     # "he wanted to inflict damage" ⚠️
    LEGAL_CHARACTERIZATION = "legal_characterization"  # "racial profiling" ⚠️
    
    # From other sources
    REPORTED_SPEECH = "reported_speech"           # "He said 'You can go'"
    DOCUMENT_CLAIM = "document_claim"             # "The medical report shows"
    WITNESS_CLAIM = "witness_claim"               # "Marcus said he saw"
    
    # Discardable
    NARRATIVE_GLUE = "narrative_glue"             # "It all started", "Out of nowhere"
    RHETORICAL = "rhetorical"                     # "which proves", "obviously"
```

### 3.4 Intent Attribution Must Be Flagged

These phrases MUST be tagged as INTENT_ATTRIBUTION (not neutral):

```python
INTENT_PATTERNS = [
    r"clearly (looking for|wanting|trying to|ready to)",
    r"(wanted|intended|meant) to (inflict|hurt|harm|damage)",
    r"(obviously|clearly) (didn't care|enjoying|conspiring)",
    r"it was (obvious|clear) they were",
    r"which proves",
    r"designed to (protect|harm|cover)",
]
```

### 3.5 Fix Status

✅ **COMPLETED (V4 Phase 3)** - `p48_classify_evidence.py` updated:

- ✅ Added `EpistemicType` enum to `nnrt/ir/enums.py`
- ✅ Added `_classify_epistemic_type()` function with pattern matching
- ✅ Added `classify_epistemic_v4()` integrated into evidence classification
- ✅ Detects and flags INTENT_ATTRIBUTION (7 in stress test)
- ✅ Detects and flags LEGAL_CHARACTERIZATION (4 in stress test)
- ✅ Detects and flags CONSPIRACY_CLAIM (4 in stress test)
- ✅ Adds V4-prefixed diagnostics for each detection

## 4. QUOTE EXTRACTION FAILURES

### 4.1 Current Output (CONTAMINATED)

```
- I asked "Am I being charged with anything?"     ← Has narrative wrapper
- He said "Sure you did, that's what they all say." ← Has narrative wrapper
- She said my injuries were consistent with "significant physical force"  ← Mixed
```

### 4.2 Required Quote Structure

```python
class ExtractedQuote:
    speaker_id: Optional[str]       # Entity ID
    speaker_label: Optional[str]    # "Officer Jenkins"
    speaker_role: Optional[str]     # "subject_officer"
    quote_text: str                 # ONLY the quoted words
    attribution_verb: str           # "said", "yelled", "whispered"
    attribution_confidence: float
    surrounding_context: str        # Narrative wrapper (separate)
```

### 4.3 Correct Output

```
Speaker: Officer Jenkins (subject_officer)
Quote: "STOP RIGHT THERE! DON'T YOU DARE MOVE!"
Attribution: yelled
Context: Officer Jenkins jumped out of the car and immediately started screaming at me.

Speaker: Reporter
Quote: "What's the problem, officer? I haven't done anything wrong."
Attribution: asked politely
Context: I asked him politely...
```

---

## 5. EVENT EXTRACTION FAILURES

### 5.1 Current Output (BROKEN)

```
Timeline shows:
  0. [hours          ] brutal attacked me       ← WRONG: "hours" is not time
  1. [(implied)      ] It started               ← WRONG: Narrative glue
  2. [(implied)      ] I walking                ← WRONG: Fragment
  6. [(implied)      ] cop looking              ← WRONG: Contains "cop" slur
```

### 5.2 Option A: Kill Event Extraction Until Fixed

```python
# In build_timeline and extract_events:
events: list[Event] = []  # Empty until properly structured
timeline: list[TimelineEntry] = []  # Empty until fixed
```

### 5.3 Option B: Proper Event Model

```python
class StructuredEvent:
    event_type: EventType
    actor_id: str                    # Entity ID
    target_id: Optional[str]         # Entity ID
    action_verb: str                 # "grabbed", "searched", "handcuffed"
    temporal_ref: Optional[str]      # "11:30 PM", "about 20 minutes later"
    location_ref: Optional[str]      # "near the patrol car"
    evidence_type: EvidenceType      # DIRECT_OBSERVATION, QUOTE, etc.
    confidence: float

class EventType(str, Enum):
    APPROACH = "approach"
    VERBAL_COMMAND = "verbal_command"
    PHYSICAL_RESTRAINT = "physical_restraint"
    SEARCH = "search"
    HANDCUFF = "handcuff"
    VEHICLE_STOP = "vehicle_stop"
    WITNESS_RECORDING = "witness_recording"
    WITNESS_INTERFERENCE = "witness_interference"
    MEDICAL_TREATMENT = "medical_treatment"
    COMPLAINT_FILED = "complaint_filed"
    RELEASE = "release"
    INVESTIGATION_OUTCOME = "investigation_outcome"
```

---

## 6. COREFERENCE CHAIN FAILURES

### 6.1 Current Output (ERRORS)

```
Jenkins: ['Jenkins', 'him', 'Jenkins', 'Jenkins', 'Jenkins', 'Jenkins', 'their', 'Jenkins']
  ← "their" likely wrong

Sergeant Williams: ['Sergeant Williams', 'He', 'She', 'She', 'Sergeant Williams']
  ← "She" wrong (Williams is male based on context)

Michael Thompson: ['Michael Thompson', 'him', 'they', 'his']
  ← "they" likely wrong
```

### 6.2 Fix Required

- **p42_coreference.py**:
  - Add gender consistency checking
  - Don't resolve "they" to single individuals
  - Add positional constraints (pronouns resolve to nearest compatible antecedent)

---

## 7. RENDERED OUTPUT ISSUES

### 7.1 Current Sample

```
"I was frightened and in shock when the officers made physical contact with me 
without stated cause..."
```

### 7.2 Issues

- "made physical contact" is euphemistic transformation
- "without stated cause" is interpretation
- Some intent language may still leak through

### 7.3 Required Invariants

1. **No new facts introduced** - Only rephrase, never add
2. **No intent inference** - "looking for trouble" → delete or flag
3. **No legal conclusions** - "racial profiling" → "described by reporter as..."
4. **Preserve ambiguity** - Don't collapse interpretations into facts

---

## 8. IMPLEMENTATION PRIORITY

### Phase 1: Critical (Correctness)
1. Entity deduplication and role typing
2. Hard ban on intent phrases in neutral output
3. Fix quote boundary extraction

### Phase 2: High (Quality)
4. Epistemic classification taxonomy
5. Temporal identifier typing and validation
6. Kill or fix event extraction

### Phase 3: Medium (Polish)
7. Coreference gender consistency
8. Location validation (no person names)
9. Narrative glue detection and filtering

---

## 9. TEST FIXTURES

The stress test narrative is saved at:
```
tests/fixtures/stress_test_narrative.txt
```

Each fix should include regression tests against this narrative.

---

## 10. SUCCESS CRITERIA

After remediation, the stress test should produce:

- [ ] 15 distinct person entities (no duplicates, no badge-as-person)
- [ ] 4 organization entities
- [ ] 2 facility entities
- [ ] 0 bare titles or roles as entities
- [ ] All temporal markers properly typed
- [ ] 0 parsing artifacts ("30 PM")
- [ ] All intent attributions flagged as REPORTER_INTERPRETATION
- [ ] All legal characterizations flagged
- [ ] Clean quote extraction with speaker attribution
- [ ] Either empty events or properly structured events
- [ ] Rendered output passes neutrality check
