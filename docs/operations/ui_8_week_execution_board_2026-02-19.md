# PhotonTrust UI 8-Week Execution Board (2026-02-19)

This board is UI-only and is designed to make the product feel fully justified to users, reviewers, and investors through the web interface itself.

## Program Window

- Start: `2026-02-23`
- End: `2026-04-19`
- Primary surface: `web/` (React + Vite + React Flow)
- Supporting surface (read-only reference): `ui/` (Streamlit)

## Program Objective

Ship a product-grade UI where a first-time user can build, run, validate, compare, and export a trustworthy result without founder guidance.

## North-Star Targets (must hit by Week 8)

- `time_to_first_credible_result_min <= 10`
- `guided_flow_task_success_rate >= 90%`
- `run_to_decision_time_min <= 5`
- `critical_ui_error_recovery_rate >= 85%`
- `investor_demo_completion_rate >= 95%` (single operator, no code edits)
- `a11y_keyboard_coverage >= 90%` on critical flows

## Scope Lock

In scope:

- Product information architecture and navigation.
- Guided flows, graph builder UX, results UX, trust/certification UX, compare UX, export UX.
- UI telemetry and UI acceptance gates.
- Demo/pitch mode and product storytelling inside the app.

Out of scope:

- New physics models.
- New protocol core math.
- New backend systems unrelated to UI contracts.

## Product Justification Requirements (UI Proof Matrix)

- `Value clarity`: user understands what the product does in 60 seconds.
- `Actionability`: every result screen tells user what to do next.
- `Trust`: every run has visible provenance, assumptions, and quality status.
- `Comparability`: users can compare two runs and decide quickly.
- `Reproducibility`: runs can be replayed/exported deterministically from UI.
- `Decision support`: UI can produce a decision packet suitable for review meetings.

## Persona-Critical Workflows

- `Research Engineer`: Build graph -> run -> tune -> compare -> export.
- `Platform Lead`: Validate trust signals -> inspect failures -> approve/reject candidate.
- `Investor/Partner`: Understand differentiation -> see benchmark closeness -> see proof packet.

## Repository Touchpoints (planned)

- `web/src/App.jsx` (to be decomposed into feature modules)
- `web/src/App.css`
- `web/src/main.jsx`
- `web/src/photontrust/PtNode.jsx`
- `web/src/photontrust/graph.js`
- `web/src/photontrust/kinds.js`
- `web/src/photontrust/templates.js`
- `web/src/photontrust/api.js`
- `web/src/features/*` (new)
- `web/src/components/*` (new)
- `web/src/state/*` (new)
- `web/src/styles/*` (new tokens/layers)
- `docs/operations/product/*` (demo and runbook updates)

## UI Telemetry Contract (required)

Events to emit from UI:

- `ui_session_started`
- `ui_guided_flow_started`
- `ui_guided_flow_completed`
- `ui_run_started`
- `ui_run_succeeded`
- `ui_run_failed`
- `ui_error_recovered`
- `ui_compare_completed`
- `ui_packet_exported`
- `ui_demo_mode_completed`

Required fields per event:

- `timestamp_utc`
- `session_id`
- `user_mode` (`builder|reviewer|exec`)
- `profile` (`qkd_link|pic_circuit|orbit`)
- `run_id` (if available)
- `duration_ms` (if applicable)
- `outcome` (`success|failure|abandoned`)

Artifact path:

- `results/ui_metrics/events.jsonl`

## Delivery Cadence (every week)

- Monday: plan + scope lock + design acceptance criteria.
- Tuesday: primary implementation.
- Wednesday: primary implementation + UX text/copy pass.
- Thursday: QA, accessibility, responsive, edge-state hardening.
- Friday: usability run, scorecard, demo recording, next-week reprioritization.

## Week 1 (2026-02-23 to 2026-03-01): Information Architecture and Product Narrative

### Weekly Goal

