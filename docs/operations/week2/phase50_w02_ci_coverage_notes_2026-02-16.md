# Phase 50 W02 Operations Notes (CI Matrix + Coverage Floor)

Date: 2026-02-16

## Week focus

Harden baseline CI quality guardrails by broadening runtime coverage, exercising
optional dependency stacks, and enforcing a minimum test coverage floor.

## Implemented controls

| Control ID | Control | Implementation | Status |
|---|---|---|---|
| P50-W2-C1 | Python-version CI matrix | `.github/workflows/ci.yml` test job runs on `3.9/3.10/3.11/3.12` | Implemented |
| P50-W2-C2 | Coverage enforcement in CI | `scripts/ci_checks.py` invocation now passes `--cov-fail-under=70` args | Implemented |
| P50-W2-C3 | Coverage policy codification | `pyproject.toml` defines coverage source/branch/report with `fail_under = 70` | Implemented |
| P50-W2-C4 | Optional dependency lanes | CI job adds non-blocking extras lanes (`qutip`, `qiskit`, `api`, `layout`) with install/import smoke | Implemented |

## Evidence

- Validation command: `py -3 -m pytest -q --cov=photonstrust --cov-fail-under=70`
- Outcome: `216 passed, 2 skipped`
- Coverage: `72.52%` (floor: `70%`)

## Open follow-up for Week 3

- Add dependency vulnerability scanning lane (`pip-audit`) with explicit severity
  handling policy.
- Add Dependabot configuration and codify disclosure process in `SECURITY.md`.
