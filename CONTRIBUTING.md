# Contributing to PhotonTrust

Thanks for contributing. PhotonTrust combines normal open-source software
practice with a research-heavy validation workflow, so good contributions are
not just code-complete, they are reproducible, reviewable, and documented.

## Start Here

- Read `README.md` for install options, main entry points, and supported
  surfaces.
- Use `docs/README.md` to find the current documentation map.
- Use `docs/dev/git_and_docs_workflow.md` for branch, commit, PR, and docs-sync
  rules.
- Use `docs/dev/testing.md` for targeted validation commands.
- Use `scripts/README.md` and `configs/README.md` to find runnable automation and
  examples.
- For security issues, use `SECURITY.md` instead of filing a public issue.

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

## Normal Contributor Flow

1. Update local `main` and branch from it.
2. Keep the branch scoped to one logical change.
3. Run the smallest relevant checks first.
4. Update docs, examples, and changelog entries in the same branch.
5. Review the diff for accidental files before pushing.
6. Open a PR only when the description reflects the real scope of the branch.

Use `docs/dev/git_and_docs_workflow.md` as the authoritative workflow for these
steps.

## Contribution Types

### Small changes

Use the standard OSS flow for:

- bug fixes,
- docs improvements,
- test-only changes,
- refactors that do not change model behavior,
- UI polish and accessibility fixes,
- contributor tooling and repo hygiene updates.

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
3. Build and validation
4. Documentation and reproducibility update

Do not skip these steps for non-trivial model, benchmark, or release-policy
work.

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

Run the smallest relevant checks first, then expand to broader gates when
needed.

Common commands:

```bash
pytest -q tests/test_docs_experience.py
python scripts/validation/ci_checks.py
python scripts/validation/check_benchmark_drift.py
python scripts/validation/run_validation_harness.py --output-root results/validation
```

For UI work:

```bash
cd web
npm run build
npm run lint
npm run test:ui
```

See `docs/dev/testing.md` for a fuller map.

## Documentation Expectations

If you change behavior, you are expected to update the docs that explain that
behavior. At minimum, review the following when relevant:

- `README.md`
- `CHANGELOG.md`
- `docs/README.md`
- `docs/reference/*.md`
- `docs/user/*.md`
- `docs/guide/*.md`
- `scripts/README.md`

Contributor workflow changes must also update:

- this file,
- `docs/dev/README.md`,
- `docs/dev/git_and_docs_workflow.md`,
- GitHub issue or PR templates when the review contract changed.

## Pull Request Expectations

- Keep changes scoped and explain why they are needed.
- Link issues, research docs, benchmark references, or state clearly that the
  change is self-contained.
- Record the validation commands you actually ran.
- Call out contract, schema, fixture, or result changes explicitly.
- Do not include unrelated generated artifacts, local scratch outputs, or build
  products.

## Quality Gates

A change should not be treated as complete unless:

- tests pass for the affected area,
- docs smoke tests pass when documentation or onboarding changed,
- docs and examples stay accurate,
- reproducibility expectations are preserved,
- research and planning artifacts exist when assumptions changed,
- `git diff --check` is clean,
- the branch contains only intentional files.

## Release and Evidence Changes

If your change affects release behavior, publication, or evidence handling, also
update:

- `docs/dev/release_process.md`
- `scripts/README.md`
- `CHANGELOG.md`
- any user-facing command examples in `README.md`

Use `scripts/release/release_gate_check.py` and related release tooling as the
current execution surface for release-adjacent work.
