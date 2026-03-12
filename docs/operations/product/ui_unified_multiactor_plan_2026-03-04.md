# Unified UI Multi-Agent Implementation Plan (2026-03-04)

## Objective
- Build a simple, intuitive UI that serves both newcomers and experienced users while representing the full PhotonTrust platform surface.
- Keep fail-closed governance visibility intact (gate status, evidence integrity, provenance, approvals).
- Ship incrementally with measurable outcomes, no big-bang rewrite.

## Current State Snapshot
- Streamlit workbench in `ui/app.py` is feature-rich and practical for operations but dense for first-time users.
- React web workspace in `web/src/App.jsx` is powerful but currently uses mode/state-driven navigation that is hard to share/bookmark.
- API contracts are strong in breadth (`photonstrust/api/server.py` + `web/src/photontrust/api.js`) but UX semantics are not yet unified between surfaces.
- Key onboarding friction: jargon density, deep controls exposed too early, and occasional results-path mismatch between API run roots and local registry views.

## Product UX Strategy
- Dual-mode experience:
  - Guided Mode: task-first, opinionated defaults, progressive disclosure, contextual help.
  - Power Mode: full controls, advanced diagnostics, CLI parity and fast-path operations.
- Canonical information architecture (same mental model across Streamlit and web):
  1. Home
  2. Build and Simulate
  3. PIC and Tapeout
  4. Orbit and Satellite
  5. Runs and Compare
  6. Governance and Readiness
  7. Evidence and Compliance
  8. Data and Benchmarks
  9. Settings and Help

## Capability Coverage Matrix (What UI Must Represent)
- QKD simulation and reliability cards.
- Graph authoring, validation, compilation, and hash/provenance tracking.
- PIC simulation, inverse design, layout/verification, foundry summaries, and tapeout readiness.
- Satellite/orbit digital twin lanes, sweeps, and optimizer outputs.
- Compliance/certify/release/production readiness checks.
- Evidence bundles, signatures, digest lookup, and verification status.
- Run registry, compare/baseline promotion, and decision packet drill-downs.
- Measurement ingestion, artifact packs, benchmark drift/validation.

## Multi-Agent Topology
- Agent A: UX Research and Persona Agent
  - Outputs: persona pack, critical jobs-to-be-done, test scripts.
- Agent B: IA and Content Agent
  - Outputs: navigation map, labeling standards, in-app copy, glossary.
- Agent C: Web Frontend Agent
  - Outputs: route shell, guided/power mode components, responsive layouts.
- Agent D: Streamlit Experience Agent
  - Outputs: aligned onboarding surfaces, beginner rails, operator shortcuts.
- Agent E: API Contract and Integration Agent
  - Outputs: endpoint contract matrix, error model, parity mapping (UI <-> CLI).
- Agent F: Accessibility Agent
  - Outputs: WCAG checklist, keyboard/focus fixes, contrast and semantics validation.
- Agent G: QA and Test Automation Agent
  - Outputs: e2e suites, regression gates, smoke packs for key workflows.
- Agent H: Observability and Metrics Agent
  - Outputs: event taxonomy, dashboards, experiment and alert thresholds.
- Agent I: Docs and Enablement Agent
  - Outputs: quickstarts, role-based runbooks, in-product help references.
- Agent J: Release Orchestrator Agent
  - Outputs: timeline, dependency board, risk log, rollout/rollback decisions.

## Handoff Contracts
- UX -> FE: wireframes, interaction rules, and completion criteria per flow.
- IA -> FE/API: canonical flow IDs, route map, and command-to-screen mapping.
- API -> FE: versioned payload examples, error taxonomy, and fallback policy.
- FE -> QA: stable selectors, scenario fixtures, and expected-state snapshots.
- A11y -> FE/QA: pass/fail evidence per critical workflow.
- Metrics -> All: required event checklist is release-blocking.

## Execution Plan by Phase