Make the app structure explain the product clearly before any deep interaction.

### Deliverables

- [ ] New top-level nav model: `Build`, `Run`, `Validate`, `Compare`, `Certify`, `Export`.
- [ ] Home/landing workspace with "what this product does" and "start here" states.
- [ ] UI copy system for labels, helper text, status text, and empty states.
- [ ] Design token baseline (color, type, spacing, depth, motion timing).

### Day Plan

- [ ] Mon: define IA v1 and route map; freeze labels and terminology.
- [ ] Tue: implement app-shell layout and route skeletons.
- [ ] Wed: implement landing workspace and contextual quick actions.
- [ ] Thu: responsive pass (desktop + laptop + tablet) and empty-state pass.
- [ ] Fri: 5-person comprehension test; update based on confusion logs.

### Acceptance Gate

- [ ] 80% of test users can explain "what PhotonTrust does" in one sentence after 60 seconds.
- [ ] No dead-end screens in primary nav.

## Week 2 (2026-03-02 to 2026-03-08): Guided Time-to-Value Flow

### Weekly Goal

Get first-time users to first credible result in under 10 minutes.

### Deliverables

- [ ] Guided setup wizard (`goal -> template -> params -> preflight -> run`).
- [ ] Scenario starter cards with confidence notes.
- [ ] Preflight guardrails for missing/invalid inputs.
- [ ] Progress timeline with clear status and recoverable errors.

### Day Plan

- [ ] Mon: define guided-flow state machine and abandonment points.
- [ ] Tue: build wizard steps and state persistence.
- [ ] Wed: add preflight checks and targeted recovery hints.
- [ ] Thu: add run timeline and post-run next-step actions.
- [ ] Fri: usability test with first-time users; tune friction points.

### Acceptance Gate

- [ ] Median `time_to_first_credible_result_min <= 10`.
- [ ] Guided-flow completion rate `>= 85%`.

## Week 3 (2026-03-09 to 2026-03-15): Graph Studio Professionalization

### Weekly Goal

Make advanced graph editing fast, predictable, and explainable.

### Deliverables

- [ ] Split monolithic `App.jsx` into feature modules.
- [ ] Schema-aware node inspector with typed controls.
- [ ] Smart palette with metadata, capability filters, and recommended blocks.
- [ ] Connection assistant (port/domain hints, conflict reasons, quick-fix prompts).
- [ ] Keyboard and command shortcuts for power users.

### Day Plan

- [ ] Mon: refactor plan; isolate graph state and side effects.
- [ ] Tue: extract feature modules (`palette`, `canvas`, `inspector`, `actions`).
- [ ] Wed: implement typed inspector and validation hints.
- [ ] Thu: implement shortcuts and productivity interactions.
- [ ] Fri: task-speed benchmark (expert and non-expert).

### Acceptance Gate

- [ ] Build/edit task success `>= 90%`.
- [ ] P95 node edit interaction under 200 ms perceived latency.

## Week 4 (2026-03-16 to 2026-03-22): Results Intelligence and Decision UX

### Weekly Goal

Replace raw-output reading with decision-oriented interpretation.

### Deliverables

- [ ] Results cockpit with KPI cards and explicit pass/caution/fail states.
- [ ] Confidence and uncertainty bands in visual summaries.
- [ ] "What changed?" panel from previous/baseline run.
- [ ] Recommended next actions with rationale.

### Day Plan

- [ ] Mon: define decision schema and thresholds for UI messaging.
- [ ] Tue: implement KPI cards and status semantics.
- [ ] Wed: implement uncertainty and delta visual layers.
- [ ] Thu: implement recommendation engine UI copy and action buttons.
- [ ] Fri: reviewer trial focused on "approve/reject" speed.

### Acceptance Gate

- [ ] `run_to_decision_time_min <= 5`.
- [ ] 90% reviewer agreement with displayed recommendation category.

