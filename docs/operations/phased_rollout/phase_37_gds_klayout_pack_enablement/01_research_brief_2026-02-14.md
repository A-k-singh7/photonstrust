# Phase 37 - GDS + KLayout Pack Enablement (v0.1.1) - Research Brief (2026-02-14)

## Goal

Enable the full PIC workflow chain to produce and verify a real `.gds` output on a developer machine:

1. layout emits `layout.gds`
2. optional KLayout macro pack runs successfully (ports/routes extraction + DRC-lite)

While preserving the "tool seam" posture:
- KLayout remains optional (no hard dependency in the open-core)
- API runs remain sandboxed under `PHOTONTRUST_API_RUNS_ROOT`

## Findings

### 1) `.gds` emission is correctly modeled as an optional dependency

The PIC layout builder only emits `.gds` when the optional dependency `gdstk` is available.

Operationally, this means:
- without `gdstk`: `layout_gds = null` and workflow-chain skips the KLayout step
- with `gdstk`: `layout.gds` is emitted and the KLayout step can execute

### 2) KLayout macro route extraction depends on true GDS PATH elements

The trusted KLayout macro template (`tools/klayout/macros/pt_pic_extract_and_drc_lite.py`) extracts routes from:
- PATH shapes on the waveguide layer
- TEXT labels on the label layer (ports)

`gdstk.FlexPath(...)` defaults to `simple_path=False`, which can polygonize routes on GDS write. Polygonized routes do not appear as PATH shapes in KLayout, and the macro will skip them.

Therefore: layout `.gds` emission must write true GDS PATH elements for waveguides.

### 3) Default DRC-lite thresholds must match the PDK used to generate layout

The KLayout macro defaults `min_waveguide_width_um` to `0.5`.

The built-in demo PDK used by the layout builder (`generic_silicon_photonics`) sets:
- `min_waveguide_width_um = 0.45`

If the KLayout pack step uses the macro defaults, it can incorrectly fail DRC-lite (false negatives) when the layout emitter uses the PDK rule (0.45 um).

Therefore: KLayout pack runs must default their settings from the source layout run (PDK design rules + layout layer conventions) unless explicitly overridden.

## Decision Summary

- Emit waveguide routes as true GDS PATH elements (`simple_path=True`) to enable reliable extraction.
- In the KLayout pack API, derive default settings from the layout build report:
  - `min_waveguide_width_um` from PDK design rules
  - `waveguide_layer`, `label_layer`, `label_prefix`, `top_cell` from layout settings

