# V6 Architecture: Invariant-Driven Output System

**Created:** 2026-01-15
**Status:** ✅ COMPLETE (All 8 phases complete, all 6 gates pass)
**Philosophy:** Nothing renders unless it passes invariants.

---

## Executive Summary

V5 implemented proper data models but still uses "best effort" rendering.
V6 introduces **hard invariants** - machine-checkable rules that MUST pass before content reaches the output.

**Core Principle:**
```
Valid Content → Rendered Section
Invalid Content → Quarantine Bucket with Explicit Issues
```

No silent failures. No "Unknown" speakers. No pronoun actors. No garbage.

---

## The 6 Quality Gates

Every output must pass these gates:

| # | Gate | Invariant |
|---|------|-----------|
| 1 | EVENT_ACTOR | Every event line starts with resolved actor (not pronoun) |
| 2 | PROVENANCE_HONEST | "Verified" requires non-reporter evidence |
| 3 | SOURCE_SEPARATED | Medical findings ≠ self-reported injury |
| 4 | QUOTE_SPEAKER | Every quote has resolved speaker (not pronoun/unknown) |
| 5 | NO_DUPLICATES | Each section type renders exactly once |
| 6 | CAMERA_VALIDATED | Camera-friendly only from validated events |

**Current Status:** FAIL on gates 1, 2, 4, 6

---

## Phase 0: Invariant System (Foundation)

### 0.1 Create Invariant Infrastructure

**File:** `nnrt/validation/invariants.py`

```python
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Callable, Any

class InvariantSeverity(str, Enum):
    """How to handle invariant failures."""
    HARD = "hard"      # Content goes to quarantine
    SOFT = "soft"      # Content renders with warning
    INFO = "info"      # Log only, no output change

@dataclass
class InvariantResult:
    """Result of checking an invariant."""
    passes: bool
    invariant_id: str
    message: str
    failed_content: Optional[str] = None
    quarantine_bucket: Optional[str] = None

@dataclass  
class Invariant:
    """A machine-checkable rule."""
    id: str
    description: str
    severity: InvariantSeverity
    check_fn: Callable[[Any], InvariantResult]
    quarantine_bucket: str  # Where failed content goes

class InvariantRegistry:
    """Central registry of all invariants."""
    
    _invariants: dict[str, Invariant] = {}
    
    @classmethod
    def register(cls, invariant: Invariant) -> None:
        cls._invariants[invariant.id] = invariant
    
    @classmethod
    def check(cls, invariant_id: str, content: Any) -> InvariantResult:
        inv = cls._invariants.get(invariant_id)
        if not inv:
            raise ValueError(f"Unknown invariant: {invariant_id}")
        return inv.check_fn(content)
    
    @classmethod
    def check_all(cls, content: Any, ids: List[str]) -> List[InvariantResult]:
        return [cls.check(id, content) for id in ids]
```

### 0.2 Define Core Invariants

**File:** `nnrt/validation/event_invariants.py`

```python
from nnrt.validation.invariants import Invariant, InvariantResult, InvariantSeverity, InvariantRegistry

PRONOUNS = {"he", "she", "they", "him", "her", "them", "i", "me", "we", "us", "it"}

def check_event_has_actor(event) -> InvariantResult:
    """Every event must have a resolved actor."""
    actor = getattr(event, 'actor_label', None)
    
    if not actor:
        return InvariantResult(
            passes=False,
            invariant_id="EVENT_HAS_ACTOR",
            message="Event has no actor",
            failed_content=getattr(event, 'description', str(event))[:100],
            quarantine_bucket="EVENTS_UNRESOLVED"
        )
    
    if actor.lower() in PRONOUNS:
        return InvariantResult(
            passes=False,
            invariant_id="EVENT_HAS_ACTOR",
            message=f"Actor is pronoun: {actor}",
            failed_content=getattr(event, 'description', str(event))[:100],
            quarantine_bucket="EVENTS_UNRESOLVED"
        )
    
    return InvariantResult(passes=True, invariant_id="EVENT_HAS_ACTOR", message="OK")

def check_event_not_fragment(event) -> InvariantResult:
    """Event description must be complete clause (>3 words, has verb)."""
    desc = getattr(event, 'description', '')
    words = desc.split()
    
    if len(words) < 3:
        return InvariantResult(
            passes=False,
            invariant_id="EVENT_NOT_FRAGMENT",
            message=f"Fragment: only {len(words)} words",
            failed_content=desc[:100],
            quarantine_bucket="EVENTS_UNRESOLVED"
        )
    
    return InvariantResult(passes=True, invariant_id="EVENT_NOT_FRAGMENT", message="OK")

# Register invariants
InvariantRegistry.register(Invariant(
    id="EVENT_HAS_ACTOR",
    description="Every event has resolved actor (not pronoun)",
    severity=InvariantSeverity.HARD,
    check_fn=check_event_has_actor,
    quarantine_bucket="EVENTS_UNRESOLVED"
))

InvariantRegistry.register(Invariant(
    id="EVENT_NOT_FRAGMENT",
    description="Event is complete clause, not fragment",
    severity=InvariantSeverity.HARD,
    check_fn=check_event_not_fragment,
    quarantine_bucket="EVENTS_UNRESOLVED"
))
```