## Week 5 (2026-03-23 to 2026-03-29): Trust, Provenance, and Certification Experience

### Weekly Goal

Expose trust posture and certification readiness as first-class UI surfaces.

### Deliverables

- [ ] Provenance timeline (`input -> compile -> run -> artifacts -> signoff`).
- [ ] Certification readiness checklist with blocking issues.
- [ ] Approval UI for reviewer workflow.
- [ ] Packet builder UX with downloadable evidence bundle.

### Day Plan

- [ ] Mon: define trust data model and visual narrative.
- [ ] Tue: implement provenance timeline and linked artifacts.
- [ ] Wed: implement readiness checklist and blocker callouts.
- [ ] Thu: implement approval actions and packet export flow.
- [ ] Fri: mock audit walkthrough and gap closure.

### Acceptance Gate

- [ ] Users can locate provenance and trust blockers in under 2 minutes.
- [ ] Certification packet generated in <= 2 clicks from completed run.

## Week 6 (2026-03-30 to 2026-04-05): Team Workflow and Enterprise Feel

### Weekly Goal

Make the UI feel like a collaborative product platform, not a single-user tool.

### Deliverables

- [ ] Workspace context (`project switch`, `saved views`, `recent activity`).
- [ ] Run collections and semantic tags.
- [ ] Dedicated compare lab (multi-run and baseline-candidate framing).
- [ ] Role-specific view presets (`Builder`, `Reviewer`, `Exec`).

### Day Plan

- [ ] Mon: define workspace and role model in UI.
- [ ] Tue: implement collections/tags and view state persistence.
- [ ] Wed: implement compare lab interactions and summary exports.
- [ ] Thu: implement role presets and onboarding shortcuts.
- [ ] Fri: team simulation test with 3-role script.

### Acceptance Gate

- [ ] Team scenario demo completes without switching to CLI.
- [ ] Zero critical UX blockers in role-based flows.

## Week 7 (2026-04-06 to 2026-04-12): Pitch Mode and Visual Distinction

### Weekly Goal

Make product differentiation obvious in a 7-minute live demo.

### Deliverables

- [ ] Guided demo mode with locked narrative sequence.
- [ ] Curated "proof screens" (`benchmark`, `trust`, `decision`, `packet`).
- [ ] Motion and hierarchy polish pass for presentation quality.
- [ ] Demo-safe fallback states for API/network issues.

### Day Plan

- [ ] Mon: define demo narrative script and scene map.
- [ ] Tue: implement demo mode routing and state orchestration.
- [ ] Wed: build proof screens and narrative transitions.
- [ ] Thu: implement offline/degraded-mode handling.
- [ ] Fri: run 10 timed demo reps; resolve friction and ambiguity.

### Acceptance Gate

- [ ] `investor_demo_completion_rate >= 95%`.
- [ ] Demo can run end-to-end with no operator code edits.

## Week 8 (2026-04-13 to 2026-04-19): Hardening, Accessibility, and Release Candidate

### Weekly Goal

Convert polished UI into release-ready UI.

### Deliverables

- [ ] Accessibility pass (focus order, keyboard navigation, contrast).
- [ ] Performance pass (bundle, interaction latency, rendering hotspots).
- [ ] Error/empty/loading state completeness pass.
- [ ] UI regression suite and final release checklist.
- [ ] UI runbook for operator and demo owner.

### Day Plan

- [ ] Mon: execute full UX + QA checklist and defect triage.
- [ ] Tue: fix P0/P1 defects and update tests.
- [ ] Wed: performance and accessibility hardening.
- [ ] Thu: release-candidate smoke tests and rollback plan.
- [ ] Fri: final signoff meeting and RC tag recommendation.

### Acceptance Gate

- [ ] No open P0 UX issues.
- [ ] Critical flow keyboard coverage `>= 90%`.
- [ ] RC smoke run passes for all persona-critical workflows.

## Weekly KPI Scorecard Template

Copy this block each Friday:

