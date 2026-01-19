# STAGE 3 AUDIT: Renderer Simplification

**Audit Date**: 2026-01-19
**Based on**: V1 structured.py (git abc0212, 2019 lines) vs structured_v2.py (493 lines)

---

## Stage 3 Objective (from milestone document)

> Strip the renderer (`structured.py`) down to **formatting-only**. It should receive pre-classified, pre-selected atoms and simply format them for display.

> **Outcome**: No classification logic. No selection logic. No business logic. Just formatting.

---

## PART 1: V1 (structured.py) ANALYSIS

### File Stats
- **Lines**: 2019
- **Function signature**: `format_structured_output(rendered_text, atomic_statements, entities, events, identifiers, metadata, timeline, time_gaps, segments)`
- **NO ctx parameter**
- **NO selection_result parameter**

### V1 Logic Inventory (Lines referenced from structured_py_git_version.py)

| Logic Block | Lines | Lines Count | Category |
|-------------|-------|-------------|----------|
| PARTIES role categorization | 143-234 | 91 | SELECTION |
| REFERENCE DATA extraction | 236-315 | 79 | FORMATTING |
| Statement grouping/dedup | 323-613 | 290 | CLASSIFICATION |
| `neutralize_for_observed()` | 391-422 | 31 | CLASSIFICATION |
| `is_strict_camera_friendly()` | 424-553 | 129 | CLASSIFICATION |
| `is_camera_friendly()` | 555-562 | 7 | CLASSIFICATION |
| `is_follow_up_event()` | 564-567 | 3 | CLASSIFICATION |
| `is_source_derived()` | 569-572 | 3 | CLASSIFICATION |
| OBSERVED EVENTS generation | 614-809 | 195 | SELECTION + V9 generation |
| ITEMS DISCOVERED extraction | 828-1031 | 203 | EXTRACTION |
| NARRATIVE EXCERPTS grouping | 1033-1069 | 36 | SELECTION |
| SOURCE-DERIVED with provenance | 1072-1116 | 44 | SELECTION + FORMATTING |
| `_is_medical_provider_content()` | 1125-1134 | 9 | CLASSIFICATION |
| SELF-REPORTED (5 subsections) | 1136-1197 | 61 | SELECTION |
| LEGAL ALLEGATIONS | 1200-1207 | 7 | FORMATTING |
| CHARACTERIZATIONS | 1209-1218 | 9 | FORMATTING |
| INFERENCES | 1220-1229 | 9 | FORMATTING |
| INTERPRETATIONS | 1231-1237 | 6 | FORMATTING |
| CONTESTED ALLEGATIONS | 1239-1248 | 9 | FORMATTING |
| MEDICAL FINDINGS with routing | 1250-1272 | 22 | SELECTION |
| ADMINISTRATIVE ACTIONS | 1274-1282 | 8 | FORMATTING |
| QUOTES speaker extraction | 1284-1494 | 210 | EXTRACTION |
| EVENTS VALIDATION | 1496-1567 | 71 | VALIDATION |
| TIMELINE with pronoun resolution | 1569-1932 | 363 | SELECTION + CLASSIFICATION |
| INVESTIGATION QUESTIONS | 1934-1994 | 60 | GENERATION |
| RAW NARRATIVE | 1996-2019 | 23 | FORMATTING |

### Summary of V1 Logic Categories

| Category | Lines | Percentage |
|----------|-------|------------|
| **CLASSIFICATION** (inline functions + patterns) | ~460 | 23% |
| **SELECTION** (choosing what goes where) | ~400 | 20% |
| **EXTRACTION** (items, quotes) | ~413 | 20% |
| **VALIDATION** (events, quotes) | ~71 | 4% |
| **GENERATION** (questions, V9 events) | ~255 | 13% |
| **FORMATTING** (pure display) | ~420 | 21% |

**V1 is only ~21% pure formatting. The other ~79% is business logic.**

---

## PART 2: structured_v2.py ANALYSIS

### File Stats
- **Lines**: 493
- **Function signature**: `format_structured_output_v2(selection_result, entities, events, identifiers, timeline, time_gaps, atomic_statements, metadata, rendered_text)`
- **REQUIRES selection_result parameter**

### structured_v2.py Logic Inventory

