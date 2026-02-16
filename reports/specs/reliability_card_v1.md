# PhotonTrust Reliability Card v1.0

## Purpose
The Reliability Card is a standardized artifact that summarizes photonic quantum
link performance, uncertainty, and recommended safe-use classification.

## Required fields
- scenario_id
- band, wavelength_nm
- inputs: source, channel, detector, timing, protocol
- derived: loss budget, timing budget, QBER breakdown
- outputs: key rate, fidelity, critical distance
- error_budget: dominant error + fractional breakdown
- safe_use_label: qualitative | security_target_ready | engineering_grade
- reproducibility: config_hash, model_hash, seed

## Optional fields
- plots: key_rate_vs_distance_path, qber_vs_distance_path
- report_pdf_path
- notes
  - recommended use: applicability bounds and model-mode disclaimers
- uncertainty.outage_probability (if uncertainty mode enabled)
- extended QBER breakdown terms (if enabled/configured):
  - derived.background_counts.qber_contrib
  - derived.raman_counts.qber_contrib
  - derived.misalignment.qber_contrib
  - derived.source_visibility.qber_contrib
- finite-key summary (if enabled/configured):
  - derived.finite_key.enabled
  - derived.finite_key.penalty
  - derived.finite_key.privacy_term_asymptotic
  - derived.finite_key.privacy_term_effective
- noise-count diagnostics (if enabled/configured):
  - derived.noise_counts_cps.background
  - derived.noise_counts_cps.raman

## Reproducibility bundle
The reproducibility bundle includes:
- config_hash: SHA-256 hash of the exact scenario configuration
- model_hash: hash of the physics model version (if available)
- seed: random seed used for stochastic processes

## Interpretation guidelines
- Use the dominant_error to guide engineering mitigation
- Treat key_rate_ci bounds as confidence intervals, not guarantees
- If QBER > 0.11, label must be qualitative
