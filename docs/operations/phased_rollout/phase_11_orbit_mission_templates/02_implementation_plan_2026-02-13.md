# Implementation Plan

## Metadata
- Work item ID: PT-PHASE-11
- Title: OrbitVerify mission templates v1 (pass envelopes + metadata)
- Date: 2026-02-13

## 1) Deliverables

### 1.1 Schemas
- Add OrbitVerify pass results schema:
  - `schemas/photonstrust.orbit_pass_results.v0.schema.json`

### 1.2 Code: pass simulation + runner
- Add module(s):
  - `photonstrust/orbit/__init__.py`
  - `photonstrust/orbit/pass_envelope.py`
    - `simulate_orbit_pass(...)` (pure function returning results dict)
    - `run_orbit_pass_from_config(...)` (writes artifacts to disk)

### 1.3 CLI integration
- Extend `photonstrust run` to detect a top-level `orbit_pass` config and run it.
  - `photonstrust/cli.py`

### 1.4 Scenario templates (YAML configs)
- Add a demo pass envelope config:
  - `configs/demo11_orbit_pass_envelope.yml`

### 1.5 Tests
- Add tests enforcing "known-sense" invariants:
  - elevation improvement at fixed distance/background
  - background penalty at fixed distance/elevation
  - best/median/worst ordering sanity at fixed samples
  - schema validation for results (jsonschema)
- File:
  - `tests/test_orbit_pass_envelope.py`

### 1.6 Documentation updates
- Add Phase 11 rollout artifacts (this folder).
- Update:
  - `docs/research/15_platform_rollout_plan_2026-02-13.md` (mark Phase 11 implemented)
  - `docs/research/14_physics_core_open_science_master_plan_2026-02-12.md` (status)
  - `docs/research/03_physics_models.md` (OrbitVerify mission layer)
  - `docs/operations/phased_rollout/README.md`
  - `docs/operations/README.md`
  - `README.md` (demo command)

## 2) Orbit pass config contract (v0.1)

Top-level YAML structure:
- `orbit_pass` (required):
  - `id` (string)
  - `band` (string; e.g., `c_1550`)
  - `wavelength_nm` (optional; defaults from band preset)
  - `dt_s` (number; fixed step for integrating key rate)
  - `samples` (array):
    - `t_s`, `distance_km`, `elevation_deg`, `background_counts_cps`
  - `cases` (optional array):
    - `id`, `label`, `channel_overrides` (dict)
- plus standard blocks:
  - `source`, `channel` (must be `model: free_space`), `detector`, `timing`, `protocol`, `uncertainty`

## 3) Output artifacts (v0.1)
Write to:
- `<output>/<orbit_pass_id>/<band>/orbit_pass_results.json`

Contents:
- pass metadata
- per-case points and summary
- contributor decomposition per sample (`free_space.total_free_space_efficiency`)
- reproducibility block
- explicit assumptions/limitations block

## 4) Validation gates
- Unit tests:
  - `py -m pytest -q`
- Release gate:
  - `py scripts/release/release_gate_check.py --output results/release_gate/phase11_release_gate_report.json`
- Manual smoke:
  - `photonstrust run configs/demo11_orbit_pass_envelope.yml --output results/orbit_demo11`

## 5) Non-goals (explicit)
- No orbit propagation / TLE parsing in v0.1.
- No weather API integration in v0.1; use explicit availability envelopes later.
- No formal standards compliance claim; only "standards-anchored assumptions".

