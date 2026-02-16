# Phase 53 (W13-W16): Satellite Realism S1/S2

Source anchors:
- `docs/research/deep_dive/32_satellite_qkd_realism_pack.md`
- `docs/upgrades/01_upgrade_ideas_qkd_and_satellite.md`

### W13 (2026-05-11 to 2026-05-17) - Atmosphere path correction
- Work: Replace slant-range atmospheric loss assumption with effective atmospheric path model.
- Artifacts: free-space channel update + atmosphere diagnostics fields.
- Validation: low-elevation monotonic tests.
- Exit: Atmospheric behavior physically bounded across test envelopes.

### W14 (2026-05-18 to 2026-05-24) - Turbulence fading distribution
- Work: Add turbulence distribution model (lognormal/gamma-gamma preview).
- Artifacts: turbulence model layer + outage reporting fields.
- Validation: scintillation-to-outage trend checks.
- Exit: Satellite outputs include distribution-aware turbulence effects.

### W15 (2026-05-25 to 2026-05-31) - Pointing distribution + outage
- Work: Add pointing bias/jitter distribution and outage semantics.
- Artifacts: pointing diagnostics, seeded reproducibility tests.
- Validation: jitter stress tests.
- Exit: Pointing risk is modeled as distribution, not single deterministic scalar.

### W16 (2026-06-01 to 2026-06-07) - Satellite trust labeling hardening
- Work: Enforce preview vs certification labeling and applicability bounds for Orbit outputs.
- Artifacts: reliability card and orbit report updates.
- Validation: orbit card schema checks.
- Exit: Satellite cards include explicit model regime and caveat fields.
