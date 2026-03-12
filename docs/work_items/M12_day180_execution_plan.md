# M12 Day-180 Execution Plan (Days 151-180)

Date: 2026-03-02
Window: Day 151 to Day 180
Parent: `M7_30_day_execution_master_plan.md`
Goal: Achieve enterprise/foundry release readiness with reproducible, signed, and policy-governed delivery artifacts.

## 1) Day-180 Mission

By Day 180, release candidates must be:
1. reproducible on independent runners,
2. cryptographically verifiable end-to-end,
3. policy-governed with auditable approvals and waivers,
4. accepted by enterprise/foundry review without manual artifact patching.

## 2) Non-Negotiable Rules (Inherited + Enforced)

1. No unsigned release candidate artifacts.
2. No unpinned dependency sets in release lanes.
3. No mutable baseline datasets without governance trail.
4. No unresolved waiver beyond SLA at release cut.
5. Unknown evidence integrity state => HOLD.

## 3) Deliverables Due by Day 180

1. DVC-backed dataset/fixture governance for critical evidence assets.
2. Lane-specific lockfile policy enforced in CI/release workflows.
3. Unified signed compliance envelope containing:
   - release gate packet,
   - tapeout package,
   - evidence verification report,
   - lineage fingerprints (git/deps/seeds/hashes).
4. Required-by-path CI policy for all critical domains.
5. Formal governance docs:
   - waiver lifecycle SLA,
   - approval RACI,
   - incident response playbook.
6. Day-180 full release rehearsal and independent replay verification.

## 4) Scope and Boundaries

In scope:
1. release/tapeout/evidence packaging hardening.
2. reproducibility and dependency governance.
3. policy and operations controls for launch-grade readiness.

Out of scope for Day 180:
1. commercial contract/legal operations outside technical artifact requirements,
2. non-core product feature expansion unrelated to release trust.

## 5) Workstreams

## WS1: DVC Data and Fixture Governance

Objective:
Make benchmark/reference artifacts versioned, reproducible, and auditable.

Tasks:
1. Initialize DVC tracking for critical fixtures/datasets.
2. Define canonical remote policy and retention.
3. Add DVC status/repro checks in CI for release-impacting paths.

Target touchpoints:
1. `.dvc/` (new)
2. `dvc.yaml`, `dvc.lock` (new)
3. `tests/fixtures/`
4. `datasets/benchmarks/`
5. `.github/workflows/ci.yml`

Acceptance:
1. Critical evidence datasets are DVC-tracked.
2. Drift without governance change is blocked.

## WS2: Dependency Lockfile and Runtime Integrity Enforcement

Objective:
Ensure deterministic environments for all release lanes.

Tasks:
1. Add lane-specific lock files.
2. Enforce lockfile integrity checks in CI and release gates.
3. Require explicit dependency fingerprints in release artifacts.

Target touchpoints:
1. `requirements/*.lock.txt`
2. `scripts/check_runtime_environment.py`
3. `scripts/production_readiness_check.py`
4. `.github/workflows/*`

Acceptance:
1. Release lanes fail on lock drift.
2. Dependency fingerprints present in compliance envelope.

## WS3: Unified Signed Compliance Envelope

Objective:
Produce one decision-grade artifact package for enterprise/foundry review.

Tasks:
1. Bundle release gate, tapeout package, and evidence verification outputs.
2. Generate unified manifest with SHA256 for every included file.
3. Sign manifest and verify signature in release workflow.

Target touchpoints:
1. `scripts/build_release_gate_packet.py`
2. `scripts/build_tapeout_package.py`
3. `scripts/release_gate_check.py`
4. `photonstrust/pic/tapeout_package.py`
5. `photonstrust/evidence/bundle.py`

Acceptance:
1. Single compliance envelope generated on candidate release.
2. Verification succeeds on independent replay runner.

## WS4: CI Policy Hardening (Required-by-Path)

Objective:
Prevent critical regressions from bypassing required checks.

Tasks:
1. Convert optional lanes to required when relevant paths change.
2. Add explicit gating map for physics/API/security/evidence/tapeout paths.
3. Add branch protection check list tied to gate IDs.

Target touchpoints:
1. `.github/workflows/ci.yml`
2. `.github/workflows/satellite-chain.yml`
3. `.github/workflows/tapeout-gate.yml`
4. `.github/workflows/security-baseline.yml`
5. `.github/workflows/cv-quick-verify.yml`

