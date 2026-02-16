# Phase 60 (W41-W44): Platform Performance and Security Scale-Up

Source anchors:
- `docs/audit/05_performance_bottlenecks.md`
- `docs/upgrades/03_upgrade_ideas_platform_quality_security.md`
- `docs/research/deep_dive/07_security_privacy_and_compliance.md`

### W41 (2026-11-23 to 2026-11-29) - Async compute and compile caching
- Work: Add background job model and config-hash compile cache.
- Artifacts: async endpoints, job status artifacts.
- Validation: API load smoke tests.
- Exit: Long-running compute no longer blocks API.

### W42 (2026-11-30 to 2026-12-06) - Uncertainty parallelization and detector fast path
- Work: Parallelize uncertainty sampling and add vectorized detector path.
- Artifacts: performance changes with determinism safeguards.
- Validation: runtime and numeric parity tests.
- Exit: Runtime targets improved with reproducible outputs.

### W43 (2026-12-07 to 2026-12-13) - AuthN/AuthZ hardening
- Work: Add role-based auth for runs/artifacts/approvals.
- Artifacts: auth middleware, role model, tests.
- Validation: 401/403/role tests.
- Exit: Governance surfaces permissioned and auditable.

### W44 (2026-12-14 to 2026-12-20) - SBOM and immutable publish by digest
- Work: Add SBOM generation and immutable content-digest publication path.
- Artifacts: SBOM outputs and manifest pointers.
- Validation: fetch-by-digest verify tests.
- Exit: Supply-chain and artifact immutability chain complete.
