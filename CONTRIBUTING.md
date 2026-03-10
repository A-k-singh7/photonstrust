# Contributing to PhotonTrust

Thanks for contributing. PhotonTrust mixes open-source software practice with a
research-heavy validation workflow, so the contribution path depends on the type
of change you are making.

## Before You Start

- Read `README.md` for install and runtime options.
- Use `docs/README.md` to find the right documentation set.
- Use `configs/README.md` and `scripts/README.md` to find runnable examples and
  maintainer commands.
- For security issues, use `SECURITY.md` instead of opening a public issue.

## Local Setup

```bash
pip install -e .[dev]
pre-commit install
```

Optional extras:

```bash
pip install -e .[api,qutip,qiskit]
cd web && npm ci && cd ..
```

## Contribution Types

### Small changes

Use the normal OSS flow for:

- bug fixes,
- docs improvements,
- test-only changes,
- refactors that do not change model behavior,
- UI polish and accessibility fixes.

### Substantial changes

Use the full research-to-build workflow for:

- new physics models,
- protocol changes,
- benchmark updates,
- new validation or release gates,
- changes that alter scientific assumptions or published outputs.

## Research-to-Build Workflow for Substantial Changes

1. Research brief
2. Implementation plan and code-fit analysis
3. Build and tests
4. Final documentation update

Do not skip these steps for non-trivial model or benchmark work.

### Research brief requirements

Minimum sections:

- problem statement and hypotheses
- related work and competing methods
- mathematical model and assumptions
- validation strategy and expected failure modes
- reproducibility and uncertainty treatment

Use `docs/templates/research_brief_template.md`.

### Planning and code-fit analysis

Map the change to current modules:

- affected files and interfaces
- migration and backward-compatibility impact
- acceptance criteria and test plan

Use `docs/templates/implementation_plan_template.md`.

### Final validation write-up

Use `docs/templates/validation_report_template.md` when the change affects model
behavior, validation, or release evidence.

## Testing Expectations

Run the smallest relevant checks first, then broader gates as needed.

Common commands:

```bash
python scripts/ci_checks.py
python scripts/check_benchmark_drift.py
python scripts/run_validation_harness.py --output-root results/validation
```

For UI work:

```bash
cd web
npm run build
npm run test:ui
```

## Pull Request Expectations

- Keep changes scoped and explain why they are needed.
- Link issues, research docs, or benchmark references when relevant.
- Update docs when behavior, examples, or contributor workflow changes.
- Do not include unrelated generated artifacts or local scratch outputs.

## Quality Gates

A change should not be treated as complete unless:

- tests pass for the affected area,
- docs and examples stay accurate,
- reproducibility expectations are preserved,
- research and planning artifacts exist when assumptions changed.

## Maintainer Baselines and Release Gates

Use these artifacts as active baseline references for architecture, API, and CI
policy:

- `docs/operations/week1/architecture_freeze_memo_2026-02-12.md`
- `docs/operations/week1/api_contract_table_2026-02-12.md`
- `docs/operations/week1/ci_baseline_rules_2026-02-12.md`

Release and completion references:

- `docs/operations/program_completion_report_2026-02-12.md`
- `scripts/release_gate_check.py`
