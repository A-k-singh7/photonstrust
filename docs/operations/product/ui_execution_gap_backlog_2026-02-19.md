# PhotonTrust UI Gap Baseline and Execution Backlog (2026-02-19)

This backlog translates `docs/operations/ui_8_week_execution_board_2026-02-19.md` into execution work items with ownership, dependencies, and KPI linkage.

## 1) Current-state architecture baseline

- `web/src/App.jsx` is a monolith containing all major state, orchestration, API interactions, and rendering concerns.
- Existing UI is engineering-strong (graph editing, run orchestration, approvals, artifacts, compare), but not yet aligned to the product journey model.
- Required modular feature surfaces (`web/src/features/*`, `web/src/components/*`, `web/src/state/*`, `web/src/styles/*`) are mostly missing.
- The UI telemetry contract defined in the board is not fully implemented as a governed event pipeline.

## 2) Week-by-week gap baseline

| Week | Board focus | Baseline status | What exists now | Primary gap to close |
| --- | --- | --- | --- | --- |
| Week 1 | IA and product narrative | Partial | Polished shell and tokenized styles | Missing `Build/Run/Validate/Compare/Certify/Export` nav and landing narrative |
| Week 2 | Guided time-to-value flow | Partial | Guided wizard shell and preflight flow are implemented | Complete abandonment analytics hardening and friction-tuning loop |
| Week 3 | Graph studio professionalization | Partial | Inspector, palette filters, connection constraints | Missing modular refactor and formal power-user command system |
| Week 4 | Results decision UX | Partial | Run outputs and diff calls exist | Missing decision cockpit, confidence layer, recommendation UX |
| Week 5 | Trust and certification UX | Partial | Approvals and artifact links exist | Missing provenance timeline and readiness checklist |
| Week 6 | Team workflow enterprise feel | Partial | Project and run browsing exists | Missing saved views, tags, role presets, compare lab framing |
| Week 7 | Pitch mode and visual distinction | Missing | No narrative-locked route mode | Missing demo mode orchestration and fallback script paths |
| Week 8 | Hardening and release candidate | Partial | Basic a11y affordances in controls | Missing formal a11y/perf regression gate and RC runbook |

## 3) Top-priority closure backlog (P0/P1)

| ID | Priority | Target week | Work item | KPI impact | Key dependencies | Planned touchpoints |
| --- | --- | --- | --- | --- | --- | --- |
| UI-001 | P0 | Week 1 | Introduce product IA shell and nav model (`Build`, `Run`, `Validate`, `Compare`, `Certify`, `Export`) | Value clarity, investor demo completion | Route map freeze | `web/src/App.jsx`, `web/src/features/shell/*` |
| UI-002 | P0 | Week 1 | Create landing workspace with product story and start actions | Value clarity, guided flow success | Copy and narrative approval | `web/src/features/shell/LandingWorkspace.jsx` |
| UI-003 | P0 | Week 2 | Implement guided flow wizard (`goal -> template -> params -> preflight -> run`) with persistence | Time to first credible result | State model and API preflight contracts | `web/src/features/guided-flow/*`, `web/src/state/guidedFlow.js` |
| UI-004 | P0 | Week 2 | Add recoverable preflight and run timeline with targeted hints | Error recovery rate, guided flow success | Error taxonomy and copy | `web/src/features/guided-flow/*`, `web/src/components/alerts/*` |
| UI-005 | P0 | Week 2 | Implement mandatory UI telemetry contract and event sink to `results/ui_metrics/events.jsonl` | All north-star KPI measurement | Event schema signoff | `web/src/state/uiTelemetry.js`, `scripts/` helper |
| UI-006 | P0 | Week 3 | Refactor monolithic `App.jsx` into feature modules (`palette`, `canvas`, `inspector`, `actions`) | Build/edit task success, delivery velocity | Architecture boundaries | `web/src/features/*`, `web/src/components/*` |
| UI-007 | P1 | Week 4 | Build results decision cockpit with status semantics and rationale | Run-to-decision time | KPI threshold definitions | `web/src/features/results/DecisionCockpit.jsx` |
| UI-008 | P1 | Week 4 | Add compare lab framing (`baseline` vs `candidate`) and decision summary export | Comparability, decision support | Run diff data quality | `web/src/features/compare/*` |
| UI-009 | P1 | Week 5 | Add provenance timeline and trust blocker surfacing | Trust and certification readiness | Provenance data map | `web/src/features/trust/ProvenanceTimeline.jsx` |
| UI-010 | P1 | Week 5 | Add certification readiness checklist and packet builder | Reproducibility, decision packet quality | Artifact map and checklist rubric | `web/src/features/certify/*`, `web/src/features/export/*` |
| UI-011 | P1 | Week 6 | Add role presets (`Builder`, `Reviewer`, `Exec`) and saved views | Team workflow completion rate | Workspace state model | `web/src/state/workspace.js`, `web/src/features/shell/*` |
| UI-012 | P0 | Week 7 | Implement guided demo mode with deterministic fallback for degraded API | Investor demo completion rate | Curated scenario fixtures | `web/src/features/demo/*`, `docs/operations/product/*` |

