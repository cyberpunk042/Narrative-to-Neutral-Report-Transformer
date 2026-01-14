# Phase 5: Pre-Alpha Validation — Implementation Spec

## Overview

Prove that NNRT meets its promise through rigorous testing.

---

## The Promise (Recap)

Given any human narrative, NNRT produces a structured output where:
1. A human can distinguish observations from claims
2. All uncertainties are explicit
3. No information was added
4. The tone is neutral

---

## Test Suite 1: Human Review Test

### Goal
Verify that humans can answer key questions using ONLY the structured output.

### Test Protocol

1. **Select 20 narratives** from extreme_cases + hard_cases
2. **Generate structured output** for each
3. **Ask 3+ human reviewers** to answer (without seeing original):
   - What actions are **claimed** to have happened?
   - What did the narrator **directly observe**?
   - What is **inferred or interpreted**?
   - What is **uncertain or ambiguous**?
4. **Compare answers** to ground truth (original narrative)
5. **Score accuracy** and agreement

### Pass Criteria
- Accuracy > 80% for each question
- Inter-rater agreement > 70%

### Implementation

Create `tests/validation/human_review/`:
```
human_review/
├── test_cases/
│   ├── case_001.json   # Input + structured output
│   ├── case_002.json
│   └── ...
├── questionnaire.md     # Standard questions
├── ground_truth/
│   ├── case_001_answers.json
│   └── ...
└── analysis.py          # Score responses
```

```python
# analysis.py
def score_response(response: dict, ground_truth: dict) -> float:
    """Score a single human response against ground truth."""
    scores = []
    
    # Score observed actions
    observed_score = jaccard_similarity(
        response["observed_actions"],
        ground_truth["observed_actions"]
    )
    scores.append(observed_score)
    
    # Score inferred
    inferred_score = jaccard_similarity(
        response["inferred"],
        ground_truth["inferred"]
    )
    scores.append(inferred_score)
    
    # Score uncertainties
    uncertainty_score = jaccard_similarity(
        response["uncertainties"],
        ground_truth["uncertainties"]
    )
    scores.append(uncertainty_score)
    
    return sum(scores) / len(scores)
```

---

## Test Suite 2: No-Hallucination Property

### Goal
Prove that NNRT never adds facts not present in input.

### Test Protocol

For each test case:
1. Extract all **entities** from structured output
2. Extract all **events** from structured output
3. Extract all **claims** from structured output
4. For each extracted item:
   - Search for evidence in original input
   - If no evidence found → **HALLUCINATION**

### Implementation

```python
# tests/validation/test_no_hallucination.py

@pytest.mark.parametrize("case_id", EXTREME_CASE_IDS)
def test_no_hallucination(case_id: str, engine):
    case = load_case(case_id)
    result = engine.transform(TransformRequest(text=case["input"]))
    output = build_structured_output(result)
    
    input_lower = case["input"].lower()
    
    # Check each entity
    for entity in output.entities:
        for mention in entity.mentions:
            assert mention["text"].lower() in input_lower, \
                f"Hallucinated entity mention: {mention}"
    
    # Check each event
    for event in output.events:
        # Event description should relate to input
        words = event.description.lower().split()
        assert any(word in input_lower for word in words), \
            f"Hallucinated event: {event.description}"
    
    # Check each statement
    for stmt in output.statements:
        # Original should be substring of input
        assert stmt.original.lower() in input_lower, \
            f"Hallucinated statement: {stmt.original}"
```

### Pass Criteria
- **Zero hallucinations** across entire test corpus
- This is a hard invariant

---

## Test Suite 3: Ambiguity Preservation

### Goal
Prove that NNRT never resolves ambiguity without user input.

### Test Cases
From `hard_cases.yaml`:
- `hard_003`: Pronoun Ambiguity
- `hard_004`: Unclear Antecedent

### Test Protocol

1. Input an ambiguous narrative
2. Check structured output
3. Verify ambiguity is **preserved or exposed**
4. Verify no **forced resolution**

### Implementation

```python
# tests/validation/test_ambiguity_preserved.py

AMBIGUOUS_CASES = [
    {
        "input": "He hit him. Then he ran.",
        "ambiguous_refs": ["He", "him", "he"],
        "should_have_uncertainty": True,
    },
    {
        "input": "They said I was resisting.",
        "ambiguous_refs": ["They"],
        "should_have_uncertainty": True,
    },
]

@pytest.mark.parametrize("case", AMBIGUOUS_CASES)
def test_ambiguity_preserved(case, engine):
    result = engine.transform(TransformRequest(text=case["input"]))
    output = build_structured_output(result)
    
    if case["should_have_uncertainty"]:
        # Must have at least one uncertainty
        assert len(output.uncertainties) > 0, \
            f"Missing uncertainty for: {case['input']}"
        
        # Check that ambiguous refs are captured
        all_unc_text = " ".join(u.text for u in output.uncertainties)
        for ref in case["ambiguous_refs"]:
            assert ref.lower() in all_unc_text.lower(), \
                f"Ambiguous ref not captured: {ref}"
    
    # Never should have resolution without user input
    for unc in output.uncertainties:
        assert unc.resolution is None, \
            f"Ambiguity resolved without user input: {unc}"
```

