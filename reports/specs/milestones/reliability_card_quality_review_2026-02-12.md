# Reliability Card Quality Review

## Card metadata
- Scenario ID: `demo1_multiband`
- Band/topology: `nir_850`, direct-link QKD
- Card version: `schema_version = 1.0`
- Reviewed card: `results/smoke/demo1/demo1_multiband/nir_850/reliability_card.json`

## Mandatory field review
- [x] Inputs complete
- [x] Derived metrics complete
- [x] Outputs include uncertainty where applicable
- [x] Error budget present and consistent
- [x] Safe-use label and rationale present
- [x] Reproducibility bundle complete

## Semantic quality review
- [x] Dominant error aligns with scenario behavior
- [x] Recommendations are actionable
- [x] Confidence level or uncertainty bounds are interpretable

## Reviewer comments
- Reviewer 1: Card structure and schema alignment are correct; outage probability now present in uncertainty block.
- Reviewer 2: Semantics are consistent with observed high-QBER regime (qualitative label), but low-key-rate scenarios should be complemented with mitigation recommendations in downstream product UX.

## Approval
- [x] Approved
- [ ] Needs revision