| Component | Lines | Category |
|-----------|-------|----------|
| Main function | 17-145 | FORMATTING |
| `_render_parties()` | 152-184 | FORMATTING (reads sel.incident_participants) |
| `_render_reference_data()` | 187-221 | FORMATTING |
| `_render_observed_events()` | 224-242 | FORMATTING (reads sel.observed_events) |
| `_render_follow_up_events()` | 245-264 | ⚠️ CONTAINS pronoun normalization (logic) |
| `_render_source_derived()` | 267-282 | FORMATTING |
| `_render_narrative_excerpts()` | 285-319 | FORMATTING |
| `_render_self_reported()` | 322-335 | FORMATTING |
| `_render_reporter_descriptions()` | 338-352 | FORMATTING |
| `_render_medical_findings()` | 355-370 | FORMATTING |
| `_render_quotes()` | 373-411 | FORMATTING |
| `_render_timeline()` | 414-469 | FORMATTING |
| `_get_role_display()` | 476-481 | HELPER |
| `_deduplicate()` | 484-492 | HELPER |

### structured_v2.py Problems

#### Problem 1: Still contains inline logic (lines 56-62)
```python
# V2 still groups statements by epistemic_type inline
statements_by_epistemic = defaultdict(list)
if atomic_statements:
    for stmt in atomic_statements:
        epistemic = getattr(stmt, 'epistemic_type', 'unknown')
        text = getattr(stmt, 'text', str(stmt))
        statements_by_epistemic[epistemic].append(text)
```
This is **SELECTION logic** that should be in p55_select.

#### Problem 2: Inline pronoun normalization (lines 258-261)
```python
text = re.sub(r'\bI\s+went\b', 'Reporter went', text)
text = re.sub(r'\bI\s+filed\b', 'Reporter filed', text)
text = re.sub(r'\bI\s+', 'Reporter ', text)
```
This is **CLASSIFICATION logic** that should be in a pass.

#### Problem 3: Missing sections vs V1

| V1 Section | structured_v2.py | Status |
|------------|------------------|--------|
| PARTIES (3 subsections) | `_render_parties()` | ✅ |
| REFERENCE DATA | `_render_reference_data()` | ✅ |
| OBSERVED EVENTS (STRICT) | `_render_observed_events()` | ✅ |
| OBSERVED EVENTS (FOLLOW-UP) | `_render_follow_up_events()` | ✅ |
| **ITEMS DISCOVERED** | *NONE* | ❌ MISSING |
| NARRATIVE EXCERPTS | `_render_narrative_excerpts()` | ✅ |
| SOURCE-DERIVED | `_render_source_derived()` | ✅ |
| SELF-REPORTED (ACUTE) | *combined* | ⚠️ |
| SELF-REPORTED (INJURY) | *combined* | ⚠️ |
| SELF-REPORTED (PSYCHOLOGICAL) | *combined* | ⚠️ |
| SELF-REPORTED (SOCIOECONOMIC) | *combined* | ⚠️ |
| SELF-REPORTED (GENERAL) | `_render_self_reported()` | ⚠️ Only handles 'self_report' |
| LEGAL ALLEGATIONS | *NONE* | ❌ MISSING |
| REPORTER CHARACTERIZATIONS | `_render_reporter_descriptions()` | ✅ |
| REPORTER INFERENCES | *NONE* | ❌ MISSING |
| REPORTER INTERPRETATIONS | *NONE* | ❌ MISSING |
| CONTESTED ALLEGATIONS | *NONE* | ❌ MISSING |
| MEDICAL FINDINGS | `_render_medical_findings()` | ⚠️ No routing from self-report |
| ADMINISTRATIVE ACTIONS | *NONE* | ❌ MISSING |
| QUOTES (SPEAKER RESOLVED) | `_render_quotes()` | ✅ |
| QUOTES (SPEAKER UNRESOLVED) | `_render_quotes()` | ✅ |
| **EVENTS (ACTOR UNRESOLVED)** | *NONE* | ❌ MISSING |
| RECONSTRUCTED TIMELINE | `_render_timeline()` | ⚠️ No pronoun resolution |
| **INVESTIGATION QUESTIONS** | *NONE* | ❌ MISSING |
| RAW NARRATIVE | inline | ✅ |

**Summary: 9 sections completely missing, 6 sections incomplete**

---

## PART 3: WHAT WAS DONE FOR STAGE 3

Looking at the milestone document claims vs reality:

