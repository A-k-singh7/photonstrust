# Phase 27 - PDK-Aware Layout Hooks (Deterministic Sidecars + LVS-lite) - Research Brief

## Metadata
- Work item ID: PT-PHASE-27
- Date: 2026-02-13
- Scope: Establish a deterministic "graph -> layout -> verify" hook surface that works with public/open PDKs first, then private foundry PDKs, without compromising the open-science physics core.

## Problem Statement
PhotonTrust's PIC stack already has:
- a graph/netlist execution engine,
- route-level layout feature extraction for performance DRC (Phase 23),
- an optional GDS ingestion seam (Phase 24),
- a calibration loop for the crosstalk primitive (Phase 25),
- and a non-placeholder ring response (Phase 26).

To become a trustworthy, workflow-relevant platform for PIC verification, the next missing link is:
- deterministic layout artifacts that can be derived from the graph (even before full foundry PDK integration), and
- mismatch summaries (LVS-lite) that compare intended connectivity vs layout-derived connectivity.

This phase is intentionally "sidecar-first": ports and routes become the stable interface. GDS and tool-specific checks are optional backends.

## Research Notes

### 1) What "PDK-aware" means in practice
At minimum:
- layer map / tech file conventions (what layer is waveguide? pin? label?),
- cross-sections and min-rule constraints (width, gap, bend radius),
- port conventions and component naming (PCell naming, pin labels),
- verification scripts (DRC macros, extraction rules).

### 2) Why "sidecar-first" is the right v0.1 posture
We need a trust surface that is:
- deterministic in CI,
- reviewable as text artifacts,
- and compatible with multiple backends.

So v0.1 prioritizes always-emitted artifacts:
- `ports.json` (explicit port markers with coordinates),
- `routes.json` (Manhattan waveguide polylines),
- `layout_provenance.json` (hashes + tool versions).

Then, optional backends can materialize/check the same intent:
- `gdstk` (optional pure-Python GDS emission),
- gdsfactory (future: richer PDK routing/placement),
- KLayout (optional batch macros for DRC/LVS-like checks).

### 3) Why KLayout is still essential (verification/runtime)
KLayout provides:
- a de facto standard environment for PDK DRC macros,
- technology file semantics,
- and plugin ecosystems (notably SiEPIC) that many photonics teams already use.

PhotonTrust should treat KLayout as:
- an optional external tool runner,
- invoked explicitly with clear provenance capture,
- without coupling the open-core to any specific PDK deck.

### 4) LVS-lite for photonics (what we can do without full LVS)
Meaningful early verification value can be delivered via:
- connectivity extraction (snapping route endpoints to known port markers),
- expected vs observed netlist comparison,
- mismatch summaries:
  - missing connection
  - extra connection
  - ambiguous/invalid port-role connections
  - unconnected ports

Full foundry LVS (device extraction + parasitics) remains a later phase.

## Key Design Goals
- Deterministic layout build:
  - same inputs -> identical sidecars (hash-stable), and GDS when backend present.
- Clear PDK boundary:
  - open-source core remains tool-agnostic.
  - private PDKs integrate via manifests + on-prem runners.
- Verification-first:
  - mismatch summaries are the trust surface, not screenshots.

## Phase 27 Exit Criteria (high-level)
- A stable interface exists:
  - `build_layout(spec) -> (ports.json, routes.json, layout_provenance.json, optional layout.gds)`
- A stable verification report exists:
  - `lvs_lite(expected_graph, extracted_connectivity) -> mismatch_summary`
- Optional KLayout runner seam exists for later DRC/LVS macro integration.
