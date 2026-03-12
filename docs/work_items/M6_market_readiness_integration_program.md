# M6 Market Readiness Integration Program

Date: 2026-03-02
Scope: Integrate the proposed OSS stack into PhotonTrust so the platform is near market-ready across physics credibility, compute scale, product API/UI, governance, and release operations.

## 1) Program Objectives

1. Keep physics-first correctness as non-negotiable.
2. Scale sweeps and optimization to practical throughput.
3. Expose stable, typed API contracts and operator-grade UI.
4. Make releases reproducible, auditable, and enterprise/foundry-friendly.
5. Preserve optional dependency seams and deterministic fallbacks.

## 2) Current Baseline (from repository)

1. Core exists: PIC simulation, certify pipeline, compliance, signoff/tapeout, satellite-chain digital twin.
2. API exists: FastAPI `/v0/*` surface and filesystem-backed run/job/project stores.
3. UI exists: Streamlit operator console plus React web client.
4. CI exists: core tests, satellite-chain workflow, tapeout gate, security baseline.
5. New Step-1 foundation exists: `ray`/`optuna` extras, satellite sweep, optuna optimizer, JAX accumulation seam.

## 3) Integration Architecture

### 3.1 Runtime lanes

1. Production simulation lane:
   - `jax` for accelerated kernels where parity to NumPy is proven.
   - `skyfield` as default real ephemeris provider for satellite pass geometry.
   - `fastapi` + `pydantic` typed contracts for API v1.
2. Distributed execution lane:
   - `ray` for parallel sweeps and trial execution.
   - `optuna` for parameter search.
3. Product visualization lane:
   - `plotly` for interactive operational and evidence plots.
   - `streamlit` for internal mission operations.

### 3.2 Validation/reference lanes

1. Orbit fidelity lane:
   - `poliastro` for mission analysis/sweep utilities.
   - `orekit` as high-fidelity reference validator (prefer sidecar service model).
2. Protocol parity lane:
   - `qiskit` primary protocol cross-check backend.
   - `cirq`, `pennylane`, `tensorflow-quantum` as optional parity/validation engines.
3. ML surrogate lane:
   - `tensorflow` only for optional surrogate acceleration, never as ground-truth replacement.

### 3.3 Governance/repro lanes

1. `mlflow` for experiment tracking and lineage.
2. `prefect` for scheduled orchestration of nightly/regression runs.
3. `dvc` for fixture/dataset locking and reproducible artifact pointers.
4. `ruff` + `pre-commit` + expanded `pytest` matrix for pre-merge quality.

## 4) Dependency Integration Matrix

1. `ray` (Apache-2.0): Production for sweeps/Monte Carlo. Integrate into `photonstrust/pipeline/satellite_chain_sweep.py`, corner-sweep orchestration, and CI optional lane promoted to required-by-path.
2. `jax` (Apache-2.0): Production acceleration with deterministic parity gates. Integrate in PIC kernels and satellite accumulation seam with strict NumPy parity tests.
3. `optuna` (MIT): Production optimization driver. Integrate in satellite and corner optimization entrypoints, with resumable study storage.
4. `mlflow` (Apache-2.0): Production tracking plane. Add run/trial lineage IDs into run manifests and evidence metadata.
5. `dvc` (Apache-2.0): Production reproducibility plane. Track fixtures, benchmark datasets, and reference outputs.
6. `fastapi` (MIT): Existing production API base; introduce typed `/v1` contracts.
7. `pydantic` (MIT): Mandatory for API v1 request/response models and strict validation.
8. `plotly` (MIT): Operator and customer evidence visualizations.
9. `streamlit` (Apache-2.0): Existing internal operations UI, upgraded with Plotly panels and role-based views.
10. `ruff` (MIT): Required lint/format gate.
11. `pre-commit` (MIT): Required local gate mirror of CI checks.
12. `pytest` (MIT): Existing base; expand deterministic physics/ops matrix.
13. `skyfield` (MIT): Production default ephemeris provider for satellite pass synthesis.
14. `poliastro` (MIT): Validation/mission-design lane.
15. `orekit` (Apache-2.0): High-fidelity validation lane (service/sidecar, not core import path).
16. `qiskit` (Apache-2.0): Existing optional lane; keep and harden.
17. `cirq` (Apache-2.0): Optional parity lane.
18. `pennylane` (Apache-2.0): Optional differentiable protocol/parameter lane.
19. `tensorflow-quantum` (Apache-2.0): Optional research lane only.
20. `tensorflow` (Apache-2.0): Optional surrogate modeling lane.
21. `prefect` (Apache-2.0): Nightly orchestration and scheduled program runs.