```
week_of:
time_to_first_credible_result_min:
guided_flow_task_success_rate:
run_to_decision_time_min:
critical_ui_error_recovery_rate:
investor_demo_completion_rate:
a11y_keyboard_coverage:
top_3_failures:
actions_next_week:
```

## Risk Register (UI Program)

- Risk: over-polish before flow clarity.
  - Mitigation: no visual polish tasks before each weekly flow gate passes.
- Risk: feature sprawl and incoherent UX.
  - Mitigation: strict weekly scope lock and Friday de-scope protocol.
- Risk: trust story remains buried in technical tabs.
  - Mitigation: trust/provenance indicators mandatory in all result surfaces.
- Risk: monolithic UI slows delivery.
  - Mitigation: Week 3 modular refactor is mandatory exit criterion.
- Risk: demo fragility under unstable API.
  - Mitigation: Week 7 degraded-mode and deterministic demo states.

## Exit Criteria (Program Complete)

- [ ] All north-star targets met.
- [ ] Persona-critical workflows pass without founder intervention.
- [ ] UI demonstrates product value, trustworthiness, and decision readiness on its own.
- [ ] Board artifacts and metrics are present and reproducible from repo state.

## Enterprise Execution Package (added 2026-02-19)

This board is now backed by an enterprise operating system and delivery artifacts:

- Program governance and controls: `docs/operations/product/ui_enterprise_program_operating_system_2026-02-19.md`
- Gap baseline and delivery backlog: `docs/operations/product/ui_execution_gap_backlog_2026-02-19.md`
- Research and telemetry blueprint: `docs/operations/product/ui_research_telemetry_blueprint_2026-02-19.md`
- RAID tracker: `docs/operations/product/ui_raid_log_2026-02-19.md`
- Weekly scorecard template: `docs/operations/product/ui_weekly_scorecard_template_2026Q1.yaml`
- Weekly decision packet template: `docs/operations/product/ui_weekly_decision_packet_template_2026-02-19.md`
- Week 1 owner execution plan: `docs/operations/product/ui_week1_owner_plan_2026-02-23.md`
- Week 2 progress update: `docs/operations/product/ui_week2_progress_update_2026-02-19.md`

Program usage rule:

- Monday: update scope, RAID, and week backlog.
- Thursday: run quality gates and defect triage against week acceptance criteria.
- Friday: publish scorecard and decision packet, then record `GO`, `GO-WITH-CONDITIONS`, or `NO-GO`.

Baseline status from current code audit:

- Week status: Week 1 partial, Week 2 missing, Week 3 partial, Week 4 partial, Week 5 partial, Week 6 partial, Week 7 missing, Week 8 partial.
- Highest-risk blockers: guided flow is missing, telemetry governance is incomplete, and modularization of `web/src/App.jsx` is still pending.

## In-flight Product UI Update (2026-02-19b)

The web UI was advanced with a multi-agent implementation pass focused on Week 4 through Week 8 execution risk.

- Week 4 progress: decision-oriented run surfaces are now present in the UI via `DecisionCockpit`, confidence/uncertainty surfacing, and recommendation-driven next actions.
- Week 5 progress: provenance and certification surfaces were added (`ProvenanceTimeline`, `CertificationWorkspace`) and wired to approvals and packet export flows.
- Week 6 progress: compare framing now supports explicit `baseline` vs `candidate` semantics, and workspace-level saved view presets plus recent activity feed are available.
- Week 7 progress: guided demo orchestration is now available through a locked narrative scene runner with degraded-mode messaging.
- Week 8 hardening progress: keyboard activation parity was improved for palette interactions, status live-region support was added, modal focus trap behavior was added, and high-cost JSON key re-renders were removed.

Remaining critical path:

- `web/src/App.jsx` modular decomposition is still required to fully satisfy Week 3 and remove delivery drag.
- Team workflow depth (collections/tags and richer role presets) remains partial.
- Full accessibility coverage and formal UI regression automation still need expansion for final RC gating.

