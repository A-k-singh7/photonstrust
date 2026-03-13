# Testing Guide

PhotonTrust uses multiple validation layers. Run the smallest relevant checks
first, then expand to broader gates when needed.

## Common Test Commands

### Python checks

```bash
python scripts/validation/ci_checks.py
python -m pytest -q tests/api tests/scripts tests/ui
```

### Full validation harness

```bash
python scripts/validation/run_validation_harness.py --output-root results/validation
python scripts/validation/validate_recent_research_examples.py
python scripts/validation/compare_recent_research_benchmarks.py
```

### Frontend checks

```bash
cd web
npm run build
npm run test:ui
```

## Test Groups

- `tests/api/`
  - API route and server-lane tests
- `tests/scripts/`
  - automation script tests
- `tests/ui/`
  - Python-side UI helper tests
- `web/tests/`
  - Playwright browser tests for the React UI

## When to run what

- bug fix in Python logic: affected unit/integration tests + `ci_checks.py`
- API changes: `tests/api/` + relevant contract/schema tests
- script changes: relevant `tests/scripts/` tests
- UI changes: `npm run build` + targeted Playwright specs
- model or benchmark changes: validation harness + research benchmark scripts
