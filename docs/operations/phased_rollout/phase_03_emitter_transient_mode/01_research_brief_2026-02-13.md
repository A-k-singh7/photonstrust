# Research Brief

## Metadata
- Work item ID: PT-PHASE-03
- Title: Emitter transient mode and spectral diagnostics
- Authors: PhotonTrust core team
- Date: 2026-02-13
- Related modules:
  - `photonstrust/physics/emitter.py`
  - `photonstrust/config.py`
  - source fields in config and reliability schemas

## 1. Problem and motivation
The existing emitter model centered on steady-state-like outputs. That is useful
for baseline throughput estimates but not enough for trustable scientific review
where pulse-mode behavior and spectral-quality indicators are needed for
cross-comparison and model critique.

## 2. Research questions and hypotheses
- RQ1: Can transient-mode behavior be introduced without breaking legacy
  scenarios and tests?
- RQ2: Can we expose interpretable emitter quality diagnostics directly from
  the model output contract?
- H1: In transient mode, increasing drive strength should not decrease
  emission probability under fixed hardware parameters.
- H2: Diagnostics fields (`spectral_purity`, `linewidth_mhz`, `mode_overlap`)
  can be emitted in bounded, deterministic form for both analytic and qutip
  backends.

## 3. Related work and baseline methods
QuTiP supports both steady-state and time-evolution methods, making transient
extensions natural for backend parity. The baseline PhotonTrust emitter path
already used Jaynes-Cummings assumptions and deterministic seed handling; this
phase extends that with mode-aware diagnostics instead of replacing the model.

## 4. Mathematical formulation
Steady-state behavior remains as baseline. Transient mode introduces a
drive-dependent contrast factor applied to emission probability and quality
metrics. Spectral purity uses a dephasing-driven bounded proxy, linewidth uses
rate scaling in MHz, and mode overlap uses combined purity and multiphoton
quality proxy terms.

## 5. Method design
- Add optional `emission_mode` with values:
  - `steady_state` (default)
  - `transient`
- Add optional `transient_steps` for qutip transient evolution.
- Emit new diagnostics in both backends:
  - `spectral_purity`
  - `linewidth_mhz`
  - `mode_overlap`
  - `transient_contrast`

## 6. Experimental design
Controls:
- steady-state vs transient mode at fixed parameters,
- low vs high drive strength in transient mode.
Metrics:
- `emission_prob`
- `g2_0`
- new diagnostics bounds and determinism.

## 7. Risk and failure analysis
Risk: transient path could destabilize legacy runs.
Mitigation: default remains `steady_state`, and all existing tests are retained
plus new transient-specific tests.

## 8. Reproducibility package
- deterministic model paths for analytic mode.
- test coverage extended in `tests/test_emitter_model.py`.
- demo config:
  - `configs/demo6_transient_emitter.yml`.

## 9. Acceptance criteria
- transient mode support implemented.
- diagnostics emitted and bounded.
- legacy tests pass.
- full test suite passes.
- demo config executes successfully.

## 10. Decision
- Decision: Proceeded and completed.
- Reviewer sign-off: Internal (2026-02-13).

## Sources
- QuTiP documentation:
  https://qutip.org/documentation
- QuTiP releases/download:
  https://qutip.org/download.html
- Integrated photonic TF-QKD network (Nature, 2026):
  https://www.nature.com/articles/s41586-026-10152-z
