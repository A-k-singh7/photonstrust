# Phase 37 - GDS + KLayout Pack Enablement (v0.1.1) - Implementation Plan (2026-02-14)

## Scope

Make "layout -> GDS -> KLayout pack" succeed in the default PIC workflow chain without requiring users to hand-tune macro settings.

## Changes

### 1) Emit true PATH waveguides in layout `.gds`

File:
- `photonstrust/photonstrust/layout/pic/build_layout.py`

Change:
- pass `simple_path=True` to `gdstk.FlexPath(...)` in `_emit_gds`

Acceptance:
- layout build emits `layout.gds`
- KLayout macro sees PATH shapes on the waveguide layer

### 2) Fix GDS extractor tuple handling (PATH layer/dtype normalization)

File:
- `photonstrust/photonstrust/layout/gds_extract.py`

Change:
- normalize `layers` / `datatypes` when they are tuples (gdstk uses tuples even for single path)

Acceptance:
- extractor no longer crashes on gdstk path objects with `layers=(1,)` / `datatypes=(0,)`

### 3) Default KLayout pack settings from the source layout build report

File:
- `photonstrust/photonstrust/api/server.py`

Change:
- in `POST /v0/pic/layout/klayout/run`, merge settings from the source run when missing:
  - `min_waveguide_width_um` from `layout_build_report.json` -> `pdk.design_rules.min_waveguide_width_um`
  - `waveguide_layer`, `label_layer`, `label_prefix`, `top_cell` from `layout_build_report.json` -> `settings`

Acceptance:
- KLayout pack DRC-lite does not false-fail due to default `0.5 um` threshold when the PDK uses `0.45 um`

## Validation Plan

1. Unit/integration tests:

```powershell
cd c:\Users\aksin\Desktop\Qutip+qskit projects\photonstrust
py -m pytest -q
```

2. Release gate:

```powershell
py scripts\release_gate_check.py
```

3. Web build:

```powershell
cd web
npm run lint
npm run build
```

4. End-to-end workflow-chain smoke run:
- run `POST /v0/pic/workflow/invdesign_chain`
- confirm:
  - `layout_gds = "layout.gds"`
  - `klayout_pack.status = "pass"`
  - evidence bundle contains `layout.gds` and KLayout pack artifacts