## 4) Critical path for Weeks 1-3

1. Freeze IA labels and route skeleton before adding any new feature surfaces.
2. Ship telemetry contract early in Week 2 so all subsequent UX changes are measurable.
3. Complete `App.jsx` modular decomposition in Week 3 to prevent Week 4-8 execution drag.

## 5) Planned structure for enterprise-ready UI modules

- `web/src/features/build/BuildPage.jsx`
- `web/src/features/run/RunPage.jsx`
- `web/src/features/validate/ValidatePage.jsx`
- `web/src/features/compare/ComparePage.jsx`
- `web/src/features/certify/CertifyPage.jsx`
- `web/src/features/export/ExportPage.jsx`
- `web/src/features/guided-flow/GuidedFlowWizard.jsx`
- `web/src/features/guided-flow/wizardMachine.js`
- `web/src/features/results/DecisionCockpit.jsx`
- `web/src/features/trust/ProvenanceTimeline.jsx`
- `web/src/state/uiTelemetry.js`
- `web/src/styles/tokens.css`
- `web/src/styles/layers.css`

## 6) In-flight update (2026-02-19)

- Backend telemetry ingestion endpoint shipped at `POST /v0/ui/telemetry/events` with JSONL persistence to `results/ui_metrics/events.jsonl`.
- Week 2 guided wizard path shipped with explicit stages (`goal -> template -> params -> preflight -> run`).
- Remaining Week 2 work is now optimization and conversion-rate tuning, not foundational scaffolding.

## 7) Execution update (2026-02-19b)

Delivered in current UI increment:

- `UI-007` (Week 4): decision cockpit, confidence/uncertainty layer, and recommendation next-actions were added to the run surface.
  - New modules: `web/src/features/results/DecisionCockpit.jsx`, `web/src/features/results/ConfidenceUncertaintyLayer.jsx`, `web/src/features/results/RecommendationNextActions.jsx`.
- `UI-008` (Week 4/6): compare lab framing now uses baseline/candidate semantics via `web/src/features/compare/CompareLabPanel.jsx`.
- `UI-009` (Week 5): provenance timeline module added at `web/src/features/trust/ProvenanceTimeline.jsx`.
- `UI-010` (Week 5): certification workspace and packet/approval framing added at `web/src/features/certify/CertificationWorkspace.jsx`.
- `UI-011` (Week 6 partial): workspace preset and activity state helpers added at `web/src/state/workspaceState.js` and wired in app shell controls.
- `UI-012` (Week 7 partial): demo orchestration scaffold added at `web/src/features/demo/DemoModeOrchestrator.jsx` with degraded-mode messaging.

Hardening improvements completed in the same pass:

