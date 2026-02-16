# Phase 42: Reliability Card v1.1 (Implementation Plan)

Date: 2026-02-14

## Scope

Implement Reliability Card v1.1 as an additive, opt-in schema and generator.

Constraints:
- Do not break existing v1.0 card consumers by changing default output.
- Keep v1.0 generation intact; add v1.1 as explicit selection.

## Planned changes

### 1) Schema

Add:
- `schemas/photonstrust.reliability_card.v1_1.schema.json`

### 2) Spec doc

Add:
- `reports/specs/reliability_card_v1_1.md`

### 3) Card generator

Update:
- `photonstrust/report.py`

Implementation approach:
- Split card generation into:
  - `_build_reliability_card_v1_0(...)`
  - `_build_reliability_card_v1_1(...)`
- Dispatch based on `scenario['reliability_card_version']` (default: 1.0).

v1.1 must populate:
- `evidence_quality` (tier + label + diagnostics)
- `operating_envelope` (distance range, channel model, key assumptions)
- `benchmark_coverage` (minimum viable object; canonical presets noted)
- `standards_alignment` (default not_assessed with explicit disclaimer)
- `provenance` (tool + versions + hashes)

### 4) Config plumbing

Update:
- `photonstrust/config.py` to carry optional `scenario.reliability_card_version`
  into built scenario dict as `reliability_card_version`.

### 5) CLI tools

Update:
- `photonstrust/cli.py` add:
  - `photonstrust card validate <card.json> [--schema v1|v1.1]`
  - `photonstrust card diff <lhs.json> <rhs.json> [--limit N]`

### 6) Tests

Add:
- `tests/test_reliability_card_v1_1_schema.py`

Update (if needed):
- existing v1.0 schema tests must continue to pass

## Validation

- `py -m pytest`
- optional smoke run:
  - `photonstrust run configs/demo1_quick_smoke.yml --output results/phase42_smoke`