## 5) 30/60/90-Day Executable Plan

## Day 0-30 (Foundation Hardening)

1. Quality gates:
   - Add `ruff` config and `.pre-commit-config.yaml`.
   - Enforce pre-merge `ruff check`, `ruff format --check`, pytest core, schema validation.
2. API contract groundwork:
   - Create `/v1` skeleton with Pydantic models for top endpoints (`health`, `qkd/run`, `pic/simulate`, `runs`).
   - Standardize error envelope (`code`, `detail`, `request_id`, `retryable`).
3. Orbit realism step-1:
   - Add orbit-provider abstraction and implement `skyfield` provider.
   - Preserve deterministic envelope fallback.
4. Sweep/optimization ops step-1:
   - Keep `ray` and `optuna` lanes optional but CI-covered with tiny deterministic workloads.
5. Visualization step-1:
   - Add Plotly panels in Streamlit for pass geometry, key-rate/yield distributions, run failure taxonomy.

Acceptance gates:
1. New CI lane for `ray+optuna` smoke passes.
2. `skyfield` provider produces pass outputs validating existing schema.
3. `/v1` typed endpoints pass contract tests.
4. Pre-commit hooks run clean on repo.

## Day 31-60 (Scale and Validation)

1. Tracking/orchestration:
   - Add `mlflow` tracker adapter and attach run/trial lineage to manifests.
   - Add `prefect` flows for nightly satellite/corner/compliance chains.
2. Orbit validation:
   - Add `poliastro` provider and `orekit` reference validator lane.
   - Publish cross-engine parity reports as CI artifacts.
3. Governance/repro:
   - Introduce `dvc` for critical fixtures and benchmark artifacts.
   - Add lane-specific lock files and runtime checks for dependency integrity.
4. API/security:
   - Expand auth enforcement on all run/sim endpoints.
   - Start tenant-scoped data access for runs/jobs/projects.

Acceptance gates:
1. Nightly Prefect flow completes with signed artifacts.
2. MLflow lineage present for all scheduled runs.
3. Orbit cross-engine parity within declared tolerance budget.
4. DVC status clean in CI on release branches.

## Day 61-90 (Market Readiness Cut)

1. Productization:
   - Complete `/v1` typed contract coverage for major endpoints.
   - Split internal ops views vs customer evidence views.
2. Validation lane expansion:
   - Add optional `cirq`/`pennylane` parity harness.
   - Add optional TensorFlow surrogate lane with strict holdout error guardrail.
3. Enterprise/foundry packaging:
   - Build unified signed compliance envelope:
     - release gate packet
     - tapeout package
     - evidence verification report
     - lock/hash lineage
4. Release governance:
   - Make dependency-specific lanes required when touched paths match.
   - Formalize waiver SLA and approval RACI.

Acceptance gates:
1. Enterprise evidence bundle verifies cryptographically and semantically.
2. Tapeout + release gates both green on candidate tag.
3. DORA and quality targets hit for 4-week window.

## 6) Concrete Repo Touchpoints

