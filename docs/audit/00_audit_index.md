# PhotonTrust Codebase Audit (2026-02-14)

This audit covers architecture, physics accuracy, test coverage, CI/CD,
performance, security, packaging, and competitive positioning. Each document
includes findings **and** concrete correction steps with code examples.
Where relevant, documents also include **research/standards anchors** (primary
papers, standards, and tool documentation) so the roadmap stays evidence-based.

## Documents

| # | File | Summary |
|---|------|---------|
| 01 | [Physics Model Assumptions](01_physics_model_assumptions.md) | Documented simplifications, missing models, and corrections |
| 02 | [Test Coverage Gaps](02_test_coverage_gaps.md) | Untested modules, missing edge cases, proposed test code |
| 03 | [Configuration & Validation](03_configuration_validation.md) | Runtime validation gaps, schema versioning, type safety |
| 04 | [CI/CD Improvements](04_ci_cd_improvements.md) | Expanded workflow, matrix strategy, coverage gates |
| 05 | [Performance Bottlenecks](05_performance_bottlenecks.md) | Hotspots with profiling data and optimization patterns |
| 06 | [Dependency & Security](06_dependency_security.md) | Outdated pins, missing security process, CVE scanning |
| 07 | [Code Quality](07_code_quality.md) | Duplication, error handling, type hints, anti-patterns |
| 08 | [Reliability Card v1.1](08_reliability_card_v1_1.md) | Evidence tiers, operating envelope, standards alignment |
| 09 | [Packaging Improvements](09_packaging_improvements.md) | pyproject.toml expansion, entry points, versioning |
| 10 | [Competitive Positioning](10_competitive_positioning.md) | Comparison with NetSquid, SeQUeNCe, QuNetSim; differentiation strategy |

## Upgrade Ideas "Front Door"

If the volume of docs is overwhelming, start here:
- `../upgrades/README.md`
  - `../upgrades/01_upgrade_ideas_qkd_and_satellite.md`
  - `../upgrades/02_upgrade_ideas_pic_and_verification.md`
  - `../upgrades/03_upgrade_ideas_platform_quality_security.md`

## Priority Matrix

### Critical (fix before next release)
- [DONE] Parameter validation layer after config loading (doc 03 / Phase 38)
- API exception handling standardization (doc 07)
- Python version matrix in CI (doc 04)
- [DONE] Document physics assumptions (doc 01)

### High (fix before v0.2)
- Coverage reporting with floor gate (doc 04)
- [DONE] PLOB bound sanity check test (doc 01 / Phase 39)
- Config versioning and migration (doc 03)
- Reliability Card v1.1 evidence tiers (doc 08)

### Medium (fix before v1.0)
- Parallelize uncertainty computation (doc 05)
- Pydantic config models (doc 03)
- Async API endpoints (doc 05)
- Linting + type checking in CI (doc 04)

### Low (polish for wider adoption)
- Sphinx/mkdocs documentation site (doc 09)
- CITATION.cff for academic citability (doc 09)
- gdsfactory interop layer (doc 10)
- ETSI/ISO compliance metadata (doc 08)
