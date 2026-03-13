# PhotonTrust 24-Week Execution Program

This document converts the research set into a delivery program with weekly
tasks, dependencies, quality gates, and explicit outputs.

## Program assumptions
- Team size: 4-7 contributors (can be fewer with slower cadence).
- Priority order: QKD + repeaters -> teleportation -> source benchmarking.
- Technical stack: Python, QuTiP, Qiskit, Streamlit, pytest, GitHub Actions.
- Cadence: weekly sprint with one planning session and one demo/review.

## Team roles used in this program
- TL: Technical Lead
- PHY: Quantum Physics Engineer
- SIM: Simulation/Kernel Engineer
- PROT: Protocol/Qiskit Engineer
- CAL: Calibration/Inference Engineer
- OPT: Optimization Engineer
- UX: Product/UI Engineer
- QA: Quality/CI Engineer
- DOC: Documentation/Developer Experience

## Cross-cutting weekly rituals
- Monday: planning and risk review (45 min)
- Wednesday: architecture sync (30 min)
- Friday: demo + acceptance check (60 min)
- Weekly outputs: changelog notes + updated run registry snapshots

## Milestone map
- M1 (W1-W4): Scientific core foundations
- M2 (W5-W8): Event kernel and protocol execution
- M3 (W9-W12): Flagship QKD + repeater quality
- M4 (W13-W16): Teleportation and source benchmarking quality
- M5 (W17-W20): Calibration, uncertainty, optimization depth
- M6 (W21-W24): Product polish, adoption package, release candidate

---

## Week-by-week plan

## Week 1 - Program initialization and architecture freeze
### Objectives
- Freeze architecture contracts and schema versions for current cycle.

### Tasks
- TL: finalize module boundaries and API interface contracts.
- DOC: publish architecture decision records for key constraints.
- QA: establish branch protection, CI minimum checks, test naming conventions.

### Outputs
- Architecture freeze memo:
  `../../operations/week1/architecture_freeze_memo_2026-02-12.md`
- API contract table with owners:
  `../../operations/week1/api_contract_table_2026-02-12.md`
- CI baseline rules documented:
  `../../operations/week1/ci_baseline_rules_2026-02-12.md`

### Exit criteria
- No open architecture blockers.
- All core modules have owner assignments.

## Week 2 - Physics model hardening (emitter)
### Objectives
- Stabilize emitter model for reproducible results and diagnostics.

### Tasks
- PHY: validate emitter trajectory outputs against analytic expectations.
- QA: add deterministic seed tests for emitter stats.
- DOC: write emitter parameter tuning guide.

### Outputs
- Emitter validation report:
  `../../operations/week2/emitter_validation_report_2026-02-12.md`
- Updated tests for emitter deterministic behavior.
- Emitter tuning guide:
  `../../operations/week2/emitter_parameter_tuning_guide_2026-02-12.md`
- Deterministic emitter tests:
  `../../../tests/test_emitter_model.py`

### Exit criteria
- Emitter outputs reproducible with fixed seed.
- g2_0 trend checks pass.

## Week 3 - Physics model hardening (memory + detector)
### Objectives
- Stabilize memory and detector models for downstream protocols.

### Tasks
- PHY: refine memory decay and retrieval behavior checks.
- SIM: calibrate detector stochastic click behavior for realistic ranges.
- QA: add model sanity tests for monotonic and bounded outputs.

### Outputs
- Memory and detector validation notebook:
  `../../operations/week3/memory_detector_validation_2026-02-12.ipynb`
- Memory and detector validation report:
  `../../operations/week3/memory_detector_validation_report_2026-02-12.md`
- Test coverage for key model invariants:
  `../../../tests/test_memory_detector_invariants.py`

### Exit criteria
- Fidelity decay monotonicity and detector bounds verified.

## Week 4 - Reliability Card v1.0 freeze prep
### Objectives
- Freeze v1.0 card semantics for core scenarios.

### Tasks
- TL + DOC: finalize card field definitions and examples.
- QA: schema checks integrated in CI.
- UX: align HTML/PDF rendering with schema fields.

### Outputs
- v1.0 card semantic freeze note.
- Schema validation tests green.

### Exit criteria
- Card generation stable for demo1 + repeater.

## Week 5 - Event kernel scheduling depth
### Objectives
- Ensure event ordering, latency handling, and topologies are robust.

### Tasks
- SIM: add richer event types and retry scheduling hooks.
- QA: event ordering and latency causality tests.
- DOC: event lifecycle diagram.

### Outputs
- Event trace examples for link and chain.
- Kernel correctness tests.

### Exit criteria
- Event traces deterministic and causally consistent.

## Week 6 - Channel realism enhancements
### Objectives
- Improve channel realism where it influences decisions.

