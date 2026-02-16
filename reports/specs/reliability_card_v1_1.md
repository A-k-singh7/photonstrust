# PhotonTrust Reliability Card v1.1

Date: 2026-02-14

v1.1 extends v1.0 by adding standardized trust fields that make cards:

- comparable across projects and time
- harder to misuse (bounded claims)
- easier to audit externally

This is not a compliance certification. Standards fields are anchors only.

## New required sections (v1.1)

The v1.1 JSON Schema requires the following additional blocks:

1) `evidence_quality`
- tier 0..3
- label (Simulation-only / Calibrated / Validated / Qualified)
- optional calibration diagnostics mirror

2) `operating_envelope`
- channel model (fiber/free_space)
- distance range (min/max)
- wavelength
- detector/source technology labels

3) `benchmark_coverage_v1_1`
- canonical presets exercised
- optional gates: PLOB check, regression baseline, golden report

4) `standards_alignment`
- explicit anchors to ETSI/ISO/ITU/NIST references
- default `not_assessed` / `informational` statuses

5) `provenance_v1_1`
- tool and environment identity
- config hash
- key dependency versions

## Backward compatibility

- v1.0 cards remain supported and are still the default output.
- v1.1 cards are opt-in via config (`scenario.reliability_card_version: 1.1`).

Schema paths:
- v1.0: `schemas/photonstrust.reliability_card.v1.schema.json`
- v1.1: `schemas/photonstrust.reliability_card.v1_1.schema.json`

## CLI tools

Validate:

```bash
photonstrust card validate results/.../reliability_card.json
photonstrust card validate results/.../reliability_card.json --schema v1.1
```

Diff:

```bash
photonstrust card diff results/a/reliability_card.json results/b/reliability_card.json
```
