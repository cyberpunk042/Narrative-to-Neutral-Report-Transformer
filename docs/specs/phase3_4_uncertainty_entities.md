# Phase 3 & 4: Uncertainty & Entity/Event Extraction — Spec

## Phase 3: Uncertainty Structured Output (2 hours)

### Goal
Structure all detected ambiguities/contradictions into the output schema.

### Current State
Uncertainties are detected but only appear as diagnostics:
```
[warning] AMBIGUOUS_PRONOUN: Ambiguous pronoun reference...
```

### Target State
Uncertainties appear in structured output:
```json
{
  "uncertainties": [
    {
      "id": "unc_001",
      "type": "ambiguous_reference",
      "text": "He hit him",
      "description": "Ambiguous pronoun - unclear who hit whom"
    }
  ]
}
```

### Implementation

#### 1. Add uncertainty tracking to TransformContext

```python
# In nnrt/core/context.py
class TransformContext:
    uncertainties: list[Uncertainty] = []
    
    def add_uncertainty(
        self,
        type: str,
        text: str,
        segment_id: str,
        description: str,
        candidates: list[dict] = None,
    ):
        self.uncertainties.append(Uncertainty(
            id=f"unc_{len(self.uncertainties) + 1:03d}",
            type=type,
            text=text,
            segment_id=segment_id,
            description=description,
            candidates=candidates,
        ))
```

#### 2. Update p25_annotate_context.py

When ambiguity is detected, add to context:

```python
if has_ambiguous_pronouns:
    ctx.add_uncertainty(
        type="ambiguous_reference",
        text=segment.text,
        segment_id=segment.id,
        description="Ambiguous pronoun reference - unclear who did what",
        candidates=[{"text": "He", "options": ["officer", "subject"]}],
    )
```

#### 3. Include in structured output

```python
def build_structured_output(result):
    # ...
    uncertainties = [
        UncertaintyOutput(**u.model_dump())
        for u in result.context.uncertainties
    ]
```

---

## Phase 4: Entity/Event Extraction (3-4 hours)

### Goal
Extract structured entities and events from the narrative.

### Current State
Identifiers (names, dates, badges) are extracted, but:
- No person/entity resolution
- No event extraction
- No actor/target linking

### Target State

```json
{
  "entities": [
    {"id": "ent_001", "type": "person", "label": "reporter", "role": "reporter"},
    {"id": "ent_002", "type": "person", "label": "officer_1", "role": "subject"}
  ],
  "events": [
    {
      "id": "evt_001",
      "type": "physical_contact",
      "description": "grabbed shirt collar",
      "actors": ["ent_002"],
      "targets": ["ent_001"]
    }
  ]
}
```

### Implementation

#### 1. Entity Extraction

Create `nnrt/passes/p32_extract_entities.py`:

```python
# Entity patterns
REPORTER_PRONOUNS = ["I", "me", "my", "mine", "myself"]
SUBJECT_PATTERNS = [
    r"\b(the\s+)?(officer|cop|police|deputy|sergeant)\b",
    r"\b(he|she|they|him|her|them)\b",  # Contextual
]

def extract_entities(ctx: TransformContext) -> TransformContext:
    # Always create reporter entity
    reporter = Entity(
        id="ent_001",
        type="person",
        label="reporter",
        role="reporter",
        mentions=[],
    )
    
    # Scan for mentions
    for seg in ctx.segments:
        for pronoun in REPORTER_PRONOUNS:
            if pronoun.lower() in seg.text.lower():
                reporter.mentions.append({
                    "text": pronoun,
                    "segment_id": seg.id,
                })
        
        # Detect officers/subjects
        if _matches_any(seg.text, SUBJECT_PATTERNS):
            # Create or update subject entity
            ...
    
    ctx.entities.append(reporter)
    return ctx
```

#### 2. Event Extraction

Create `nnrt/passes/p34_extract_events.py`:

```python
EVENT_PATTERNS = {
    "physical_contact": [
        r"\b(grabbed|yanked|pulled|pushed|shoved|threw|slammed)\b",
        r"\b(punched|struck|hit|kicked|tackled)\b",
        r"\b(handcuffed|cuffed|restrained)\b",
    ],
    "verbal": [
        r"\b(said|screamed|yelled|shouted|told)\b",
    ],
    "movement": [
        r"\b(approached|walked|ran|drove)\b",
    ],
}

def extract_events(ctx: TransformContext) -> TransformContext:
    for seg in ctx.segments:
        for event_type, patterns in EVENT_PATTERNS.items():
            if _matches_any(seg.text, patterns):
                event = Event(
                    id=f"evt_{len(ctx.events) + 1:03d}",
                    type=event_type,
                    description=extract_action(seg.text),
                    source_statement=seg.id,
                    actors=infer_actors(seg, ctx),
                    targets=infer_targets(seg, ctx),
                )
                ctx.events.append(event)
    
    return ctx
```

#### 3. Actor/Target Inference

```python
def infer_actors(seg: Segment, ctx: TransformContext) -> list[str]:
    """Infer who performed the action."""
    text = seg.text.lower()
    
    # "He grabbed me" → actor is subject, target is reporter
    if text.startswith("he ") or text.startswith("she "):
        return ["ent_002"]  # Subject
    
    # "I grabbed him" → actor is reporter
    if text.startswith("i "):
        return ["ent_001"]  # Reporter
    
    return []  # Unknown

def infer_targets(seg: Segment, ctx: TransformContext) -> list[str]:
    """Infer who received the action."""
    text = seg.text.lower()
    
    if " me" in text or " my " in text:
        return ["ent_001"]  # Reporter
    
    if " him" in text or " her " in text:
        return ["ent_002"]  # Subject
    
    return []
```

---

## Pipeline Update

New pipeline order:

```
p00_normalize
p10_segment
p20_tag_spans
p22_classify_statements  ← Phase 1
p25_annotate_context
p30_extract_identifiers
p32_extract_entities     ← Phase 4
p34_extract_events       ← Phase 4
p40_build_ir
p50_policy
p60_augment_ir
p70_render
p80_package
```

---

## Exit Criteria

### Phase 3
- [ ] Uncertainties tracked in TransformContext
- [ ] Uncertainties appear in structured output
- [ ] All detection types preserved

### Phase 4
- [ ] Entities extracted (reporter always, subjects when detectable)
- [ ] Events extracted with type classification
- [ ] Actor/target inference works for simple cases
- [ ] Entities/events appear in structured output

---

## Estimated Time

| Phase | Task | Hours |
|-------|------|-------|
| 3 | Uncertainty tracking | 1 |
| 3 | Structured output | 0.5 |
| 3 | Testing | 0.5 |
| 4 | Entity extraction | 1.5 |
| 4 | Event extraction | 1.5 |
| 4 | Actor/target inference | 1 |
| 4 | Testing | 0.5 |
| **Total** | | **6.5** |
