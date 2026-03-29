# Operational Readiness and Release Gates

This document defines hard gates before declaring release readiness.

## Gate A: Scientific correctness
- Protocol validation matrix passing
- Calibration diagnostics acceptable

## Gate B: Reproducibility
- Baselines and golden report checks passing
- Run registry generated and complete

## Gate C: Product quality
- UI loads and compares runs correctly
- Reliability Card reports generated in HTML and PDF modes

## Gate D: Adoption readiness
- Docs complete and navigable
- Benchmark suite available for external users

## Release candidate checklist
- All tests pass in CI
- Changelog and release notes updated
- Bundle generated and verified
- Automated gate command passes:
  `python scripts/release/release_gate_check.py`

## Definition of done
- All gates pass with signed release approval from maintainers.
- Release gate report artifact exists:
  `results/release_gate/release_gate_report.json`


## Inline citations (web, verified 2026-02-12)
Applied to: release gates, reproducibility checks, and release-candidate integrity policy.
- ACM Artifact Review and Badging policy: https://www.acm.org/publications/policies/artifact-review-and-badging-current
- Semantic Versioning 2.0.0: https://semver.org/spec/v2.0.0.html
- Keep a Changelog 1.1.0: https://keepachangelog.com/en/1.1.0/
- SLSA v1.0 notes: https://slsa.dev/spec/v1.0/whats-new
- Sigstore cosign signature verification: https://docs.sigstore.dev/cosign/verifying/verify/
- GitHub CODEOWNERS and review enforcement context: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners
