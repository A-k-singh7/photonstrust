# Phase 35 - Workflow Replay + Evidence Bundle Export - Research Brief

## Metadata
- Work item ID: PT-PHASE-35
- Date: 2026-02-14
- Scope: Add replay + portable evidence bundles for chained PIC workflows, plus run-to-run linking UX in the Run Browser.

## Problem Statement
PhotonTrust now supports a chained PIC workflow run (Phase 34):
`invdesign -> layout -> LVS-lite -> (optional) KLayout pack -> SPICE export`

However, a "trustable platform" needs two additional properties:
1. **Portable review**: reviewers and partners must be able to download a single bundle containing the evidence artifacts for offline inspection and archival.
2. **Replayability**: a chained workflow should be re-runnable from its recorded request inputs, producing a new workflow run whose provenance explicitly links back to the prior run.

Without these:
- evidence review requires clicking multiple served links and manually stitching context,
- provenance chains are harder to audit ("which runs belong together?"),
- and it is harder to build an academic/open-science flywheel because papers and labs expect portable artifact packs.

## Research Findings (What "Trust" Looks Like in Practice)
In real engineering review, the strongest evidence is:
- complete enough to reproduce or independently validate key outputs,
- captured with explicit tool provenance,
- and packaged in a way that survives being moved between machines/teams.

Common patterns across scientific computing and EDA-adjacent workflows:
- Produce a single “artifact bundle” for review/archival (often a zip/tarball).
- Include a machine-readable manifest that lists included files and hashes.
- Provide a replay mechanism that regenerates the same evidence from the recorded request.

PhotonTrust already has the right building blocks:
- per-run `run_manifest.json` with stable artifact relpaths,
- safe artifact resolution under a run directory (`run_store.resolve_artifact_path`),
- and strict external-tool seams (KLayout/ngspice are optional and must not create non-auditable behavior).

## Trust + Safety Constraints (Non-Negotiables)
- Evidence bundles must not allow arbitrary filesystem reads:
  - only include files that are under run directories and referenced by manifests/reports.
- Bundles should be deterministic enough for hashing and diffing:
  - stable file ordering, stable zip metadata where feasible, and a bundle manifest with per-file sha256.
- Replay must not allow arbitrary execution:
  - replay uses stored workflow request JSON and runs the same trusted code paths as normal API calls.
- Provenance linking must be explicit:
  - replayed runs record `replayed_from_run_id` (parent workflow run).

## Outcome (Phase 35)
PhotonTrust becomes more "review-grade":
- `GET /v0/runs/{run_id}/bundle` exports a single evidence bundle (zip) for any run, and (by default) includes workflow child runs when the root run is a workflow.
- `POST /v0/pic/workflow/invdesign_chain/replay` replays a prior workflow run from recorded inputs, producing a new workflow run and linking provenance.
- Run Browser shows child-run links and bundle/replay actions for workflow runs.

