# 08 - Reliability Card v1.1 Proposal

PhotonTrust's core differentiator is the **reliability card** -- a
machine-readable trust artifact for quantum links. This document proposes
v1.1 enhancements based on cross-domain certification best practices.

---

## Research & Standards Anchors (Primary Links)

### QKD / QKDN standards and guidance (to cite inside cards)
- ETSI GS QKD 016 v2.1.1 (Protection Profile for QKD): https://www.etsi.org/deliver/etsi_gs/qkd/001_099/016/02.01.01_60/gs_qkd016v020101p.pdf
- ISO/IEC 23837-1 and 23837-2 (QKD security requirements / evaluation): https://www.iso.org/standard/83834.html and https://www.iso.org/standard/86580.html
- ITU-T Y.3800 (overview of QKD networks): https://www.itu.int/rec/T-REC-Y.3800
- NIST SP 800-57 Part 1 Rev. 5 (key management guidance): DOI 10.6028/NIST.SP.800-57pt1r5

### Evidence tiers: calibration diagnostics / uncertainty reporting
- MCMC convergence diagnostics (improved R-hat and ESS guidance): Vehtari et al. (2021), Bayesian Analysis, DOI: 10.1214/20-BA1221

### Supply chain provenance (reproducibility and tamper-evidence)
- NIST SSDF: NIST SP 800-218, DOI: 10.6028/NIST.SP.800-218
- SLSA provenance levels/spec: https://slsa.dev/spec/v1.2/
- in-toto (artifact metadata for supply chain integrity): https://in-toto.io/
- Sigstore (artifact signing/verification ecosystem): https://www.sigstore.dev/
- OpenSSF Scorecard (supply-chain posture checks): https://scorecard.dev/

## Current State (v1.0)

The current reliability card (see `reports/specs/reliability_card_v1.md`)
captures simulation outputs: key rates, QBER, fidelity, uncertainty bands,
and a qualitative `safe_use_label`.

---

## Proposed v1.1 Fields

### 1. Evidence Quality Tier

Map every card to a defined evidence tier:

| Tier | Label | Requirements |
|------|-------|-------------|
| 0 | Simulation-only | Model predictions without calibration data |
| 1 | Calibrated | Model calibrated against measurement data; diagnostics passing (R-hat < 1.01, ESS > 400) |
| 2 | Validated | Calibrated model validated against independent held-out test data |
| 3 | Qualified | Validated + full uncertainty propagation + all canonical benchmarks pass |

```yaml
evidence_quality:
  tier: 2
  label: "Validated"
  calibration_date: "2026-02-10"
  calibration_diagnostics:
    r_hat_max: 1.003
    ess_min: 812
    ppc_passed: true
  validation_dataset: "measurements/field_trial_2026-02-08.json"
  validation_residual_mean: 0.003
  validation_residual_max: 0.012
```

---

### 2. Operating Envelope

Explicitly state conditions under which the card is valid:

```yaml
operating_envelope:
  wavelength_range_nm: [1540, 1560]
  temperature_range_c: [-10, 50]
  distance_range_km: [0, 100]
  fiber_type: "SMF-28e+"
  detector_technology: "SNSPD"
  source_technology: "emitter_cavity"
  channel_model: "fiber"
  notes: "Card invalid for free-space or coexistence channels."
```

---

### 3. Benchmark Coverage

Track which canonical test scenarios have been evaluated:

```yaml
benchmark_coverage:
  canonical_scenarios:
    metro_qkd_10km: {status: "pass", key_rate_bps: 1.2e6}
    metro_qkd_50km: {status: "pass", key_rate_bps: 4.5e4}
    long_haul_100km: {status: "pass", key_rate_bps: 1.1e3}
    repeater_chain_200km: {status: "skip", reason: "repeater not configured"}
    satellite_downlink: {status: "skip", reason: "free-space model not used"}
  plob_bound_check: "pass"
  golden_report_hash_match: true
  regression_baseline_match: true
```

---

### 4. Standards Alignment

Reference emerging QKD certification standards:

