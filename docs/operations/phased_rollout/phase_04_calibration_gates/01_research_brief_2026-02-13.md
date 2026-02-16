# Research Brief

## Metadata
- Work item ID: PT-PHASE-04
- Title: Calibration diagnostics enforcement gates
- Authors: PhotonTrust core team
- Date: 2026-02-13
- Related modules:
  - `photonstrust/calibrate/bayes.py`
  - `photonstrust/cli.py`
  - `configs/calibration_example.yml`

## 1. Problem and motivation
Calibration output previously exposed diagnostics but did not enforce quality
gates. This allowed low-quality posterior summaries to pass silently into
downstream workflows, reducing trust in published reliability artifacts.

## 2. Research questions and hypotheses
- RQ1: Can diagnostics gates be added while preserving backward compatibility?
- RQ2: Can gates be configurable and optionally enforced from CLI config?
- H1: Gate diagnostics can be computed deterministically from existing weight
  statistics.
- H2: Strict thresholds should trigger failure when enforcement is enabled.

## 3. Related work and baseline methods
The existing Bayesian calibration code already produced effective sample size and
entropy-like diagnostics. This phase extends those statistics into explicit gate
policies and pass/fail behavior aligned with the master plan requirement for
auditable calibration quality.

## 4. Mathematical formulation
Derived gate metrics:
- ESS ratio: `effective_sample_size / samples`
- R-hat proxy from weight concentration
- PPC proxy score from normalized weight entropy

Gate pass condition is conjunction over threshold checks. Failures are captured
as explicit reason labels.

## 5. Method design
- Add gate thresholds with defaults.
- Add diagnostics block fields:
  - `ess_ratio`, `r_hat_proxy`, `ppc_score`
  - `gate_pass`, `gate_failures`, `gate_thresholds`
- Add optional enforcement in calibration fitting functions.
- Add CLI support for:
  - `calibration.quality_gates.enforce`
  - `calibration.quality_gates.thresholds`

## 6. Experimental design
Controls:
- standard calibration call without enforcement
- enforced call with default thresholds
- enforced call with intentionally strict thresholds
Metrics:
- gate pass state
- expected raise behavior on gate failure.

## 7. Risk and failure analysis
Risk: thresholds too strict could fail normal examples.
Mitigation: broadened likelihood scale floor and calibrated default thresholds so
reference example passes while strict tests still fail predictably.

## 8. Reproducibility package
- deterministic seed retained.
- updated tests in `tests/test_completion_quality.py`.
- CLI example run:
  - `py -m photonstrust.cli run configs/calibration_example.yml --output ...`

## 9. Acceptance criteria
- diagnostics gates emitted in calibration output.
- optional enforcement supported by API and CLI.
- strict-threshold failure path tested.
- full test suite passes.
- calibration example passes with configured thresholds.

## 10. Decision
- Decision: Proceeded and completed.
- Reviewer sign-off: Internal (2026-02-13).

## Sources
- GUM/JCGM uncertainty context:
  https://www.bipm.org/doi/10.59161/JCGM100-2008E
- ArviZ diagnostics reference:
  https://python.arviz.org/en/stable/api/diagnostics.html
- Stan posterior predictive checks:
  https://mc-stan.org/docs/stan-users-guide/posterior-predictive-checks.html
