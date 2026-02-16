# Phase 32 - KLayout Pack: Run Registry Source Selection - Research Brief

## Metadata
- Work item ID: PT-PHASE-32
- Date: 2026-02-14
- Scope: Allow KLayout artifact pack runs to target any `.gds` artifact selected from the run registry (not only the "last Layout build run" from the graph workflow).

## Problem Statement
Phase 31 added an API endpoint and web UI tab to run the Phase 30 KLayout macro template and capture an artifact pack. However, the current UX and API contract are primarily wired for:
- "graph -> layout build -> (optional gdstk emits layout.gds) -> run KLayout pack"

In real workflows, engineers will often want to run checks on:
- imported GDS, hand-edited GDS, or partner-provided GDS,
- GDS produced by an external flow,
- older layout runs (not the latest one),
- any run that has a GDS artifact attached.

PhotonTrust already has a run registry picker that surfaces run artifacts. The KLayout workflow must allow:
- selecting a run in the registry browser,
- selecting a `.gds` artifact from that run,
- running the KLayout pack against it,
- and producing a new run with provenance linking back to the source run + artifact path.

## Trust + Safety Constraints
- The API must not accept arbitrary filesystem paths.
  - It may only accept `(run_id, artifact_relpath)` pairs and resolve them using the existing safe artifact resolver.
- The API must not accept arbitrary macros/scripts from clients.
  - Only repo-owned templates are permitted (Phase 30 posture).
- The resulting run must be auditable:
  - store `source_run_id` and `source_gds_artifact_path` in the run manifest input.

## Design Notes
- Many run types may contain multiple artifacts. For GDS selection:
  - defaulting is only safe if exactly one `.gds` artifact is present (or a canonical `layout_gds` artifact exists).
  - otherwise the client must specify `gds_artifact_path`.

## Outcome
PhotonTrust becomes a stronger "verification control plane":
- any GDS in the evidence system can be checked,
- and KLayout results remain diffable/servable with provenance.

