# V1 → V2 Fix Plan: Issue #1 — RAW NEUTRALIZED NARRATIVE Corruption

## Problem Statement

The V2 output contains the ENTIRE structured report embedded inside the RAW NEUTRALIZED NARRATIVE section on a single line. This is a **double rendering bug**.

### What V1 Produces:
```
RAW NEUTRALIZED NARRATIVE (AUTO-GENERATED)
──────────────────────────────────────────────────────────────────────
⚠️ This is machine-generated neutralization. Review for accuracy.

I was frightened and in shock when the officers made physical contact with me...
[~4000 chars of properly neutralized prose narrative]
```

### What V2 Produces:
```
RAW NEUTRALIZED NARRATIVE (AUTO-GENERATED)
──────────────────────────────────────────────────────────────────────
⚠️ This is machine-generated neutralization. Review for accuracy.

══════════════════════════════════════════════════════════════════════ 
NEUTRALIZED REPORT ══════════════════════════════════════════════════
PARTIES ──────────────────────────────────────────────────────────────
INCIDENT PARTICIPANTS: • Reporter (Reporter)...
[ENTIRE STRUCTURED REPORT ON SINGLE LINE]
```

---

## Root Cause Analysis

### Pipeline Order (from `setup_default_pipeline`):
```python
passes=[
    ...
    render,                # p70: Produces PROSE → ctx.rendered_text
    render_structured,     # p90: Produces STRUCTURED OUTPUT → ctx.rendered_text (OVERWRITES)
    safety_scrub,          # p72: Operates on ctx.rendered_text
    cleanup_punctuation,   # p75: Operates on ctx.rendered_text
    package,               # p80: Packages ctx.rendered_text
]
```

### The Bug Flow:

1. **p70_render** produces prose narrative (e.g., "I was frightened...") → stored in `ctx.rendered_text`

2. **p90_render_structured** calls `format_structured_output_v2()`:
   - Passes `rendered_text=ctx.rendered_text` (the prose from p70) ✓
   - `structured_v2.py` line 173: `lines.append(rendered_text)` — embeds the prose ✓
   - Returns the full structured output

3. **p90_render_structured** line 55: `ctx.rendered_text = rendered`
   - **OVERWRITES** `ctx.rendered_text` with the ENTIRE structured output

4. **Next time `p90` or any structured renderer runs**, `ctx.rendered_text` now contains the structured output, not prose. If embedded again → **infinite nesting**

5. Even if not nested, the **output returned to the user is the structured output** stored in `ctx.rendered_text`, which is correct. But the prose inside the RAW NEUTRALIZED NARRATIVE section is **wrong** if `ctx.rendered_text` was already overwritten before p90 ran.

### Wait — Let me re-read this more carefully:

Looking at p90_render_structured.py line 52:
```python
rendered = format_structured_output_v2(
    ...
    rendered_text=ctx.rendered_text or '',  # <-- Gets prose from p70
)

ctx.rendered_text = rendered  # <-- Overwrites with structured output
```

**This is correct behavior for the pipeline.** The structured output SHOULD be in `ctx.rendered_text` at the end.

### So where is the bug?

Let me look at the V2 output more carefully. The issue is:
- `rendered_text` in the V2 structured output contains the structured output AGAIN

This means when `format_structured_output_v2` was called:
- `ctx.rendered_text` already had the structured output from a PREVIOUS p90 run
- OR `ctx.rendered_text` was not the prose but something else

### Check: Is p90 being called TWICE?

Looking at the pipeline:
```python
passes=[
    render,                # p70
    render_structured,     # p90 -- called ONCE
    safety_scrub,
    cleanup_punctuation,
    package,
]
```

p90 is only in the list once. So it's not called twice by the pipeline.

### Alternative hypothesis: V1 renderer is being used first, then V2

Let me check if there's dual rendering happening via a different path.

Actually, looking at the V2 output in the diff (line 522):
```
══════════════════════════════════════════════════════════════════════ 
NEUTRALIZED REPORT ══════════════════════════════════════════════════
```

This is the HEADER of the structured report. So the content inside RAW NEUTRALIZED NARRATIVE is another copy of the structured report.

**Hypothesis**: Before p90 ran its V2 path, `ctx.rendered_text` was ALREADY populated with structured output from the V1 fallback path, OR from a previous invocation.

Let me check web/server.py to see if it's calling render twice:

---

## CONFIRMED ROOT CAUSE

Looking at `scripts/stress_test.py` lines 56-69:

