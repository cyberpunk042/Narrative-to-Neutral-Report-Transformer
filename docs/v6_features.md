# V6 Verification Platform Features

NNRT V6 transforms the tool from a simple neutralization utility into a comprehensive **Verification Platform** for investigating incident narratives. This document covers the three major V6 features.

## Overview

| Feature | Purpose | Use Case |
|---------|---------|----------|
| **Timeline Reconstruction** | Build chronological event timeline | Identify memory gaps, sequence events |
| **Question Generation** | Auto-generate investigation questions | Prepare follow-up interviews |
| **Multi-Narrative Comparison** | Compare multiple accounts | Cross-reference witness/officer statements |

---

## 1. Enhanced Timeline Reconstruction

### What It Does

The V6 timeline system extracts and organizes temporal information from narratives:

- **Temporal Expressions**: Times, dates, durations, relative markers
- **Temporal Relations**: How events relate (before, after, during, etc.)
- **Multi-Day Support**: Track events across days, weeks, months
- **Gap Detection**: Identify unexplained periods that need investigation

### Pipeline Stages

```
p44a_temporal_expressions  →  Extract times, dates, markers
         ↓
p44b_temporal_relations    →  Determine event relationships
         ↓
p44c_timeline_ordering     →  Build ordered timeline
         ↓
p44d_timeline_gaps         →  Detect unexplained gaps
```

### Sample Output

```
RECONSTRUCTED TIMELINE
──────────────────────────────────────────────────────────────────────
  ┌─── INCIDENT DAY (Day 0) ───
  │
  │  ⏱️ [11:30 PM] Walking on Cedar Street
  │  ○  ⚠️ Officer approached complainant
  │  ⟳ [About 20 minutes later] Sgt. Williams arrived
  │
  ┌─── NEXT DAY (Day 1) ───
  │
  │  ⟳ [The next day] Visited emergency room
  │
  ┌─── ~3 MONTHS LATER (Day 91) ───
  │
  │  ⟳ [Three months later] Filed formal complaint
  │
  └─────────────────────────────

  Legend: ⏱️=explicit time  ⟳=relative time  ○=inferred  ⚠️=gap needs investigation

  ⚠️ TIMELINE GAPS REQUIRING INVESTIGATION:
    1. [UNCERTAIN] What happened between 'Officer approached' and 'woke up'?

  📊 Timeline: 6 events across 3 day(s)
```

### Key Data Structures

```python
from nnrt.ir import TemporalExpression, TemporalRelationship, TimelineEntry, TimeGap

# TemporalExpression: A normalized time reference
expr = TemporalExpression(
    original_text="11:30 PM",
    type=TemporalExpressionType.TIME,
    normalized_value="T23:30:00",  # ISO format
)

# TimelineEntry: An event in the timeline
entry = TimelineEntry(
    event_id="evt_001",
    day_offset=0,  # 0 = incident day, 1 = next day, etc.
    normalized_time="T23:30:00",
    time_source=TimeSource.EXPLICIT,
)

# TimeGap: A detected gap in the narrative
gap = TimeGap(
    gap_type=TimeGapType.UNCERTAIN,
    requires_investigation=True,
    suggested_question="What happened during this period?",
)
```

---

## 2. Automatic Question Generation

### What It Does

V6 analyzes the narrative and timeline to automatically generate investigation questions:

- **Timeline Gap Questions**: What happened during unexplained periods?
- **Missing Actor Questions**: Who performed this action? (passive voice)
- **Vague Statement Questions**: Clarify "someone", "something", etc.
- **Injury/Medical Questions**: Follow up on health-related claims

### Priority Levels

| Priority | Icon | Examples |
|----------|------|----------|
| **CRITICAL** | 🔴 | Memory gaps, major timeline discontinuities |
| **HIGH** | 🟠 | Missing actors, injury details |
| **MEDIUM** | 🟡 | Vague language, unclear descriptions |
| **LOW** | ⚪ | Minor clarifications |

### Usage

```python
from nnrt.v6.questions import generate_all_questions

question_set = generate_all_questions(
    time_gaps=result.time_gaps,
    atomic_statements=result.atomic_statements,
    events=result.events,
)

print(f"Total questions: {question_set.total_count}")
print(f"Critical: {question_set.critical_count}")

for q in question_set.questions:
    print(f"[{q.priority.value}] {q.text}")
```

### Sample Output

