# M11 Day-150 Execution Plan (Days 121-150)

Date: 2026-03-02
Window: Day 121 to Day 150
Parent: `M7_30_day_execution_master_plan.md`
Goal: Reach high scientific defensibility through protocol cross-engine validation, calibrated model governance, and uncertainty-aware signoff.

## 1) Day-150 Mission

By Day 150, GO decisions must be backed by:
1. protocol parity evidence across designated engines,
2. research-cited and validity-bounded model metadata,
3. quantified uncertainty budgets included in signoff artifacts,
4. fail-closed behavior when parity/calibration constraints are unmet.

## 2) Non-Negotiable Rules (Inherited + Enforced)

1. No GO without uncertainty budget completeness.
2. No engine promotion without parity suite pass.
3. No unlabeled model (citation/validity domain/known failure modes).
4. No synthetic benchmark accepted as calibration truth without provenance.
5. Unknown parity state => HOLD.

## 3) Deliverables Due by Day 150

1. Protocol engine abstraction layer for validation lanes.
2. Qiskit-backed primary parity suite for canonical protocol primitives.
3. Optional parity lanes for Cirq and PennyLane.
4. Optional TensorFlow Quantum research lane (explicitly non-blocking unless promoted).
5. Uncertainty budget rollup integrated into certificates/signoff outputs.
6. Calibration/provenance governance policy for benchmark and measurement bundles.
7. CI gates for parity, drift checks, and uncertainty enforcement.

## 4) Scope and Boundaries

In scope:
1. protocol-level cross-engine parity and trust promotion rules.
2. uncertainty and calibration governance integration into signoff.
3. scientific auditability outputs for release candidates.

Out of scope for Day 150:
1. broad commercial GTM workflows,
2. full enterprise tenancy and billing domains,
3. non-core UI redesign.

## 5) Workstreams

## WS1: Protocol Engine Abstraction

Objective:
Make protocol validation engine-agnostic while keeping one trusted baseline lane.

Tasks:
1. Add engine adapter interfaces for protocol primitives.
2. Implement baseline adapter around existing Qiskit lane.
3. Define strict output equivalence contract for parity testing.

Target touchpoints:
1. `photonstrust/protocols/engines/` (new)
2. `photonstrust/protocols/circuits.py`
3. `tests/test_protocol_*`

Acceptance:
1. Engine adapters produce contract-compatible outputs.
2. Qiskit baseline lane remains deterministic and green.

## WS2: Cross-Engine Parity Harness

Objective:
Quantify consistency across engines and block unqualified divergence.

Tasks:
1. Add parity harness for canonical BB84/BBM92-related primitives.
2. Add Cirq and PennyLane optional lanes.
3. Add threshold policy by metric class (probability, key-rate proxy, error rates).

Target touchpoints:
1. `tests/test_protocol_circuits_qiskit.py`
2. new `tests/test_protocol_parity_*`
3. `.github/workflows/ci.yml` optional/required path rules

Acceptance:
1. Parity report artifact generated for each candidate run.
2. Out-of-threshold results force HOLD.

## WS3: Uncertainty Budget Integration

Objective:
Make uncertainty explicit in every decision-grade artifact.

Tasks:
1. Define uncertainty components and rollup formulas.
2. Extend certificate/signoff structures with budget fields.
3. Add signoff guardrails for max allowable uncertainty.

Target touchpoints:
1. `photonstrust/pipeline/certify.py`
2. `photonstrust/pipeline/satellite_chain.py`
3. `photonstrust/pic/signoff.py`
4. `photonstrust/workflow/schema.py`

Acceptance:
1. GO impossible without complete uncertainty section.
2. Budget overrun produces HOLD with explicit reason codes.

## WS4: Calibration and Data Provenance Governance

Objective:
Ensure model inputs are trustworthy and auditable.

Tasks:
1. Add calibration metadata contract (`dataset_id`, acquisition date, method).
2. Add drift checks against locked benchmark fixtures.
3. Add policy for stale/out-of-domain calibration rejection.

Target touchpoints:
1. `datasets/benchmarks/`
2. `tests/fixtures/`
3. `scripts/validation/check_benchmark_drift.py`
4. `scripts/validation/compare_recent_research_benchmarks.py`

Acceptance:
1. Calibration provenance fields present in artifacts.
2. Stale/out-of-domain calibrations trigger HOLD.

