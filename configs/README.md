# Config Catalog

The `configs/` directory is the quickest way to run PhotonTrust without writing
custom code.

## Main Groups

- `quickstart/`
  - Curated first-run configs for QKD and orbit paths.
- `product/`
  - Product and pilot-facing configs used in demo and readiness flows.
- `research/`
  - Calibration, optimization, coexistence, and finite-key research examples.
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
- remaining top-level `demo*` configs
  - Legacy historical config names still pending later migration waves.

## Good Starting Points

- Fast smoke run: `quickstart/qkd_quick_smoke.yml`
- Basic local run: `quickstart/qkd_default.yml`
- Product-ready guided example: `product/pilot_day0_kickoff.yml`
- Orbit example: `quickstart/orbit_pass_envelope.yml`
- Canonical validation: `canonical/phase41_smoke_10km_c_1550_ideal.yml`

## Typical Commands

```bash
photonstrust run configs/quickstart/qkd_default.yml
photonstrust run configs/quickstart/qkd_quick_smoke.yml --output results/smoke_quick
photonstrust run configs/quickstart/orbit_pass_envelope.yml --output results/orbit_demo11
```
