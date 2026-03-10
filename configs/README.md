# Config Catalog

The `configs/` directory is the quickest way to run PhotonTrust without writing
custom code.

## Main Groups

- `demo1_*`
  - Baseline fiber-QKD examples across bands and parameter sweeps.
- `demo2_*` to `demo7_*`
  - Repeater, teleportation, benchmark, satellite, transient emitter, and
    multifidelity demo flows.
- `demo11_*` to `demo13_*`
  - Orbit-pass, coexistence, and finite-key focused examples.
- `canonical/`
  - Deterministic validation fixtures used in regression and release gates.
- `compliance/`
  - ETSI-style compliance scenarios.
- `satellite/`
  - Satellite-chain mission configs and reference lanes.
- `pdks/`
  - PIC process design kit manifests.
- `maintainability/`
  - Internal maintainability budget configuration.

## Good Starting Points

- Fast smoke run: `demo1_quick_smoke.yml`
- Basic local run: `demo1_default.yml`
- Product-ready guided example: `pilot_day0_kickoff.yml`
- Orbit example: `demo11_orbit_pass_envelope.yml`
- Canonical validation: `canonical/phase41_smoke_10km_c_1550_ideal.yml`

## Typical Commands

```bash
photonstrust run configs/demo1_default.yml
photonstrust run configs/demo1_quick_smoke.yml --output results/smoke_quick
photonstrust run configs/demo11_orbit_pass_envelope.yml --output results/orbit_demo11
```
