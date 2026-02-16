# Validation Report

## Metadata
- Work item ID: PT-PHASE-01
- Date: 2026-02-12
- Reviewer: Internal QA

## 1. Scope validated
- Components tested:
  - free-space channel decomposition
  - QKD integration path for `channel.model = free_space`
  - schema compatibility
- Scenarios tested:
  - free-space monotonicity checks
  - background count sensitivity
  - baseline QKD scenario smoke checks

## 2. Test evidence
- Unit tests status: pass
  - `tests/test_free_space_channel.py`
- Integration tests status: pass
  - `tests/test_qkd_free_space.py`
- Regression/golden status: pass
  - full `pytest` suite
- Schema validation status: pass
  - `tests/test_schema_validation.py`

## 3. Scientific checks
- Hypotheses confirmed/rejected:
  - H1 confirmed (distance penalty observed).
  - H2 confirmed (background penalty observed).
- Calibration/uncertainty checks:
  - existing uncertainty path unchanged; no regression observed.
- Error budget consistency checks:
  - reliability-card generation stable with free-space scenarios.

## 4. Performance checks
- Runtime profile:
  - no material regression in test runtime.
- Resource usage:
  - within existing unit/integration envelope.
- Regressions observed:
  - none.

## 5. Documentation completeness
- Research docs updated:
  - yes
- User docs updated:
  - yes (`README.md` demo command)
- Release notes/changelog updated:
  - captured in phased rollout records

## 6. Final decision
- Approved / changes requested:
  - Approved.
- Notes:
  - next priority moved to detector stateful model (Phase 02).