- Added style token/layer files (`web/src/styles/tokens.css`, `web/src/styles/layers.css`) and imported them in `web/src/main.jsx`.
- Added keyboard parity for palette item activation (`Enter` and `Space`) and stage lock behavior during demo mode.
- Added status live-region support and modal focus trap behavior.
- Removed expensive `JSON.stringify(...)` key patterns from JsonBox call sites to reduce avoidable remount/render pressure.

## 8) Continuation update (2026-02-19c)

Delivered in this continuation cycle:

- Week 6 workflow depth (partial closure):
  - Added run collection and tag persistence helper module: `web/src/state/runCollectionsState.js`.
  - Added run-collections control surface: `web/src/features/workspace/RunCollectionsPanel.jsx`.
  - Added workspace context bar with role presets/project/view/activity controls: `web/src/features/workspace/WorkspaceContextBar.jsx`.
- Week 8 maintainability hardening:
  - Added reusable common components: `web/src/components/common/JsonBox.jsx`, `web/src/components/common/Modal.jsx` and integrated app usage.
- Week 8 regression lane enablement:
  - Added Playwright config and tests: `web/playwright.config.js`, `web/tests/ui.smoke.spec.js`, `web/tests/ui.a11y.spec.js`.
  - Added UI test scripts in `web/package.json` and usage notes in `web/tests/README.md`.
  - Current run status: `npm run test:ui` passes.

## 9) Continuation update (2026-02-19d)

Delivered in this continuation cycle:

- Week 3 modularization follow-through:
  - Replaced inlined manifest panel section in `web/src/App.jsx` with `web/src/features/runs/ManifestPanel.jsx` composition.
  - Replaced inlined diff panel section in `web/src/App.jsx` with `web/src/features/runs/DiffPanel.jsx` composition.
  - Replaced local inline kind trust panel definition with imported module usage from `web/src/features/graph/KindTrustPanel.jsx`.
- Monolith hygiene:
  - Removed duplicate inline trust-panel implementation and obsolete violation helper functions from `web/src/App.jsx`.
  - Removed obsolete unused callback (`applyKlayoutPackSettingsText`) after extracted panel wiring.
- Regression and release checks:
  - `npm run lint`: pass.
  - `npm run build`: pass (non-blocking bundle-size warning remains).
  - `npm run test:ui`: pass (8/8).

Open item after this cycle:

- `UI-006` is still partial: `web/src/App.jsx` is now less duplicated but remains large and should be split further into route/page containers plus feature-level state boundaries.

## 10) Continuation update (2026-02-19e)

Delivered in this continuation cycle:

- Week 3 modularization follow-through (render-boundary extraction):
  - Added `web/src/features/shell/CenterWorkspacePane.jsx` and replaced inlined center-pane mode rendering in `web/src/App.jsx`.
  - Added `web/src/features/shell/StatusFooter.jsx` and replaced inlined status footer rendering in `web/src/App.jsx`.
  - Added `web/src/features/shell/GraphJsonModals.jsx` and replaced inlined graph import/export modal rendering in `web/src/App.jsx`.
- Duplicate-control cleanup:
  - Added `web/src/features/runs/ApprovalControls.jsx` and replaced duplicated approval-control JSX fragments used by `CertificationWorkspace` and `ManifestPanel` integration points in `web/src/App.jsx`.
- Monolith hygiene impact:
  - Removed additional duplicate UI markup from `web/src/App.jsx` and reduced direct rendering responsibilities for center/workspace/footer/modal surfaces.
- Regression and release checks:
  - `npm run lint`: pass.
  - `npm run build`: pass (bundle-size warning remains non-blocking).
  - `npm run test:ui`: pass (8/8).

Open item after this cycle:

- `UI-006` remains partial but improved: remaining closure work is extraction of large mode-specific sidebar trees into dedicated page/container components to reduce orchestration density in `web/src/App.jsx`.

## 11) Continuation update (2026-02-19f)

Delivered in this continuation cycle:

