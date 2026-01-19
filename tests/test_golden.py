"""
Golden tests for regression testing.

Golden tests validate that transformation behavior matches expected,
locked-in behavior. Any changes to these tests require explicit review.
"""

import re
from pathlib import Path

import pytest
import yaml

from nnrt.core.context import TransformRequest
from nnrt.core.engine import Engine, Pipeline
from nnrt.cli.main import setup_default_pipeline
from nnrt.passes import (
    augment_ir,
    build_ir,
    evaluate_policy,
    extract_identifiers,
    normalize,
    package,
    render,
    segment,
    tag_spans,
)

# Path to golden test cases
GOLDEN_DIR = Path(__file__).parent.parent / "data" / "golden"


@pytest.fixture
def engine():
    """Create an engine with the default pipeline."""
    eng = Engine()
    setup_default_pipeline(eng)
    return eng


def load_golden_cases():
    """Load all golden test cases from YAML files."""
    cases = []
    for yaml_file in GOLDEN_DIR.glob("case_*.yaml"):
        with open(yaml_file) as f:
            data = yaml.safe_load(f)
            data["_file"] = yaml_file.name
            cases.append(data)
    return cases


# Dynamically generate test IDs from filenames
golden_cases = load_golden_cases()
golden_ids = [c["_file"].replace(".yaml", "") for c in golden_cases]


@pytest.mark.parametrize("golden_case", golden_cases, ids=golden_ids)
class TestGoldenCases:
    """Parameterized golden tests."""

    def test_preserved_content(self, engine, golden_case):
        """Verify expected content is preserved."""
        text = golden_case["input"]
        expected_preserved = golden_case.get("expected_preserved", [])
        
        if not expected_preserved:
            pytest.skip("No preserved content defined")
        
        request = TransformRequest(text=text)
        result = engine.transform(request)
        
        for expected in expected_preserved:
            assert expected in result.rendered_text, (
                f"Expected '{expected}' to be preserved in output.\n"
                f"Output: {result.rendered_text}"
            )

    def test_validation_rules(self, engine, golden_case):
        """Verify validation rules are satisfied."""
        text = golden_case["input"]
        validation_rules = golden_case.get("validation_rules", [])
        
        if not validation_rules:
            pytest.skip("No validation rules defined")
        
        request = TransformRequest(text=text)
        result = engine.transform(request)
        
        # V7: For 'must not contain' rules, check only the RAW NEUTRALIZED NARRATIVE section
        # V2 structured output includes original text in sections like REPORTER INFERENCES
        full_output = result.rendered_text
        full_output_lower = full_output.lower()
        
        if "raw neutralized narrative" in full_output_lower:
            raw_idx = full_output_lower.find("raw neutralized narrative")
            prose_output = full_output[raw_idx:]
        else:
            prose_output = full_output
        
        for rule in validation_rules:
            # Parse rule syntax
            if "must not contain" in rule.lower():
                match = re.search(r"'([^']+)'", rule)
                if match:
                    forbidden = match.group(1)
                    # V7: Check only prose section for forbidden content
                    assert forbidden not in prose_output, (
                        f"Rule violated: {rule}\n"
                        f"Prose output contains forbidden content"
                    )
            elif "must contain" in rule.lower():
                match = re.search(r"'([^']+)'", rule)
                if match:
                    required = match.group(1)
                    assert required in result.rendered_text, (
                        f"Rule violated: {rule}\n"
                        f"Output: {result.rendered_text}"
                    )

    def test_diagnostics(self, engine, golden_case):
        """Verify expected diagnostics are generated."""
        text = golden_case["input"]
        expected_diagnostics = golden_case.get("expected_diagnostics", [])
        
        if not expected_diagnostics:
            pytest.skip("No diagnostics expectations defined")
        
        request = TransformRequest(text=text)
        result = engine.transform(request)
        
        for expected in expected_diagnostics:
            code = expected.get("code")
            min_count = expected.get("min_count", 1)
            
            matching = [d for d in result.diagnostics if d.code == code]
            assert len(matching) >= min_count, (
                f"Expected at least {min_count} diagnostics with code '{code}', "
                f"got {len(matching)}.\n"
                f"All diagnostics: {[d.code for d in result.diagnostics]}"
            )
