# NNRT Documentation Index

Welcome to the NNRT documentation. This page is the canonical entry point: it lists every document under `docs/` and groups them by audience so you can land on the right page without digging.

If you are new to the project, start with the repository [README.md](../README.md) and then [`CONVERSATION_INTRO_AND_CONTEXT.md`](CONVERSATION_INTRO_AND_CONTEXT.md).

> **Doc status conventions.** Pages dated on a single calendar day (e.g. `Date: 2026-01-14`) are point-in-time analyses or design notes — useful as history, not as current truth. Specs (`docs/specs/`) and the IR/schema documents are the authoritative living references.

---

## For users

You want to run NNRT or understand what it produces.

| Doc | What it covers |
|-----|----------------|
| [Repository README](../README.md) | Project overview, motivation, what NNRT is and is not |
| [CLI reference](#cli-reference) *(planned — see [WOR-14](#planned-pages))* | Flags, env vars, formats, pipelines, profiles, selection modes |
| [Web app guide](#web-app-guide) *(planned — see [WOR-18](#planned-pages))* | The Flask + SSE backend in `web/` and its browser frontend |
| [`v6_features.md`](v6_features.md) | V6 Verification Platform features (entity tracking, timeline, contradiction surfaces) |

---

## For contributors

You want to make changes, run the test suite, or open a PR.

| Doc | What it covers |
|-----|----------------|
| [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | Local dev setup, running tests, conventional commits, PR process |
| [`architecture/architecture_guide.md`](architecture/architecture_guide.md) | Current architecture (post-remediation, v0.3.x) — module boundaries, IR flow, pass responsibilities |
| [`PROJECT_STRUCTURE_AND_DOMAIN_STYLE.md`](PROJECT_STRUCTURE_AND_DOMAIN_STYLE.md) | Python package layout, naming conventions, domain-oriented module style |
| [`PROJECT_GOVERNANCE_AND_PLANNING.md`](PROJECT_GOVERNANCE_AND_PLANNING.md) | Documentation-as-artifact policy, planning rules, spec-before-code rule |
| Pass map *(planned — see [WOR-15](#planned-pages))* | Canonical user-level pass map (p00 → p90) and the IR contract |

---

## For implementers and spec readers

You are writing or reviewing a pass, an IR change, or an output schema.

### IR and schema

| Doc | What it covers |
|-----|----------------|
| [`IR_SPEC_v0_1.md`](IR_SPEC_v0_1.md) | Intermediate Representation specification (v0.1) — the contract between passes |
| [`schema/nnrt_output_schema_v0.1.yaml`](schema/nnrt_output_schema_v0.1.yaml) | Structured output schema (YAML) |
| [`schema/gold_standard_example.md`](schema/gold_standard_example.md) | Worked example of correct decomposition |
| [`CONTEXT_METADATA_AND_REFERENCES.md`](CONTEXT_METADATA_AND_REFERENCES.md) | How NNRT carries metadata, external references, and complex domain terms |
| [`NARRATIVE_RESPONSE_AND_DEFENSE_MOTIVATION.md`](NARRATIVE_RESPONSE_AND_DEFENSE_MOTIVATION.md) | Why narrative and thread identifiers exist, and how they enable response/defense flows |

### Pass and feature specs (`specs/`)

The full catalogue lives in [`specs/README.md`](specs/README.md). Highlights:

| Spec | Status |
|------|--------|
| [`specs/phase1_statement_classification.md`](specs/phase1_statement_classification.md) | Classify statements as observation/claim/interpretation |
| [`specs/phase2_structured_output.md`](specs/phase2_structured_output.md) | JSON output schema |
| [`specs/phase3_4_uncertainty_entities.md`](specs/phase3_4_uncertainty_entities.md) | Uncertainty + entity/event extraction |
| [`specs/phase5_validation.md`](specs/phase5_validation.md) | Validation test suites |
| [`specs/p51-contradiction-detection.md`](specs/p51-contradiction-detection.md) | Contradiction detection pass (Milestone 3 — Draft) |

---

## For decision and planning context

You want to understand *why* a thing is the way it is, or what is planned next.

### Milestones (`milestones/`)

Sequenced delivery targets. The current focus is Milestone 3.

| Doc | What it covers |
|-----|----------------|
| [`milestones/milestone0.md`](milestones/milestone0.md) | Architecture & technology blueprint |
| [`milestones/milestone1.md`](milestones/milestone1.md) | Core NLP integration |
| [`milestones/milestone2.md`](milestones/milestone2.md) | Advanced features & production hardening |
| [`milestones/milestone3.md`](milestones/milestone3.md) | Intelligence & edge cases (meta-detection, ambiguity, contradictions, sarcasm) |
| [`milestones/road_to_pre_alpha.md`](milestones/road_to_pre_alpha.md) | Master roadmap to pre-alpha |
| [`milestones/v5_blocking_issues.md`](milestones/v5_blocking_issues.md) | V5 blocking issues — historical |
| [`milestones/v6_verification_platform.md`](milestones/v6_verification_platform.md) | V6 verification platform plan |

### Roadmap (`roadmap/`)

| Doc | What it covers |
|-----|----------------|
| [`roadmap/nnrt_v2_roadmap.md`](roadmap/nnrt_v2_roadmap.md) | v2 implementation roadmap (lexical → structural decomposer) |
| [`roadmap/QUICK_REFERENCE.md`](roadmap/QUICK_REFERENCE.md) | One-page v2 reference |

### Governance, scope, ethics, positioning

| Doc | What it covers |
|-----|----------------|
| [`SCOPE_AND_ETHICS.md`](SCOPE_AND_ETHICS.md) | What NNRT will and will not do — design constraints, ethical guardrails |
| [`PROJECT_GOVERNANCE_AND_PLANNING.md`](PROJECT_GOVERNANCE_AND_PLANNING.md) | Planning, spec, and documentation rules |
| [`CONVERSATION_INTRO_AND_CONTEXT.md`](CONVERSATION_INTRO_AND_CONTEXT.md) | Quick-establish-context primer for new discussions |
| [`../LLM_VS_NLP_POSITIONING.md`](../LLM_VS_NLP_POSITIONING.md) | LLM usage policy — what models may and may not do inside NNRT |

### Analyses and audits (`analysis/`)

Point-in-time reviews that informed the current architecture. Useful for **why** decisions were made; do **not** treat as current state.

| Doc | What it covers |
|-----|----------------|
| [`analysis/architectural_gap_analysis_v4.md`](analysis/architectural_gap_analysis_v4.md) | v4 architectural gaps (2026-01-14) |
| [`analysis/comprehensive_pre_alpha_audit.md`](analysis/comprehensive_pre_alpha_audit.md) | Full pre-alpha audit |
| [`analysis/deep_architectural_review.md`](analysis/deep_architectural_review.md) | Deep architectural review & critical analysis |
| [`analysis/infrastructure_gaps_v1.md`](analysis/infrastructure_gaps_v1.md) | Infrastructure gaps — round 1 |
| [`analysis/infrastructure_gaps_v2.md`](analysis/infrastructure_gaps_v2.md) | Infrastructure gaps — round 2 |
| [`analysis/infrastructure_gaps_v3.md`](analysis/infrastructure_gaps_v3.md) | Grammar & transformation bugs |
| [`analysis/pre_alpha_audit.md`](analysis/pre_alpha_audit.md) | Pre-alpha audit & critical analysis |
| [`analysis/pre_alpha_gap_analysis.md`](analysis/pre_alpha_gap_analysis.md) | Pre-alpha gap analysis |

---

## For history (design, research, future)

These are kept for traceability. They document earlier reasoning and exploratory work; some have since been superseded by specs and the architecture guide.

### Design notes (`design/`)

| Doc | What it covers |
|-----|----------------|
| [`design/decomposition_rules.md`](design/decomposition_rules.md) | Phase 1: how to break segments into atomic statements |
| [`design/diff_comparison_feature.md`](design/diff_comparison_feature.md) | Diff comparison feature plan |
| [`design/logging_system.md`](design/logging_system.md) | Channel-aware logging architecture |
| [`design/nnrt_quality_analysis.md`](design/nnrt_quality_analysis.md) | Pipeline quality issues |
| [`design/nnrt_v3_architecture.md`](design/nnrt_v3_architecture.md) | v3 semantic-understanding architecture |
| [`design/pass_logging_plan.md`](design/pass_logging_plan.md) | Pass logging instrumentation plan |
| [`design/v3_implementation_plan.md`](design/v3_implementation_plan.md) | v3 clean-architecture implementation plan |
| [`design/v4_remediation_plan.md`](design/v4_remediation_plan.md) | V4 remediation plan (post stress test) |
| [`design/v6_timeline_research.md`](design/v6_timeline_research.md) | V6 timeline reconstruction research (implemented) |

### Research (`research/`)

| Doc | What it covers |
|-----|----------------|
| [`research/decomposition_research.md`](research/decomposition_research.md) | NLP-science grounding for Phase 1–2 decomposition |

### Future / exploratory (`future/`)

Forward-looking concepts beyond the current milestones.

| Doc | What it covers |
|-----|----------------|
| [`future/FactualReport.md`](future/FactualReport.md) | Neutral reporting infrastructure — concept, engine, future evolutions |
| [`future/MultiOutputMode.md`](future/MultiOutputMode.md) | Structured multi-output mode |

---

## Architecture deep dives (`architecture/`)

The headline document is [`architecture_guide.md`](architecture/architecture_guide.md). The other files in this directory are historical refactor proposals and problem statements.

| Doc | What it covers |
|-----|----------------|
| [`architecture/architecture_guide.md`](architecture/architecture_guide.md) | Current architecture guide (v0.3.x) — start here |
| [`architecture/DATA_FLOW_PROBLEM.md`](architecture/DATA_FLOW_PROBLEM.md) | Why context was getting lost (problem statement) |
| [`architecture/MINIMAL_REFACTOR.md`](architecture/MINIMAL_REFACTOR.md) | Minimal viable refactor: span decision tracking |
| [`architecture/REFACTORING_PROPOSAL.md`](architecture/REFACTORING_PROPOSAL.md) | Architecture review & refactoring proposal |
| [`architecture/policy_engine_redesign.md`](architecture/policy_engine_redesign.md) | Policy engine redesign |

---

## Planned pages

The pages below do not yet exist. They are tracked as documentation issues and will be linked from this index once they land.

| Page | Issue |
|------|-------|
| CLI reference | `WOR-14` — User docs: CLI Reference (flags, env vars, formats, pipelines, profiles, selection modes) |
| Web app guide | `WOR-18` — Web app docs: document `web/` Flask backend + browser frontend |
| Pass map (p00 → p90) | `WOR-15` — Architecture overview: canonical pass-map + IR contract |

---

*This index lives at `docs/README.md`. When adding a new document under `docs/`, please link it here so it stays discoverable.*
