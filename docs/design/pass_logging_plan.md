# Pass Logging Instrumentation Plan

## Overview

This document tracks the instrumentation of passes with channel-aware logging.

---

## Channel Mapping

| Pass | Channel | Rationale |
|------|---------|-----------|
| `p00_normalize` | PIPELINE | Basic preprocessing |
| `p10_segment` | PIPELINE | Structural segmentation |
| `p20_tag_spans` | TRANSFORM | Semantic labeling |
| `p22_classify_statements` | TRANSFORM | Classification |
| `p25_annotate_context` | TRANSFORM | Context annotation |
| `p26_decompose` | TRANSFORM | Decomposition |
| `p27_classify_atomic` | TRANSFORM | Classification |
| `p28_link_provenance` | TRANSFORM | Provenance linking |
| `p30_extract_identifiers` | EXTRACT | Identifier extraction |
| `p32_extract_entities` | EXTRACT | Entity extraction |
| `p34_extract_events` | EXTRACT | Event extraction |
| `p40_build_ir` | PIPELINE | IR assembly |
| `p50_policy` | POLICY | Policy evaluation |
| `p60_augment_ir` | PIPELINE | IR augmentation |
| `p70_render` | RENDER | Text rendering |
| `p75_cleanup_punctuation` | RENDER | Output cleanup |
| `p80_package` | PIPELINE | Result packaging |

---

## Log Points by Pass

### p00_normalize (PIPELINE)
- **INFO**: Input/output character counts
- **VERBOSE**: Paragraph count, unicode normalizations applied

### p10_segment (PIPELINE)
- **INFO**: Segment count created
- **VERBOSE**: Quote-aware merges performed
- **DEBUG**: Individual segment boundaries

### p20_tag_spans (TRANSFORM)
- **INFO**: Total spans created, flags detected
- **VERBOSE**: Intent attribution found, legal conclusions found
- **DEBUG**: Per-token classification decisions

### p22_classify_statements (TRANSFORM)
- **INFO**: Classification distribution (observations/claims/etc)
- **VERBOSE**: Per-segment classification

### p25_annotate_context (TRANSFORM)
- **INFO**: Contexts applied (quotes, reported_speech, etc)
- **VERBOSE**: Per-segment context annotations

### p26_decompose (TRANSFORM)
- **INFO**: Atomic statements created
- **VERBOSE**: Clause splits (conj, advcl, ccomp)
- **DEBUG**: Clause boundary decisions

### p27_classify_atomic (TRANSFORM)
- **INFO**: Classification counts by type
- **VERBOSE**: Intent/interpretation flags

### p28_link_provenance (TRANSFORM)
- **INFO**: Provenance links created
- **VERBOSE**: Derivation chains

### p30_extract_identifiers (EXTRACT)
- **INFO**: Identifiers found by type (badge, date, location)
- **VERBOSE**: Individual identifier details

### p32_extract_entities (EXTRACT) 
- **INFO**: Entity count, role distribution
- **VERBOSE**: Pronoun resolution decisions
- **DEBUG**: NER results, mention linking

### p34_extract_events (EXTRACT)
- **INFO**: Event count by type
- **VERBOSE**: Event-entity linking

### p40_build_ir (PIPELINE)
- **INFO**: IR components assembled
- **VERBOSE**: Component counts

### p50_policy (POLICY)
- **INFO**: Rule matches count, decisions count
- **VERBOSE**: Per-rule match details
- **DEBUG**: Rule condition evaluation

### p60_augment_ir (PIPELINE)
- **INFO**: Augmentations applied

### p70_render (RENDER)
- **INFO**: Mode (template/LLM), segments rendered
- **VERBOSE**: Transform count per segment
- **DEBUG**: Rule applications

### p75_cleanup_punctuation (RENDER)
- **INFO**: Cleanups applied
- **VERBOSE**: Individual fixes

### p80_package (PIPELINE)
- **INFO**: Final status

---

## Implementation Order

1. **Phase 1**: Core passes (p00, p10, p50, p70, p80) — 5 files
2. **Phase 2**: Transform passes (p20, p22, p25, p26, p27, p28) — 6 files  
3. **Phase 3**: Extraction passes (p30, p32, p34, p40) — 4 files
4. **Phase 4**: Cleanup passes (p60, p75) — 2 files

---

## Template Pattern

Each pass should follow this pattern:

```python
"""
Pass XX — Description
"""

from nnrt.core.context import TransformContext
from nnrt.core.logging import get_pass_logger

PASS_NAME = "pXX_name"
log = get_pass_logger(PASS_NAME)


def pass_function(ctx: TransformContext) -> TransformContext:
    """Docstring."""
    log.info("starting", input_count=len(ctx.segments))
    
    # ... processing ...
    
    for item in items:
        log.verbose("processed_item", item_id=item.id)
        log.debug("item_details", raw_data=item.data)
    
    log.info("completed", output_count=result_count)
    
    ctx.add_trace(...)
    return ctx
```

---

## Status

| Pass | Status | Notes |
|------|--------|-------|
| p00_normalize | ✅ Done | INFO: char counts, VERBOSE: paragraphs |
| p10_segment | ✅ Done | INFO: segment count, VERBOSE: quote merges |
| p20_tag_spans | ✅ Done | INFO: span count + flags, VERBOSE: detections |
| p22_classify_statements | ✅ Done | INFO: classification distribution |
| p25_annotate_context | ✅ Done | INFO: annotation counts, VERBOSE: detections |
| p26_decompose | ✅ Done | INFO: atomic statement count |
| p27_classify_atomic | ✅ Done | INFO: type distribution |
| p28_link_provenance | ✅ Done | INFO: link count |
| p30_extract_identifiers | ✅ Done | INFO: identifier count by type |
| p32_extract_entities | ✅ Done | INFO: entity count by role |
| p34_extract_events | ✅ Done | INFO: event count by type |
| p40_build_ir | ✅ Done | INFO: IR component counts |
| p50_policy | ✅ Done | INFO: match/decision counts, VERBOSE: rule details |
| p60_augment_ir | ✅ Done | VERBOSE: stub note |
| p70_render | ✅ Done | INFO: mode + output stats |
| p75_cleanup_punctuation | ✅ Done | INFO: fix types applied |
| p80_package | ✅ Done | INFO: final summary |

---

*Created: 2026-01-14*
*Completed: 2026-01-14*