Core implementation surfaces:
1. `photonstrust/pipeline/satellite_chain.py`
2. `photonstrust/pipeline/satellite_chain_sweep.py`
3. `photonstrust/pipeline/satellite_chain_optuna.py`
4. `photonstrust/orbit/pass_envelope.py`
5. `photonstrust/orbit/geometry.py`
6. `photonstrust/api/server.py`
7. `photonstrust/api/runs.py`
8. `photonstrust/api/jobs.py`
9. `ui/app.py`
10. `web/src/photontrust/api.js`
11. `schemas/photonstrust.satellite_qkd_chain.v0.schema.json`
12. `pyproject.toml`

CI/workflows:
1. `.github/workflows/ci.yml`
2. `.github/workflows/satellite-chain.yml`
3. `.github/workflows/tapeout-gate.yml`
4. `.github/workflows/security-baseline.yml`
5. `.github/workflows/cv-quick-verify.yml`

New likely folders:
1. `photonstrust/orbit/providers/`
2. `photonstrust/protocols/engines/`
3. `photonstrust/ops/`
4. `photonstrust/api/models/v1/`

## 7) Physics Credibility Program

1. Truth sources:
   - TLE snapshot fixtures + known pass windows.
   - Locked satellite-chain reference fixtures.
2. Cross-engine checks:
   - `skyfield` vs `poliastro` vs `orekit` on elevation/slant-range/pass-window.
   - JAX vs NumPy parity for deterministic kernels.
   - Qiskit vs other circuit engines on canonical protocol primitives.
3. Error budget tracked in certificates:
   - orbit geometry uncertainty
   - atmosphere/pointing uncertainty
   - detector drift
   - PIC eta uncertainty
   - numerical tolerance residual
4. Gate policy:
   - Release candidate is HOLD if uncertainty budget is exceeded or parity checks fail.

## 8) Security, Compliance, and Multitenancy Minimums

1. Enforce authn/authz on all sensitive endpoints.
2. Tenant/project-scoped isolation for artifacts and metadata.
3. Immutable audit logs for approvals, waivers, releases, and evidence exports.
4. Signed manifests and verification reports as mandatory release artifacts.
5. Rate limiting and input constraints on heavy compute endpoints.

## 9) KPI/SLO Targets (Near-Market Readiness)

Engineering:
1. Deployment frequency: >= 3 per week on main.
2. Lead time for change: < 24 hours median.
3. Change failure rate: < 10%.
4. MTTR: < 4 hours.

Quality:
1. Coverage floor: >= 80%.
2. Flaky test rate: < 3%.
3. Repro replay success: >= 95%.
4. Reference fixture drift incidents: 0 unreviewed.

Physics/Product:
1. Orbit parity tolerance pass: >= 99% of validation cases.
2. Certificate schema and signature verification: 100% on releases.
3. P95 satellite scenario runtime reduction vs baseline: >= 40% in distributed lane.

## 10) Execution Model (Recommended Team)

1. Physics platform owner: orbit providers + parity + uncertainty budget.
2. Compute platform owner: Ray/Optuna/Prefect/MLflow/TensorFlow lanes.
3. Product platform owner: API v1 contracts + UI split + security model.
4. Quality/governance owner: CI matrix, DVC/locks, release envelopes, audit policy.

## 11) Immediate Sprint Backlog (Next 2 Weeks)

1. Add `ruff` + `pre-commit` and wire required CI quality job.
2. Add `/v1` model scaffolding and one typed endpoint pair (`/v1/qkd/run`, `/v1/pic/simulate`).
3. Implement `orbit provider` interface and `skyfield` provider.
4. Add `ray+optuna` smoke lane to satellite CI.
5. Add Plotly charts to Streamlit mission dashboard.
6. Define DVC tracking scope for top benchmark/fixture artifacts.
7. Draft waiver/approval SLA policy doc and map to current signoff flow.

Definition of done for sprint:
1. All new lanes green in CI.
2. Backward compatibility preserved for `/v0` and existing CLI commands.
3. New artifacts include deterministic hashes and pass schema validation.
