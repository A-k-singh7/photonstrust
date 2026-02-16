# Implementation Plan

## Metadata
- Work item ID: PT-PHASE-03
- Scope owner: Physics/emitter modeling
- Target milestone: Emitter transient-mode extension

## 1. Code-fit analysis
- Current modules impacted:
  - `photonstrust/physics/emitter.py`
  - `photonstrust/config.py`
  - source definitions in schemas
- New modules/files required:
  - `configs/demo6_transient_emitter.yml`
- Interface changes and compatibility strategy:
  - Add optional source fields only.
  - Keep default `emission_mode` as `steady_state`.
  - Preserve existing output keys used by QKD pipeline.

## 2. Incremental build plan
### Step 1
- Objective: Add emission-mode resolver and transient calculations in analytic emitter path.
- File-level edits:
  - `photonstrust/physics/emitter.py`
- Tests:
  - `tests/test_emitter_model.py`

### Step 2
- Objective: Add transient-capable qutip path and unified diagnostics.
- File-level edits:
  - `photonstrust/physics/emitter.py`
- Tests:
  - `tests/test_emitter_model.py`
  - `tests/test_completion_quality.py`

### Step 3
- Objective: Extend source defaults/schema and add runnable transient demo.
- File-level edits:
  - `photonstrust/config.py`
  - `schemas/photonstrust.config.demo1.schema.json`
  - `schemas/photonstrust.reliability_card.v1.schema.json`
  - `README.md`
  - `configs/demo6_transient_emitter.yml`
- Tests:
  - `tests/test_schema_validation.py`
  - full suite `pytest`

## 3. Validation plan
- Unit tests:
  - transient diagnostics bounds
  - transient drive-strength monotonicity
- Integration tests:
  - QKD basic path
  - completion quality suite
- Regression/golden tests:
  - full test suite
- Performance checks:
  - maintain current runtime envelope

## 4. Documentation update plan
- Research docs to update:
  - phase rollout artifacts for Phase 03
- User docs to update:
  - `README.md` demo commands
- Changelog/release notes impact:
  - covered by phased rollout records

## 5. Done criteria
- [x] Research accepted
- [x] Code implemented
- [x] Tests passing
- [x] Docs updated
