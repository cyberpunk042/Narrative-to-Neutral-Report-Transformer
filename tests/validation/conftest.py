import pytest
import yaml
from pathlib import Path
from nnrt.core.engine import get_engine
from nnrt.cli.main import setup_default_pipeline

# Path to hard cases (relative to tests/validation/)
HARD_CASES_FILE = Path(__file__).parent.parent.parent / "data" / "synthetic" / "hard_cases.yaml"

@pytest.fixture(scope="session")
def hard_cases():
    if not HARD_CASES_FILE.exists():
        return []
        
    with open(HARD_CASES_FILE) as f:
        data = yaml.safe_load(f)
    return data.get("cases", [])

@pytest.fixture
def engine():
    """Create an engine with the default pipeline."""
    eng = get_engine()
    setup_default_pipeline(eng)
    return eng