```python
# Run pipeline
result = engine.transform(TransformRequest(text=text), pipeline_id="default")

# THIS IS THE BUG:
report = format_structured_output(
    rendered_text=result.rendered_text,  # <-- This is ALREADY structured output!
    atomic_statements=result.atomic_statements,
    ...
)
```

### The Problem:

1. **Pipeline runs** with `render_structured` (p90) → produces structured output → stores in `ctx.rendered_text`
2. **`result.rendered_text`** now contains the FULL structured report (from p90)
3. **stress_test.py** or whoever generated v2_fresh_output.txt calls `format_structured_output()` AGAIN
4. **V1 renderer** embeds `rendered_text` (which is structured output) into RAW NEUTRALIZED NARRATIVE
5. **DOUBLE RENDERING** — structured output embedded inside itself

### Why V1 Worked:

In V1, the pipeline did NOT include `render_structured` (p90). The flow was:
1. Pipeline produces prose → `ctx.rendered_text` = prose
2. External code calls `format_structured_output()` with prose
3. Structured output created with prose in RAW NEUTRALIZED NARRATIVE section
4. **Single rendering** — prose correctly embedded

### Why V2 Is Broken:

In V2, we added `render_structured` (p90) to the pipeline:
1. Pipeline produces structured output → `ctx.rendered_text` = structured output
2. External code calls `format_structured_output()` AGAIN with structured output
3. **Double rendering** — structured output embedded inside itself

---

## FIX OPTIONS

### Option A: Remove p90 from Pipeline (Quick Fix)
- Remove `render_structured` from the default pipeline
- Let external callers invoke structured rendering explicitly
- **Pro**: Minimal change, immediate fix
- **Con**: Breaks the "pipeline produces final output" architecture

### Option B: Store Prose Separately (Proper Fix)
- Add `ctx.prose_text` to store the prose from p70
- Have p90 use `ctx.prose_text` for RAW NEUTRALIZED NARRATIVE
- Don't overwrite `ctx.rendered_text` until p90 is done
- **Pro**: Clean architecture, supports both prose and structured output
- **Con**: Requires changes to context and multiple passes

### Option C: Don't Embed in p90 (Avoid Double Rendering)
- Modify structured_v2.py to NOT embed `rendered_text` if it already contains structured markers
- Add detection logic for "═" or "NEUTRALIZED REPORT" in input
- **Pro**: Self-healing, defensive
- **Con**: Hacky, doesn't address root architecture issue

### Option D: Save Prose Before p90, Restore After (Minimal Change)
- In p90, save the prose to a different field before overwriting
- Use the saved prose for the RAW NEUTRALIZED NARRATIVE section
- **Pro**: Minimal pipeline changes
- **Con**: Adds complexity to p90

---

## RECOMMENDED FIX: Option D (Minimal, Targeted)

1. In `p90_render_structured.py`, before calling the renderer:
   ```python
   # Save prose for embedding in structured output
   prose_text = ctx.rendered_text or ''
   
   rendered = format_structured_output_v2(
       ...
       rendered_text=prose_text,  # Pass the PROSE, not what p90 will produce
   )
   
   ctx.rendered_text = rendered
   ```

2. This is actually what's already happening in the code. The REAL issue is:
   - **External code is calling `format_structured_output()` AGAIN after the pipeline**

3. **FIX**: Remove the external call to `format_structured_output()` in stress_test.py
   - The pipeline already produces the structured output
   - Just use `result.rendered_text` directly

---

## IMPLEMENTATION PLAN

### Step 1: Verify the Issue
Run:
```bash
python -c "
from nnrt.core.engine import Engine
from nnrt.cli.main import setup_default_pipeline
from nnrt.core.context import TransformRequest

with open('tests/fixtures/stress_test_narrative.txt') as f:
    text = f.read()

engine = Engine()
setup_default_pipeline(engine)
result = engine.transform(TransformRequest(text=text), pipeline_id='default')

# Check if result.rendered_text already contains structured output
print('Contains NEUTRALIZED REPORT header:', 'NEUTRALIZED REPORT' in result.rendered_text)
print('First 200 chars:', result.rendered_text[:200])
"
```

### Step 2: Fix stress_test.py
Remove the extra `format_structured_output()` call — just use `result.rendered_text` directly.

### Step 3: Check Other Callers
Verify that web/server.py and any other code paths don't have the same double-rendering issue.

---

*Root cause confirmed. Ready to implement fix.*
