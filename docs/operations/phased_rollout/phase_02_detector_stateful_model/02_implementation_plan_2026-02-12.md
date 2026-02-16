# Implementation Plan

## Metadata
- Work item ID: PT-PHASE-02
- Scope owner: Physics/detector modeling
- Target milestone: Detector realism extension

## 1. Code-fit analysis
- Current modules impacted:
  - `photonstrust/physics/detector.py`
  - detector fields in config and reliability schemas
- New modules/files required:
  - `tests/test_detector_stateful.py`
- Interface changes and compatibility strategy:
  - Keep `simulate_detector` function signature unchanged.
  - Add optional config fields only.
  - Preserve default behavior when new fields are absent.

## 2. Incremental build plan
### Step 1
- Objective: Introduce stateful event queue detector logic.
- File-level edits:
  - `photonstrust/physics/detector.py`
- Tests:
  - existing detector tests

### Step 2
- Objective: Add gating and saturation controls with diagnostics.
- File-level edits:
  - `photonstrust/physics/detector.py`
- Tests:
  - `tests/test_detector_stateful.py`

### Step 3
- Objective: Extend schemas for optional detector parameters.
- File-level edits:
  - `schemas/photonstrust.config.demo1.schema.json`
  - `schemas/photonstrust.reliability_card.v1.schema.json`
- Tests:
  - `tests/test_schema_validation.py`

## 3. Validation plan
- Unit tests:
  - gating, saturation, and boundedness tests.
- Integration tests:
  - QKD detector path checks and invariants.
- Regression/golden tests:
  - full suite `pytest`.
- Performance checks:
  - no significant runtime increase in unit/integration suite.

## 4. Documentation update plan
- Research docs to update:
  - phased rollout artifacts for Phase 02
- User docs to update:
  - none required for CLI surface change
- Changelog/release notes impact:
  - tracked in rollout docs

## 5. Done criteria
- [x] Research accepted
- [x] Code implemented
- [x] Tests passing
- [x] Docs updated
