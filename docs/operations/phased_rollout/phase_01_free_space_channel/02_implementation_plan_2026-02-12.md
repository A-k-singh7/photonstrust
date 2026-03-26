# Implementation Plan

## Metadata
- Work item ID: PT-PHASE-01
- Scope owner: Physics + simulation
- Target milestone: Free-space foundation

## 1. Code-fit analysis
- Current modules impacted:
  - `photonstrust/qkd.py`
  - `photonstrust/config.py`
  - `photonstrust/report.py`
  - config and reliability schemas
- New modules/files required:
  - `photonstrust/channels/free_space.py`
  - `tests/test_free_space_channel.py`
  - `tests/test_qkd_free_space.py`
  - `configs/demo5_satellite_downlink.yml`
- Interface changes and compatibility strategy:
  - Add optional `channel.model` switch with default `fiber`.
  - Preserve legacy behavior if `model` is omitted.

## 2. Incremental build plan
### Step 1
- Objective: Add free-space channel decomposition functions.
- File-level edits:
  - `photonstrust/channels/free_space.py`
- Tests:
  - `tests/test_free_space_channel.py`

### Step 2
- Objective: Integrate free-space into QKD compute path.
- File-level edits:
  - `photonstrust/qkd.py`
- Tests:
  - `tests/test_qkd_free_space.py`
  - `tests/test_qkd_smoke.py`

### Step 3
- Objective: Support config/schema/report compatibility.
- File-level edits:
  - `photonstrust/config.py`
  - `photonstrust/report.py`
  - `schemas/photonstrust.config.demo1.schema.json`
  - `README.md`
- Tests:
  - `tests/test_schema_validation.py`

## 3. Validation plan
- Unit tests:
  - free-space function invariants and monotonicity.
- Integration tests:
  - QKD results sensitivity to distance and background count in free-space mode.
- Regression/golden tests:
  - run full suite to ensure no fiber regression.
- Performance checks:
  - maintain existing runtime envelope for standard tests.

## 4. Documentation update plan
- Research docs to update:
  - `docs/research/14_physics_core_open_science_master_plan_2026-02-12.md`
- User docs to update:
  - `README.md` demo command section
- Changelog/release notes impact:
  - included in phased rollout artifacts

## 5. Done criteria
- [x] Research accepted
- [x] Code implemented
- [x] Tests passing
- [x] Docs updated
