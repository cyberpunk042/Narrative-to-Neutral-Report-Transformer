# Phase 4 Implementation Plan: Entity & Event Extraction

## Overview
Phase 4 focuses on extracting structured **Entities** (people, objects) and **Events** (actions, interactions) from the narrative.
We will leverage the existing `nnrt/passes/p40_build_ir.py` pass, which already contains foundational logic for this, rather than creating new passes.

## Goal
Populate the `entities` and `events` arrays in the `StructuredOutput` JSON.

## Implementation Steps

### 1. Analysis of Existing `p40_build_ir.py`
The current pass uses spaCy to:
- Identify entities from noun chunks.
- Assign roles (Reporter, Subject, Authority) based on heuristics.
- Extract events from verbs.
- Link actors and targets.

**Gap Analysis:**
- **Identifiers vs Entities**: `p30` extracts "Badge #1234", but `p40` extracts "The officer". We need to merge these or clearly easier output them.
- **Deduplication**: `p40` has basic deduplication. We need to ensure "Officer Smith" and "He" (if referring to Smith) are the same entity.
- **Output Mapping**: The `StructuredOutput` schema needs to be wired up to `TransformResult.entities` and `TransformResult.events`.

### 2. Update `nnrt/output/structured.py`
Map the IR models to the Output models.

```python
def build_structured_output(result, ...):
    ...
    # Map Entities
    entities = []
    for ent in result.entities:
        entities.append(EntityOutput(
            id=ent.id,
            type="person", # Logic to determine type (person/vehicle/etc)
            label=ent.mentions[0] if ent.mentions else "unknown",
            role=ent.role.value,
            mentions=[{"text": m} for m in ent.mentions], # Simplified
        ))

    # Map Events
    events = []
    for evt in result.events:
        events.append(EventOutput(
            id=evt.id,
            type=evt.type.value,
            description=evt.description,
            actors=[evt.actor_id] if evt.actor_id else [],
            targets=[evt.target_id] if evt.target_id else [],
            source_statement=evt.source_spans[0] if evt.source_spans else "unknown",
            confidence=evt.confidence
        ))
```

### 3. Refine `p40_build_ir.py`
Enhance the extraction logic:
- **Better Role Inference**: Use `p25` context (e.g., if inside `CHARGE_DESCRIPTION`, the subject is likely the target).
- **Consolidate Entities**: Merge "Identifier" findings (like names) into Entities.
- **Event Types**: Ensure `EventType` enum maps cleanly to output.

### 4. Testing
Create `tests/test_extraction.py` to verify:
- "I saw him" -> Reporter (Actor), Subject (Target)
- "Officer Smith arrested me" -> Officer Smith (Actor), Reporter (Target)

## Timeline
- **Step 1 & 2 (Wiring)**: 1 hour
- **Step 3 (Refinement)**: 2 hours
- **Step 4 (Testing)**: 1 hour
**Total**: 4 hours

## Validation
Run `nnrt transform` on the "Observation/Claim" test cases and verify the `entities` and `events` JSON fields are populated and correct.
