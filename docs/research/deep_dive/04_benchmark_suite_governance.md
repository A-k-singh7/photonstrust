# Benchmark Suite Governance

This document defines benchmark lifecycle, integrity, and versioning.

## Benchmark categories
- Core: metro QKD, repeater chain, teleportation SLA
- Extended: source benchmarking and stress scenarios

## Governance model
- Benchmark owners: maintain scenario validity and thresholds.
- Change control: benchmark updates require rationale and migration notes.
- Versioning: semantic tags for benchmark bundles.

## Dataset quality requirements
- Every entry must include config hash and generation timestamp.
- Seeds must be explicit and deterministic.
- Schema validation required before publication.

## Baseline policy
- Store baselines in repository fixtures.
- Update baselines only via controlled script and review.
- Include changelog note when baseline shifts materially.

## Benchmark drift detection
- CI checks metric deviations against baseline tolerance windows.
- Flags drift by scenario and metric.

## Public benchmark publication
- Provide machine-readable dataset bundle.
- Provide human-readable summary and caveats.

## Definition of done
- Benchmark suite passes CI.
- Baseline update workflow documented and reproducible.


## Inline citations (web, verified 2026-02-12)
Applied to: benchmark governance model, dataset quality requirements, and publication policy.
- FAIR principles for data stewardship: https://doi.org/10.1038/sdata.2016.18
- Datasheets for Datasets: https://arxiv.org/abs/1803.09010
- Model Cards for Model Reporting: https://arxiv.org/abs/1810.03993
- ACM Artifact Review and Badging (current policy): https://www.acm.org/publications/policies/artifact-review-and-badging-current
- CodeMeta metadata project: https://codemeta.github.io/
- W3C PROV overview: https://www.w3.org/TR/prov-overview/

