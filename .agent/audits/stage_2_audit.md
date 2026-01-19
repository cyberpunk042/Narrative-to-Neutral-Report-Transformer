# STAGE 2 AUDIT: Selection Layer Creation

**Document**: `.agent/milestones/stage_2_selection.md`
**Audit Date**: 2026-01-19

---

## Stage 2 Objective (from document)

> Create a dedicated **Selection layer** that sits between Classification and Rendering. This layer determines **which atoms to include** in output and **which section** each atom belongs to.

> **Outcome**: Selection decisions are made ONCE in the pipeline and stored. The renderer receives pre-filtered, pre-routed atoms and simply formats them.

---

## DONE CRITERIA FROM DOCUMENT (lines 558-577)

| Claim | Status | Evidence |
|-------|--------|----------|
| SelectionMode enum created | ✅ VERIFIED | models.py lines 16-43 |
| SelectionResult dataclass created | ✅ VERIFIED | models.py lines 46-120 |
| TransformContext.selection_result added | ✅ VERIFIED | p55_select sets ctx.selection_result |
| Helper methods added | ⚠️ Need to verify | get_event_by_id, etc. |
| p55_select pass implemented | ✅ VERIFIED | 379 lines |
| Pass wired into pipeline | ⚠️ Need to verify | Check pipeline config |
| Renderer uses SelectionResult | ❌ "Stage 3" | Document says deferred |
| Mode configurable via CLI | ⚠️ Need to verify | Check CLI code |
| Unit tests | ⚠️ Need to verify | tests/test_selection.py |
| 602 tests pass | ⚠️ Unknown | Need to run tests |

---

## PART 1: WHAT p55_select DOES (VERIFIED)

### Event Selection (lines 183-229)
- Routes by `is_camera_friendly` + `is_follow_up` + `is_source_derived`
- Outputs to: observed_events, follow_up_events, source_derived_events, narrative_excerpts, excluded_events

### Entity Selection (lines 232-295)
- Uses INCIDENT_ROLES, POST_INCIDENT_ROLES, BARE_ROLE_LABELS
- Outputs to: incident_participants, post_incident_pros, mentioned_contacts, excluded_entities

### Quote Selection (lines 298-333)
- Uses speaker_resolved or speaker_label
- Outputs to: preserved_quotes, quarantined_quotes

### Timeline Selection (lines 336-378)
- Filters fragments and unresolved pronouns
- Outputs to: timeline_entries, excluded_timeline

---

## PART 2: SelectionResult vs V1 OUTPUT SECTIONS

### V1 Renders 28 Sections (from Stage 1 audit)

Now comparing what SelectionResult can support:

| V1 Section | SelectionResult Field | Status |
|------------|----------------------|--------|
| PARTIES - INCIDENT PARTICIPANTS | incident_participants | ✅ |
| PARTIES - POST-INCIDENT PROFESSIONALS | post_incident_pros | ✅ |
| PARTIES - MENTIONED CONTACTS | mentioned_contacts | ✅ |
| REFERENCE DATA | *No field* | ❌ MISSING |
| OBSERVED EVENTS (STRICT) | observed_events | ✅ |
| OBSERVED EVENTS (FOLLOW-UP) | follow_up_events | ✅ |
| **ITEMS DISCOVERED** | *No field* | ❌ MISSING |
| NARRATIVE EXCERPTS | narrative_excerpts | ✅ |
| SOURCE-DERIVED | source_derived_events | ✅ |
| SELF-REPORTED (ACUTE) | *No field* | ❌ MISSING |
| SELF-REPORTED (INJURY) | *No field* | ❌ MISSING |
| **SELF-REPORTED (PSYCHOLOGICAL)** | *No field* | ❌ MISSING |
| **SELF-REPORTED (SOCIOECONOMIC)** | *No field* | ❌ MISSING |
| **SELF-REPORTED (GENERAL)** | *No field* | ❌ MISSING |
| **LEGAL ALLEGATIONS** | *No field* | ❌ MISSING |
| REPORTER CHARACTERIZATIONS | *No field* | ❌ MISSING |
| **REPORTER INFERENCES** | *No field* | ❌ MISSING |
| **REPORTER INTERPRETATIONS** | *No field* | ❌ MISSING |
| **CONTESTED ALLEGATIONS** | *No field* | ❌ MISSING |
| **MEDICAL FINDINGS** | *No field* | ❌ MISSING |
| **ADMINISTRATIVE ACTIONS** | *No field* | ❌ MISSING |
| PRESERVED QUOTES | preserved_quotes | ✅ |
| QUOTES (SPEAKER UNRESOLVED) | quarantined_quotes | ✅ |
| **EVENTS (ACTOR UNRESOLVED)** | *No field* | ❌ MISSING |
| RECONSTRUCTED TIMELINE | timeline_entries | ✅ |
| **INVESTIGATION QUESTIONS** | *No field* | ❌ MISSING |
| RAW NEUTRALIZED NARRATIVE | *No field* | ❌ MISSING (uses rendered_text) |
| Context Summary | *No field* | ❌ MISSING |

