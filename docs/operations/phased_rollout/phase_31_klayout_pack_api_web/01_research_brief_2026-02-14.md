# Phase 31 - KLayout Artifact Pack API + Web Integration - Research Brief

## Metadata
- Work item ID: PT-PHASE-31
- Date: 2026-02-14
- Scope: Integrate the Phase 30 KLayout macro template + artifact pack contract into the managed workflow surface (FastAPI + web UI) without weakening tool-seam security posture.

## Problem Statement
Phase 30 added:
- a trusted KLayout macro template (GDS -> ports/routes + DRC-lite JSON outputs), and
- a deterministic "KLayout run artifact pack" wrapper + schema contract.

But the platform wedge requires these to be usable from the primary workflow surface:
- engineers build a layout from a PIC graph,
- then run verification hooks and review artifacts via the run registry UI.

Without API + UI integration:
- KLayout evidence packs are hard to demo,
- artifacts are not first-class in the managed review loop (runs browser, diffs, approvals),
- and users cannot easily navigate from "layout build run" to "KLayout check run".

## Trust/Safety Constraints (Non-negotiable)
- KLayout remains an **external tool seam** (optional).
- The API must not accept arbitrary macro/script execution from the client.
- Input paths must be constrained to existing run artifacts via safe resolution (no path traversal).
- Runs must be reproducible/auditable:
  - record which layout run and which GDS artifact was checked,
  - record the macro template identity (hash),
  - store stdout/stderr logs and outputs as served artifacts.

## Integration Targets
- API endpoint:
  - `POST /v0/pic/layout/klayout/run`
  - input: `layout_run_id` + optional `settings`
  - output: new run with a `run_manifest.json` linking to `klayout_run_artifact_pack.json` and logs
- Web UI:
  - Add a `KLayout` tab under PIC graph mode.
  - Use last Layout run as the default `layout_run_id`.
  - Surface served artifact links for:
    - pack manifest JSON
    - stdout/stderr logs
    - extracted ports/routes + DRC-lite outputs when present

## References
- PhotonTrust Phase 30 outputs:
  - `docs/operations/phased_rollout/phase_30_klayout_macros_artifact_pack/`
- Existing run registry surface:
  - `docs/operations/phased_rollout/phase_19_run_registry_artifact_serving/`
  - `docs/operations/phased_rollout/phase_20_run_browser_diff/`

