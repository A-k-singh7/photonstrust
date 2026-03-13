# UI Clarity Redesign Plan (2026-03-12)

## Goal

Turn the React product surface from a capable internal workbench into a clear,
credible self-serve product experience.

## Core Problem Statement

The current UI exposes real power, but the first-run experience is too dense and
 too implementation-shaped.

Observed issues:

1. The first screen leads with controls before it explains value.
2. Landing, guidance, context, and shell chrome compete for attention.
3. Advanced state concepts are exposed too early (`mode`, `graph_id`, saved
   views, raw tabs, manifest scope).
4. The interface does not clearly justify the strongest product capabilities in
   user language.
5. Compare/certify/export feel like separate panels instead of one decision
   journey.

## Product Principles

1. Guided mode should feel calm, obvious, and spacious.
2. Power mode should feel deep, but organized and intentional.
3. The UI should lead with outcomes, not implementation terms.
4. Every major visible control should justify itself through a user job.
5. The first-run path should make the product promise clear within 5 seconds.

## Jobs To Be Done

### Newcomer jobs

1. Simulate a QKD link and understand the result.
2. Generate a PIC layout and export a GDS artifact.
3. Compare two candidates and see why one is better.
4. Certify, approve, and export evidence for a decision.

### Expert jobs

1. Jump directly to advanced controls.
2. Inspect manifests, diffs, GDS-derived artifacts, and workflow lineage.
3. Replay or publish evidence without losing context.

## North-Star Information Architecture

### Guided mode

1. Start
2. Simulate
3. Compare
4. Decide
5. Export

### Power mode

1. Build and simulate
2. PIC and GDS
3. Orbit and satellite
4. Runs and compare
5. Certify and evidence
6. Advanced diagnostics

## Capability Framing That Must Be Visible

The UI should explicitly explain that PhotonTrust can:

1. simulate QKD links,
2. generate PIC layout artifacts and GDS,
3. analyze orbit and satellite scenarios,
4. compare candidates against baselines,
5. certify, approve, publish, and verify evidence bundles.

## Redesign Phases

### Phase 0: Entry-Screen Declutter

Goal: reduce immediate overload without removing real capability.

Changes:

1. Simplify the top bar in guided mode.
2. Hide advanced setup behind an explicit reveal.
3. Remove duplicated start surfaces on the landing screen.
4. Rework the landing screen around outcomes and recommended paths.

Primary files:

- `web/src/features/shell/AppTopBar.jsx`
- `web/src/features/shell/LandingWorkspace.jsx`
- `web/src/features/shell/copy.js`
- `web/src/App.css`
- `web/src/App.jsx`

Acceptance criteria:

1. Guided first screen shows fewer controls than today.
2. Landing page has a single clear narrative and primary path.
3. Advanced controls remain available without breaking existing flows.

### Phase 1: Workspace Clarity

Goal: make the main shell easier to scan once the user enters the workspace.

Changes:

1. Reduce density in the workspace context bar.
2. Move secondary context and recent activity lower in the hierarchy.
3. Clarify stage labels and action hierarchy.

Primary files:

- `web/src/features/workspace/WorkspaceContextBar.jsx`
- `web/src/features/shell/GuidanceStrip.jsx`
- `web/src/App.css`

Acceptance criteria:

1. The shell clearly shows where the user is and what to do next.
2. The context bar no longer feels like a second top bar.

### Phase 2: Decision Flow Cohesion

Goal: make compare, certify, publish, and export feel like one connected flow.

Changes:

1. Reframe compare output around decision questions.
2. Reframe manifest/certify around trust posture, approvals, and next actions.
3. Present evidence and publish/verify as the last step of the same workflow.

Primary files:

- `web/src/features/compare/CompareLabPanel.jsx`
- `web/src/features/runs/ManifestPanel.jsx`
- `web/src/features/certify/CertificationWorkspace.jsx`
- `web/src/features/results/*`

Acceptance criteria:

1. A user can understand the baseline vs candidate story quickly.
2. Approval and packet actions feel like the natural end of the flow.

### Phase 3: Power Mode and Expert Surfacing

Goal: preserve depth while keeping the product approachable.

Changes:

1. Group advanced JSON/config surfaces more deliberately.
2. Move rarely used expert operations into explicit advanced sections.
3. Keep parity with backend capability without exposing every internal concept at once.

## Copy and Language Rules

1. Prefer user language over implementation language.
2. Prefer action labels over object labels.
3. Use internal terms only when they provide genuine expert value.

Examples:

- `Profile` -> keep for experts, explain in context
- `graph_id` -> advanced only
- `Manifest` -> pair with trust or evidence framing
- `Diff scope` -> explain in compare context, not on landing

## Metrics For Success

1. Less first-screen visual density.
2. Clearer primary action on landing.
3. Faster newcomer orientation.
4. Fewer advanced controls visible before the user asks for them.
5. No regression in the existing Playwright workflow coverage.

## Immediate Execution Order

1. Implement Phase 0 now.
2. Validate build + targeted UI tests.
3. Continue with Phase 1 after reviewing the new shell density.