### Summary:
- **Fields Present:** 12
- **Fields Missing:** 16

### Critical Missing Fields:

```python
@dataclass
class SelectionResult:
    # === MISSING: Statement-based sections ===
    
    # Self-reported state (routed by epistemic_type)
    acute_state: list[str]           # AtomicStatement IDs with epistemic_type='state_acute'
    injury_state: list[str]          # AtomicStatement IDs with epistemic_type='state_injury'
    psychological_state: list[str]   # epistemic_type='state_psychological'
    socioeconomic_impact: list[str]  # epistemic_type='state_socioeconomic'
    general_self_report: list[str]   # epistemic_type='self_report'
    
    # Legal and characterization (routed by epistemic_type)
    legal_allegations: list[str]     # epistemic_type='legal_claim'
    characterizations: list[str]     # epistemic_type='characterization'
    inferences: list[str]            # epistemic_type='inference'
    interpretations: list[str]       # epistemic_type='interpretation'
    contested_allegations: list[str] # epistemic_type='conspiracy_claim'
    
    # Medical content (special routing)
    medical_findings: list[str]      # Routed from self-report via _is_medical_provider_content
    
    # Administrative actions
    admin_actions: list[str]         # epistemic_type='admin_action'
    
    # === MISSING: Extracted content ===
    
    # Items discovered (complex extraction, not just selection)
    discovered_items: dict[str, list[str]]  # Categories → item text
    
    # Investigation questions (generated, not selected)
    investigation_questions: list[dict]
    
    # Time gaps (for timeline gaps)
    time_gaps: list[str]  # TimeGap IDs requiring investigation
    
    # === MISSING: Event validation ===
    
    events_actor_unresolved: list[tuple[str, str]]  # (Event ID, issues)
    
    # === MISSING: Reference data ===
    
    identifiers_by_type: dict[str, list[str]]  # date, time, location, badge_number, etc.
```

---

## PART 3: p55_select LOGIC vs V1 LOGIC

### Entity Selection

**p55 (lines 30-46):**
```python
INCIDENT_ROLES = {'reporter', 'subject_officer', 'supervisor', 'witness_civilian', 'witness_official', 'bystander'}
POST_INCIDENT_ROLES = {'medical_provider', 'legal_counsel', 'investigator'}
BARE_ROLE_LABELS = {'partner', 'passenger', 'suspect', 'manager', 'driver', 'victim', 'witness', 'officer', 'the partner', 'his partner', 'the suspect', 'a suspect', 'the manager', 'my manager'}
```

**V1 (lines 150-167):**
```python
INCIDENT_ROLES = {'reporter', 'subject_officer', 'supervisor', 'witness_civilian', 'witness_official', 'bystander'}
POST_INCIDENT_ROLES = {'medical_provider', 'legal_counsel', 'investigator'}
BARE_ROLE_LABELS = {'partner', 'passenger', 'suspect', 'manager', 'driver', 'victim', 'witness', 'officer', 'the partner', 'his partner', 'the suspect', 'a suspect', 'the manager', 'my manager'}
```

**Status: ✅ IDENTICAL** - These arrays are exactly the same.

### Timeline Selection

**p55 (lines 53-54):**
```python
FRAGMENT_STARTS = {'and', 'but', 'when', 'which', 'although', 'while', 'because'}
PRONOUN_PATTERN = re.compile(r'^(He|She|They|It|We|I)\s', re.IGNORECASE)
```

