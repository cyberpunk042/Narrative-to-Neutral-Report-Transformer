# Pre-Alpha Specs Index

## Overview

These specs define the implementation path from current state (v0.2) to pre-alpha.

---

## Documents

| Doc | Purpose | Estimated Hours |
|-----|---------|-----------------|
| [road_to_pre_alpha.md](../milestones/road_to_pre_alpha.md) | Master roadmap | N/A |
| [phase1_statement_classification.md](phase1_statement_classification.md) | Classify statements as observation/claim/interpretation | 4-6 |
| [phase2_structured_output.md](phase2_structured_output.md) | JSON output schema | 2-3 |
| [phase3_4_uncertainty_entities.md](phase3_4_uncertainty_entities.md) | Uncertainty & entity/event extraction | 5-6 |
| [phase5_validation.md](phase5_validation.md) | Validation test suites | 3-4 |

---

## Implementation Order

```
Phase 1: Statement Classification
    ↓
Phase 2: Structured Output
    ↓
Phase 3: Uncertainty Output  ─┬─→  Phase 4: Entity/Event Extraction
                              │
                              ↓
Phase 5: Validation
    ↓
PRE-ALPHA COMPLETE
```

---

## Quick Reference

### New Passes
```
p22_classify_statements.py   ← Phase 1
p32_extract_entities.py      ← Phase 4
p34_extract_events.py        ← Phase 4
```

### New Modules
```
nnrt/output/structured.py    ← Phase 2
```

### New Enums
```python
StatementType.OBSERVATION    # "I saw him grab me"
StatementType.CLAIM          # "He grabbed me"
StatementType.INTERPRETATION # "He wanted to hurt me"
StatementType.QUOTE          # "'Stop!' he yelled"
```

### CLI Changes
```bash
nnrt transform "..." --format structured   # JSON output
nnrt transform "..." --format text         # Current behavior
```

---

## Total Estimated Time

| Phase | Hours |
|-------|-------|
| Phase 1 | 4-6 |
| Phase 2 | 2-3 |
| Phase 3 | 2 |
| Phase 4 | 3-4 |
| Phase 5 | 3-4 |
| **Total** | **14-19** |

---

## Exit Criteria Summary

1. **Statement Classification**: Every segment has `statement_type`
2. **Structured Output**: `nnrt --format structured` produces valid JSON
3. **Uncertainty**: All ambiguities in `uncertainties` array
4. **Entity/Event**: Actors and events extracted
5. **Validation**: All test suites pass

---

*Created: 2026-01-13*
