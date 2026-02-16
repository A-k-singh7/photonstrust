# Phase 23 — Performance DRC + Layout Feature Extraction (Route-Level) v0.1

## Metadata
- Work item ID: PT-PHASE-23
- Date: 2026-02-13
- Scope: Connect performance DRC (parallel-waveguide crosstalk) to deterministic routing metadata by extracting route-level geometry features ("parallel run segments") and using the *worst-case envelope* across those segments.

## Problem Statement
PhotonTrust already has a performance DRC primitive for parallel-waveguide crosstalk, but the v0 interface is a scalar check (`gap_um`, `parallel_length_um`). That is useful as a physics primitive, but not yet workflow-integrated: real designs have many routed segments, and the engineer needs a layout-aware answer: *where are the risky segments and what is the worst-case envelope across wavelengths?*

To become a trustworthy verification platform, the check must:
- operate on deterministic layout/routing metadata (before GDS exists),
- remain fast enough for interactive use,
- remain reproducible (stable extraction + stable evaluation),
- preserve backwards compatibility for existing users.

## Research Notes (What Matters Scientifically/Practically)
### 1) Minimum sufficient geometry for first-order crosstalk risk
For the current performance DRC model (coupled-mode inspired heuristic), the dominant drivers are:
- **edge-to-edge gap** between parallel waveguides, and
- **parallel interaction length**.

This motivates a v0.1 extractor that only needs routed centerlines + waveguide widths to compute:
- `gap_um` (edge-to-edge), and
- `parallel_length_um` (overlap along the routing axis).

### 2) Route-level first, then GDS-level
GDS extraction is absolutely required for manufacturing-grade signoff, but it is a slower and heavier dependency surface (KLayout/gdsfactory/PDK tech files, layer maps, boolean ops).

Route-level extraction is the fastest path to:
- UI-integrated checks,
- deterministic evidence generation,
- and a clean seam for later GDS-based “ground truth” extraction.

### 3) Determinism and trust
To avoid “verification by vibes,” v0.1 is intentionally strict:
- **Manhattan (axis-aligned) polylines only** (routes with diagonal segments error out).
- Canonicalization merges colinear points to avoid undercounting parallel lengths.
- Output ordering is deterministic for stable diffs and reproducibility.

### 4) Alignment with existing ecosystem signals
Photonic tooling ecosystems (notably KLayout-centric flows) strongly emphasize layout-aware netlists and verification loops. PhotonTrust’s architecture is explicitly aiming at that same loop, but with an evidence-first run registry and approvals workflow.

## Primary Sources / References (Entry Points)
- KLayout documentation (layout editor + scripting + DRC macros): `https://www.klayout.de/`
- KLayout licensing page (important for workflow integration decisions): `https://www.klayout.de/about/license/index.html`
- gdsfactory documentation (open PIC layout + routing workflows): `https://gdsfactory.github.io/gdsfactory/`
- SiEPIC-Tools ecosystem (KLayout-first photonics tooling signal): `https://github.com/SiEPIC/SiEPIC-Tools`

Internal research anchors:
- `docs/research/deep_dive/18_open_pdk_klayout_gdsfactory_playbook.md`
- `docs/research/deep_dive/21_v1_to_v3_fast_execution_plan.md`
- `docs/research/16_web_research_update_2026-02-13.md`

## Design Decisions (v0.1)
- Introduce a deterministic route extractor that outputs “parallel run segments.”
- Extend the existing performance DRC check to accept `routes` + `layout_extract` and compute:
  - per-wavelength worst-case crosstalk across segments,
  - overall worst-case crosstalk across the sweep,
  - physical min-gap violations across all segments.
- Preserve the existing scalar input path for backwards compatibility.

## Known Limitations (Explicitly Declared)
- Manhattan routing only (no arcs, no 45-degree segments, no bezier paths).
- No GDS-level geometry booleaning or layer/PDK tech-file interpretation.
- No bend-proximity or crossing proximity features yet.
- Extracted “parallel run segments” are conservative approximations; final signoff needs GDS-level extraction and/or calibrated simulation/measurement.

## Exit Criteria (Phase Acceptance)
- Deterministic extraction of parallel run segments from route polylines.
- Performance DRC can run from routes and returns a worst-case envelope.
- Tests cover at least three routing cases and schema validation still passes.
- All gates pass (`pytest`, release gate, web lint, web build).