**V1 (lines 1642-1646):**
```python
fragment_starters = ['to ', 'for ', 'from ', 'by ', 'where ', 'which ', 'who ', 'because ', 'until ', 'unless ', 'what ', 'how ', 'why ', 'if ']
```

**p55 additional skip (not in p55):**
```python
# V1 lines 1701-1702
if desc_lower.startswith('but ') or desc_lower.startswith('or ') or desc_lower.startswith('yet '):
    continue
```

**Status: ⚠️ PARTIAL**
- p55 has: and, but, when, which, although, while, because (7)
- V1 has: to, for, from, by, where, which, who, because, until, unless, what, how, why, if (14) + but, or, yet (3)
- **Missing from p55:** to, for, from, by, where, who, until, unless, what, how, why, if, or, yet

### Quote Selection

**p55 uses:**
- speaker_resolved field
- speaker_label as proxy
- is_quarantined field

**V1 uses:**
- SPEECH_VERBS (18 verbs) for extraction
- NOT_SPEAKERS (17 exclusions) for filtering
- name_patterns (10 regexes) for extraction
- Complex inline speaker extraction

**Status: ⚠️ REQUIRES p36**
p55 assumes quotes already have speaker_resolved populated, but no p36_resolve_quotes exists to populate it.

---

## PART 4: WHAT p55_select CANNOT DO

### 1. Statement-Based Section Routing

V1 routes atomic statements by epistemic_type to 12+ different sections:

```python
# V1 sections using statements_by_epistemic:
statements_by_epistemic['state_acute']        → SELF-REPORTED (ACUTE)
statements_by_epistemic['state_injury']       → SELF-REPORTED (INJURY)
statements_by_epistemic['state_psychological'] → SELF-REPORTED (PSYCHOLOGICAL)
statements_by_epistemic['state_socioeconomic'] → SELF-REPORTED (SOCIOECONOMIC)
statements_by_epistemic['self_report']        → SELF-REPORTED (GENERAL)
statements_by_epistemic['legal_claim']        → LEGAL ALLEGATIONS
statements_by_epistemic['characterization']   → REPORTER CHARACTERIZATIONS
statements_by_epistemic['inference']          → REPORTER INFERENCES
statements_by_epistemic['interpretation']     → REPORTER INTERPRETATIONS
statements_by_epistemic['conspiracy_claim']   → CONTESTED ALLEGATIONS
statements_by_epistemic['medical_finding']    → MEDICAL FINDINGS
statements_by_epistemic['admin_action']       → ADMINISTRATIVE ACTIONS
```

**p55 has NO statement selection.** It only selects:
- Events
- Entities
- Quotes (SpeechAct)
- Timeline entries

### 2. Items Discovered Extraction

V1 lines 828-1031 (200+ lines) extract and categorize discovered items.

**p55 does not handle this.** No field for it.

### 3. Medical Content Routing

V1 lines 1125-1134 route medical provider content from SELF-REPORTED to MEDICAL FINDINGS.

**p55 has no medical routing logic.**

### 4. Quote Speaker Extraction

V1 lines 1315-1410 (95 lines) extract speakers from quote text.

**p55 assumes speaker already populated.** But no pass does this.

### 5. Investigation Question Generation

V1 lines 1934-1994 generate investigation questions.

**p55 does not handle this.** No field for it.

### 6. Reference Data Selection

V1 lines 236-316 select and categorize identifiers.

**p55 does not handle identifiers.**

---

## PART 5: SELECTION FLOW ANALYSIS

### What V1 Does:

```
1. Build statements_by_type dict from atomic_statements
2. Build statements_by_epistemic dict from atomic_statements
3. Process OBSERVABLE_EPISTEMIC_TYPES for events
4. Route to strict_events, narrative_excerpts, follow_up_events, source_derived
5. Extract items_discovered from statement text
6. Route self-reported by sub-type + medical filtering
7. Route legal/characterization/inference by epistemic_type
8. Extract quotes and resolve speakers
9. Filter timeline entries
10. Generate investigation questions
11. Render each section
```

### What p55 Does:

