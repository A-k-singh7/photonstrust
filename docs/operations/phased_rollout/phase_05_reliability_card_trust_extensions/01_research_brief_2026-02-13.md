# Research Brief

## Metadata
- Work item ID: PT-PHASE-05
- Title: Reliability-card trust extensions
- Authors: PhotonTrust core team
- Date: 2026-02-13
- Related modules:
  - `photonstrust/report.py`
  - `schemas/photonstrust.reliability_card.v1.schema.json`

## 1. Problem and motivation
Reliability cards contained strong core metrics but lacked explicit trust-layer
fields for evidence quality and calibration status. This made it harder to
differentiate simulated exploratory outputs from calibrated or field-backed
evidence in external reviews.

## 2. Research questions and hypotheses
- RQ1: Can trust metadata be added without breaking existing card schema usage?
- RQ2: Can the card carry calibration-quality diagnostics in a machine-readable
  way suitable for downstream filtering?
- H1: Trust-extension fields can be added to card output while maintaining
  backward compatibility.
- H2: Schema validation remains green after extension.

## 3. Related work and baseline methods
Model-card and artifact-reporting practices motivate explicit evidence tiers and
diagnostic transparency. The existing PhotonTrust card already carries
reproducibility context and is a natural host for trust extensions.

## 4. Mathematical formulation
No new simulation equations were introduced. This phase extends metadata and
governance semantics:
- evidence tier classification
- benchmark coverage labels
- calibration diagnostic summary
- reproducibility artifact URI

## 5. Method design
- Extend report builder to emit default trust fields.
- Add optional scenario overrides for richer trust metadata.
- Extend reliability card schema with new optional properties.
- Add tests validating field presence and integration behavior.

## 6. Experimental design
Controls:
- baseline scenario with defaults,
- scenario with explicit trust metadata overrides.
Metrics:
- schema validity,
- trust-field persistence in output cards.

## 7. Risk and failure analysis
Risk: schema mismatch or consumer regressions.
Mitigation: additive optional fields only and full suite validation.

## 8. Reproducibility package
- deterministic tests in `tests/test_completion_quality.py`.
- schema validation in `tests/test_schema_validation.py`.
- end-to-end run check via CLI scenario execution.

## 9. Acceptance criteria
- trust-extension fields emitted in reliability cards.
- schema updated and valid.
- tests pass (targeted + full suite).

## 10. Decision
- Decision: Proceeded and completed.
- Reviewer sign-off: Internal (2026-02-13).

## Sources
- Model Cards:
  https://arxiv.org/abs/1810.03993
- Datasheets for Datasets:
  https://arxiv.org/abs/1803.09010
- FAIR principles:
  https://doi.org/10.1038/sdata.2016.18
