# Phase 50 (W1-W4): Quality + Security Foundation

Source anchors:
- `docs/upgrades/03_upgrade_ideas_platform_quality_security.md`
- `docs/audit/03_configuration_validation.md`
- `docs/audit/04_ci_cd_improvements.md`
- `docs/audit/06_dependency_security.md`

### W01 (2026-02-16 to 2026-02-22) - Program lock and phase scaffolding
- Work: Open `phase_50_quality_security_foundation`, lock owner map, refresh risk register and gates.
- Artifacts: Phase 50 `01/02/03/04` docs, updated risk table in weekly ops notes.
- Validation: `python scripts/release/release_gate_check.py`
- Exit: No open owner gaps on release-critical workstreams.

### W02 (2026-02-23 to 2026-03-01) - CI matrix and coverage floor
- Work: Python version matrix, optional dependency lanes, coverage fail floor in CI.
- Artifacts: CI workflow updates, coverage config in `pyproject.toml`.
- Validation: `pytest -q --cov=photonstrust --cov-fail-under=70`
- Exit: CI matrix green with coverage enforcement.

### W03 (2026-03-02 to 2026-03-08) - Security baseline
- Work: Dependabot, pip-audit lane, deterministic frontend install policy, disclosure process.
- Artifacts: `.github/dependabot.yml`, `SECURITY.md`, security CI job.
- Validation: `pip-audit`
- Exit: Security scanning runs in CI and policy documented.

### W04 (2026-03-09 to 2026-03-15) - Config versioning + migration skeleton
- Work: Add `schema_version` governance for scenario configs, migration hooks, API strict validation.
- Artifacts: Config loader upgrades, migration notes, validation tests.
- Validation: `python -m photonstrust.cli run configs/product/pilot_day0_kickoff.yml --validate-only`
- Exit: Unsupported schema versions fail fast with migration guidance.
