# Phase 42: Reliability Card v1.1 (Research Brief)

Date: 2026-02-14

## Goal

Upgrade PhotonTrust’s reliability card from v1.0 (good internal summary) to v1.1
(audit-ready trust artifact) by standardizing:

- evidence tier semantics (what level of evidence supports a claim)
- operating envelope (when a card is valid)
- benchmark coverage reporting (what was tested, what was not)
- standards anchors (explicitly not “certification”, but traceable alignment cues)
- provenance and reproducibility fields (tool/version identity + hashes)

This phase is about preventing over-claiming and making cards comparable across
projects and time.

## Current state (repo reality)

Today, `photonstrust/report.py` generates a v1.0 reliability card that includes:

- primary outputs (key rate, QBER, fidelity)
- decomposed error budget fractions
- finite-key fields (when enabled)
- coexistence/background counts decomposition
- reproducibility core (`config_hash`, `seed`)

The v1.0 JSON Schema exists at:
- `schemas/photonstrust.reliability_card.v1.schema.json`

Audit and deep-dive anchors that motivate v1.1:
- `docs/audit/08_reliability_card_v1_1.md`
- `docs/research/deep_dive/06_reliability_card_v1_1_draft.md`

## Why v1.1 is required (trust closure)

Simulator outputs are not the product; the card is the product. A “trustable”
card needs explicit structure to answer reviewer questions:

1) What evidence backs this number?
2) Where is this valid (envelope)?
3) What was benchmarked and what was not?
4) What standards/requirements were considered?
5) Can someone reproduce/verify the artifact integrity?

## Evidence tiers (core semantics)

v1.1 introduces a defined evidence tier taxonomy (0..3):

- Tier 0: Simulation-only (no calibration)
- Tier 1: Calibrated (calibration bundle + diagnostics)
- Tier 2: Validated (held-out validation or external benchmark anchoring)
- Tier 3: Qualified (validated + canonical benchmark suite + governance gates)

This is not a compliance claim; it’s an evidence classification.

## Standards anchors (do not over-claim)

Cards should reference standards to show what was considered, but must include a
clear disclaimer that the card is not itself a certification.

Primary anchors used in v1.1 design:

- ETSI GS QKD 016 (Protection Profile):
  https://www.etsi.org/deliver/etsi_gs/qkd/001_099/016/01.01.01_60/gs_QKD016v010101p.pdf
- ISO/IEC 23837-1 and 23837-2 (QKD security requirements/evaluation):
  https://www.iso.org/standard/83834.html
  https://www.iso.org/standard/86580.html
- ITU-T Y.3800 (QKDN overview): https://www.itu.int/rec/T-REC-Y.3800
- NIST SP 800-57 Part 1 Rev. 5 (key management guidance): DOI 10.6028/NIST.SP.800-57pt1r5

Supply chain provenance anchors (for v1.1 provenance posture):

- NIST SSDF (SP 800-218): https://doi.org/10.6028/NIST.SP.800-218
- SLSA spec: https://slsa.dev/spec/v1.2/
- Sigstore: https://www.sigstore.dev/

## Definition of done

- New schema exists: `schemas/photonstrust.reliability_card.v1_1.schema.json`
- Generator can emit v1.1 cards (opt-in to avoid breaking existing users)
- Tests enforce v1.1 schema validation
- Cards include v1.1 fields consistently (evidence_quality, operating_envelope,
  benchmark_coverage, standards_alignment, provenance)
