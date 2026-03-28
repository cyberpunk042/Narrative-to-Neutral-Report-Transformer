# Contributing to NNRT

Thank you for your interest in contributing!

## Development Setup

```bash
# Clone and create a virtual environment
git clone https://github.com/cyberpunk042/Narrative-to-Neutral-Report-Transformer.git
cd Narrative-to-Neutral-Report-Transformer
python -m venv .venv
source .venv/bin/activate

# Install with dev dependencies
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest                        # run all tests with coverage
pytest tests/unit/            # unit tests only
pytest -k "test_name"         # filter by name
```

Coverage is reported automatically. Keep it green before submitting a PR.

## Code Style

```bash
ruff check .      # lint
ruff format .     # format (line-length 100, target py311)
mypy nnrt/        # type check
```

All public functions require type hints and docstrings on non-obvious logic.

## Commit Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): short description
```

**Types:** `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`
**Scope:** module or area affected (e.g. `pipeline`, `cli`, `tests`)

Examples:
- `feat(pipeline): add legal hygiene pass`
- `fix(cli): handle empty input gracefully`
- `docs: update CONTRIBUTING.md`

## PR Process

1. Fork the repo and create a branch: `git checkout -b feat/your-feature`
2. Make changes with tests alongside implementation.
3. Run `pytest` and `ruff check .` — both must pass.
4. Open a PR with a clear title (conventional commit format) and description.
5. Address review comments promptly.

PRs without tests for new functionality will not be merged.