- Week 3 modularization follow-through (sidebar boundary extraction):
  - Added `web/src/features/shell/RightSidebarTabs.jsx` and replaced inlined right-rail tab selector rendering in `web/src/App.jsx`.
  - Added `web/src/features/orbit/OrbitConfigPanel.jsx` and replaced inlined orbit-config right-tab body rendering in `web/src/App.jsx`.
- Monolith hygiene impact:
  - Reduced additional inlined conditional JSX in `web/src/App.jsx` and moved mode-aware tab/preview concerns into dedicated feature modules.
- Regression and release checks:
  - `npm run lint`: pass.
  - `npm run build`: pass (bundle-size warning remains non-blocking).
  - `npm run test:ui`: pass (8/8).

Open item after this cycle:

- `UI-006` remains partial but materially advanced: the remaining high-volume extraction target is decomposition of mode-specific left/right detail bodies (especially graph editor right-rail content) into dedicated container components.

## 12) Continuation update (2026-02-19g)

Delivered in this continuation cycle:

- Week 7 closure-oriented demo mode upgrades:
  - Added deterministic scene-to-stage orchestration in `web/src/App.jsx` for `benchmark`, `trust`, `decision`, and `packet` demo scenes.
  - Added demo-safe interaction lock behavior (top controls, workspace controls, and main surface interaction lock while demo mode is active) with state restore on exit.
  - Added curated proof fallback panel for degraded mode continuity: `web/src/features/demo/DemoProofSnapshot.jsx`.
  - Added demo regression tests: `web/tests/ui.demo.spec.js`.
- Week 8 accessibility/regression upgrades:
  - Added ARIA tablist/tab semantics and tab-panel linkage support: `web/src/features/shell/RightSidebarTabs.jsx` and right-panel ids in `web/src/App.jsx`.
  - Added accessible dialog title linkage in `web/src/components/common/Modal.jsx`.
  - Extended a11y test coverage for right-rail tab semantics in `web/tests/ui.a11y.spec.js`.
- Week 3 modularization follow-through:
  - Added `web/src/features/runs/RunsSidebarPanel.jsx` and replaced inlined runs-mode left sidebar sections in `web/src/App.jsx`.
  - Added workspace context-bar global disable support for locked demo mode in `web/src/features/workspace/WorkspaceContextBar.jsx`.

Regression and release checks:

- `npm run lint`: pass.
- `npm run build`: pass (bundle-size warning remains non-blocking).
- `npm run test:ui`: pass (11/11).

Open item after this cycle:

- `UI-006` remains partially open but near-closed: primary remaining extraction hotspot is the graph inspect/compile/run right-rail body in `web/src/App.jsx`.

## 13) Continuation update (2026-02-19h)

Delivered in this continuation cycle:

- Week 3 modularization closure:
  - Added `web/src/features/shell/AppTopBar.jsx` and replaced inlined top-header controls in `web/src/App.jsx`.
  - Added `web/src/features/shell/LeftSidebarByMode.jsx` and extracted mode-specific left rail into:
    - `web/src/features/graph/GraphLeftSidebarPanel.jsx`
    - `web/src/features/orbit/OrbitLeftSidebarPanel.jsx`
    - `web/src/features/runs/RunsSidebarPanel.jsx` (reused).
  - Added `web/src/features/graph/GraphRightSidebarContent.jsx` and replaced remaining graph right-tab inlined bodies in `web/src/App.jsx`.
  - Added `web/src/features/results/RunModePanel.jsx` and replaced the inlined `mode !== runs` run-tab body in `web/src/App.jsx`.
  - Added `web/src/features/orbit/OrbitValidatePanel.jsx` and replaced inlined orbit validation tab body in `web/src/App.jsx`.
- Monolith hygiene impact:
  - Removed additional duplicated UI logic from `web/src/App.jsx` and converted app shell to feature-first composition.
- Regression and release checks:
  - `npm run lint`: pass.
  - `npm run build`: pass (bundle-size warning remains non-blocking).
  - `npm run test:ui`: pass (11/11).

Status after this cycle:

- `UI-006` is considered closed for this execution board: the monolithic render surface has been decomposed into feature containers and reusable panels.