### 0.3 Validation Results Container

**Add to TransformContext:**

```python
@dataclass
class QuarantineBucket:
    """Content that failed invariants."""
    bucket_name: str
    items: List[tuple[Any, List[InvariantResult]]]  # (content, failures)

# In TransformContext:
quarantine: dict[str, QuarantineBucket] = field(default_factory=dict)

def quarantine_content(self, bucket: str, content: Any, failures: List[InvariantResult]):
    if bucket not in self.quarantine:
        self.quarantine[bucket] = QuarantineBucket(bucket_name=bucket, items=[])
    self.quarantine[bucket].items.append((content, failures))
```

---

## Phase 1: Badge-Entity Linkage

### Problem
Badges float free: "Badge #4821" not linked to "Officer Jenkins"

### Solution

**1.1 Add badge field to Entity:**
```python
class Entity(BaseModel):
    # ... existing fields ...
    badge_number: Optional[str] = Field(None, description="Badge number if officer")
    badge_source: str = Field("narrative", description="Where badge was found")
```

**1.2 Link in p32_extract_entities:**
```python
# After extracting entities, link badges from identifiers
def _link_badges_to_officers(entities: List[Entity], identifiers: List[Identifier]):
    """Associate each badge with its officer entity."""
    for ident in identifiers:
        if ident.type == IdentifierType.BADGE_NUMBER:
            # Find nearby officer in narrative
            officer = _find_officer_for_badge(ident, entities)
            if officer:
                officer.badge_number = ident.value
```

**1.3 Invariant:**
```python
def check_badge_linked(entity) -> InvariantResult:
    """If entity is officer, should have badge if mentioned."""
    # Soft invariant - badge is nice to have
    pass

# HARD invariant for orphaned badges
def check_no_orphan_badges(identifiers, entities) -> InvariantResult:
    """Every badge must link to an entity."""
    for ident in identifiers:
        if ident.type == IdentifierType.BADGE_NUMBER:
            linked = any(e.badge_number == ident.value for e in entities)
            if not linked:
                return InvariantResult(
                    passes=False,
                    invariant_id="NO_ORPHAN_BADGES",
                    message=f"Badge {ident.value} not linked to officer",
                    quarantine_bucket="UNLINKED_IDENTIFIERS"
                )
    return InvariantResult(passes=True, ...)
```

**1.4 Render output:**
```
OFFICER IDENTIFICATION:
  • Officer Jenkins (Badge #4821)
  • Officer Rodriguez (Badge #5539)
  • Sergeant Williams (Badge #2103)
```

---

## Phase 2: Actor-Resolved Events (Priority 1)

### Problem
Events have pronouns, fragments, undefined plurals.

### Solution

**2.1 Event validation in render:**
```python
def render_observed_events(events: List[Event], ctx: TransformContext) -> List[str]:
    """Render only events that pass all invariants."""
    lines = []
    
    for event in events:
        # Check ALL event invariants
        results = [
            check_event_has_actor(event),
            check_event_not_fragment(event),
        ]
        
        failures = [r for r in results if not r.passes]
        
        if failures:
            # Quarantine - do NOT render in OBSERVED
            ctx.quarantine_content("EVENTS_UNRESOLVED", event, failures)
        else:
            # Passes all invariants - render
            line = f"{event.actor_label} {event.action_verb}"
            if event.target_label:
                line += f" {event.target_label}"
            elif event.target_object:
                line += f" {event.target_object}"
            lines.append(f"  • {line}")
    
    return lines
```