```yaml
standards_alignment:
  etsi_qkd_016: "partial"       # ETSI Protection Profile for QKD
  iso_23837_1: "not_assessed"   # ISO Security requirements for QKD
  itu_y_3800: "informational"   # ITU QKDN overview
  nist_sp_800_57: "compatible"  # Key management (symmetric key sizes)
  notes: >
    This card does not constitute a formal certification.
    Standards references indicate which requirements were
    considered during simulation design.
```

---

### 5. Supply Chain Attestation

Track software provenance for reproducibility:

```yaml
provenance:
  photonstrust_version: "0.1.0"
  photonstrust_commit: "a1b2c3d"
  python_version: "3.11.7"
  numpy_version: "1.26.4"
  qutip_version: "4.7.6"
  config_hash: "sha256:abc123..."
  output_hash: "sha256:def456..."
  generation_timestamp: "2026-02-14T12:00:00Z"
  reproducibility_bundle: "results/repro_pack_demo1.tar.gz"
```

---

## Implementation Plan

### Step 1: Update the card schema

Create `schemas/reliability_card_v1_1.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "PhotonTrust Reliability Card v1.1",
  "type": "object",
  "required": ["card_version", "scenario_id", "evidence_quality", "results"],
  "properties": {
    "card_version": {"const": "1.1"},
    "scenario_id": {"type": "string"},
    "evidence_quality": {
      "type": "object",
      "required": ["tier", "label"],
      "properties": {
        "tier": {"type": "integer", "minimum": 0, "maximum": 3},
        "label": {"enum": ["Simulation-only", "Calibrated", "Validated", "Qualified"]}
      }
    },
    "operating_envelope": {"type": "object"},
    "benchmark_coverage": {"type": "object"},
    "standards_alignment": {"type": "object"},
    "provenance": {"type": "object"},
    "results": {"type": "object"}
  }
}
```

### Step 2: Update the card generator

In the sweep/reporting pipeline, populate the new fields automatically:

```python
def _build_card_v1_1(scenario, results, calibration=None):
    tier = 0
    if calibration and calibration.get("diagnostics", {}).get("ppc_passed"):
        tier = 1
    if calibration and calibration.get("validation_residual_max") is not None:
        tier = 2
    # Tier 3 requires benchmark suite pass (checked separately)

    return {
        "card_version": "1.1",
        "scenario_id": scenario["scenario_id"],
        "evidence_quality": {
            "tier": tier,
            "label": ["Simulation-only", "Calibrated", "Validated", "Qualified"][tier],
        },
        "operating_envelope": _extract_envelope(scenario),
        "provenance": _build_provenance(),
        "results": results,
    }
```

### Step 3: Add canonical qualification scenarios

Define 5-10 reference scenarios in `configs/canonical/`:

```
configs/canonical/
  metro_qkd_10km.yml
  metro_qkd_50km.yml
  long_haul_100km.yml
  repeater_chain_200km.yml
  satellite_leo_downlink.yml
  teleportation_swap_chain.yml
```

Each must pass with specific thresholds to qualify a release.

### Step 4: Add `photonstrust card` CLI command

```bash
# Generate a reliability card
photonstrust card generate configs/demo1_default.yml --output results/card_demo1.json

# Validate a card against schema
photonstrust card validate results/card_demo1.json

# Compare two cards
photonstrust card diff results/card_v1.json results/card_v2.json
```

---

## Cross-Domain Lessons Applied

| Domain | Lesson | PhotonTrust Application |
|--------|--------|------------------------|
| Telecom (IETF) | Standardized performance metrics | Canonical test scenarios with pass/fail thresholds |
| Semiconductor (JEDEC) | Qualification = passing defined stress tests | Evidence tiers map to test coverage requirements |
| Space (ECSS) | Qualification vs. acceptance levels | Tier 3 = full qualification suite |
| Classical networking | Conformance testing suites | Benchmark coverage tracking |
| PDK model cards | Characterized models with uncertainty | Operating envelope + calibration diagnostics |