### Pass Criteria
- All ambiguous inputs have `uncertainties` in output
- No `resolution` field is set
- Ambiguous references are identified

---

## Test Suite 4: Neutralization Quality

### Goal
Prove that output is neutralized without changing factual meaning.

### Test Protocol

1. Input emotional/accusatory narrative
2. Generate structured output
3. Verify:
   - No inflammatory language
   - No moral framing
   - Facts preserved
   - Quotes preserved

### Implementation

```python
# tests/validation/test_neutralization.py

INFLAMMATORY_WORDS = [
    "brutal", "vicious", "thug", "pig", "monster",
    "murderer", "criminal", "scum", "bastard",
]

MORAL_FRAMING = [
    "obviously", "clearly", "definitely", 
    "everyone knows", "anyone can see",
]

@pytest.mark.parametrize("case_id", EXTREME_CASE_IDS)
def test_neutralization(case_id: str, engine):
    case = load_case(case_id)
    result = engine.transform(TransformRequest(text=case["input"]))
    output = build_structured_output(result)
    
    rendered = output.rendered_text.lower()
    
    # No inflammatory words
    for word in INFLAMMATORY_WORDS:
        assert word not in rendered, \
            f"Inflammatory word in output: {word}"
    
    # No moral framing (outside quotes)
    # TODO: Exclude quoted text from check
    for phrase in MORAL_FRAMING:
        assert phrase not in rendered, \
            f"Moral framing in output: {phrase}"
    
    # Expected content preserved
    for expected in case.get("expected_preserved", []):
        assert expected.lower() in rendered.lower(), \
            f"Expected content missing: {expected}"
```

---

## Test Suite 5: LLM-Off Regression

### Goal
Prove that guarantees hold when LLM is disabled.

### Test Protocol

1. Run test corpus with LLM enabled
2. Run same corpus with LLM disabled
3. Compare:
   - Guarantees still hold
   - Quality degrades gracefully
   - No crashes

### Implementation

```python
# tests/validation/test_llm_off.py

@pytest.fixture
def engine_no_llm():
    engine = get_engine()
    setup_default_pipeline(engine, use_llm=False)
    return engine

@pytest.mark.parametrize("case_id", EXTREME_CASE_IDS)
def test_llm_off_no_hallucination(case_id: str, engine_no_llm):
    # Same as regular no-hallucination test
    ...

@pytest.mark.parametrize("case_id", EXTREME_CASE_IDS)
def test_llm_off_preserves_facts(case_id: str, engine_no_llm):
    case = load_case(case_id)
    result = engine_no_llm.transform(TransformRequest(text=case["input"]))
    
    # Expected content still preserved
    for expected in case.get("expected_preserved", []):
        assert expected.lower() in result.rendered_text.lower(), \
            f"LLM-off lost expected content: {expected}"
```

---

## Validation Dashboard

Create `scripts/validate_pre_alpha.py`:

```python
#!/usr/bin/env python3
"""Run all pre-alpha validation tests and report results."""

import subprocess
import json

TESTS = [
    ("Human Review", "tests/validation/human_review/"),
    ("No Hallucination", "tests/validation/test_no_hallucination.py"),
    ("Ambiguity Preserved", "tests/validation/test_ambiguity_preserved.py"),
    ("Neutralization", "tests/validation/test_neutralization.py"),
    ("LLM-Off", "tests/validation/test_llm_off.py"),
]

def main():
    results = []
    
    for name, path in TESTS:
        result = subprocess.run(
            ["pytest", path, "-v", "--tb=short"],
            capture_output=True
        )
        passed = result.returncode == 0
        results.append({
            "name": name,
            "passed": passed,
            "output": result.stdout.decode(),
        })
    
    # Print report
    print("=" * 60)
    print("PRE-ALPHA VALIDATION REPORT")
    print("=" * 60)
    
    all_passed = all(r["passed"] for r in results)
    
    for r in results:
        status = "✅ PASS" if r["passed"] else "❌ FAIL"
        print(f"{status} {r['name']}")
    
    print("=" * 60)
    if all_passed:
        print("🎉 PRE-ALPHA READY")
    else:
        print("⚠️  NOT READY - Fix failing tests")

if __name__ == "__main__":
    main()
```

---

## Exit Criteria (Pre-Alpha Complete)

### Must Pass
- [ ] Human Review Test: >80% accuracy
- [ ] No-Hallucination: Zero failures
- [ ] Ambiguity Preserved: All ambiguities captured
- [ ] Neutralization: All inflammatory removed
- [ ] LLM-Off: Graceful degradation

### Documentation
- [ ] Promise document updated
- [ ] Schema documented
- [ ] Examples provided

### Process
- [ ] All 40+ existing tests still pass
- [ ] Validation dashboard green
- [ ] Version bumped to 0.3.0 (pre-alpha)

---

## Estimated Time: 3-4 hours

| Task | Hours |
|------|-------|
| Test Suite 1 (Human Review) | 1 |
| Test Suite 2 (No Hallucination) | 0.5 |
| Test Suite 3 (Ambiguity) | 0.5 |
| Test Suite 4 (Neutralization) | 0.5 |
| Test Suite 5 (LLM-Off) | 0.5 |
| Validation Dashboard | 0.5 |
| Documentation | 0.5 |