Acceptance:
1. Required lanes trigger deterministically for critical path changes.
2. No release tag can pass with skipped critical gates.

## WS5: Governance and Operational Controls

Objective:
Make trust decisions operationally enforceable and auditable.

Tasks:
1. Formalize waiver SLA and escalation policy.
2. Formalize approval RACI and minimum reviewer set for GO.
3. Add incident response playbook for gate failures and evidence integrity issues.

Target touchpoints:
1. `docs/` governance area
2. `photonstrust/pic/signoff.py`
3. release/tapeout scripts and policy docs

Acceptance:
1. Waiver aging beyond SLA automatically flags HOLD.
2. Approval chain is machine-checkable in release artifacts.

## WS6: Final Readiness Rehearsal

Objective:
Prove end-to-end launch readiness under realistic conditions.

Tasks:
1. Run full candidate pipeline (compile/simulate/certify/sweep/signoff/tapeout/release).
2. Perform independent runner replay and verification.
3. Publish readiness report and unresolved risk register.

Target touchpoints:
1. CI workflows and release scripts
2. `results/` rehearsal artifacts
3. `docs/` readiness reports

Acceptance:
1. Rehearsal packet complete, signed, and reproducible.
2. GO only if all critical gates pass and risk register is acceptable.

## 6) Week-by-Week Execution (Day 151-180)

## Week 21 (Day 151-157): Data and Lock Foundations

1. Enable DVC for critical fixtures.
2. Finalize lane-specific lockfiles.
3. Add integrity checks in CI.

Exit:
1. Data/lock governance gates are active and passing.

## Week 22 (Day 158-164): Compliance Envelope Assembly

1. Build unified envelope schema and manifest.
2. Integrate cryptographic signing and verification.
3. Add independent replay verifier script.

Exit:
1. Envelope generation and verification working end-to-end.

## Week 23 (Day 165-171): Policy and Required Lanes

1. Enable required-by-path CI matrix.
2. Finalize waiver/approval/incident policy docs.
3. Add machine-checkable policy checks in release gate.

Exit:
1. Policy enforcement automated in pipelines.

## Week 24 (Day 172-180): Final Rehearsal and Signoff

1. Execute full Day-180 rehearsal.
2. Perform independent replay verification.
3. Produce Day-180 readiness and decision report.

Exit:
1. Day-180 acceptance gates pass.
2. Launch-grade evidence packet is signed and archived.

## 7) Day-180 Acceptance Gates

1. `data_governance_gate`:
   - DVC and fixture integrity checks pass.
2. `dependency_integrity_gate`:
   - lockfile and runtime fingerprint checks pass.
3. `compliance_envelope_gate`:
   - unified package signed and verifiable.
4. `policy_gate`:
   - waiver/approval SLA and RACI checks pass.
5. `independent_replay_gate`:
   - external runner reproduces and verifies package.

Fail any gate => HOLD.

## 8) Metrics for Day-180 Review

1. Signed artifact coverage = 100%.
2. Independent replay verification success = 100% for candidate releases.
3. Critical-gate bypass incidents = 0.
4. Over-SLA waiver count at release = 0.
5. Release/tapeout gate pass rate on main >= 95% over trailing month.

## 9) Risks and Mitigations (Day-180 Specific)

1. Operational overhead from governance controls:
   - Mitigation: automate checks and templates.
2. DVC adoption friction:
   - Mitigation: limit scope to critical artifacts first.
3. Lockfile churn across environments:
   - Mitigation: lane-specific locks and controlled update cadence.
4. Signature/key lifecycle issues:
   - Mitigation: key rotation policy and verification drills.
5. False readiness due to single-run success:
   - Mitigation: multi-run rehearsal and independent verification requirement.

## 10) Artifacts Required at Day-180 Close

1. DVC governance report.
2. Dependency integrity and lock compliance report.
3. Unified signed compliance envelope and verification report.
4. Governance policy pack (waiver/RACI/incident).
5. Final readiness decision report (GO/HOLD with rationale).

## 11) Immediate Start Sequence

1. Add DVC and lockfile integrity controls.
2. Implement unified compliance envelope.
3. Make critical lanes required-by-path.
4. Enforce waiver/approval policy gates.
5. Run final independent replay rehearsal.