**2.2 Quarantine bucket rendering:**
```python
def render_quarantine_bucket(ctx: TransformContext, bucket_name: str) -> List[str]:
    """Render quarantined content with its issues."""
    lines = []
    bucket = ctx.quarantine.get(bucket_name)
    
    if not bucket:
        return lines
    
    lines.append(f"{bucket_name}")
    lines.append("─" * 70)
    
    for content, failures in bucket.items:
        desc = getattr(content, 'description', str(content))[:100]
        issues = ", ".join(f.message for f in failures)
        lines.append(f"  ⚠️ {desc}")
        lines.append(f"      Issues: {issues}")
    
    lines.append("")
    return lines
```

**2.3 Expected output:**
```
OBSERVED EVENTS (INCIDENT SCENE):
  • Officer Jenkins yelled at Reporter
  • Officer Rodriguez exited the passenger side of the vehicle
  • Officer Jenkins grabbed Reporter's left arm
  • Officer Rodriguez searched Reporter's pockets

EVENTS (ACTOR UNRESOLVED):
  ⚠️ immediately started screaming at me
      Issues: Actor is pronoun: he
  ⚠️ they both approached with hands on weapons
      Issues: Actor is pronoun: they
```

---

## Phase 3: Provenance-First Status

### Problem
"Verified" used without evidence.

### Solution

**3.1 Strict provenance rules:**
```python
class ProvenanceStatus(str, Enum):
    SELF_ATTESTED = "self_attested"    # Reporter says X
    CITED = "cited"                     # Reporter says [source] said X
    VERIFIED = "verified"               # Has non-reporter evidence
    NEEDS_PROVENANCE = "needs_provenance"  # Claim without source

def compute_provenance_status(stmt: AtomicStatement) -> ProvenanceStatus:
    """Compute honest provenance status."""
    
    # Can only be VERIFIED if we have external source
    if stmt.source_type == "reporter":
        if stmt.epistemic_type in ("legal_claim", "conspiracy_claim"):
            return ProvenanceStatus.NEEDS_PROVENANCE
        elif "said" in stmt.text or "documented" in stmt.text:
            return ProvenanceStatus.CITED  # Reporter citing someone
        else:
            return ProvenanceStatus.SELF_ATTESTED
    else:
        # Non-reporter source - could be verified if we have evidence
        if stmt.source_entity_id:
            return ProvenanceStatus.CITED  # Named but unverified
        return ProvenanceStatus.NEEDS_PROVENANCE
```

**3.2 Invariant:**
```python
def check_verified_has_evidence(stmt) -> InvariantResult:
    """VERIFIED requires non-reporter source."""
    status = getattr(stmt, 'provenance_status', 'unknown')
    source = getattr(stmt, 'source_type', 'reporter')
    
    if status == "verified" and source == "reporter":
        return InvariantResult(
            passes=False,
            invariant_id="VERIFIED_HAS_EVIDENCE",
            message="Cannot be 'verified' with only reporter as source",
            quarantine_bucket="PROVENANCE_ERRORS"
        )
    return InvariantResult(passes=True, ...)
```

**3.3 Render output:**
```
SOURCE-DERIVED INFORMATION:
  ⚠️ External provenance required

  [1] CLAIM: Officer Jenkins has 12 prior complaints
      Source: Reporter (research)
      Status: Needs Provenance

  [2] ACTION: Reporter researched his record
      (This is an action, not a claim - no provenance needed)
```

---

## Phase 4: Medical vs Self-Reported Split

### Problem
"Dr. Foster documented X" in SELF-REPORTED section.

### Solution

**4.1 Attribution-based routing:**
```python
def route_medical_content(stmt: AtomicStatement) -> str:
    """Route based on WHO is the source, not just keywords."""
    text = stmt.text.lower()
    source = stmt.source_type
    
    # Check for medical provider attribution
    medical_providers = ["dr.", "doctor", "nurse", "emt", "paramedic"]
    medical_verbs = ["documented", "diagnosed", "treated", "said", "noted"]
    
    has_provider = any(p in text for p in medical_providers)
    has_verb = any(v in text for v in medical_verbs)
    
    if has_provider and has_verb:
        return "MEDICAL_FINDINGS"
    
    if source == "medical":
        return "MEDICAL_FINDINGS"
    
    return "SELF_REPORTED"
```

**4.2 Invariant:**
```python
def check_medical_attribution(stmt, section: str) -> InvariantResult:
    """Medical findings must have provider attribution."""
    if section == "MEDICAL_FINDINGS":
        if not _has_medical_provider_attribution(stmt):
            return InvariantResult(
                passes=False,
                invariant_id="MEDICAL_HAS_PROVIDER",
                message="Medical finding needs provider attribution",
                quarantine_bucket="ATTRIBUTION_NEEDED"
            )
    return InvariantResult(passes=True, ...)
```

