# Gold Standard: Manual NNRT Decomposition
# One paragraph from the stress test, manually decomposed correctly

## Original Input

> Officer Jenkins deliberately grabbed my left arm with excessive force and twisted it behind my back. I screamed in pain and said "You're hurting me! Please stop!" but he intentionally ignored my pleas because he wanted to inflict maximum damage.

---

## Current NNRT Output (WRONG)

> Officer Jenkins grabbed my left arm with described as excessive force and twisted it behind my back. I spoke loudly in pain and said "You're hurting me! Please stop!" but he appeared to ignore my pleas because he appeared to inflict maximum damage.

### Problems:
- "described as excessive force" — semantic mush
- "appeared to inflict maximum damage" — still smuggles intent
- Linear prose flow preserved — should be decomposed
- Can't distinguish observation from interpretation

---

## Correct NNRT Output (TARGET)

```yaml
statements:
  - id: stmt_001
    type: observation
    content: "Officer Jenkins grabbed reporter's left arm."
    source: {type: reporter}
    confidence: high
    notes: "Physical action, verifiable"

  - id: stmt_002
    type: observation
    content: "Officer Jenkins twisted reporter's arm behind reporter's back."
    source: {type: reporter}
    confidence: high
    notes: "Physical action, verifiable"

  - id: stmt_003
    type: claim
    content: "Reporter states force was applied."
    source: {type: reporter}
    confidence: high
    derived_from: [stmt_001, stmt_002]

  - id: stmt_004
    type: interpretation
    content: "Reporter characterizes force as 'excessive'."
    source: {type: reporter}
    confidence: medium
    derived_from: [stmt_003]
    flags: [subjective_judgment]
    notes: "'Excessive' is reporter's judgment, not objective measure"

  - id: stmt_005
    type: interpretation
    content: "Reporter believes action was 'deliberate'."
    source: {type: reporter}
    confidence: low
    derived_from: [stmt_001, stmt_002]
    flags: [intent_attribution]
    notes: "Reporter inferring intent, not observable"

  - id: stmt_006
    type: observation
    content: "Reporter vocalized loudly."
    source: {type: reporter}
    confidence: high
    notes: "'Screamed' → vocalized loudly (factual description)"

  - id: stmt_007
    type: claim
    content: "Reporter experienced pain."
    source: {type: reporter}
    confidence: high
    notes: "Internal state, can only be claimed by reporter"

  - id: stmt_008
    type: reported_speech
    speaker: reporter
    content: "You're hurting me! Please stop!"
    source: {type: reporter}
    confidence: high
    notes: "Direct quote, preserved verbatim"

  - id: stmt_009
    type: observation
    content: "Officer Jenkins did not respond to reporter's verbal request."
    source: {type: reporter}
    confidence: medium
    notes: "Observable behavior (or lack thereof)"

  - id: stmt_010
    type: interpretation
    content: "Reporter believes officer 'intentionally' ignored pleas."
    source: {type: reporter}
    confidence: low
    derived_from: [stmt_008, stmt_009]
    flags: [intent_attribution]
    notes: "Reporter inferring intent from behavior"

  - id: stmt_011
    type: interpretation
    content: "Reporter believes officer 'wanted to inflict maximum damage'."
    source: {type: reporter}
    confidence: low
    flags: [intent_attribution, extreme_claim]
    notes: "Strong intent attribution, unverifiable"
```

---

## Key Differences

| Aspect | Current Output | Correct Output |
|--------|---------------|----------------|
| **Format** | Prose | Structured statements |
| **Observation vs Interpretation** | Mixed | Explicitly separated |
| **Intent attribution** | Hedged but present | Labeled as interpretation |
| **Subjective terms** | "described as" mush | Flagged with provenance |
| **Verifiability** | Unclear | Explicit confidence levels |
| **Reviewer clarity** | Must re-read original | Can instantly see layers |

---

## Decomposition Rules Applied

1. **Observation**: Physical actions that could be verified by video
   - "grabbed", "twisted", "vocalized" ✓
   
2. **Claim**: Reporter's assertions about their own state
   - "experienced pain" — only reporter can know ✓
   
3. **Interpretation**: Inferences about others' intent/motive
   - "deliberately", "intentionally", "wanted to" → all flagged ✓
   
4. **Reported Speech**: Direct quotes preserved verbatim
   - "You're hurting me!" → kept exactly ✓

5. **Provenance**: Each interpretation links to its source observations
   - "believes force was excessive" ← derived from "force was applied" ✓

---

## What the Reviewer Can Now Do

With correct NNRT output, a reviewer can:

1. **Filter by type**: Show me only observations
2. **Review interpretations**: See all intent attributions flagged
3. **Check provenance**: Trace each interpretation back to observations
4. **Make own judgment**: Observations are neutral, interpretations are explicit

This is what NNRT must produce.
