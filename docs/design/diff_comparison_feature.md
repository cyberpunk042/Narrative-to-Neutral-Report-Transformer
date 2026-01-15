# Diff Comparison Feature — Implementation Plan

**Status**: � In Progress  
**Priority**: High  
**Created**: 2026-01-14  
**Approach**: Option A — Track in Render Pass

---

## Overview

Enable users to see exactly what changed during transformation and WHY through:
- Inline diff highlighting in the UI
- Hover tooltips explaining each change
- Per-segment transformation records

---

## Architecture

```
Input Text → Segments → [Passes] → p70_render (records transforms) → Output
                                         ↓
                           SegmentTransform records
                                         ↓
                              API diff_data response
                                         ↓
                            Frontend Diff Renderer
```

---

## Phase 1: Add SegmentTransform Model ✅

**Files to modify:**
- `nnrt/ir/schema_v0_1.py` — Add `SegmentTransform` model
- Update `Segment` to include `transforms` field

```python
class SegmentTransform(BaseModel):
    """Record of a single text transformation within a segment."""
    
    original_text: str = Field(..., description="Text that was changed")
    replacement_text: str = Field(..., description="What it became (empty if deleted)")
    reason_code: str = Field(..., description="Machine-readable reason (e.g., intent_attribution)")
    reason_message: str = Field(..., description="Human-readable explanation")
    start_offset: int = Field(..., description="Start position within segment.text")
    end_offset: int = Field(..., description="End position within segment.text")
    policy_rule_id: Optional[str] = Field(None, description="Rule that triggered this transform")
```

---

## Phase 2: Refactor p70_render to Record Transforms

**Files to modify:**
- `nnrt/passes/p70_render.py`

**Changes:**
1. Before applying a transformation, record it in segment.transforms
2. Capture the exact span being transformed
3. Include the reason from the policy decision or flagged span

**Key transformation points to instrument:**
- Intent attribution removal
- Loaded language replacement
- Hedging word removal
- Direct quote preservation (no transform, but record why)

---

## Phase 3: Add diff_data to API Response

**Files to modify:**
- `nnrt/output/structured.py` — Add `DiffSegment`, `DiffData` models
- `web/server.py` — Include diff_data in response

**New response structure:**
```json
{
  "diff_data": {
    "segments": [
      {
        "segment_id": "seg_001",
        "original": "The officer deliberately grabbed my arm",
        "neutral": "The officer made contact with my arm",
        "start_char": 0,
        "end_char": 42,
        "transforms": [
          {
            "original": "deliberately",
            "replacement": "",
            "reason_code": "intent_attribution",
            "reason": "Removed intent attribution",
            "position": [12, 24]
          }
        ]
      }
    ],
    "total_transforms": 3,
    "segments_changed": 2,
    "segments_unchanged": 5
  }
}
```

---

## Phase 4: Frontend Diff Renderer

**Files to modify:**
- `web/app.js` — Add diff rendering logic
- `web/styles.css` — Add diff highlighting styles
- `web/index.html` — Add diff view toggle

**UI Components:**
1. **Toggle button** in output panel: "Show Diff"
2. **Diff view** with inline annotations:
   - ~~struck-through red~~ for deletions
   - **green underline** for additions
3. **Hover tooltip** with reason message
4. **Category legend** (intent, loaded language, etc.)

---

## Phase 5: Polish & Enhancements

- Click on transform to jump to relevant diagnostic
- Filter transforms by reason category
- Side-by-side view option
- Export diff as HTML/PDF

---

## Reason Codes

| Code | Category | Example | Message |
|------|----------|---------|---------|
| `intent_attribution` | Intent | "deliberately" | Removed intent attribution |
| `loaded_language` | Language | "grabbed" → "made contact with" | Neutralized loaded language |
| `legal_conclusion` | Legal | "assaulted" | Avoided legal conclusion |
| `emotional_language` | Emotional | "terrified" | Softened emotional language |
| `hedging_removed` | Hedging | "obviously" | Removed hedging word |
| `quote_preserved` | Quote | (no change) | Preserved direct quote |

---

## Progress Tracker

- [x] Phase 1: Add SegmentTransform model ✅
- [x] Phase 2: Refactor p70_render ✅
- [x] Phase 3: API diff_data response ✅
- [x] Phase 4: Frontend diff renderer ✅
- [ ] Phase 5: Polish

---

## Testing

1. Transform test narrative with known changes
2. Verify transforms are recorded with correct positions
3. Verify diff_data appears in API response
4. Verify UI renders diff correctly
5. Verify hover tooltips work
