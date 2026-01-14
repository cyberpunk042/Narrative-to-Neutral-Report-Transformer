import pytest
from nnrt.core.context import TransformRequest
from nnrt.output.structured import build_structured_output

AMBIGUOUS_IDS = ["hard_002", "hard_003"]

def test_ambiguity_preserved(engine, hard_cases):
    """
    Verify that ambiguous inputs result in structured uncertainties
    and are not arbitrarily resolved.
    """
    found_cases = 0
    
    for case in hard_cases:
        if case["id"] in AMBIGUOUS_IDS:
            found_cases += 1
            text = case["input"]
            result = engine.transform(TransformRequest(text=text))
            output = build_structured_output(result, text)
            
            # 1. Must produce uncertainty output
            assert len(output.uncertainties) > 0, \
                f"[Case: {case['id']}] expected uncertainties, found none."
            
            # 2. Must not resolve it automatically
            for unc in output.uncertainties:
                assert unc.resolution is None, \
                    f"[Case: {case['id']}] Uncertainty {unc.id} was auto-resolved: {unc.resolution}"
                assert unc.requires_human_review is True
                
            # 3. Text fragment should be in input
            for unc in output.uncertainties:
                if unc.text:
                    assert unc.text.lower() in text.lower(), \
                         f"[Case: {case['id']}] Uncertainty text '{unc.text}' not in input."

    if found_cases == 0:
        pytest.skip("No ambiguous test cases found in hard_cases.yaml")
