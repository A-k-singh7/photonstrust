# Phase 49 — One-Command Baseline Fixture Regeneration + Validation

**Date:** 2026-02-16  
**Scope:** Regenerate both baseline fixture sets (demo + Phase 41 canonical) deterministically and validate them.

## One-command flow (copy/paste)

```bash
cd "/mnt/c/Users/aksin/Desktop/Qutip+qskit projects/photonstrust" && ./.venv/bin/python scripts/regenerate_baseline_fixtures.py
```

## What this command does (lightweight wrapper over existing commands)

The wrapper script `scripts/regenerate_baseline_fixtures.py` reuses current project commands:

1. `python scripts/generate_baselines.py`
2. `python scripts/generate_phase41_canonical_baselines.py`
3. Re-runs (1) and (2), then compares SHA-256 hashes of:
   - `tests/fixtures/baselines.json`
   - `tests/fixtures/canonical_phase41_baselines.json`
   to enforce deterministic regeneration
   - Note: Phase 41 fixture metadata timestamp is deterministic by default (`SOURCE_DATE_EPOCH` if set, else fixed epoch).
4. `python -m pytest tests/test_regression_baselines.py tests/test_phase41_canonical_baselines.py tests/test_validation_harness.py`
5. `python scripts/check_benchmark_drift.py`
6. `python scripts/run_validation_harness.py --output-root results/validation`

## Success criteria

- Command exits with status `0`
- Script prints: `Baseline fixtures regenerated and validated successfully.`
- Validation harness summary shows `"ok": true`

## Optional flags

- Custom harness artifact path:
  - `./.venv/bin/python scripts/regenerate_baseline_fixtures.py --output-root results/validation_phase49`
- Skip the second-pass hash determinism check (not recommended for release workflow):
  - `./.venv/bin/python scripts/regenerate_baseline_fixtures.py --skip-determinism-check`