### Tasks
- SIM: add configurable polarization drift proxy and dispersion handling.
- PHY: validate channel impacts against expected ranges.
- QA: channel regression tests.

### Outputs
- Channel realism report.
- Updated benchmark config defaults.

### Exit criteria
- Channel effects produce plausible and stable metric shifts.

## Week 7 - Protocol compiler integration (swapping + purification)
### Objectives
- Integrate protocol circuits with event engine callbacks.

### Tasks
- PROT: wire measurement outcomes to feed-forward events.
- SIM: ensure protocol events schedule with proper latency.
- QA: protocol callback correctness tests.

### Outputs
- End-to-end swapping and purification run logs.

### Exit criteria
- Protocol outcomes reflected in event traces and metrics.

## Week 8 - Teleportation control flow integration
### Objectives
- Complete teleportation control flow under realistic latency.

### Tasks
- PROT: finalize teleportation flow and correction mapping.
- SIM: integrate memory wait penalties due to classical latency.
- QA: teleportation consistency tests.

### Outputs
- Teleportation run report with latency/fidelity trade-off.

### Exit criteria
- Teleportation scenario reproducible with confidence metrics.

## Week 9 - QKD flagship quality pass (part 1)
### Objectives
- Improve quality and interpretability of metro QKD outputs.

### Tasks
- PHY + SIM: tune detector and multiphoton influence visibility.
- UX: improve report readability for engineering audiences.
- QA: add qkd regression checks per band.

### Outputs
- Metro QKD quality report.

### Exit criteria
- Reliable key-rate curves and stable card generation for all bands.

## Week 10 - QKD flagship quality pass (part 2)
### Objectives
- Ensure cross-band comparisons are robust and actionable.

### Tasks
- PHY: validate band assumptions and detector pairings.
- DOC: publish interpretation guide for band trade-offs.
- QA: baseline updates with controlled process.

### Outputs
- Band comparison brief.
- Updated baseline artifacts.

### Exit criteria
- Cross-band reliability cards consistent and interpretable.

## Week 11 - Repeater optimization quality pass
### Objectives
- Strengthen repeater recommendations with uncertainty and cost proxies.

### Tasks
- OPT: improve spacing optimization and recommendation summary.
- PHY: validate memory-driven failure regimes.
- QA: repeater regression checks.

### Outputs
- Repeater decision report with sensitivity insights.

### Exit criteria
- Recommendations stable under small parameter perturbations.

## Week 12 - M3 checkpoint review
### Objectives
- Lock flagship QKD + repeater package for external preview.

### Tasks
- TL: checkpoint review against M3 acceptance criteria.
- DOC: prepare external demo narrative and limitations.
- QA: full suite run and issue triage.

### Outputs
- M3 checkpoint package.

### Exit criteria
- M3 acceptance signed.

## Week 13 - Teleportation quality pass
### Objectives
- Raise teleportation scenario quality to publication-ready level.

### Tasks
- PROT + SIM: refine latency model integration.
- PHY: verify fidelity/outage outputs under expected regimes.
- QA: teleportation golden checks.

### Outputs
- Teleportation SLA report with uncertainty.

### Exit criteria
- SLA outputs stable and reproducible.

## Week 14 - Source benchmarking quality pass
### Objectives
- Make source benchmarking externally credible and actionable.

### Tasks
- PHY: calibrate source metrics mapping to network impact.
- DOC: create source interpretation guide.
- QA: source scenario regression checks.

### Outputs
- Source benchmarking reliability card series.

### Exit criteria
- Source metrics produce expected network impact trends.

## Week 15 - Benchmark suite governance implementation
### Objectives
- Operationalize benchmark governance and update workflows.

### Tasks
- QA: enforce baseline update scripts and review checks.
- DOC: benchmark change protocol and owner list.
- TL: approve benchmark lifecycle process.

### Outputs
- Benchmark governance policy in repo.

### Exit criteria
- Baseline updates cannot bypass governance checks.

## Week 16 - M4 checkpoint review
### Objectives
- Complete use-case breadth package.

### Tasks
- TL: evaluate all three use-cases against acceptance criteria.
- QA: regression + schema + golden tests.
- UX: final demo path in UI for all use-cases.

### Outputs
- M4 acceptance report.

### Exit criteria
- QKD/repeater, teleportation, source benchmarking all accepted.

## Week 17 - Calibration depth (posterior diagnostics)
### Objectives
- Elevate calibration from utility to publishable quality.

### Tasks
- CAL: add posterior diagnostics (ESS, R-hat, PPC summaries).
- QA: tests for calibration stability and seed reproducibility.
- DOC: calibration methods and caveats.

### Outputs
- Calibration diagnostics report.