## Continuation Update (2026-02-19c)

Additional continuation work was completed with parallel agent execution:

- Week 6 depth advanced: run collections and semantic run tags were added with baseline/candidate controls and local persistence (`web/src/state/runCollectionsState.js`, `web/src/features/workspace/RunCollectionsPanel.jsx`).
- Week 6 role/workspace controls advanced: workspace context bar now exposes project switching, role presets, saved views, and recent activity (`web/src/features/workspace/WorkspaceContextBar.jsx`).
- Week 8 hardening advanced: common UI primitives were extracted (`web/src/components/common/JsonBox.jsx`, `web/src/components/common/Modal.jsx`) to reduce monolithic coupling and improve reuse.
- Week 8 regression lane added: Playwright smoke + keyboard tests were introduced and passing (`web/tests/ui.smoke.spec.js`, `web/tests/ui.a11y.spec.js`, `web/playwright.config.js`).

Current status note:

- The UI still requires deeper decomposition of `web/src/App.jsx` into feature-container composition to fully close Week 3 maintainability risk, but release hardening confidence increased due to runnable UI checks.

## Continuation Update (2026-02-19d)

Refactor completion and validation updates from the next continuation cycle:

- Completed replacement of inline run manifest and run diff right-rail sections in `web/src/App.jsx` with extracted feature modules (`web/src/features/runs/ManifestPanel.jsx`, `web/src/features/runs/DiffPanel.jsx`).
- Completed replacement of inline kind trust panel implementation with shared feature module usage (`web/src/features/graph/KindTrustPanel.jsx`), including pretty-json helper wiring for `applies_when` readability parity.
- Removed now-unused inline helper code from `web/src/App.jsx` after extraction pass, reducing monolith surface area and duplicate logic.
- Regression validation status after refactor: `npm run lint` passed, `npm run build` passed, and `npm run test:ui` passed (8/8 Playwright tests).

Current status note:

- Week 3 decomposition risk is reduced but not fully closed: `web/src/App.jsx` remains orchestration-heavy and still needs deeper container/page decomposition in a follow-on pass.

## Continuation Update (2026-02-19e)

Parallel-agent modularization continued and closed another extraction tranche:

- Added new reusable shell modules and integrated them into `web/src/App.jsx`:
  - `web/src/features/shell/CenterWorkspacePane.jsx` (graph/orbit/runs center-pane rendering boundary).
  - `web/src/features/shell/StatusFooter.jsx` (status and runtime summary footer).
  - `web/src/features/shell/GraphJsonModals.jsx` (export/import graph JSON modal pair).
- Added approval form module and removed duplicate inline approval form blocks:
  - `web/src/features/runs/ApprovalControls.jsx`.
- App-shell cleanup from this pass:
  - Removed direct `ReactFlow`/`Background`/`Controls`/`MiniMap` JSX from `App.jsx` in favor of `CenterWorkspacePane` composition.
  - Removed direct modal JSX from `App.jsx` in favor of `GraphJsonModals` composition.
  - Consolidated duplicated run-approval control fragments behind `ApprovalControls`.
- Validation status after extraction:
  - `npm run lint` passed.
  - `npm run build` passed.
  - `npm run test:ui` passed (8/8).

Current status note:

- Week 3 modularization risk is further reduced and the render tree is now more componentized, but full closure still requires splitting the remaining large left/right sidebars into dedicated mode/page containers.

## Continuation Update (2026-02-19f)

Parallel-agent modularization was continued with sidebar composition cleanup:

- Added new modular sidebar primitives and integrated them into `web/src/App.jsx`:
  - `web/src/features/shell/RightSidebarTabs.jsx` (mode-aware right-rail tab strip).
  - `web/src/features/orbit/OrbitConfigPanel.jsx` (orbit config preview/copy panel for the right rail).
