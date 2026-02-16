# Implementation Plan

## Metadata
- Work item ID: PT-PHASE-05
- Scope owner: Reporting and schema governance
- Target milestone: Reliability-card trust metadata

## 1. Code-fit analysis
- Current modules impacted:
  - `photonstrust/report.py`
  - `schemas/photonstrust.reliability_card.v1.schema.json`
  - `tests/test_completion_quality.py`
- New modules/files required:
  - none
- Interface changes and compatibility strategy:
  - additive fields only, no removal of existing keys.
  - defaults supplied when scenario does not include trust metadata.

## 2. Incremental build plan
### Step 1
- Objective: add trust-extension fields to card build output.
- File-level edits:
  - `photonstrust/report.py`
- Tests:
  - completion-quality trust field test

### Step 2
- Objective: extend card schema for trust metadata.
- File-level edits:
  - `schemas/photonstrust.reliability_card.v1.schema.json`
- Tests:
  - `tests/test_schema_validation.py`

### Step 3
- Objective: ensure end-to-end stability under new metadata.
- File-level edits:
  - `tests/test_completion_quality.py`
- Tests:
  - targeted tests and full `pytest`

## 3. Validation plan
- Unit tests:
  - trust fields present and populated.
- Integration tests:
  - reliability card generation from scenario sweeps.
- Regression/golden tests:
  - full suite.
- Performance checks:
  - no runtime impact expected.

## 4. Documentation update plan
- Research docs to update:
  - Phase 05 artifacts in rollout folder
- User docs to update:
  - none mandatory beyond existing research/operations references
- Changelog/release notes impact:
  - tracked via phase docs

## 5. Done criteria
- [x] Research accepted
- [x] Code implemented
- [x] Tests passing
- [x] Docs updated
