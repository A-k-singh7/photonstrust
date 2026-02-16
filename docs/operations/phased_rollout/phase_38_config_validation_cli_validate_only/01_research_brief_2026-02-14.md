# Phase 38 - Config Validation + CLI `--validate-only` (v0.1.1) - Research Brief (2026-02-14)

## Goal

Increase trustworthiness of scenario-based runs (YAML config -> scenario expansion -> sweep) by ensuring:

- invalid/unphysical parameter values are caught early with clear error messages
- users can validate configs without running expensive simulations
- distance sweep expansion is numerically stable (no float drift, includes stop)

## Drivers (Audit)

This phase implements high-priority items from:

- `docs/audit/03_configuration_validation.md`
- `docs/audit/07_code_quality.md` (distance expansion drift)

## Findings

### 1) Scenario configs were expanded without validation

`photonstrust/config.py` expands YAML configs into scenario dicts via defaults and presets.
Before this phase, there was no consistent range validation after defaults were applied.

Risks:
- silent acceptance of invalid values (e.g. `pde > 1`, negative losses)
- misleading “trust artifacts” because the engine ran on impossible inputs

### 2) CLI lacked a validation-only mode

Users had to run the simulation to discover config errors. This slows iteration and makes
preflight checks difficult in CI or in “contract” style workflows.

### 3) Distance sweep expansion could accumulate float drift

The `distance_km` dict expansion used a manual count and `start + i * step`, which can
produce values like `99.999999999` instead of the intended stop value.

## Decision

Implement a lightweight validation layer (no new heavy dependencies) and wire it into the CLI:

- New module: `photonstrust/validation.py`
- CLI: `photonstrust run --validate-only`
- Always validate scenarios before running (fail-fast)
- Make `_expand_distance` deterministic and validate step/start/stop

