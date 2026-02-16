# Implementation Plan

## Metadata
- Work item ID: PT-PHASE-18
- Title: OrbitVerify evidence hardening v0.2 (availability envelope + standards anchors)
- Date: 2026-02-13

## 1) Deliverables

### 1.1 Availability envelope (config-first)
- Modify:
  - `photonstrust/orbit/pass_envelope.py`
- Add optional config:
  - `orbit_pass.availability.clear_fraction` (float in `[0, 1]`)
- Extend case summaries:
  - `summary.expected_total_keys_bits = summary.total_keys_bits * clear_fraction`
  - include `clear_fraction` in results metadata/assumptions for provenance.

### 1.2 Standards anchors (explicit references, no compliance claim)
- Modify:
  - `photonstrust/orbit/pass_envelope.py`
- Add to results:
  - an assumptions note listing standards anchors used as conceptual mapping
    for loss contributor categories (e.g., ITU-R P.1814/P.1817; CCSDS optical comm
    spec references used as context).
- Extend HTML report:
  - show the standards anchors in a “References/Anchors” panel.

### 1.3 Diagnostics extension
- Modify:
  - `photonstrust/orbit/diagnostics.py`
- Add checks:
  - `orbit_pass.availability.clear_fraction`:
    - error if not a number
    - error if outside `[0, 1]`

### 1.4 Tests
- Modify:
  - `tests/test_orbit_pass_envelope.py`
  - `tests/test_orbit_diagnostics.py`
- Add assertions:
  - expected_total_keys_bits exists and matches clear_fraction scaling.
  - diagnostics flags invalid clear_fraction values.

### 1.5 Docs
- Add Phase 18 artifacts:
  - `03_build_log_2026-02-13.md`
  - `04_validation_report_2026-02-13.md`
- Update indices after acceptance:
  - `docs/operations/phased_rollout/README.md`
  - `docs/operations/README.md`
  - `docs/research/14_physics_core_open_science_master_plan_2026-02-12.md`
  - `docs/research/15_platform_rollout_plan_2026-02-13.md`

## 2) Validation gates

- Python:
  - `py -m pytest -q`
  - `py scripts/release_gate_check.py`
- Web:
  - `cd web && npm run lint`
  - `cd web && npm run build`

## 3) Risk / mitigation

- Risk: users interpret expected keys as guaranteed.
  - Mitigation: label as expectation under declared clear_fraction assumption,
    and only compute it when availability is explicitly provided.

