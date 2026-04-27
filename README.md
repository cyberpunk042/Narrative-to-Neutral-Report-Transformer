# NNRT — Narrative-to-Neutral Report Transformer

> A local, deterministic pipeline that converts first‑person narratives into neutral, fact‑focused, legally cautious text — preserving lived experience while stripping accusation, intent, and inflammatory phrasing.

[![CI](https://github.com/cyberpunk042/Narrative-to-Neutral-Report-Transformer/actions/workflows/ci.yml/badge.svg)](https://github.com/cyberpunk042/Narrative-to-Neutral-Report-Transformer/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE.md)
[![Python ≥ 3.11](https://img.shields.io/badge/python-%E2%89%A53.11-blue.svg)](pyproject.toml)

---

## What it is

NNRT is a **local text‑to‑text transformer** that runs a deterministic, inspectable pipeline over a raw narrative and emits a constrained output that:

- Preserves first‑person perspective.
- Foregrounds observable actions and direct statements.
- Removes legal conclusions, intent attribution, and charged terminology.
- Exposes structure (atomic statements, entities, events, identifiers, timeline) when requested.

It is a tool for **language hygiene**, not truth determination.

## What it is NOT

NNRT is not a reporting platform, a complaint submission system, a verification engine, a legal judgment tool, or an incident database. It does not determine whether events occurred, assign fault, or replace courts, journalism, or oversight bodies. See [`docs/SCOPE_AND_ETHICS.md`](docs/SCOPE_AND_ETHICS.md) for the full ethical framing.

---

## Status

**Version:** `0.3.0` · **Maturity:** Pre-Alpha (PyPI classifier *Development Status :: 2 - Pre-Alpha*)

NNRT currently ships:

- A multi-pipeline CLI (`default`, `raw`, `structured_only`).
- ~36 pipeline passes spanning normalization, segmentation, decomposition, classification, entity/event extraction, coreference, timeline, policy, selection, and rendering.
- A typed Intermediate Representation (**IR v0.1.0** — see [`docs/IR_SPEC_v0_1.md`](docs/IR_SPEC_v0_1.md)).
- Three policy profiles (`base`, `standard`, `law_enforcement`).
- Five selection modes (`strict`, `full`, `timeline`, `events`, `recompose`).
- Four output formats (`text`, `json`, `ir`, `structured`).
- A Flask web UI that exercises the same pipelines.

Roadmap to first alpha is tracked in [`docs/milestones/road_to_pre_alpha.md`](docs/milestones/road_to_pre_alpha.md).

This is not yet intended for production use.

---

## Install

NNRT requires **Python ≥ 3.11**.

```bash
git clone https://github.com/cyberpunk042/Narrative-to-Neutral-Report-Transformer.git
cd Narrative-to-Neutral-Report-Transformer
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

### Optional extras

The package declares optional dependency groups in [`pyproject.toml`](pyproject.toml):

| Extra        | Installs                                           | When you need it                                              |
| ------------ | -------------------------------------------------- | ------------------------------------------------------------- |
| `dev`        | `pytest`, `pytest-cov`, `ruff`, `mypy`             | Contributing — running tests, lint, type checks.              |
| `nlp`        | `transformers`, `torch`, `spacy`, `accelerate`, …  | LLM-assisted rendering (`--llm`) and richer event extraction. |
| `production` | `pyyaml`, `structlog`                              | Structured logging and YAML config in deployment.             |
| `all`        | `dev` + `nlp` + `production`                       | One-shot install for full-stack development.                  |

Example: `pip install -e ".[all]"`.

---

## Quickstart

Transform a short narrative to neutral prose:

```bash
nnrt transform "Officer Smith grabbed me and shouted that I was resisting."
```

Or read from a file or stdin (`-`):

```bash
nnrt transform path/to/narrative.txt
echo "..." | nnrt transform -
```

Get the structured pre-alpha JSON (atomic statements, entities, events, identifiers, diagnostics):

```bash
nnrt transform "..." --format structured
```

Switch the policy profile, selection mode, or pipeline:

```bash
nnrt transform "..." --profile law_enforcement --mode timeline --pipeline default
```

A reader unfamiliar with the project can run a transform within minutes using only the commands above.

---

## CLI summary

`nnrt transform <input> [flags]`. The `<input>` may be a literal string, a path to a text file, or `-` for stdin.

| Flag             | Values                                                                | Default          | Purpose                                                                |
| ---------------- | --------------------------------------------------------------------- | ---------------- | ---------------------------------------------------------------------- |
| `-o, --output`   | path                                                                  | stdout           | Write the rendered output to a file.                                   |
| `--format`       | `text`, `json`, `ir`, `structured`                                    | `text`           | Output format. `structured` is the pre-alpha JSON envelope.            |
| `--pipeline`     | `default`, `raw`, `structured_only`                                   | `default`        | Which registered pipeline to run.                                      |
| `--profile`      | `base`, `standard`, `law_enforcement`                                 | `law_enforcement`| Policy profile applied at the policy pass.                             |
| `--mode`         | `strict`, `full`, `timeline`, `events`, `recompose`                   | `strict`         | Atom selection mode for structured output.                             |
| `--llm`          | flag                                                                  | off              | Enable LLM-assisted rendering (requires the `nlp` extra).              |
| `--raw`          | flag                                                                  | off              | Debug: emit raw decomposed IR without rewriting.                       |
| `--no-prose`     | flag                                                                  | off              | Skip prose rendering, return structured data only.                     |
| `--log-level`    | `silent`, `info`, `verbose`, `debug`                                  | `info`           | Log verbosity (or `NNRT_LOG_LEVEL`).                                   |
| `--log-channel`  | comma-separated subset of `pipeline,transform,extract,policy,render,system` | all       | Restrict log output to specific channels.                              |
| `--version`      | flag                                                                  | —                | Print the installed version and exit.                                  |

Run `nnrt transform --help` for the up-to-date authoritative list.

---

## Architecture

The pipeline is a sequence of small, named **passes** (`p00_normalize` → `p90_render_structured`) operating on a typed IR. Each pass is independently testable and has a single responsibility.

- Architecture overview: [`docs/architecture/architecture_guide.md`](docs/architecture/architecture_guide.md)
- Intermediate Representation contract: [`docs/IR_SPEC_v0_1.md`](docs/IR_SPEC_v0_1.md)
- Output schema (YAML): [`docs/schema/nnrt_output_schema_v0.1.yaml`](docs/schema/nnrt_output_schema_v0.1.yaml)
- Pipeline pass sources: [`nnrt/passes/`](nnrt/passes/)

---

## Web UI

A minimal Flask app under [`web/`](web/) exposes the same pipelines via a browser interface, with side-by-side input/output panels and live streaming logs.

```bash
pip install flask flask-cors    # only required for the web UI
python -m web.server            # serves on http://localhost:5050
```

Endpoints: `/api/transform`, `/api/transform-stream` (SSE), `/api/history`, `/api/examples`. Source: [`web/server.py`](web/server.py).

---

## Documentation

Start at [`docs/README.md`](docs/README.md) — the canonical documentation index, grouped by audience (users, contributors, implementers, planning, history).

Frequently linked entry points:

- [`docs/SCOPE_AND_ETHICS.md`](docs/SCOPE_AND_ETHICS.md) — design boundaries and ethical position.
- [`docs/IR_SPEC_v0_1.md`](docs/IR_SPEC_v0_1.md) — Intermediate Representation v0.1.
- [`docs/architecture/architecture_guide.md`](docs/architecture/architecture_guide.md) — architecture overview.
- [`docs/specs/`](docs/specs/) — phase and feature specs.
- [`docs/milestones/road_to_pre_alpha.md`](docs/milestones/road_to_pre_alpha.md) — roadmap to first alpha.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — development setup, tests, commit format, PR process.
- [`LLM_VS_NLP_POSITIONING.md`](LLM_VS_NLP_POSITIONING.md) — positioning vs. pure-LLM approaches.

`CHANGELOG.md` and `SECURITY.md` are scheduled under the [Docs Foundation](docs/milestones/road_to_pre_alpha.md) initiative.

---

## License

Licensed under the **Apache License 2.0**. See [`LICENSE.md`](LICENSE.md) for the full text.

---

## Closing note

NNRT is an exploration of how careful process design can let difficult experiences be expressed *without becoming accusations*, and *without requiring individuals to navigate legal complexity on their own*. It does not claim to solve injustice; it demonstrates one way language can be handled more responsibly under constraint.
