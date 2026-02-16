# Research Brief

## Metadata
- Work item ID: PT-PHASE-06
- Title: Multi-fidelity execution and performance acceleration foundations
- Authors: PhotonTrust core team
- Date: 2026-02-13
- Related modules:
  - `photonstrust/qkd.py`
  - `photonstrust/config.py`
  - `photonstrust/sweep.py`
  - config schema and performance plan docs

## 1. Problem and motivation
PhotonTrust needs an interactive pathway for drag-drop workflows while also
supporting high-confidence results for publication and external design reviews.
The existing execution path treated uncertainty computation and detector Monte
Carlo cost as fixed, which limits usability for rapid iteration and hampers
clear "preview vs certification" semantics.

## 2. Research questions and hypotheses
- RQ1: Can we introduce explicit execution modes without breaking existing
  scenario configs and tests?
- RQ2: Can preview mode substantially reduce runtime while keeping the model
  contract stable?
- H1: Preview mode should reduce uncertainty sampling and detector Monte Carlo
  cost relative to standard execution.
- H2: Certification mode should increase sampling/cost relative to standard and
  surface mode metadata for auditability.

## 3. Related work and baseline methods
Multi-fidelity simulation is a standard strategy for interactive scientific
tools. PhotonTrust already has optional stochastic detector execution and
Monte Carlo uncertainty propagation; this phase makes these knobs first-class,
mode-driven, and auditable.

## 4. Mathematical formulation
No changes are made to the physics equations; this phase changes the computational
budget policy:
- uncertainty sampling count is mode-dependent
- detector stochastic sample count is scaled by a mode multiplier

## 5. Method design
- Add scenario execution modes:
  - `standard` (default)
  - `preview`
  - `certification`
- Add mode-dependent settings:
  - uncertainty samples
  - detector sample scaling factor
- Emit a `performance.json` artifact per run with the applied settings and
  elapsed runtime.

## 6. Experimental design
Controls:
- identical scenario under preview and certification modes.
Metrics:
- runtime elapsed seconds
- uncertainty sample counts
- detector scaling factor

## 7. Risk and failure analysis
Risk: mode changes could create silent accuracy regressions.
Mitigation: mode is explicit in output artifacts, defaults preserve standard
behavior, and tests verify settings are applied.

## 8. Reproducibility package
- unit tests validating settings mapping and output structure:
  `tests/test_multifidelity_execution.py`
- runnable demo configs:
  - `configs/demo7_multifidelity_preview.yml`
  - `configs/demo7_multifidelity_certification.yml`
- performance artifacts:
  `performance.json` emitted per run.

## 9. Acceptance criteria
- mode settings applied deterministically.
- existing regression baselines remain valid.
- performance artifact emitted.
- preview vs certification runtimes differ measurably in demos.
- full test suite passes.

## 10. Decision
- Decision: Proceeded and completed.
- Reviewer sign-off: Internal (2026-02-13).

## Sources
- PhotonTrust performance engineering plan:
  `../../../research/deep_dive/05_performance_engineering_plan.md`
- QuTiP benchmark information:
  https://qutip.org/qutip-benchmark/
