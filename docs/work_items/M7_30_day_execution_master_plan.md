# M7 30-Day Execution Master Plan (No Stubs, Research-Backed, Physics-First)

Date: 2026-03-02
Scope: Execution plan in 30-day blocks to move PhotonTrust to near-market readiness with strict engineering and physics controls.

## 1) Non-Negotiable Rules

1. No production stubs:
   - Stub/mock backends are forbidden in release/certification mode.
   - If a required backend is unavailable, execution fails closed with explicit reason.
2. No false tests:
   - No tests that only assert mocked happy paths without physical/contract meaning.
   - Every major test must validate a real invariant, measured fixture, or schema contract.
3. No hidden hardcoded physics constants:
   - Constants must come from config or model registries with citation metadata.
4. Research traceability required:
   - Every physics model needs citation, validity range, and uncertainty annotation.
5. Determinism required:
   - All stochastic paths must accept explicit seed and emit seed in artifacts.
6. Safety over optimism:
   - Unknown trust state => HOLD, never GO.

## 2) Reality Clause (Important)

Absolute "100% physics correct all the time" is not scientifically provable.  
Execution target is:
1. fail-closed correctness policy,
2. explicit uncertainty budgets,
3. cross-engine parity and calibration checks,
4. zero unqualified assumptions in release artifacts.

## 3) Global Gate Set (Applied Every Month)

1. `quality_gate`: lint/format/test/schema all green.
2. `physics_gate`: model validity + parity + uncertainty budget pass.
3. `repro_gate`: replayed run reproduces within tolerance with same seed/hash.
4. `security_gate`: auth/audit/signature checks pass.
5. `evidence_gate`: signed manifest + verification report present.

If any gate fails: status = HOLD.

## 4) Month-by-Month 30-Day Plan

## Month 1 (Days 0-30): Integrity Baseline and Enforcement

Primary outcome:
Hard enforcement scaffolding so bad science or weak engineering cannot merge.

Build:
1. Add `ruff` + `pre-commit` + strict CI checks.
2. Add testing policy doc and lint rule for hardcoded physics constants in runtime paths.
3. Add model metadata contract (`citation`, `validity_domain`, `uncertainty_model`).
4. Define release/certification mode behavior as fail-closed.
5. Add deterministic seed propagation and artifact logging for all stochastic routines.

Repo targets:
1. `pyproject.toml`
2. `.github/workflows/ci.yml`
3. `photonstrust/workflow/schema.py`
4. `photonstrust/pipeline/*`
5. `docs/` policy pages

Exit criteria:
1. No PR merges without pre-commit-equivalent checks.
2. All major stochastic outputs include seed/hash lineage.
3. Release gate rejects stub backend in certification mode.

## Month 2 (Days 31-60): Orbit Physics Upgrade (Research-Backed)

Primary outcome:
Real ephemeris-driven pass geometry in production lane with validation lane.

Build:
1. Introduce orbit provider interface.
2. Implement `skyfield` production provider for TLE/ephemeris pass geometry.
3. Add `poliastro` analysis provider for mission sweeps.
4. Add `orekit` reference validation lane (service/sidecar model preferred).
5. Add cross-engine parity tests: elevation, slant range, pass window timings.

Repo targets:
1. `photonstrust/orbit/providers/`
2. `photonstrust/orbit/pass_envelope.py`
3. `photonstrust/pipeline/satellite_chain.py`
4. `schemas/photonstrust.satellite_qkd_chain.v0.schema.json`
5. `tests/test_satellite_*`

Exit criteria:
1. Orbit outputs include provider name + version + ephemeris source hash.
2. Cross-engine parity within declared tolerances on reference fixtures.
3. Any out-of-domain orbit config returns HOLD with reason.

## Month 3 (Days 61-90): Distributed Physics Compute + Optimization

Primary outcome:
Scale sweeps/optimization without compromising determinism or lineage.

Build:
1. Harden `ray` execution path with resource caps/retries/timeouts.
2. Harden `optuna` studies with resumable storage and deterministic seeds.
3. Add `mlflow` experiment tracking adapter with run/trial lineage links.
4. Add `prefect` nightly orchestration flows for satellite + corner + compliance lanes.
5. Add cost/perf guardrails (max trials/runtime/workers).

Repo targets:
1. `photonstrust/pipeline/satellite_chain_sweep.py`
2. `photonstrust/pipeline/satellite_chain_optuna.py`
3. `photonstrust/ops/` (new)
4. `scripts/run_satellite_chain_*.py`
5. `.github/workflows/satellite-chain.yml`

