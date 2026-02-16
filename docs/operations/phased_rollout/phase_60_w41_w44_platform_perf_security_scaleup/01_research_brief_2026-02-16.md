# Phase 60: Platform Performance and Security Scale-Up (Research Brief)

Date: 2026-02-16

## Goal

Execute Phase 60 (W41-W44) by hardening API throughput and governance posture:
async/background execution, compile caching, deterministic uncertainty
parallelization, detector fast-path acceleration, role-based access controls,
and immutable bundle publish-by-digest with SBOM artifacts.

## Scope executed

### W41: Async compute and compile caching

1. Added filesystem-backed async job registry and status surfaces.
2. Added graph compile cache keyed by graph+schema requirement.
3. Added async QKD run submission and job lifecycle endpoints.

### W42: Uncertainty parallelization and detector fast path

1. Added deterministic uncertainty parallelization with worker controls.
2. Added detector fast path for no-afterpulse operation with parity-safe
   legacy fallback and explicit diagnostics path labels.
3. Added targeted parity/reproducibility tests for uncertainty and detector
   runtime behavior.

### W43: AuthN/AuthZ hardening

1. Added header-driven RBAC mode (`off|header`) with optional dev token gate.
2. Added role/scope checks for run, artifact, bundle, diff, projects, approvals,
   and jobs governance surfaces.
3. Added 401/403/allow-path tests for role and project scope enforcement.

### W44: SBOM and immutable publish by digest

1. Added CycloneDX SBOM artifact emission into evidence bundles.
2. Added bundle publish-by-digest endpoint and fetch/verify-by-digest surfaces.
3. Added publish manifest schema and schema-backed API test coverage.

## Source anchors used

- `docs/audit/05_performance_bottlenecks.md`
- `docs/upgrades/03_upgrade_ideas_platform_quality_security.md`
- `docs/research/deep_dive/07_security_privacy_and_compliance.md`
- `docs/operations/365_day_plan/phase_60_w41_w44_platform_perf_security_scaleup.md`
