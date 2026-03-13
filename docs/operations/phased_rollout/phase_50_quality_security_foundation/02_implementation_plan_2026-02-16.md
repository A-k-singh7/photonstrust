# Phase 50: Quality + Security Foundation (Implementation Plan)

Date: 2026-02-16

## Scope for this build slice

This implementation plan now covers Week 1 through Week 4:

- Week 1 governance lock (phase scaffolding, owner map, risk refresh, release gate),
- Week 2 CI hardening (Python matrix, optional dependency lanes, coverage floor),
- Week 3 security baseline (Dependabot, security CI lane, disclosure policy hardening),
- Week 4 scenario config schema governance (versioning, migration hooks, strict validation).

## Owner map lock (release-critical workstreams)

Owner roles follow `docs/research/deep_dive/13_raci_matrix.md`.

| Workstream | Accountable | Responsible | Consulted | Backup |
|---|---|---|---|---|
| Release gate health (`release_gate_check.py`) | TL | QA | SIM | DOC |
| CI and coverage policy | QA | SIM | TL | DOC |
| Dependency and vulnerability response | TL | QA | DOC | SIM |
| Config schema and migration governance | TL | SIM | QA, DOC | PROT |
| Evidence/report quality and claim boundaries | TL | DOC | QA | PHY |

No release-critical stream is left without accountable and responsible roles.

## Implementation tasks

1. Add Phase 50 folder and mandatory files:
   - `01_research_brief_2026-02-16.md`
   - `02_implementation_plan_2026-02-16.md`
   - `03_build_log_2026-02-16.md`
   - `04_validation_report_2026-02-16.md`
2. Update phased-rollout index to include Phase 50 status.
3. Add weekly ops note with refreshed risk table.
4. Execute validation gate:
   - `py -3 scripts/release/release_gate_check.py`
5. Upgrade CI workflow (`.github/workflows/ci.yml`) to include:
   - Python matrix (`3.9`, `3.10`, `3.11`, `3.12`),
   - coverage-enforced pytest invocation through `scripts/validation/ci_checks.py`,
   - optional dependency lanes for `qutip`, `qiskit`, `api`, `layout` extras.
6. Update package/dev and coverage policy config (`pyproject.toml`):
   - add `pytest-cov` to `dev` extras,
   - set coverage source/branch/report policy with `fail_under = 70`.
7. Execute Week 2 validation command:
   - `py -3 -m pytest -q --cov=photonstrust --cov-fail-under=70`
8. Add Dependabot config (`.github/dependabot.yml`) for:
   - Python dependencies,
   - npm dependencies in `/web`,
   - GitHub Actions updates.
9. Add security workflow (`.github/workflows/security-baseline.yml`) with:
   - blocking `pip-audit` runtime dependency scan,
   - deterministic web dependency install (`npm ci`),
   - non-blocking Node runtime audit baseline (`npm audit --omit=dev`).
10. Upgrade disclosure process documentation (`SECURITY.md`) with response targets,
    coordinated disclosure policy, and dependency monitoring statements.
11. Update web dev setup docs to deterministic install commands:
    - `README.md`
    - `web/README.md`
12. Execute Week 3 validation command:
    - `pip-audit`
13. Add scenario config schema-version governance in `photonstrust/config.py`:
    - define supported schema versions,
    - include migration hooks for legacy config payloads,
    - emit actionable failure message for unsupported versions.
14. Wire strict fail-fast handling in CLI run path (`photonstrust/cli.py`) for
    unsupported schema versions.
15. Add schema-governance tests (`tests/test_config_schema_versioning.py`) for:
    - legacy migration behavior,
    - unsupported-version rejection,
    - `--validate-only` fail-fast semantics.
16. Seed explicit schema version in the pilot day-0 config:
    - `configs/pilot_day0_kickoff.yml`
17. Execute Week 4 validation command:
    - `py -3 -m photonstrust.cli run configs/pilot_day0_kickoff.yml --validate-only`

## Week 1 acceptance gates

- Required artifacts exist in Phase 50 folder.
- Owner map contains no release-critical gaps.
- Weekly risk table is updated with explicit mitigations and gate triggers.
- Release gate command returns PASS.

## Week 2 acceptance gates

- CI workflow defines supported Python version matrix.
- CI workflow includes optional dependency lanes for extension extras.
- Coverage floor (`70%`) is enforced in CI and policy config.
- Coverage validation command returns PASS.

## Week 3 acceptance gates

- Dependabot is configured for Python, npm (`/web`), and GitHub Actions.
- Security CI workflow runs `pip-audit` automatically on push, PR, and schedule.
- Disclosure and vulnerability response policy is documented in `SECURITY.md`.
- Deterministic frontend install policy is reflected in active web setup docs.
- `pip-audit` validation command returns no known vulnerabilities.

## Week 4 acceptance gates

- Scenario config loader enforces `schema_version` governance.
- Legacy scenario configs can be migrated through explicit migration hooks.
- Unsupported config schema versions fail fast with migration guidance.
- Validation tests exist for migration and strict failure semantics.
- `--validate-only` pilot command returns PASS on supported schema version.

## Deferred beyond Phase 50

- None.
