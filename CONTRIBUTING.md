# Contributing to PhotonTrust

PhotonTrust uses a strict research-to-build workflow for all substantial
features, model changes, and benchmark updates.

## Required workflow (must follow in order)
1. Research document (PhD-level depth)
2. Implementation plan and code-fit analysis
3. Build and tests
4. Final documentation update

Do not skip steps for non-trivial work.

## 1) Research document requirements
Create a research brief before implementation. Minimum sections:
- Problem statement and hypotheses
- Related work and competing methods
- Mathematical model and assumptions
- Validation strategy and expected failure modes
- Reproducibility and uncertainty treatment

Use:
- `docs/templates/research_brief_template.md`

Store completed work items under:
- `docs/work_items/`

## 2) Planning and code-fit analysis
Before coding, map changes to current modules:
- affected files and interfaces
- migration and backward-compatibility impact
- acceptance criteria and test plan

Use:
- `docs/templates/implementation_plan_template.md`

## 3) Build and test
Required minimum checks:
- Unit and integration tests updated
- Schema validation still passing
- Regression baselines or golden snapshots reviewed when impacted

Commands:
```bash
python scripts/ci_checks.py
python scripts/check_benchmark_drift.py
```

## 4) Final documentation update
Every merged change must update:
- relevant research docs (if assumptions changed)
- user-facing docs and examples
- release notes/changelog when externally visible

Use:
- `docs/templates/validation_report_template.md`

## Quality gates
Changes should not be marked complete unless:
- research, plan, implementation, and docs are all present
- tests pass and outputs are reproducible with recorded seeds

## Week 1 baseline artifacts (M1 freeze)
Use these artifacts as the active baseline for architecture/API/CI policy:
- `docs/operations/week1/architecture_freeze_memo_2026-02-12.md`
- `docs/operations/week1/api_contract_table_2026-02-12.md`
- `docs/operations/week1/ci_baseline_rules_2026-02-12.md`

Program completion and release gating:
- `docs/operations/program_completion_report_2026-02-12.md`
- `scripts/release_gate_check.py`
