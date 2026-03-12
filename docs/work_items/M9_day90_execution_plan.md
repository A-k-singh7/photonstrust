# M9 Day-90 Execution Plan (Days 61-90)

Date: 2026-03-02
Window: Day 61 to Day 90
Parent: `M7_30_day_execution_master_plan.md`
Goal: Deliver deterministic distributed compute and optimization at production quality, with full lineage and fail-closed decision policy.

## 1) Day-90 Mission

By Day 90, PhotonTrust sweeps and optimization must be:
1. scalable across local and distributed backends,
2. reproducible with seed/hash/backend lineage,
3. auditable through experiment tracking and signed artifacts,
4. blocked from GO when reproducibility or trust gates fail.

## 2) Non-Negotiable Rules (Inherited + Enforced)

1. No production stubs in certification/release mode.
2. No uncontrolled randomness in optimization/sweeps.
3. No missing lineage fields in GO evidence.
4. No silent backend fallback for required execution mode.
5. Unknown trust state => HOLD.

## 3) Deliverables Due by Day 90

1. Hardened Ray execution path:
   - retries/timeouts/resource limits/worker failure handling.
2. Hardened Optuna studies:
   - deterministic seeds, resumable storage, ask/tell reproducibility.
3. MLflow tracking integration:
   - params/metrics/artifacts linked to run manifests.
4. Prefect orchestration integration:
   - scheduled nightly flows for satellite/corner/compliance pipelines.
5. Deterministic lineage schema:
   - seed/config hash/graph hash/pdk hash/backend version in output artifacts.
6. CI and nightly lanes for distributed/repro validation.

## 4) Scope and Boundaries

In scope:
1. `ray`, `optuna`, `mlflow`, `prefect` execution and lineage.
2. reproducibility enforcement for sweeps and studies.
3. CI gates for distributed and scheduled runs.

Out of scope for Day 90:
1. full API v1 typed coverage,
2. full tenant isolation rollout,
3. full protocol-engine federation.

## 5) Workstreams

## WS1: Ray Distributed Execution Hardening

Objective:
Make distributed sweep execution robust, observable, and bounded.

Tasks:
1. Add job-level timeout/retry policy.
2. Add resource controls (`cpu`, memory hints, worker caps).
3. Add deterministic task ordering/report assembly.
4. Fail closed on partial result corruption.

Target touchpoints:
1. `photonstrust/pipeline/satellite_chain_sweep.py`
2. `scripts/run_satellite_chain_sweep.py`
3. `tests/test_satellite_chain_sweep_backend.py`

Acceptance:
1. Worker failure and timeout paths are tested and deterministic.
2. Run summary remains valid and schema-compliant under retries.

## WS2: Optuna Optimization Hardening

Objective:
Ensure optimization is reproducible and evidence-grade.

Tasks:
1. Add strict seed handling and seed recording per trial.
2. Add resumable study storage options.
3. Add lineage fields (`trial_id`, objective config hash, backend metadata).
4. Add fail-closed behavior for missing optimizer dependencies in required mode.

Target touchpoints:
1. `photonstrust/pipeline/satellite_chain_optuna.py`
2. `scripts/run_satellite_chain_optuna.py`
3. `tests/test_satellite_chain_optuna.py`
4. `tests/test_run_satellite_chain_optuna_script.py`

Acceptance:
1. Identical config+seed reproduces trial ranking within tolerance.
2. Report includes full study and backend metadata.

## WS3: MLflow Experiment Tracking

Objective:
Attach first-class experiment lineage to existing run artifacts.

Tasks:
1. Add tracking adapter with `local_json` and `mlflow` modes.
2. Log params/metrics/artifacts for sweep and optuna runs.
3. Persist `mlflow_run_id` and tracking URI in run manifest/evidence metadata.

Target touchpoints:
1. `photonstrust/ops/tracking.py` (new)
2. `photonstrust/api/runs.py`
3. `photonstrust/pipeline/*`

Acceptance:
1. Every scheduled optimization run has a trackable experiment ID.
2. Manifest and tracker records are cross-resolvable.

## WS4: Prefect Orchestration for Nightly Flows

Objective:
Provide schedule-driven reliability validation with auditable outputs.

Tasks:
1. Define Prefect flows for nightly satellite/corner/compliance chains.
2. Add failure notification and automatic artifact export.
3. Add explicit policy boundaries between preview and certification runs.

Target touchpoints:
1. `photonstrust/ops/prefect_flows.py` (new)
2. `scripts/run_prefect_flow.py` (new)
3. `.github/workflows/` nightly workflow additions

