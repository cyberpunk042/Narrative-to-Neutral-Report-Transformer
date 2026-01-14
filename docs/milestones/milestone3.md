# NNRT — Milestone 3: Intelligence & Edge Cases

## Purpose

Milestone 3 focuses on **intelligent detection capabilities** that go beyond simple pattern matching. The goal is to handle complex real-world scenarios where the system needs to:

1. **Detect when it CAN'T help** (meta-detection)
2. **Flag ambiguity** for human review
3. **Identify contradictions** in the narrative
4. **Handle sarcasm/irony** appropriately

This milestone transforms NNRT from a "dumb transformer" to an "intelligent advisor."

---

## Core Capabilities

### 3.1 Meta-Detection

**Goal:** Detect when transformation is unnecessary, impossible, or should be refused.

| Case | Detection | Response |
|------|-----------|----------|
| Already neutral | No biased language found | Return as-is with NEUTRAL diagnostic |
| All conclusions, no facts | Nothing factual to preserve | REFUSE with explanation |
| Pure opinion | No verifiable events | FLAG for human review |
| Incoherent | Cannot parse meaning | WARN and preserve original |

**Implementation:**
- New context: `SegmentContext.ALREADY_NEUTRAL`
- New context: `SegmentContext.OPINION_ONLY`
- Policy rule: Refuse if all segments are opinion
- Diagnostic: `TRANSFORMATION_NOT_NEEDED`

---

### 3.2 Ambiguity Detection

**Goal:** Flag unclear references that could be misinterpreted.

| Type | Example | Detection |
|------|---------|-----------|
| Pronoun ambiguity | "He hit him" (which he?) | Multiple candidate antecedents |
| Unclear antecedent | "The officer and the man. He ran." | NER + dependency parsing |
| Dangling reference | "They said I did it" (who is they?) | No clear referent |

**Implementation:**
- Extend `p20_tag_spans` with coreference analysis
- New span label: `SpanLabel.AMBIGUOUS_REFERENCE`
- Context: `SegmentContext.AMBIGUOUS`
- Diagnostic: `AMBIGUOUS_REFERENCE_DETECTED`
- Policy: FLAG but preserve (human must clarify)

---

### 3.3 Contradiction Detection

**Goal:** Identify statements that conflict with each other.

| Type | Example | Detection |
|------|---------|-----------|
| Self-contradiction | "I was handcuffed. I punched him." | Physical impossibility |
| Timeline conflict | "At 3pm I was home. At 3pm I was arrested." | Time collision |
| Logical impossibility | "I never touched him. After I shoved him..." | Direct contradiction |

**Implementation:**
- New pass: `p35_detect_contradictions`
- Cross-segment analysis
- New diagnostic: `CONTRADICTION_DETECTED`
- Preserve both statements, flag for review

---

### 3.4 Sarcasm/Irony Detection

**Goal:** Identify sarcastic statements and flag them.

| Type | Example | Detection |
|------|---------|-----------|
| Obvious sarcasm | "Oh yeah, he was SO gentle" | Exaggerated positive + negative context |
| Understatement | "He gave me a little tap" (broken ribs) | Minimized description + injury context |
| Ironic quotation | "For my 'safety'" | Quote marks around positive words |

**Implementation:**
- Context: `SegmentContext.SARCASM` (already exists!)
- Pattern detection in `p25_annotate_context`
- Policy: FLAG, preserve literal text with diagnostic

---

## Architecture Additions

### New Pass: p35_detect_contradictions

```
p00_normalize
p10_segment
p20_tag_spans
p25_annotate_context
p30_extract_identifiers
p35_detect_contradictions  ← NEW
p40_build_ir
p50_policy
p60_augment_ir
p70_render
p80_package
```

### New Context Types

Add to `SegmentContext` enum:
- `ALREADY_NEUTRAL`
- `OPINION_ONLY`
- `AMBIGUOUS`
- `CONTRADICTS_PREVIOUS`

### New Span Labels

Add to `SpanLabel` enum:
- `AMBIGUOUS_REFERENCE`
- `SARCASM_INDICATOR`
- `UNDERSTATEMENT`
- `CONTRADICTION`

---

## Hard Case Coverage

This milestone addresses these hard case levels:

| Level | Cases | Status |
|-------|-------|--------|
| 2 | Pronoun Ambiguity, Unclear Antecedent | → Ambiguity Detection |
| 4 | Obvious Sarcasm, Understatement | → Sarcasm Detection |
| 8 | Self-Contradiction, Timeline Inconsistency | → Contradiction Detection |
| 9 | Already Neutral, Mixed Neutral/Biased | → Meta-Detection |
| 10 | All Conclusions No Facts, Meta-Commentary | → Meta-Detection |

---

## Exit Criteria

- [ ] Meta-detection identifies already-neutral input
- [ ] Meta-detection refuses all-opinion input
- [ ] Ambiguous references are flagged with diagnostics
- [ ] Contradictions are detected and flagged
- [ ] Sarcasm is detected and flagged
- [ ] Hard case tests pass for levels 2, 4, 8, 9, 10
- [ ] All 40+ existing tests still pass

---

## Implementation Priority

### Phase 1: Meta-Detection (Easiest)
1. Add `ALREADY_NEUTRAL` context detection
2. Add policy rules to detect and respond
3. Test with hard_017, hard_018

### Phase 2: Sarcasm/Irony (Medium)
1. Add sarcasm detection patterns to p25
2. Add policy rules to flag
3. Test with hard_007, hard_008

### Phase 3: Ambiguity Detection (Hard)
1. Research coreference resolution
2. Add ambiguity detection logic
3. Test with hard_003, hard_004

### Phase 4: Contradiction Detection (Hardest)
1. Design cross-segment analysis
2. Implement p35_detect_contradictions
3. Test with hard_015, hard_016

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Hard case pass rate | > 80% for levels 2-10 |
| False positive rate | < 10% (wrong flags) |
| Test coverage | > 70% |
| Performance | < 3s per narrative |
