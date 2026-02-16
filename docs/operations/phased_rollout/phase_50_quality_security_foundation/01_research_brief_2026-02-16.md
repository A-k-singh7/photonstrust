# Phase 50: Quality + Security Foundation (Research Brief)

Date: 2026-02-16

## Goal

Kick off the 365-day execution cycle with a strict platform quality/security
foundation before multi-fidelity and protocol expansion work.

Week 1 objective is governance and execution hygiene lock:

- open the phase folder under strict rollout protocol,
- lock owner assignments for release-critical workstreams,
- refresh the active risk register and explicit gates,
- prove current baseline remains green.

## Current baseline (repo reality)

- Phase 49 closeout and day-0 rehearsal are complete and green:
  - `docs/operations/phased_rollout/phase_49_cross_track_integration/10_phase49_closeout_report_2026-02-16.md`
  - `docs/operations/phased_rollout/phase_49_cross_track_integration/13_day0_rehearsal_report_2026-02-16.md`
- Core release gate command is available:
  - `scripts/release_gate_check.py`
- Weekly phase artifact contract is active and mandatory:
  - `docs/operations/phased_rollout/README.md`

## Week 1 scope (Phase 50 W01)

1. Create `phase_50_quality_security_foundation/` with required `01/02/03/04`
   artifacts.
2. Lock owner map for release-critical streams:
   - CI and regression gate health,
   - dependency and vulnerability response,
   - config schema governance and migration discipline,
   - release evidence and approvals quality.
3. Refresh risk table in weekly operations notes.
4. Re-run release gate to confirm no baseline regressions.

## Week 2 scope (Phase 50 W02)

1. Expand CI from a single Python runtime to a supported-version matrix.
2. Add optional dependency lanes to exercise extras installation and import-smoke
   checks for major extension stacks.
3. Enforce a minimum test coverage floor in CI and codify coverage policy in
   `pyproject.toml`.
4. Validate coverage gate with:
   - `py -3 -m pytest -q --cov=photonstrust --cov-fail-under=70`

## Week 3 scope (Phase 50 W03)

1. Add automated dependency update governance with Dependabot.
2. Add a security CI workflow with a blocking Python vulnerability scan lane
   (`pip-audit`) and deterministic web dependency install checks (`npm ci`).
3. Strengthen repository disclosure policy (`SECURITY.md`) with response targets
   and coordinated disclosure expectations.
4. Enforce deterministic frontend install policy in active developer docs
   (`README.md`, `web/README.md`) by using `npm ci`.
5. Validate security gate by executing `pip-audit` in an isolated environment.

## Week 4 scope (Phase 50 W04)

1. Add scenario config `schema_version` governance to config loading.
2. Add migration skeleton hooks for legacy scenario configs.
3. Make unsupported schema versions fail fast with actionable migration guidance.
4. Add tests for schema migration and unsupported-version failure semantics.
5. Validate strict config path with:
   - `py -3 -m photonstrust.cli run configs/pilot_day0_kickoff.yml --validate-only`

## Why this sequence is required

Phase 50 sets constraints for all downstream work (Phases 51-62). If ownership,
risk, and gate policy are not explicit now, later physics and protocol work
accumulates unbounded delivery risk.

## References used for this phase kickoff

- Local execution plan:
  - `docs/operations/365_day_plan/phase_50_w01_w04_quality_security_foundation.md`
- Ownership model:
  - `docs/research/deep_dive/13_raci_matrix.md`
- Quality/security upgrade anchors:
  - `docs/upgrades/03_upgrade_ideas_platform_quality_security.md`
  - `docs/audit/03_configuration_validation.md`
  - `docs/audit/04_ci_cd_improvements.md`
  - `docs/audit/06_dependency_security.md`

## Week 2 implementation references

- CI workflow baseline:
  - `.github/workflows/ci.yml`
- Build/test guardrail entry point:
  - `scripts/ci_checks.py`
- Packaging and coverage policy configuration:
  - `pyproject.toml`

## Week 3 implementation references

- Dependency update automation:
  - `.github/dependabot.yml`
- Security CI baseline:
  - `.github/workflows/security-baseline.yml`
- Disclosure and vulnerability response process:
  - `SECURITY.md`
- Deterministic frontend install policy surfaces:
  - `README.md`
  - `web/README.md`

## Week 4 implementation references

- Scenario config governance and migrations:
  - `photonstrust/config.py`
- CLI strict fail-fast behavior for unsupported schema versions:
  - `photonstrust/cli.py`
- Validation tests:
  - `tests/test_config_schema_versioning.py`
- Seeded config with explicit schema version:
  - `configs/pilot_day0_kickoff.yml`
