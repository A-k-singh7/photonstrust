# Phase 43: MDI-QKD + TF/PM-QKD Protocol Surfaces (Validation Report)

Date: 2026-02-14

## Status

- PASS

## Checks

- `py -m pytest`

## Evidence

- Environment:
  - Python: 3.12.10
- Test run (repo root `photonstrust/`):
  - `156 passed, 2 skipped`

## Notes

- `tests/test_qkd_plob_bound.py` is explicitly scoped to `protocol.name: BBM92` to avoid false positives for relay-based protocols (MDI/TF/PM).
