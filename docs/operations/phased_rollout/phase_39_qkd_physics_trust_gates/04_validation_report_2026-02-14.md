# Phase 39 - Validation Report (2026-02-14)

## Unit Test Gate

Command:

```powershell
cd c:\Users\aksin\Desktop\Qutip+qskit projects\photonstrust
py -m pytest -q
```

Result:

- `145 passed, 2 skipped`

## Release Gate

Command:

```powershell
py scripts\release_gate_check.py
```

Result:

- `Release gate: PASS`

## CLI Smoke: QKD Sweep

Command:

```powershell
py -m photonstrust.cli run configs\demo1_quick_smoke.yml --output results\phase_39_smoke_qkd
```

Artifacts (example):

- `results/phase_39_smoke_qkd/demo1_quick_smoke/nir_850/reliability_card.json`
- `results/phase_39_smoke_qkd/demo1_quick_smoke/nir_850/results.json`
- `results/phase_39_smoke_qkd/demo1_quick_smoke/nir_850/report.html`

## CLI Smoke: Orbit Pass Envelope (Free-Space Channel)

Command:

```powershell
py -m photonstrust.cli run configs\demo11_orbit_pass_envelope.yml --output results\phase_39_smoke_orbit
```

Artifacts (example):

- `results/phase_39_smoke_orbit/orbit_pass_run.json` (runner summary with paths)
- `results/phase_39_smoke_orbit/demo11_orbit_pass_envelope/c_1550/orbit_pass_results.json`

Evidence that airmass is now Kasten & Young (1989):

- In `results/phase_39_smoke_orbit/demo11_orbit_pass_envelope/c_1550/orbit_pass_results.json`,
  sample points include `channel_diag.airmass` (e.g., elevation 20 deg gives ~2.90).

## Decision

Phase 39 is **approved**:

- PLOB sanity check is enforced via unit tests.
- Uncertainty bands are now seed-controlled for reproducibility.
- Free-space airmass is upgraded and low-elevation sensitivity is explicit via warnings.