## WS5: Scientific Reporting and Evidence

Objective:
Make Day-150 science claims defensible to external technical reviewers.

Tasks:
1. Publish parity summary and uncertainty report per candidate.
2. Link model citations and validity domains in evidence packet.
3. Add signed scientific integrity appendix artifact.

Target touchpoints:
1. `scripts/release/release_gate_check.py`
2. evidence packet generation scripts
3. `docs/` scientific governance notes

Acceptance:
1. Scientific appendix generated and signed.
2. All model references are traceable from artifacts.

## WS6: CI and Signoff Gate Enforcement

Objective:
Prevent parity/uncertainty regressions from reaching release.

Tasks:
1. Add parity and uncertainty checks as required lanes for touched domains.
2. Add regression lane for calibration drift.
3. Integrate results into release and tapeout GO/HOLD logic.

Target touchpoints:
1. `.github/workflows/ci.yml`
2. `.github/workflows/cv-quick-verify.yml`
3. `scripts/release/release_gate_check.py`

Acceptance:
1. Parity and uncertainty gates are hard-blocking where applicable.
2. Release candidate cannot pass with unresolved scientific HOLD reasons.

## 6) Week-by-Week Execution (Day 121-150)

## Week 17 (Day 121-127): Engine Contracts and Baseline

1. Finalize protocol engine interface.
2. Stabilize Qiskit baseline parity set.
3. Add initial adapter and contract tests.

Exit:
1. Baseline protocol parity lane stable.

## Week 18 (Day 128-134): Cross-Engine Expansion

1. Add Cirq and PennyLane optional parity lanes.
2. Define threshold policies and failure codes.
3. Add CI artifact reporting for parity deltas.

Exit:
1. Multi-engine parity report generated in CI.

## Week 19 (Day 135-141): Uncertainty and Calibration Governance

1. Integrate uncertainty rollups in certificates/signoff.
2. Add calibration provenance and drift gates.
3. Add HOLD policy for out-of-domain conditions.

Exit:
1. GO/HOLD now uncertainty- and calibration-aware.

## Week 20 (Day 142-150): Hardening and Day-150 Rehearsal

1. Run scientific integrity rehearsal.
2. Produce signed parity + uncertainty appendix.
3. Lock Day-150 reference artifacts.

Exit:
1. Day-150 acceptance gates pass.
2. Rehearsal evidence is complete and signed.

## 7) Day-150 Acceptance Gates

1. `parity_gate`:
   - baseline and enabled optional engine parity within thresholds.
2. `uncertainty_gate`:
   - full uncertainty budget present and in-bounds.
3. `calibration_gate`:
   - provenance and drift checks pass.
4. `science_evidence_gate`:
   - citations/validity ranges attached and signed.
5. `repro_gate`:
   - parity and uncertainty outputs reproducible on replay.

Fail any gate => HOLD.

## 8) Metrics for Day-150 Review

1. Parity pass rate >= 99% on canonical suite.
2. Uncertainty section completeness = 100% on candidate artifacts.
3. Calibration drift unresolved incidents = 0.
4. Scientific appendix generation success = 100%.
5. Replay consistency for scientific reports >= 95%.

## 9) Risks and Mitigations (Day-150 Specific)

1. Engine semantic mismatch:
   - Mitigation: metric-specific tolerance policies and explicit failure taxonomy.
2. Overfitting thresholds:
   - Mitigation: holdout validation fixtures and periodic threshold review.
3. Weak calibration provenance:
   - Mitigation: mandatory metadata contract and stale data rejection.
4. Report complexity and reviewer confusion:
   - Mitigation: standardized appendix format with concise summaries and raw links.
5. CI instability from optional heavy engines:
   - Mitigation: tiered lanes (PR smoke, nightly full parity).

## 10) Artifacts Required at Day-150 Close

1. Protocol parity report packet.
2. Uncertainty budget methodology and run-level outputs.
3. Calibration provenance and drift report.
4. Scientific integrity appendix (signed).
5. Day-150 rehearsal report with GO/HOLD justifications.

## 11) Immediate Start Sequence

1. Lock protocol adapter contracts and parity metrics.
2. Add baseline Qiskit parity harness.
3. Integrate uncertainty rollup in signoff.
4. Add calibration governance checks.
5. Promote parity/uncertainty lanes to required-by-path.