| Claim | Evidence | Status |
|-------|----------|--------|
| "ctx parameter added" | Not in V1 signature | ❌ NEVER ADDED TO V1 |
| "selection_result parameter added" | Not in V1 signature | ❌ NEVER ADDED TO V1 |
| "Entity section uses SelectionResult" | V1 lines 143-234 use inline logic | ❌ NOT DONE |
| "OBSERVED uses SelectionResult" | V1 lines 614-809 use inline logic | ❌ NOT DONE |
| "QUOTES uses SelectionResult" | V1 lines 1284-1494 use inline extraction | ❌ NOT DONE |
| "TIMELINE uses SelectionResult" | V1 lines 1569-1932 use inline logic | ❌ NOT DONE |
| "V8 fallback removed" | V1 IS the V8 path | ❌ NOT DONE |
| "structured.py ~500-800 lines" | V1 is 2019 lines | ❌ NOT DONE |
| "structured_v2.py created" | File exists, 493 lines | ✅ DONE |
| "structured_v2.py is drop-in replacement" | Missing 9 sections | ❌ NOT DONE |

---

## PART 4: TIMELINE COMPARISON

### V1 Timeline Logic (lines 1569-1932) = 363 lines

V1 TIMELINE does:
1. Group entries by day (lines 1580-1586)
2. Filter fragments by length <15 chars (line 1638)
3. Skip fragment starters (lines 1642-1648)
4. **Pronoun resolution** (lines 1650-1697):
   - "He" → context-based (Marcus Johnson, Officer Rodriguez, etc.)
   - "She" → context-based (Amanda Foster, Patricia Chen, etc.)
   - "They" → "Officers"
5. Skip conjunction starts (line 1701)
6. Deduplicate entries (lines 1704-1711)
7. **Skip interpretive patterns** (lines 1719-1741)
8. **Neutralize patterns** (lines 1745-1759)
9. **First-person normalization** (lines 1761-1778)
10. Smart truncation (lines 1794-1810)
11. Quote cleanup (lines 1812-1821)
12. Incomplete skip (lines 1823-1826)
13. Incomplete markers (lines 1828-1833)
14. Orphan skip (lines 1835-1840)
15. Time display conversion (lines 1848-1866)
16. Gap markers (lines 1880-1885)
17. Investigation questions (lines 1898-1919)
18. Summary stats (lines 1921-1932)

### structured_v2.py Timeline Logic (lines 414-469) = 55 lines

V2 TIMELINE does:
1. Group entries by day
2. Display time info
3. Display description (truncated to 80 chars)

**MISSING FROM V2:**
- Pronoun resolution (47 lines)
- Interpretive skip patterns (22 lines)
- Neutralize patterns (14 lines)
- First-person normalization (17 lines)
- Fragment filtering
- Incomplete entry handling
- Investigation questions
- Summary stats

---

## STAGE 3 VERDICT

### Status: ❌ **INCOMPLETE**

| Metric | Target | Actual |
|--------|--------|--------|
| V1 structured.py lines | 500-800 | 2019 |
| V1 has SelectionResult | Yes | No |
| V1 is formatting-only | Yes | No (79% logic) |
| V2 sections complete | 28 | 16 |
| V2 is drop-in replacement | Yes | No |

### What Was Actually Done:
1. ✅ structured_v2.py file created (493 lines)
2. ✅ V2 has SelectionResult parameter
3. ✅ V2 has 12 section renderers
4. ❌ V2 missing 9 sections entirely
5. ❌ V2 missing timeline intelligence
6. ❌ V1 was never modified to use SelectionResult
7. ❌ V1 still contains all inline logic

### Why Stage 3 Failed:

**The fundamental mistake**: structured_v2.py was written as a "clean" renderer WITHOUT migrating the logic from V1 into upstream passes first.

Result: V2 is clean but produces **different and inferior output** because:
- No items extraction
- No pronoun resolution
- No neutralization
- No medical routing
- No investigation questions
- Collapsed self-reported sections

**To fix Stage 3, you must first complete Stages 1 and 2** — move classification and selection logic into passes, THEN the renderer can be simplified.

---

## REMEDIATION REQUIRED

### Before structured.py can be simplified:

1. **Complete Stage 1** — Move ALL classification logic to passes:
   - `neutralize_for_observed()` → p35
   - `is_strict_camera_friendly()` → p35  
   - `is_follow_up_event()` → p35
   - `is_source_derived()` → p35
   - `_is_medical_provider_content()` → p35 or p37
   - Timeline pronoun resolution → p43
   - Timeline neutralization → p43

2. **Complete Stage 2** — Extend SelectionResult:
   - Add fields for all 28 sections
   - Add items discovered extraction
   - Add investigation questions generation

3. **Then Stage 3** — Simplify renderer:
   - Remove inline functions
   - Read from SelectionResult only
   - Pure formatting

---

*Stage 3 Audit — 2026-01-19*
