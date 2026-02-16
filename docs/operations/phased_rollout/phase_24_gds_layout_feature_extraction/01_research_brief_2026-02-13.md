# Phase 24 — GDS-Level Layout Feature Extraction (v0.2 seam)

## Metadata
- Work item ID: PT-PHASE-24
- Date: 2026-02-13
- Scope: Add an optional, dependency-light bridge from **GDS** to the existing **route-level** layout feature extraction contract, so Performance DRC can be driven from real layout artifacts (without committing to a full KLayout/PDK stack yet).

## Problem Statement
Phase 23 connected performance DRC to route-level geometry (`routes` polyline metadata). Real verification workflows also need to consume **GDS** artifacts (the lingua franca of layout exchange).

However, full GDS-level extraction is a large surface area:
- hierarchical cell transforms,
- curved paths and PDK-specific waveguide shapes,
- layer maps and technology files,
- and toolchain licensing constraints (KLayout vs pure-Python libraries).

This phase establishes a pragmatic seam:
- Introduce a minimal GDS importer that produces PhotonTrust `routes[*]` objects.
- Keep it optional so the physics core remains lightweight and CI-stable.

## Research Findings (Tooling and Interfaces)

### 1) gdstk is a practical “GDS reader” primitive for early phases
`gdstk` supports:
- reading GDS (`read_gds`) with:
  - unit conversion and
  - layer/datatype filtering
- extracting PATH centerline geometry via `path_spines()`

This aligns directly with our route-level contract:
- `points_um` can be taken from path spines,
- `width_um` can be derived from path widths,
- then we reuse the Phase 23 extractor to compute “parallel run segments.”

Reference docs:
- gdstk API docs: `read_gds`, `FlexPath`, `RobustPath` (path spines and widths)
  - `https://gdstk.readthedocs.io/`

### 2) KLayout remains the long-term workhorse for foundry-accurate workflows
KLayout provides:
- mature GDS viewing/editing,
- DRC scripting,
- technology-file-driven workflows (layer maps, DRC macros).

But “GDS extraction” in KLayout tends to be coupled to:
- foundry rule decks,
- PDK layer conventions,
- and macro execution environments.

For v0.2 we intentionally *do not* hard-require KLayout; we keep the seam so KLayout can become a backend later.

Reference:
- `https://www.klayout.de/`
- License / workflow considerations:
  - `https://www.klayout.de/about/license/index.html`

### 3) gdsfactory fits as the future layout generation partner
gdsfactory is the likely engine for PDK-aware layout generation in Phase 27, and can be combined with:
- a route sidecar file for deterministic verification,
- and optional GDS extraction to cross-check or backfill missing route metadata.

Reference:
- `https://gdsfactory.github.io/gdsfactory/`

## Design Decisions (v0.2 seam)
- Use **gdstk (optional)** as the initial GDS ingestion backend.
- Convert:
  - PATH objects (FlexPath/RobustPath) into PhotonTrust routes.
  - (Optional) axis-aligned rectangle polygons into 2-point routes (for simple Manhattan waveguide rectangles).
- Keep limitations explicit:
  - no hierarchical transform traversal,
  - no curved-path support for route extraction (Manhattan-only mode),
  - polygons are only supported as rectangles (v0.2).

## Trust/Scientific Posture
- This phase is not “signoff extraction.”
- It is a workflow seam:
  - makes GDS artifacts usable in the evidence pipeline,
  - preserves determinism,
  - and keeps the path open for KLayout-backed extraction and foundry tech-file semantics later.

## Exit Criteria
- Optional dependency seam exists (`photonstrust[layout]`).
- `extract_routes_from_gds()` produces deterministic `routes[*]` objects for supported geometry.
- A JSON schema exists for the parallel-run extraction output to avoid silently drifting formats.
- Gates pass.

