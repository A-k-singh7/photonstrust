# Implementation Plan

## Metadata
- Work item ID: PT-PHASE-06
- Scope owner: Performance and kernel engineering
- Target milestone: Multi-fidelity mode support

## 1. Code-fit analysis
- Current modules impacted:
  - `photonstrust/qkd.py`
  - `photonstrust/config.py`
  - `photonstrust/sweep.py`
  - `schemas/photonstrust.config.demo1.schema.json`
- New modules/files required:
  - `tests/test_multifidelity_execution.py`
  - `configs/demo7_multifidelity_preview.yml`
  - `configs/demo7_multifidelity_certification.yml`
- Interface changes and compatibility strategy:
  - new scenario fields are optional with defaults.
  - old configs work unchanged (`execution_mode` defaults to `standard`).

## 2. Incremental build plan
### Step 1
- Objective: implement mode settings and apply to uncertainty sampling and detector MC cost.
- File-level edits:
  - `photonstrust/qkd.py`
- Tests:
  - `tests/test_multifidelity_execution.py`

### Step 2
- Objective: propagate scenario mode fields from config build layer.
- File-level edits:
  - `photonstrust/config.py`
  - `schemas/photonstrust.config.demo1.schema.json`
- Tests:
  - schema validation tests

### Step 3
- Objective: emit performance metadata artifacts per run.
- File-level edits:
  - `photonstrust/sweep.py`
- Tests:
  - full suite `pytest`

### Step 4
- Objective: add demo configs and doc references.
- File-level edits:
  - `configs/demo7_multifidelity_preview.yml`
  - `configs/demo7_multifidelity_certification.yml`
  - `README.md`

## 3. Validation plan
- Unit tests:
  - preview and certification settings applied.
- Integration tests:
  - regression baselines remain valid.
- Regression/golden tests:
  - full suite.
- Performance checks:
  - compare preview vs certification elapsed times using `performance.json`.

## 4. Documentation update plan
- Research docs to update:
  - Phase 06 rollout artifact set
- User docs to update:
  - demo commands in `README.md`
- Release notes/changelog impact:
  - tracked via phase docs

## 5. Done criteria
- [x] Research accepted
- [x] Code implemented
- [x] Tests passing
- [x] Docs updated
