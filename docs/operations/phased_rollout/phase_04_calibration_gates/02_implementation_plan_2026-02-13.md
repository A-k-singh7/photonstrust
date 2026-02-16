# Implementation Plan

## Metadata
- Work item ID: PT-PHASE-04
- Scope owner: Calibration and quality engineering
- Target milestone: Calibration gate enforcement

## 1. Code-fit analysis
- Current modules impacted:
  - `photonstrust/calibrate/bayes.py`
  - `photonstrust/cli.py`
  - `tests/test_completion_quality.py`
  - `configs/calibration_example.yml`
- New modules/files required:
  - none
- Interface changes and compatibility strategy:
  - new args are optional and default to non-enforcing behavior.
  - existing calibration calls remain valid.

## 2. Incremental build plan
### Step 1
- Objective: add gate metric calculation and diagnostics output.
- File-level edits:
  - `photonstrust/calibrate/bayes.py`
- Tests:
  - diagnostics field checks in completion-quality tests

### Step 2
- Objective: add enforce mode with threshold controls and failure behavior.
- File-level edits:
  - `photonstrust/calibrate/bayes.py`
  - `photonstrust/cli.py`
- Tests:
  - enforced-pass and enforced-fail tests

### Step 3
- Objective: ship calibrated example config and docs for CLI workflow.
- File-level edits:
  - `configs/calibration_example.yml`
  - `README.md`
- Tests:
  - CLI calibration example run
  - full `pytest`

## 3. Validation plan
- Unit tests:
  - gate field bounds and booleans
  - strict threshold failure path
- Integration tests:
  - completion-quality suite
  - CLI calibration execution
- Regression/golden tests:
  - full test suite
- Performance checks:
  - no material runtime regression in calibration tests

## 4. Documentation update plan
- Research docs to update:
  - phase rollout artifacts for Phase 04
- User docs to update:
  - calibration note in `README.md`
- Changelog/release notes impact:
  - captured in phase records

## 5. Done criteria
- [x] Research accepted
- [x] Code implemented
- [x] Tests passing
- [x] Docs updated
