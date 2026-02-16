# Phase 29 - PIC Layout + LVS-lite + SPICE (API + Web Tabs) - Research Brief

## Metadata
- Work item ID: PT-PHASE-29
- Date: 2026-02-14
- Scope: Integrate the Phase 27/28 layout + EDA seams into the managed workflow surface:
  - API endpoints that write run manifests + served artifacts
  - web UI tabs that trigger these runs and expose artifacts in a reviewable way

## Problem Statement
Phase 27/28 established the core contracts:
- deterministic PIC layout sidecars (`ports.json`, `routes.json`, provenance, optional GDS)
- LVS-lite mismatch summaries
- SPICE export artifacts
- optional external tool runner seams (KLayout, ngspice)

But without API + UI integration, these capabilities are not usable as a workflow gate.

To become the most applicable and trustworthy platform, we need:
- a managed, audit-friendly run registry surface for layout/LVS/SPICE actions
- artifact serving links for reviewers (no filesystem access required)
- a UI that keeps users in the "graph -> build -> check -> review" loop

## Design Principles
- Evidence-first:
  - every run produces a manifest and stable artifact relpaths
  - reviewers can open artifacts directly from the UI
- Deterministic by default:
  - layout and export artifacts are stable for identical inputs
- Tool-agnostic open core:
  - KLayout/ngspice remain optional external tools
  - managed API/UI do not hard-require them

## Phase 29 Exit Criteria
- API endpoints exist and write run manifests:
  - `POST /v0/pic/layout/build`
  - `POST /v0/pic/layout/lvs_lite`
  - `POST /v0/pic/spice/export`
- Web UI exposes new PIC tabs:
  - Layout
  - LVS-lite
  - SPICE
- Artifacts are served and linkable from the UI (ports/routes/provenance/reports/netlist).
- All gates pass (pytest + release gate + web lint + web build).
