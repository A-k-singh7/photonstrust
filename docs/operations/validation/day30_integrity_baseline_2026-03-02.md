# Day-30 Integrity Baseline (2026-03-02)

This baseline defines merge-time controls for Month-1 execution.

## Required local hooks

Run once per clone:

```bash
pip install -e .[dev]
pre-commit install
```

## Merge gates

1. `ruff` lint gate (`E9`, `F63`, `F7`, `F82`) must pass.
2. Physics model metadata contract must pass (`scripts/check_model_metadata_contract.py`).
3. Runtime hardcoded-constant gate must pass (`scripts/check_hardcoded_physics_constants.py`).
4. Pytest and validation harness smoke must pass via `scripts/ci_checks.py`.

## Physics model metadata contract

Every production model must provide:

1. `citation`
2. `validity_domain`
3. `uncertainty_model`
4. `known_failure_regimes`

Registry location:

- `photonstrust/physics/model_metadata.py`

## Hardcoded physics constants policy

Module-level numeric constants in runtime paths are blocked unless one of these is true:

1. The value is in a dedicated constants/metadata module.
2. The assignment line includes `physics-constant-ok` with an explicit reason.

Gate implementation:

- `scripts/check_hardcoded_physics_constants.py`

## Runtime strict models

Satellite chain config/certificate payloads are validated with strict Pydantic runtime models:

- `photonstrust/workflow/runtime_models.py`

Certification mode fails closed when `accumulate_backend` is not in `runtime.trusted_backends`.
