# Risks, Quality, and Governance

This document covers risks for both chip and satellite expansion.

## Major risks

## Scientific and product risks
- Model mismatch against measured hardware behavior.
- Interactive UX requirements forcing overly coarse approximations.
- Overconfidence from weak calibration diagnostics.

## Delivery and scale risks
- Simulation runtime/cost growth as scenario complexity increases.
- Graph editor complexity outrunning backend maturity.
- Integration churn across QuTiP/Qiskit/Streamlit release lines.

## Market and adoption risks
- Slow conversion from pilots to paid subscriptions.
- Product too research-oriented for engineering managers.
- Enterprise buyers requiring compliance artifacts earlier than planned.

## Regulatory and deployment risks
- export-control constraints for specific customers/use cases
  (EAR/ITAR context).
- space mission policy constraints (FCC orbital debris/deorbit obligations).
- traceability gaps for safety/security review workflows.

## Mitigations
- publish uncertainty and calibration diagnostics on all external reports.
- enforce multi-fidelity modes with explicit confidence labels.
- freeze and version graph + card schemas with compatibility tests.
- implement signed provenance bundles before broad enterprise rollout.
- maintain policy metadata fields for EAR/ITAR/FCC workflow tagging.

## Quality gates
- schema validation for all cards and graph payloads.
- benchmark drift checks with explicit owner-approved overrides.
- diagnostics thresholds (R-hat, ESS, PPC) must pass for report publication.
- deterministic replay checks by config hash + seed.
- release-gate checklist includes compliance metadata completeness.

## Governance model
- versioned schemas and migration notes for each release.
- ADRs for all breaking architecture decisions.
- monthly benchmark board review.
- quarterly risk register refresh.

## External references (regulatory anchors)
- EAR Part 774:
  https://www.ecfr.gov/current/title-15/subtitle-B/chapter-VII/subchapter-C/part-774
- ITAR/USML text:
  https://www.ecfr.io/Title-22/Section-121.1
- FCC deorbit rule release:
  https://www.fcc.gov/document/fcc-adopts-new-5-year-rule-deorbiting-satellites-0

## Related docs
- `12_web_research_update_2026-02-12.md`
- `13_business_expansion_and_build_plan_2026-02-12.md`

