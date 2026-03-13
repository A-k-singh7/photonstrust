# Phase 53: Satellite Realism S1/S2 (Implementation Plan)

Date: 2026-02-16

## Scope

Implement Phase 53 W13-W16 by upgrading satellite/free-space realism with
bounded atmosphere-path behavior, turbulence and pointing distributions, outage
semantics, and explicit trust labeling in orbit results and schema surfaces.

## Owner map lock (release-critical workstreams)

Owner roles follow `docs/research/deep_dive/13_raci_matrix.md`.

| Workstream | Accountable | Responsible | Consulted | Backup |
|---|---|---|---|---|
| Atmosphere-path model correction + diagnostics | TL | SIM | QA | DOC |
| Turbulence/pointing distributions + outage semantics | TL | SIM | QA | DOC |
| Orbit diagnostics/report/schema trust labeling updates | TL | DOC | QA | SIM |
| Regression + release validation gates | QA | SIM | TL | DOC |

## Implementation tasks

1. Add bounded atmosphere-path behavior in free-space channel calculations:
   - `photonstrust/channels/free_space.py`
2. Propagate decomposition/outage details through channel engine:
   - `photonstrust/channels/engine.py`
3. Extend free-space/satellite defaults for realism controls:
   - `photonstrust/config.py`
4. Surface trust/outage fields in orbit envelope and diagnostics:
   - `photonstrust/orbit/pass_envelope.py`
   - `photonstrust/orbit/diagnostics.py`
5. Update orbit pass result schema contract:
   - `schemas/photonstrust.orbit_pass_results.v0.schema.json`
6. Add/refresh regression coverage for realism behavior:
   - `tests/test_free_space_channel.py`
   - `tests/test_channel_engine_unified.py`
   - `tests/test_orbit_pass_envelope.py`
   - `tests/test_orbit_diagnostics.py`
   - `tests/api/test_api_server_optional.py`
7. Execute validation gates:
   - `py -3 -m pytest -q tests/test_free_space_channel.py tests/test_channel_engine_unified.py tests/test_orbit_pass_envelope.py tests/test_orbit_diagnostics.py tests/api/test_api_server_optional.py`
   - `py -3 -m pytest -q`
   - `py -3 scripts/release/release_gate_check.py`
   - `py -3 scripts/validation/ci_checks.py`
   - `py -3 scripts/validation/run_validation_harness.py --output-root results/validation`

## Acceptance gates

- Atmosphere-path behavior is bounded and physically plausible at low elevation.
- Turbulence/pointing are represented by distribution-aware controls.
- Outage semantics are visible in orbit outputs and diagnostics.
- Orbit outputs include explicit trust labeling for preview/certification context.
- Targeted, full, release, CI, and validation harness gates all pass.
