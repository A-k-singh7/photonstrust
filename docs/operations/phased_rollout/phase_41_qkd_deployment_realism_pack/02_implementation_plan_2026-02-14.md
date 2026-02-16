# Phase 41: QKD Deployment Realism Pack (Fiber) (Implementation Plan)

Date: 2026-02-14

## Scope

Implement the *deployment realism pack as a product surface*:

- canonical configs for fiber deployment regimes
- drift governance for those canonical configs
- explicit applicability notes in Reliability Cards (v1.0 schema-compatible)

Not in scope:
- Reliability Card v1.1 (Phase 42)
- new protocol families (Phase 43)

## Work items

### 1) Canonical config presets

Add:
- `configs/canonical/README.md`
- `configs/canonical/phase41_*.yml` preset configs

Acceptance:
- each config validates via `photonstrust run --validate-only`
- each config produces stable outputs (no uncertainty sampling)

### 2) Drift governance for canonical presets

Add:
- `scripts/generate_phase41_canonical_baselines.py`
- `tests/fixtures/canonical_phase41_baselines.json`
- `tests/test_phase41_canonical_baselines.py`

Acceptance:
- test compares current outputs to baselines with tight tolerances
- regeneration script exists for intentional baseline updates

### 3) Applicability notes in Reliability Cards

Update:
- `photonstrust/report.py`

Acceptance:
- cards include a `notes` field that:
  - states whether finite-key and coexistence are enabled
  - states whether misalignment/visibility floor is enabled
  - warns that finite-key is a v1 penalty surrogate (not a full composable proof)

### 4) Documentation updates

Update:
- `docs/upgrades/01_upgrade_ideas_qkd_and_satellite.md` mark UPG-QKD-003 done
- `docs/operations/phased_rollout/README.md` mark Phase 41 complete

## Validation

- `py -m pytest`
- `photonstrust run configs/canonical/<preset>.yml --output results/canonical_phase41_<preset>` (optional local spot checks)
