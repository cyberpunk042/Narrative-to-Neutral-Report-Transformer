# Data Flow Problem: Why Context Gets Lost

## The Current Flow (Broken)

```
Input Text
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  p20_tag_spans                                          │
│  - Detects "assault" → labels as LEGAL_CONCLUSION       │
│  - Doesn't know if it's a charge or accusation          │
│  - Context LOST at this point                           │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  p50_policy                                             │
│  - Sees "accused me of assaulting" → flags for preserve │
│  - Makes a DECISION, but decision isn't attached to     │
│    the span in a way render can see                     │
│  - Creates PolicyDecision object but it's disconnected  │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  p70_render                                             │
│  - Sees LEGAL_CONCLUSION span                           │
│  - Has no idea policy said to preserve                  │
│  - REMOVES IT (wrong!)                                  │
│  - Has to RE-ANALYZE text to check for charge context   │
│  - This is the hack we added                            │
└─────────────────────────────────────────────────────────┘
```

## The Problem in One Sentence

**Spans carry labels, but not decisions about what to do with them.**

---

## What Should Happen

```
Input Text
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  p20_tag_spans                                          │
│  - Detects "assault" → labels as LEGAL_CONCLUSION       │
│  - Adds span to context                                 │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  p25_annotate_context (NEW)                             │
│  - Sees segment contains "accused me of"                │
│  - Tags segment as CHARGE_CONTEXT                       │
│  - Now the context is EXPLICIT IN THE DATA              │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  p50_policy                                             │
│  - Evaluates rule: "if LEGAL_CONCLUSION in CHARGE       │
│    context, then PRESERVE"                              │
│  - Attaches PRESERVE decision to the SPAN               │
│  - ctx.decisions.append(Decision(span_id, PRESERVE))    │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  p70_render                                             │
│  - Sees LEGAL_CONCLUSION span                           │
│  - Checks: ctx.get_decision(span.id) → PRESERVE         │
│  - Does NOT remove it                                   │
│  - No re-analysis needed!                               │
└─────────────────────────────────────────────────────────┘
```

---

## Key Insight: Decisions Should Be Attached to Spans

Instead of:
```python
decisions: list[PolicyDecision]  # Floating, disconnected
```

We need:
```python
span_decisions: dict[str, PolicyDecision]  # span_id → decision
```

Then render can simply:
```python
decision = ctx.span_decisions.get(span.id)
if decision and decision.action == PolicyAction.PRESERVE:
    continue  # Don't touch it
```

---

## The Three Levels of Data We Need

### Level 1: Raw Classification (Current - Works)
```
Span: "assault"
Label: LEGAL_CONCLUSION
```

### Level 2: Contextual Meaning (Missing)
```
Segment Context: CHARGE_DESCRIPTION
Meaning: "assault" is what they CHARGED me with, not my accusation
```

### Level 3: Action Decision (Disconnected)
```
Decision: PRESERVE
Reason: Legal terms in charge context are preserved
Affected: span_id="span_042"
```

We have Level 1 and Level 3, but:
- Level 2 is missing entirely
- Level 3 isn't connected to Level 1

---

## Minimal Fix vs Full Refactor

### Minimal Fix (What we did)
- Hack: Check charge context in render
- Problem: Logic scattered, not reusable

### Proper Fix (What we should do)
- Add `segment.contexts` field
- Attach decisions to spans
- Passes check decisions, not labels

---

## Implementation Priority

1. **Add span_decisions to context** — Immediate impact
2. **Have policy update span_decisions** — Wire it up
3. **Have render check span_decisions** — Remove hacks
4. **Add context annotation pass** — Prevent future hacks
