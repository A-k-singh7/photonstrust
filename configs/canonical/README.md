# Canonical Config Presets

These configs are deterministic, small-runtime presets used for:

- benchmark drift governance (stable numerical outputs)
- documentation examples
- quick sanity checks on deployed-fiber realism terms

Phase 41 presets focus on fiber QKD deployment realism:

- coexistence Raman noise
- misalignment / visibility floors
- finite-key penalty mode

Phase 54 presets focus on satellite drift governance:

- satellite channel split (uplink/downlink)
- radiance-proxy background model (day/night + optics dependence)
- finite-key enabled canonical satellite baselines

Run validation only:

```bash
photonstrust run configs/canonical/phase41_metro_25km_c_1550_realistic.yml --validate-only

# regenerate canonical baseline fixtures
py -3 scripts/generate_phase54_satellite_canonical_baselines.py
```