Exit criteria:
1. Sweep/optimization reports include full lineage (seed/hash/backend/version).
2. Nightly flow produces signed, reproducible artifacts.
3. Re-run of same study config reproduces ranking within tolerance.

## Month 4 (Days 91-120): API v1 Contracts + Multitenant Security Basics

Primary outcome:
Typed, stable API contracts and secure access boundaries.

Build:
1. Add `/v1` typed models via `pydantic` for core endpoints.
2. Standardize error envelope and request-id propagation.
3. Enforce authz on all run/sim/export endpoints.
4. Add tenant/project scope enforcement in run/job/artifact access.
5. Add Plotly ops dashboards in Streamlit for run health and risk metrics.

Repo targets:
1. `photonstrust/api/server.py`
2. `photonstrust/api/models/v1/` (new)
3. `photonstrust/api/runs.py`
4. `photonstrust/api/jobs.py`
5. `ui/app.py` and `ui/data.py`

Exit criteria:
1. `/v1` contracts validated by schema + integration tests.
2. Unauthorized or cross-tenant access denied in tests.
3. Operational dashboards reflect real run/job/evidence states.

## Month 5 (Days 121-150): Physics Credibility and Cross-Engine Protocol Validation

Primary outcome:
Strong scientific defensibility through calibration, parity, and uncertainty accounting.

Build:
1. Add protocol engine abstraction for validation lanes.
2. Keep `qiskit` as primary parity lane.
3. Add optional `cirq` and `pennylane` parity checks.
4. Add optional `tensorflow-quantum` research lane only.
5. Build model error budget rollup included in certificates/signoff.

Repo targets:
1. `photonstrust/protocols/engines/` (new)
2. `photonstrust/protocols/circuits.py`
3. `photonstrust/pipeline/certify.py`
4. `photonstrust/pipeline/satellite_chain.py`
5. `tests/test_protocol_*`

Exit criteria:
1. Cross-engine protocol parity reports attached to release candidates.
2. Certificates include uncertainty budget and confidence bounds.
3. GO decision blocked when uncertainty budget exceeds threshold.

## Month 6 (Days 151-180): Enterprise/Foundry Release Readiness

Primary outcome:
Decision-grade, auditable release process for enterprise and foundry submission.

Build:
1. Add DVC tracking for major fixtures/datasets/reference artifacts.
2. Enforce lane-specific lock files in CI.
3. Produce unified signed compliance envelope:
   - release gate packet
   - tapeout package
   - evidence verification report
   - dependency/seed/hash lineage
4. Enforce path-based required CI lanes for changed domains.
5. Finalize waiver SLA, approval RACI, and incident response playbook.

Repo targets:
1. `.github/workflows/*`
2. `scripts/release_gate_check.py`
3. `scripts/build_tapeout_package.py`
4. `photonstrust/pic/tapeout_package.py`
5. governance docs under `docs/`

Exit criteria:
1. Release candidate passes all gates with signed manifests.
2. Foundry package validates without manual patching.
3. Reproducibility replay succeeds on independent runner.

## 5) KPI Targets by End of 180 Days

Engineering:
1. Coverage >= 80%.
2. Flaky tests < 3%.
3. Mean lead time < 24h.
4. Change failure rate < 10%.

Physics/Product:
1. Orbit parity pass >= 99% on validation suite.
2. 100% release artifacts signed and verifiable.
3. 0 unresolved high-severity uncertainty-budget violations in GO releases.

Operations:
1. Sweep throughput improvement >= 40% vs Month-1 baseline.
2. Repro replay success >= 95% for deterministic profiles.

## 6) Execution Policy for "No Stubs"

1. Allowed:
   - mock/stub in unit tests only, clearly labeled.
   - optional preview mode for developer exploration.
2. Not allowed:
   - mock/stub in certification/release mode.
   - hidden fallback from real backend to stub without explicit HOLD.

## 7) Definition of "Research-Backed"

Each model must include:
1. Source citation (DOI/paper/spec URL).
2. Parameter validity domain.
3. Calibration provenance (dataset and timestamp).
4. Uncertainty method.
5. Known failure regimes.

No metadata => model cannot participate in GO signoff.

## 8) Immediate Next 30-Day Sprint Start (Now)

1. Implement Month-1 gates first (`ruff`, `pre-commit`, fail-closed enforcement).
2. Add model metadata contract and seed lineage in key pipelines.
3. Add CI checks that reject certification runs using untrusted backends.

This unlocks safe acceleration for every subsequent 30-day block.