```
INVESTIGATION QUESTIONS
──────────────────────────────────────────────────────────────────────
Auto-generated questions for investigator follow-up:

  🔴 [CRITICAL] Timeline Gap
     What happened between 'Officer approached' and 'woke up in police car'?

  🟠 [HIGH] Missing Actor
     Who performed this action?
     Context: "I was grabbed."

  🟠 [HIGH] Injury Detail
     Can you describe the injury and any medical treatment received?
     Context: "My shoulder was hurting badly."

  🟡 [MEDIUM] Vague Description
     Who specifically?
     Context: "when someone approached me"

  📊 Question Summary: 12 total
      🔴 Critical: 4
      🟠 High Priority: 4
```

---

## 3. Multi-Narrative Comparison

### What It Does

Compare multiple accounts of the same incident to identify:

- **Agreements**: Facts that multiple sources confirm
- **Contradictions**: Conflicting statements between accounts
- **Unique Claims**: Information only appearing in one account
- **Timeline Discrepancies**: Different event sequences

### Usage

```python
from nnrt.v6.comparison import compare_narratives, format_comparison_report

# Compare two narratives
result = compare_narratives([
    ("complainant", complainant_result),
    ("officer", officer_result),
])

# Print formatted report
print(format_comparison_report(result))

# Access findings programmatically
for finding in result.findings:
    print(f"[{finding.type.value}] {finding.description}")
```

### Sample Output

```
══════════════════════════════════════════════════════════════════════
              MULTI-NARRATIVE COMPARISON REPORT
══════════════════════════════════════════════════════════════════════

📊 SUMMARY
   Sources Compared: 2 (complainant, officer)
   Total Findings: 8
   Overall Consistency: 12%

   ✅ Agreements: 1
   ❌ Contradictions: 0
   ⚠️ Unique Claims: 7
   🔄 Timeline Discrepancies: 0

──────────────────────────────────────────────────────────────────────
⚠️ UNIQUE CLAIMS (7)
──────────────────────────────────────────────────────────────────────

  Only complainant mentions: He twisted my arm behind my back...
    • complainant: "He twisted my arm behind my back and pushed me to..."

  Only complainant mentions: I did not resist...
    • complainant: "I did not resist..."
```

### Severity Levels

| Severity | Description |
|----------|-------------|
| **CRITICAL** | Major factual contradiction (e.g., "I resisted" vs "I did not resist") |
| **SIGNIFICANT** | Important difference (e.g., number of officers) |
| **MINOR** | Small detail difference (e.g., exact wording) |

---

## Integration

### Web Server

V6 features are automatically integrated into the structured output mode:

```bash
curl -X POST http://localhost:5000/transform \
  -H "Content-Type: application/json" \
  -d '{"text": "...", "mode": "structured"}'
```

### CLI

```bash
nnrt transform --input narrative.txt --output report.txt --mode structured
```

### Programmatic

```python
from nnrt.core.engine import Engine
from nnrt.cli.main import setup_default_pipeline

engine = Engine()
setup_default_pipeline(engine)

result = engine.transform(TransformRequest(text=text))

# Access V6 data
print(f"Timeline entries: {len(result.timeline)}")
print(f"Time gaps: {len(result.time_gaps)}")
print(f"Temporal expressions: {len(result.temporal_expressions)}")
```

---

## Best Practices

### 1. Timeline Analysis

- Look for **UNCERTAIN** gaps - these often indicate memory loss or key missing information
- Pay attention to **day_offset** changes - incidents spanning multiple days need careful sequencing
- Use `estimated_minutes_from_start` for events with explicit times

### 2. Question Prioritization

- Address **CRITICAL** questions first - they often reveal the most important gaps
- **HIGH** priority missing actor questions may indicate passive voice used to obscure responsibility
- Use `follow_up_hints` for investigator guidance

### 3. Narrative Comparison

- Low **overall_consistency** scores suggest significantly different accounts
- Focus on **CRITICAL** severity contradictions
- **UNIQUE_CLAIM** findings in force-related events are particularly important to verify

---

## API Reference

### Timeline

```python
# Access timeline data
result.temporal_expressions  # List[TemporalExpression]
result.temporal_relationships  # List[TemporalRelationship]
result.timeline  # List[TimelineEntry]
result.time_gaps  # List[TimeGap]
```

### Questions

```python
from nnrt.v6.questions import (
    generate_all_questions,
    QuestionSet,
    InvestigationQuestion,
    QuestionPriority,
    QuestionCategory,
)
```

### Comparison

```python
from nnrt.v6.comparison import (
    compare_narratives,
    format_comparison_report,
    ComparisonResult,
    ComparisonFinding,
    ComparisonType,
    SeverityLevel,
)
```
