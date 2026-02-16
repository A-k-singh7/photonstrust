# Phase 54: Satellite S3/S4 + Pilot Hardening (Implementation Plan)

Date: 2026-02-16

## Scope

Implement Phase 54 W17-W20 by shipping radiance-proxy background estimation,
orbit finite-key pass budgeting, canonical satellite drift governance fixtures,
and pilot packet v2 documentation updates.

## Owner map lock (release-critical workstreams)

Owner roles follow `docs/research/deep_dive/13_raci_matrix.md`.

| Workstream | Accountable | Responsible | Consulted | Backup |
|---|---|---|---|---|
| Radiance-proxy background model + uncertainty surfaces | TL | SIM | QA | DOC |
| Orbit finite-key pass budgeting + epsilon metadata | TL | SIM | QA | DOC |
| Satellite canonical benchmark fixtures + drift governance | QA | SIM | TL | DOC |
| Pilot packet v2 claim/readiness updates | TL | DOC | QA | SIM |

## Implementation tasks

1. Add radiance-proxy channel behavior + diagnostics:
   - `photonstrust/channels/free_space.py`
   - `photonstrust/channels/engine.py`
   - `photonstrust/config.py`
2. Add orbit finite-key pass budgeting and summary metadata:
   - `photonstrust/orbit/pass_envelope.py`
   - `photonstrust/orbit/diagnostics.py`
   - `schemas/photonstrust.orbit_pass_envelope.v0_1.schema.json`
   - `schemas/photonstrust.orbit_pass_results.v0.schema.json`
   - `photonstrust/api/server.py`
3. Add canonical satellite benchmark governance assets:
   - `configs/canonical/phase54_satellite_*.yml`
   - `scripts/generate_phase54_satellite_canonical_baselines.py`
   - `tests/fixtures/canonical_phase54_satellite_baselines.json`
   - `photonstrust/benchmarks/validation_harness.py`
   - `scripts/check_benchmark_drift.py`
   - `scripts/regenerate_baseline_fixtures.py`
4. Add/refresh regression tests:
   - `tests/test_free_space_channel.py`
   - `tests/test_orbit_pass_envelope.py`
   - `tests/test_orbit_diagnostics.py`
   - `tests/test_api_server_optional.py`
   - `tests/test_phase54_satellite_canonical_baselines.py`
   - `tests/test_validation_harness.py`
5. Update pilot packet v2 docs:
   - `docs/operations/pilot_readiness_packet/README.md`
   - `docs/operations/pilot_readiness_packet/01_pilot_intake_checklist.md`
   - `docs/operations/pilot_readiness_packet/02_pilot_success_criteria_template.md`
   - `docs/operations/pilot_readiness_packet/03_claim_boundaries_summary.md`
   - `docs/operations/pilot_readiness_packet/04_day0_operator_runbook.md`
6. Execute validation gates:
   - `py -3 -m pytest -q`
   - `py -3 scripts/check_benchmark_drift.py`
   - `py -3 scripts/release_gate_check.py`
   - `py -3 scripts/ci_checks.py`
   - `py -3 scripts/run_validation_harness.py --output-root results/validation`

## Acceptance gates

- Radiance-proxy behavior is directional (`day > night`) and optics-sensitive.
- Orbit pass outputs include finite-key pass budget + epsilon fields.
- Benchmark drift governance includes Phase 54 satellite canonical fixtures.
- Pilot packet docs explicitly align claims to new satellite validity envelope.
- Full tests, drift checks, release gate, CI checks, and harness pass.
