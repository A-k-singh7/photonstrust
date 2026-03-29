# Reliability Card v1.1 Draft

This draft extends v1.0 for stronger interoperability and trust.

## New fields proposed
- confidence_level (low/medium/high)
- outage_probability
- calibration_reference (dataset hash)
- model_version and solver backend details

## Backward compatibility
- v1.1 fields optional for v1.0 readers
- Maintain v1.0 required field set unchanged

## Interoperability goals
- Easy ingestion by dashboards and external review tools
- Stable naming and units for automated comparison

## Extended card sections
- Decision recommendation block
- Uncertainty interpretation note
- Known limitations block

## Publishing guidance
- Always include reproducibility metadata
- Include links to benchmark scenario definition

## Definition of done
- Draft schema validated with at least three scenario types.
- Side-by-side v1.0 and v1.1 examples published.


## Inline citations (web, verified 2026-02-12)
Applied to: v1.1 schema field design, interoperability, and evidence quality semantics.
- Model Cards framework: https://arxiv.org/abs/1810.03993
- Datasheets for Datasets framework: https://arxiv.org/abs/1803.09010
- FAIR principles: https://doi.org/10.1038/sdata.2016.18
- ACM Artifact Review and Badging policy: https://www.acm.org/publications/policies/artifact-review-and-badging-current
- CodeMeta metadata profile: https://codemeta.github.io/
- W3C PROV overview: https://www.w3.org/TR/prov-overview/
