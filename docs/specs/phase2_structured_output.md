# Phase 2: Structured Output Schema — Implementation Spec

## Overview

Create a JSON output schema that exposes all NNRT analysis in structured form.

---

## Output Schema V1

### Top-Level Structure

```json
{
  "nnrt_version": "0.3.0",
  "schema_version": "1.0",
  "input_hash": "sha256:abc123...",
  "timestamp": "2026-01-13T23:30:00Z",
  "transformed": true,
  
  "statements": [...],
  "uncertainties": [...],
  "entities": [...],
  "events": [...],
  
  "diagnostics": [...],
  "metadata": {...},
  
  "rendered_text": "The neutralized narrative..."
}
```

---

## Statement Object

```json
{
  "id": "stmt_001",
  "type": "observation|claim|interpretation|quote",
  "original": "I saw him grab my shirt collar",
  "neutral": "Individual grabbed reporter's shirt collar",
  "segment_id": "seg_001",
  
  "classification_confidence": 0.85,
  "contexts": ["physical_force", "already_neutral"],
  
  "transformations": [
    {
      "rule_id": "intent_explicit_wanted",
      "action": "replace",
      "original": "wanted to",
      "replacement": "appeared to"
    }
  ],
  
  "flags": [],
  "linked_entities": ["ent_001", "ent_002"],
  "linked_events": ["evt_001"]
}
```

---

## Uncertainty Object

```json
{
  "id": "unc_001",
  "type": "ambiguous_reference|vague_reference|contradiction|missing_info",
  "text": "He hit him",
  "segment_id": "seg_003",
  
  "description": "Ambiguous pronoun - unclear who hit whom",
  "candidates": [
    {"reference": "He", "candidates": ["officer", "subject"]},
    {"reference": "him", "candidates": ["officer", "subject"]}
  ],
  
  "resolution": null,
  "requires_human_review": true
}
```

---

## Entity Object

```json
{
  "id": "ent_001",
  "type": "person|vehicle|location|organization|time",
  "label": "reporter",
  "role": "reporter|subject|officer|witness|other",
  
  "mentions": [
    {"text": "I", "segment_id": "seg_001"},
    {"text": "me", "segment_id": "seg_002"},
    {"text": "my", "segment_id": "seg_003"}
  ],
  
  "attributes": {
    "occupation": "nurse",
    "age": "45"
  }
}
```

---

## Event Object

```json
{
  "id": "evt_001",
  "type": "physical_contact|verbal|movement|legal|observation",
  "description": "grabbed shirt collar",
  "neutral_description": "Individual grabbed reporter's shirt collar",
  
  "actors": ["ent_002"],
  "targets": ["ent_001"],
  "instruments": [],
  
  "timestamp": "unclear",
  "temporal_relation": "after evt_000",
  
  "source_statement": "stmt_001",
  "confidence": 0.90
}
```

---

## Implementation

### New Module: `nnrt/output/structured.py`

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class StatementOutput(BaseModel):
    id: str
    type: str
    original: str
    neutral: Optional[str]
    segment_id: str
    classification_confidence: float
    contexts: list[str]
    transformations: list[dict]
    flags: list[str]
    linked_entities: list[str] = []
    linked_events: list[str] = []

class UncertaintyOutput(BaseModel):
    id: str
    type: str
    text: str
    segment_id: str
    description: str
    candidates: Optional[list[dict]] = None
    resolution: Optional[str] = None
    requires_human_review: bool = True

class EntityOutput(BaseModel):
    id: str
    type: str
    label: str
    role: str
    mentions: list[dict]
    attributes: dict = {}

class EventOutput(BaseModel):
    id: str
    type: str
    description: str
    neutral_description: Optional[str]
    actors: list[str]
    targets: list[str]
    source_statement: str
    confidence: float

class StructuredOutput(BaseModel):
    nnrt_version: str
    schema_version: str = "1.0"
    input_hash: str
    timestamp: datetime
    transformed: bool
    
    statements: list[StatementOutput]
    uncertainties: list[UncertaintyOutput]
    entities: list[EntityOutput] = []
    events: list[EventOutput] = []
    
    diagnostics: list[dict]
    metadata: dict = {}
    
    rendered_text: str
```

---

## CLI Changes

Location: `nnrt/cli/main.py`

```python
@app.command()
def transform(
    text: str,
    format: str = typer.Option("text", help="Output format: text or structured"),
):
    result = engine.transform(TransformRequest(text=text))
    
    if format == "structured":
        output = build_structured_output(result)
        print(output.model_dump_json(indent=2))
    else:
        print(result.rendered_text)
```

---

## Conversion Function

```python
def build_structured_output(result: TransformResult) -> StructuredOutput:
    statements = []
    for seg in result.context.segments:
        stmt = StatementOutput(
            id=f"stmt_{seg.id}",
            type=seg.statement_type.value,
            original=seg.text,
            neutral=get_rendered_segment(seg, result),
            segment_id=seg.id,
            classification_confidence=seg.statement_confidence,
            contexts=seg.contexts,
            transformations=get_transformations(seg, result),
            flags=get_flags(seg, result),
        )
        statements.append(stmt)
    
    uncertainties = build_uncertainties(result)
    
    return StructuredOutput(
        nnrt_version=VERSION,
        input_hash=hash_input(result.context.input_text),
        timestamp=datetime.utcnow(),
        transformed=result.status == TransformStatus.TRANSFORMED,
        statements=statements,
        uncertainties=uncertainties,
        diagnostics=[d.model_dump() for d in result.diagnostics],
        rendered_text=result.rendered_text,
    )
```

---

## Exit Criteria

- [ ] `StructuredOutput` model exists
- [ ] `nnrt transform --format structured` works
- [ ] Output validates against schema
- [ ] All statement types appear correctly
- [ ] Uncertainties appear in structured form
- [ ] Diagnostics preserved

---

## Estimated Time: 2-3 hours

| Task | Hours |
|------|-------|
| Schema models | 1 |
| CLI integration | 0.5 |
| Conversion function | 1 |
| Testing | 0.5 |