- Replaced remaining inline right-rail tab-selector and orbit-config tab body blocks in `web/src/App.jsx` with these dedicated feature components.
- Validation status after this extraction pass:
  - `npm run lint` passed.
  - `npm run build` passed.
  - `npm run test:ui` passed (8/8).

Current status note:

- Week 3 modularization remains in progress but has crossed another boundary: center pane, footer/modals, tab strip, orbit config panel, manifest/diff panels, and trust panel are now modularized; remaining major extraction target is the large mode-specific left/right content bodies still hosted in `web/src/App.jsx`.

## Continuation Update (2026-02-19g)

Parallel-agent completion pass delivered Week 7/8 closure items plus additional Week 3 reduction:

- Week 7 demo orchestration hardening:
  - Demo scenes are now wired to deterministic app state transitions (`benchmark -> trust -> decision -> packet`) with explicit stage/mode/tab mapping in `web/src/App.jsx`.
  - Demo mode now locks disruptive controls during narration and restores prior workspace context on exit.
  - Added curated proof snapshot fallback surface for demo continuity under degraded API conditions via `web/src/features/demo/DemoProofSnapshot.jsx`.
  - Added demo regression coverage in `web/tests/ui.demo.spec.js` for scene progression and lock/unlock behavior.
- Week 8 accessibility and regression hardening:
  - Added ARIA tab semantics for right-rail tabs in `web/src/features/shell/RightSidebarTabs.jsx`.
  - Added dialog title association (`aria-labelledby`) in `web/src/components/common/Modal.jsx`.
  - Added keyboard/a11y regression for right-rail tab semantics in `web/tests/ui.a11y.spec.js`.
- Week 3 modularization follow-through:
  - Extracted runs-mode left sidebar into `web/src/features/runs/RunsSidebarPanel.jsx` and integrated in `web/src/App.jsx`.

Validation status after this cycle:

- `npm run lint` passed.
- `npm run build` passed.
- `npm run test:ui` passed (11/11).

Current status note:

- Week 7 demo-flow closure is now materially complete for operator narrative control.
- Week 8 regression/a11y coverage is significantly stronger and passing in CI-style local runs.
- Remaining non-blocker: bundle-size warning persists and deeper `App.jsx` decomposition is still recommended for long-term maintainability.

## Continuation Update (2026-02-19h)

Final modularization closure pass completed with parallel-agent execution:

- Week 3 modularization completion:
  - Extracted top application header into `web/src/features/shell/AppTopBar.jsx` and integrated in `web/src/App.jsx`.
  - Extracted left-rail mode switch composition into `web/src/features/shell/LeftSidebarByMode.jsx` with dedicated panels:
    - `web/src/features/graph/GraphLeftSidebarPanel.jsx`
    - `web/src/features/orbit/OrbitLeftSidebarPanel.jsx`
    - `web/src/features/runs/RunsSidebarPanel.jsx`
  - Extracted graph right-rail tab bodies into `web/src/features/graph/GraphRightSidebarContent.jsx` and removed remaining duplicated inline graph-tab JSX from `web/src/App.jsx`.
  - Extracted run-tab body into `web/src/features/results/RunModePanel.jsx` and orbit-validate body into `web/src/features/orbit/OrbitValidatePanel.jsx`.
- Week 8 sustainment hardening in same pass:
  - Preserved full UI regression coverage while refactoring (`web/tests/ui.demo.spec.js`, `web/tests/ui.a11y.spec.js`, smoke/workspace suites).

Validation status after final pass:

- `npm run lint` passed.
- `npm run build` passed.
- `npm run test:ui` passed (11/11).

Current status note:

- Week 3 modular decomposition objective is now satisfied for this program cycle; `web/src/App.jsx` is operating as an orchestration shell with feature-container composition.
- Remaining non-blocker: build chunk-size warning persists and can be addressed in a separate performance/code-splitting optimization lane.
