# Reliability Card

The reliability card is PhotonTrust's central artifact. It is the shortest
shareable representation of a run outcome, its evidence quality, its main
assumptions, and the files needed to reproduce or inspect it.

## Generate a Card

```bash
photonstrust run configs/quickstart/qkd_quick_smoke.yml --output results/smoke_quick
photonstrust card validate results/smoke_quick/demo1_quick_smoke/nir_850/reliability_card.json
```

The generated card lives at:

- `results/smoke_quick/demo1_quick_smoke/nir_850/reliability_card.json`

Related artifacts referenced from the card:

- `report.html`
- `report.pdf`
- `results.json`

## What the Card Tells You

The current card format exposes five questions a reviewer usually asks first:

### 1. What was run?

Look at:

- `scenario_id`
- `band`
- `wavelength_nm`
- `inputs`
- `model_provenance`

This is the basic identity of the scenario, channel, source, detector, and
protocol that produced the result.

### 2. How strong is the evidence?

Look at:

- `evidence_quality_tier`
- `benchmark_coverage`
- `calibration_diagnostics`
- `reproducibility`

The default quickstart card is intentionally modest. It is typically
`simulated_only` rather than calibrated or field-validated evidence.

### 3. What outcome matters?

Look at:

- `outputs.key_rate_bps`
- `outputs.fidelity_est`
- `outputs.critical_distance_km`
- `confidence_intervals`

These fields tell you the main performance result plus any uncertainty bounds
the run captured.

### 4. Why did performance degrade?

Look at:

- `error_budget.dominant_error`
- `error_budget.error_budget`
- `derived.loss_budget`
- `derived.qber_total`

This is the fastest way to see whether loss, detector noise, multiphoton
effects, timing, or another factor is dominating the result.

### 5. Under what assumptions is this safe to interpret?

Look at:

- `safe_use_label`
- `security_assumptions_metadata`
- `finite_key_epsilon_ledger`
- `notes`

These fields matter more than the headline rate if you are comparing scenarios
for real-world decisions.

## How to Read a Quickstart Card

The shipped quick smoke card is useful for proving the workflow, not for
claiming deployment readiness.

Interpret it as:

- a valid example of the artifact format
- a reproducible demo run
- a view into the engine's current assumptions

Do not interpret it as:

- field validation
- a deployment-ready certification packet
- a substitute for a full security review

## What Makes a Card Stronger

A stronger card has more than a positive key rate. It should also have:

- calibrated or benchmark-backed parameter sources
- explicit finite-key treatment when applicable
- clear security assumption metadata
- reproducibility links or evidence pack references
- good supporting reports and provenance fields

## Related Docs

- `limitations.md`
- `../reference/cli.md`
- `../reference/config.md`
- `../research/07_reliability_card_standard.md`
