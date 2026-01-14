---
description: Development workflow for NNRT project
---

# NNRT Development Workflow

## Setup (First Time)

1. Ensure pyenv is configured in your shell:
   ```bash
   export PYENV_ROOT="$HOME/.pyenv"
   [[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
   eval "$(pyenv init -)"
   ```

2. Navigate to project:
   ```bash
   cd /home/jfortin/Narrative-to-Neutral-Report-Transformer
   ```

3. Activate the virtual environment:
   ```bash
   source .venv/bin/activate
   ```

## Daily Development

// turbo
1. Activate the environment:
   ```bash
   source .venv/bin/activate
   ```

// turbo
2. Run tests:
   ```bash
   pytest tests/ -v
   ```

// turbo
3. Run type checking:
   ```bash
   mypy nnrt/
   ```

// turbo
4. Run linting:
   ```bash
   ruff check nnrt/
   ```

// turbo
5. Format code:
   ```bash
   ruff format nnrt/
   ```

## CLI Usage

Transform text (direct):
```bash
nnrt transform "Your narrative text here"
```

Transform from file:
```bash
nnrt transform path/to/file.txt
```

Transform with JSON output:
```bash
nnrt transform "Your text" --format json
```

Transform with full IR output:
```bash
nnrt transform "Your text" --format ir
```

## Project Structure

```
nnrt/
├── core/       # Engine, context, contracts
├── ir/         # Intermediate Representation
├── passes/     # Pipeline stages (p00-p80)
├── nlp/        # Semantic sensors (stub, hf_encoder, json_instruct)
├── policy/     # Deterministic rules
├── render/     # Text generation from IR
├── validate/   # Validators
└── cli/        # Command-line interface
```

## Key Documents

- `LLM_VS_NLP_POSITIONING.md` - LLM usage policy (critical)
- `docs/IR_SPEC_v0_1.md` - IR specification
- `docs/milestones/milestone0.md` - Architecture blueprint