```
1. Select events by is_camera_friendly
2. Route to observed_events, follow_up_events, source_derived_events, narrative_excerpts
3. Select entities by role
4. Route to incident_participants, post_incident_pros, mentioned_contacts
5. Select quotes by speaker_resolved
6. Route to preserved_quotes, quarantined_quotes
7. Select timeline by fragment/pronoun check
8. Store in ctx.selection_result
```

### Gap:

p55 handles 4 atom types: Events, Entities, SpeechActs, Timeline.

**V1 also routes:**
- AtomicStatements (12 epistemic_type categories)
- Identifiers (reference data)
- Generated content (items, questions)

---

## STAGE 2 VERDICT

### What Was Done:

| Component | Status |
|-----------|--------|
| SelectionMode enum | ✅ Complete |
| SelectionResult dataclass | ⚠️ Partial (12/28 sections) |
| p55_select pass | ✅ Created (379 lines) |
| Event selection | ✅ Done |
| Entity selection | ✅ Done (matching V1) |
| Quote selection | ⚠️ Assumes speaker was resolved upstream |
| Timeline selection | ⚠️ Partial (missing 10 fragment patterns) |
| Statement selection | ❌ Not implemented |
| Identifier selection | ❌ Not implemented |
| Item extraction | ❌ Not implemented |
| Question generation | ❌ Not implemented |

### SelectionResult Field Coverage:

| Present | Missing |
|---------|---------|
| observed_events | acute_state, injury_state, psychological_state |
| follow_up_events | socioeconomic_impact, general_self_report |
| source_derived_events | legal_allegations, characterizations |
| narrative_excerpts | inferences, interpretations |
| preserved_quotes | contested_allegations, medical_findings |
| quarantined_quotes | admin_actions, events_actor_unresolved |
| incident_participants | discovered_items, investigation_questions |
| post_incident_pros | time_gaps, identifiers_by_type |
| mentioned_contacts | |
| timeline_entries | |
| excluded_* fields | |

**Coverage: 12/28 sections (43%)**

### Outcome Status: ⚠️ PARTIALLY COMPLETE

**Stated Outcome:**
> "The renderer receives pre-filtered, pre-routed atoms and simply formats them."

**Reality:**
- p55 can route 4 atom types to 12 output buckets
- V1 routes to 28 output sections
- 16 sections have no selection support
- Renderer must still do statement routing, item extraction, question generation

---

## REMEDIATION REQUIRED

### Priority 1: Add Statement Selection

Add fields and logic for all 12 epistemic_type categories:

```python
# In SelectionResult
acute_state: list[str] = field(default_factory=list)
injury_state: list[str] = field(default_factory=list)
# ... etc.

# In p55_select
def _select_statements(ctx, result, mode):
    for stmt in ctx.atomic_statements:
        epistemic = stmt.epistemic_type
        if epistemic == 'state_acute':
            result.acute_state.append(stmt.id)
        elif epistemic == 'state_injury':
            result.injury_state.append(stmt.id)
        # ... etc.
```

### Priority 2: Add Medical Content Routing

```python
def _route_medical_content(ctx, result):
    """Route medical provider content from self-report to medical_findings."""
    for stmt_id in result.injury_state[:]:  # Copy to allow modification
        stmt = ctx.get_statement_by_id(stmt_id)
        if _is_medical_provider_content(stmt.text):
            result.injury_state.remove(stmt_id)
            result.medical_findings.append(stmt_id)
```

### Priority 3: Add Identifier Selection

```python
identifiers_by_type: dict[str, list[str]] = field(default_factory=dict)

def _select_identifiers(ctx, result, mode):
    for ident in ctx.identifiers:
        ident_type = ident.type.value
        if ident_type not in result.identifiers_by_type:
            result.identifiers_by_type[ident_type] = []
        result.identifiers_by_type[ident_type].append(ident.id)
```

### Priority 4: Add Missing Timeline Fragment Patterns

Add to p55:
```python
FRAGMENT_STARTS = {
    'and', 'but', 'when', 'which', 'although', 'while', 'because',
    'to', 'for', 'from', 'by', 'where', 'who', 'until', 'unless',
    'what', 'how', 'why', 'if', 'or', 'yet'
}
```

### Priority 5: Items Extraction
Needs separate pass (not selection) — complex extraction logic.

### Priority 6: Question Generation
Needs separate pass (not selection) — generation logic.

---

*Stage 2 Audit — 2026-01-19*
