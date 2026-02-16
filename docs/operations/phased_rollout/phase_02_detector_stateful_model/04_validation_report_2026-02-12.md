# Validation Report

## Metadata
- Work item ID: PT-PHASE-02
- Date: 2026-02-12
- Reviewer: Internal QA

## 1. Scope validated
- Components tested:
  - detector event-state logic
  - gating and saturation options
  - detector schema compatibility
- Scenarios tested:
  - gating on/off
  - saturation on/off
  - afterpulse + dead-time boundedness

## 2. Test evidence
- Unit tests status: pass
  - `tests/test_detector_model.py`
  - `tests/test_memory_detector_invariants.py`
  - `tests/test_detector_stateful.py`
- Integration tests status: pass
  - `tests/test_completion_quality.py`
  - `tests/test_qkd_basic.py`
  - `tests/test_qkd_free_space.py`
- Regression/golden status: pass
  - full `pytest` suite
- Schema validation status: pass
  - `tests/test_schema_validation.py`

## 3. Scientific checks
- Hypotheses confirmed/rejected:
  - H1 confirmed: gating decreases processed events and duty cycle.
  - H2 confirmed: saturation lowers effective PDE/click outcomes.
- Calibration/uncertainty checks:
  - no calibration-path regression observed.
- Error budget consistency checks:
  - detector false-click path remains bounded and reproducible.

## 4. Performance checks
- Runtime profile:
  - test suite remained within expected execution window.
- Resource usage:
  - no material increase observed in local run.
- Regressions observed:
  - none.

## 5. Documentation completeness
- Research docs updated:
  - yes (phase artifacts created)
- User docs updated:
  - protocol docs updated in operations rollout index
- Release notes/changelog updated:
  - tracked in rollout docs

## 6. Final decision
- Approved / changes requested:
  - Approved.
- Notes:
  - Phase 03 should target emitter transient mode and spectral diagnostics.