### Exit criteria
- Posterior diagnostics meet thresholds.

## Week 18 - Uncertainty propagation depth
### Objectives
- Ensure confidence intervals and outage probabilities are robust.

### Tasks
- CAL + SIM: optimize uncertainty propagation path.
- UX: surface uncertainty clearly in cards and UI.
- QA: uncertainty consistency tests.

### Outputs
- Uncertainty quality report.

### Exit criteria
- Uncertainty fields available and validated in all flagship cards.

## Week 19 - Optimization decision quality
### Objectives
- Make optimization outputs genuinely actionable.

### Tasks
- OPT: refine recommendation text and sensitivity output.
- DOC: decision interpretation guide for engineers.
- QA: optimization regression tests.

### Outputs
- Decision output quality pack.

### Exit criteria
- Recommendations are stable and explainable.

## Week 20 - M5 checkpoint review
### Objectives
- Lock scientific and decision quality for release candidate prep.

### Tasks
- TL: review M5 criteria.
- QA: full validation sweep.
- DOC: update release notes draft.

### Outputs
- M5 acceptance report.

### Exit criteria
- M5 accepted with no critical blockers.

## Week 21 - UI and reporting polish
### Objectives
- Improve external usability for evaluators and partners.

### Tasks
- UX: add comparison clarity and metadata filters.
- DOC: quickstart and tutorial updates.
- QA: UI smoke checks.

### Outputs
- Improved UI walkthrough.

### Exit criteria
- New user can run and compare scenarios in under 20 minutes.

## Week 22 - Release bundle and governance polish
### Objectives
- Finalize release artifact quality and governance docs.

### Tasks
- TL + DOC: finalize changelog and release notes.
- QA: verify release bundle integrity and completeness.
- SIM: ensure run registry includes all essential metadata.

### Outputs
- Release candidate bundle.

### Exit criteria
- Bundle reproducible from clean environment.

## Week 23 - External reviewer dry run
### Objectives
- Validate adoption readiness with an external simulation user flow.

### Tasks
- DOC + UX: run guided pilot with reviewers.
- TL: collect and triage feedback.
- QA: prioritize blocker fixes.

### Outputs
- Reviewer feedback report.

### Exit criteria
- No critical usability or trust blockers remain.

## Week 24 - v1.0 release gate
### Objectives
- Execute final release gate and publish.

### Tasks
- TL: run final gate checklist from deep-dive release gate doc.
- QA: final CI run and baseline lock.
- DOC: publish v1.0 release notes and documentation index.

### Outputs
- v1.0 publication package.

### Exit criteria
- All release gates pass and release is approved.

---

## Dependency chain summary
- Calibration quality depends on validated physics models.
- Optimization quality depends on stable uncertainty propagation.
- Adoption package depends on benchmark governance and UI clarity.

## Program risk triggers (monitor weekly)
- Drift in benchmark outputs without documented changes.
- Calibration diagnostics below thresholds.
- Runtime growth exceeding performance envelopes.

## Definition of program success
- All three flagship use-cases pass acceptance.
- Reliability Card standard adopted in at least one external evaluation.
- Public release bundle reproducible by an external user.

## Completion evidence (2026-02-12)
- Program completion summary:
  `../../operations/program_completion_report_2026-02-12.md`
- Release gate automation:
  `../../../scripts/release/release_gate_check.py`
- Benchmark drift check:
  `../../../scripts/validation/check_benchmark_drift.py`
- Milestone acceptance artifacts:
  `../../../reports/specs/milestones/milestone_readiness_m6_2026-02-12.md`,
  `../../../reports/specs/milestones/regression_baseline_gate_2026-02-12.md`,
  `../../../reports/specs/milestones/reliability_card_quality_review_2026-02-12.md`,
  `../../../reports/specs/milestones/external_reviewer_dry_run_2026-02-12.md`,
  `../../../reports/specs/milestones/release_gate_v1_0_2026-02-12.md`


## Inline citations (web, verified 2026-02-12)
Applied to: 24-week sequencing assumptions, tooling milestones, and release-readiness constraints.
- QuTiP release cadence (v5.2.3 listed): https://qutip.org/download.html
- Qiskit SDK 2.2 release notes: https://quantum.cloud.ibm.com/docs/en/api/qiskit/release-notes/2.2
- Streamlit release notes (2026 line): https://docs.streamlit.io/develop/quick-reference/release-notes
- RFC 9340 architecture baseline: https://www.rfc-editor.org/info/rfc9340
- NIST CSF 2.0 governance/risk baseline: https://doi.org/10.6028/NIST.CSWP.29
- Keep a Changelog standard format: https://keepachangelog.com/en/1.1.0/
- Semantic Versioning 2.0.0: https://semver.org/spec/v2.0.0.html