Acceptance:
1. Nightly flows run deterministically on pinned configs.
2. Flow outputs are signed and schema-validated.

## WS5: Reproducibility and Lineage Schema

Objective:
Guarantee re-run traceability for every Day-90 output.

Tasks:
1. Extend report/certificate payloads with lineage fields.
2. Add replay check command that re-evaluates a run from stored artifacts.
3. Gate GO decisions on lineage completeness.

Target touchpoints:
1. `photonstrust/workflow/schema.py`
2. `schemas/*sweep*` and `schemas/*optuna*` (as needed)
3. `scripts/release_gate_check.py`

Acceptance:
1. Repro replay succeeds on clean runner with pinned inputs.
2. Missing lineage fields trigger HOLD.

## WS6: CI and Cost-Guardrails

Objective:
Scale responsibly and keep CI trustworthy.

Tasks:
1. Add dedicated `ray+optuna` lane with small deterministic workload.
2. Add nightly heavy integration lane with capped budget.
3. Add runtime/cost budget assertions for long studies.

Target touchpoints:
1. `.github/workflows/satellite-chain.yml`
2. `.github/workflows/ci.yml`
3. `.github/workflows/cv-quick-verify.yml` (if release coupling is required)

Acceptance:
1. PR lanes stay fast and deterministic.
2. Nightly lanes catch distributed regressions before release.

## 6) Week-by-Week Execution (Day 61-90)

## Week 9 (Day 61-67): Ray and Optuna Contracts

1. Finalize distributed execution and study metadata contracts.
2. Implement hard timeout/retry/seed handling.
3. Extend schemas for lineage fields.

Exit:
1. Contract tests pass.
2. Schema validation passes.

## Week 10 (Day 68-74): MLflow Integration

1. Add tracker adapter and manifest linkage.
2. Emit artifact lineage for sweep and optuna runs.
3. Validate tracker backfill/recovery behavior.

Exit:
1. Tracker IDs appear in run manifests.
2. Artifacts are traceable from manifest to tracker and back.

## Week 11 (Day 75-81): Prefect Nightly Flows

1. Implement flow definitions and runner scripts.
2. Add scheduled execution and artifact publishing.
3. Add failure-handling and HOLD escalation path.

Exit:
1. Nightly flow artifacts produced and validated.
2. Flow failures are explicit and non-silent.

## Week 12 (Day 82-90): Hardening and Day-90 Rehearsal

1. Add replay reproducibility checks and release-gate hooks.
2. Run full rehearsal on reference configs.
3. Lock Day-90 reference artifacts and reports.

Exit:
1. Day-90 acceptance gates pass.
2. Rehearsal report includes GO/HOLD evidence.

## 7) Day-90 Acceptance Gates

1. `distributed_gate`:
   - Ray lane passes reliability tests.
2. `optimizer_gate`:
   - Optuna studies reproducible under fixed seed.
3. `lineage_gate`:
   - Complete seed/hash/backend metadata in outputs.
4. `repro_gate`:
   - Replay run matches stored result within tolerance.
5. `evidence_gate`:
   - Signed artifacts and validation reports present.

Fail any gate => HOLD.

## 8) Metrics for Day-90 Review

1. Sweep throughput gain vs Month-1 baseline >= 40%.
2. Repro replay success >= 95%.
3. Missing-lineage incidence = 0 in certification candidates.
4. Distributed lane failure due to control-plane defects < 2%.
5. CI deterministic lane pass rate >= 99%.

## 9) Risks and Mitigations (Day-90 Specific)

1. Ray nondeterminism/order drift:
   - Mitigation: canonical output ordering and deterministic seed threading.
2. Optuna drift across versions:
   - Mitigation: version pinning and study schema version tags.
3. Tracking outages:
   - Mitigation: local fallback tracker with deferred sync policy.
4. Nightly cost blowout:
   - Mitigation: hard worker/trial/runtime budgets.
5. False confidence from smoke-only CI:
   - Mitigation: nightly heavy lane and replay gate.

## 10) Artifacts Required at Day-90 Close

1. Distributed run reliability report.
2. Optimization reproducibility report.
3. MLflow lineage manifest mapping.
4. Prefect nightly run packet.
5. Day-90 release rehearsal report with signed evidence.

## 11) Immediate Start Sequence

1. Lock lineage schema first.
2. Harden Ray and Optuna execution paths.
3. Add MLflow linkage.
4. Add Prefect nightly orchestration.
5. Enable replay + evidence gates in CI.
