# Reliability Card Standard

This document defines the Reliability Card as a shareable trust artifact.

## Required Sections
- Inputs (source, channel, detector, timing, protocol)
- Derived metrics (loss budget, QBER breakdown)
- Outputs (key rate, fidelity, critical distance)
- Error budget and dominant error
- Safe-use label
- Reproducibility bundle (config hash + seed + artifact pointers)

## Safe-Use Labels
- qualitative: QBER above threshold or key rate unusable
- security_target_ready: usable with validation
- engineering_grade: stable and low uncertainty

## Implementation Checklist
- JSON schema validated in tests
- HTML and PDF renderers
- Config hash and seed recorded
- Evidence tier and benchmark coverage fields present on external cards
- Reproducibility artifact URI set when a repro pack or immutable bundle exists

## Web Research Extension (2026-02-12)
See `12_web_research_update_2026-02-12.md` section `07 Reliability Card standard: documentation maturity`.