### Phase 0 (Days 1-3): Baseline and Scope Lock
- Deliverables:
  - Current UX baseline audit (new vs experienced user lens).
  - Top 5 newcomer workflows and top 5 expert workflows.
  - Baseline telemetry dashboard (completion rate, time-to-first-success).
- Acceptance criteria:
  - Critical workflow list approved.
  - No unresolved scope ambiguities in phase backlog.

### Phase 1 (Days 4-10): Architecture and Contracts
- Deliverables:
  - Shared IA and route/state model.
  - Guided Mode and Power Mode interaction contract.
  - API contract mapping for all critical workflows.
- Acceptance criteria:
  - Contract review passed by FE/API/QA/A11y.

### Phase 2 (Weeks 3-4): Guided Mode MVP
- Deliverables:
  - Guided Home and Start Here flow.
  - Beginner rails for first successful run and first comparison decision.
  - Contextual glossary and help cues.
- Acceptance criteria:
  - New-user first-task success improves vs baseline.
  - No critical onboarding blockers in usability tests.

### Phase 3 (Weeks 5-6): Power Mode and Deep Coverage
- Deliverables:
  - Advanced controls grouped under explicit Expert surfaces.
  - CLI parity utilities and rapid replay actions.
  - Governance/readiness drill-down with hard-stop explanations.
- Acceptance criteria:
  - Expert task duration reduced vs baseline.
  - Cross-surface parity tests pass for critical lanes.

### Phase 4 (Weeks 7-8): Hardening and Rollout
- Deliverables:
  - Full e2e regression and accessibility signoff.
  - Updated docs and runbooks.
  - Feature-flagged staged rollout with rollback hooks.
- Acceptance criteria:
  - No P0/P1 defects open.
  - Telemetry guardrails green in staged rollout.

## Two-Week Sprint Plan (Immediate)

### Week 1
- Agent A/B: finalize personas, glossary, and guided narratives.
- Agent E/H: lock event schema and API error categories.
- Agent C/D: implement shell-level Guided/Power mode switch.
- Agent G/F: create first smoke tests for onboarding and keyboard navigation.

### Week 2
- Agent C/D: implement first two critical guided workflows end-to-end:
  - first run with interpretation,
  - baseline vs candidate compare decision.
- Agent E: unify response handling and user-facing diagnostics.
- Agent G/F: run usability + accessibility pass and file defects.
- Agent I/J: publish sprint report, update runbook, and stage phase-2 backlog.

## Metrics and Instrumentation
- Primary KPI: time-to-first-success (new users).
- Secondary KPIs:
  - workflow completion rate,
  - median time per workflow,
  - error recovery rate,
  - power-user shortcut adoption,
  - accessibility task pass rate.
- Required event set:
  - `flow_started`, `step_completed`, `validation_error`, `help_opened`,
  - `task_submitted`, `task_succeeded`, `task_failed`, `mode_switched`, `shortcut_used`.
- Alerts:
  - completion rate regression,
  - p95 latency spike,
  - error-rate spike,
  - accessibility regression in critical flows.

## Risk Controls
- Feature flags for each new major flow.
- Preserve legacy advanced paths until parity and adoption targets are met.
- Use deterministic acceptance tests for critical workflows before enabling by default.
- Weekly integration demo with stop/go gate and explicit rollback criteria.

## Definition of Done
- Beginner can complete first run + compare + decision flow without external help.
- Expert can reach advanced controls in <= 2 actions from main navigation.
- UI reflects all major platform domains with clear drill-down paths.
- CLI/API/UI parity is verified for critical workflows.
- Accessibility and telemetry gates pass.

## Phase 1 Kickoff Implementation Status
- Implemented Guided/Power experience switch in Streamlit sidebar with guided-first tab order and Start Here checklist.
- Implemented Guided/Power experience switch in web top bar with guided checklist + glossary strip and advanced tab gating in guided mode.
- Added shared glossary help surfaces for newcomer terminology in both Streamlit and web flows.
- Hardened Streamlit run registry card rendering path access to avoid nested-key crashes on partial cards.