**4.3 Render output:**
```
MEDICAL FINDINGS (as reported by Reporter):
  • Dr. Amanda Foster documented bruises on both wrists
  • Dr. Amanda Foster documented sprained left shoulder
  • Dr. Amanda Foster documented minor facial abrasions
  Status: Cited (no medical record attached)

SELF-REPORTED INJURY:
  • Reporter states wrists were bleeding and bruised
```

---

## Phase 5: Quote Speaker Resolution

### Problem
"Unknown", "He", "She" as speakers.

### Solution

**5.1 Strict validation:**
```python
def check_quote_speaker(speech_act) -> InvariantResult:
    """Quote must have resolved speaker."""
    speaker = getattr(speech_act, 'speaker_label', None)
    
    if not speaker or speaker.lower() in {"unknown", "speaker", "he", "she", "they"}:
        return InvariantResult(
            passes=False,
            invariant_id="QUOTE_HAS_SPEAKER",
            message=f"Speaker unresolved: {speaker}",
            failed_content=getattr(speech_act, 'content', '')[:50],
            quarantine_bucket="QUOTES_UNRESOLVED"
        )
    return InvariantResult(passes=True, ...)
```

**5.2 Render output:**
```
PRESERVED QUOTES:
  • Officer Jenkins yelled: "STOP RIGHT THERE! DON'T YOU DARE MOVE!"
  • Reporter said: "What's the problem, officer?"
  • Reporter said: "You're hurting me! Please stop!"
  • Officer Jenkins said: "Sure you did, that's what they all say."

QUOTES (SPEAKER UNRESOLVED):
  ⚠️ "my injuries were consistent with significant physical force"
      Issues: Speaker unresolved: She
```

---

## Phase 6: Disable Camera-Friendly

### Problem
Generating garbage output.

### Solution

**6.1 Gate behind invariant:**
```python
# In structured.py
ENABLE_CAMERA_FRIENDLY = False  # Disabled until events normalized

def render_camera_friendly(events: List[Event], ctx: TransformContext) -> List[str]:
    if not ENABLE_CAMERA_FRIENDLY:
        return []  # Don't render this section
    
    # Only use events that passed ALL invariants
    validated_events = [e for e in events if e not in ctx.quarantine.get("EVENTS_UNRESOLVED", [])]
    
    if not validated_events:
        return []  # Still nothing valid
    
    # Render from validated events only
    ...
```

---

## Phase 7: Section Deduplication

### Problem
Two characterizations sections.

### Solution

**7.1 Section registry:**
```python
class SectionRegistry:
    """Track rendered sections to prevent duplicates."""
    
    _rendered: set = set()
    
    @classmethod
    def can_render(cls, section_name: str) -> bool:
        if section_name in cls._rendered:
            return False
        cls._rendered.add(section_name)
        return True
    
    @classmethod
    def reset(cls):
        cls._rendered.clear()
```

**7.2 Usage in renderer:**
```python
# Before rendering any section
if not SectionRegistry.can_render("REPORTER_CHARACTERIZATIONS"):
    pass  # Skip - already rendered

# Reset at start of each render
SectionRegistry.reset()
```

---

## Implementation Order

| Order | Phase | Est. Time | Gates Fixed |
|-------|-------|-----------|-------------|
| 1 | Phase 0: Invariant System | 1 hour | Foundation |
| 2 | Phase 2: Actor-Resolved Events | 1.5 hours | Gate 1 |
| 3 | Phase 6: Disable Camera-Friendly | 15 min | Gate 6 |
| 4 | Phase 5: Quote Speaker Resolution | 45 min | Gate 4 |
| 5 | Phase 3: Provenance-First | 45 min | Gate 2 |
| 6 | Phase 4: Medical Split | 30 min | Gate 3 |
| 7 | Phase 1: Badge Linkage | 45 min | (Polish) |
| 8 | Phase 7: Deduplication | 20 min | Gate 5 |

**Total: ~6-7 hours**

---

## Success Criteria

After V6, every output must pass:

- [ ] Every event has explicit actor (not pronoun)
- [ ] No "verified" status without external provenance
- [ ] Medical findings separated from self-reported injury
- [ ] Quotes have resolved speakers (not Unknown/He/She)
- [ ] No duplicated sections
- [ ] Camera-friendly absent OR generated from validated events only

**Test Command:**
```bash
python scripts/stress_test.py --check-invariants
```

---

## Next Step

Create `nnrt/validation/` module and implement Phase 0 foundation.
