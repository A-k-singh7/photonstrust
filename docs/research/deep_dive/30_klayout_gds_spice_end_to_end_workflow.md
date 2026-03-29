# KLayout + GDS + SPICE: End-to-End Verification Chain (How to Run It)

Date: 2026-02-14

This document is the "how we prove it works" workflow for the PIC chain:

graph -> simulate -> layout -> GDS -> KLayout pack -> DRC-lite -> extraction ->
LVS-lite -> SPICE export -> evidence bundle.

It connects the implemented phases:
- Phase 28 (SPICE export seam)
- Phase 30-32 (KLayout pack contract + API/web)
- Phase 34 (workflow chaining)
- Phase 37 (GDS PATH emission that KLayout can read)

---

## 0) Key Concept: KLayout Is an External Tool Seam

PhotonTrust treats KLayout as optional:
- core tests should pass without KLayout installed
- when KLayout is present, PhotonTrust captures provenance and artifacts as evidence

Code anchors:
- KLayout runner seam: `photonstrust/layout/pic/klayout_runner.py`
- Artifact pack wrapper: `photonstrust/layout/pic/klayout_artifact_pack.py`
- Macro template: `tools/klayout/macros/pt_pic_extract_and_drc_lite.py`

---

## 1) Enablement Checklist (Tools)

Required for full chain:
- `gdstk` installed (to emit `layout.gds` in PIC workflows)
- KLayout installed and discoverable on PATH, or set:
  - `PHOTONTRUST_KLAYOUT_EXE`

Optional:
- `ngspice` if you want to run the exported netlist (Phase 28 seam)

---

## 2) The Minimal Contract (What Must Exist as Artifacts)

The chain is considered "working" when a run folder contains:

Layout:
- `layout.gds`
- `layout_build_report.json`

KLayout pack:
- `klayout_run_artifact_pack.json`
- `ports_extracted.json`
- `routes_extracted.json`
- `drc_lite.json`
- `macro_provenance.json`
- `klayout_stdout.txt`
- `klayout_stderr.txt`

Verification:
- `lvs_lite_report.json`
- `performance_drc_report.json` (and optional HTML)

Interop:
- `netlist.sp`
- `spice_map.json`
- `spice_provenance.json`

Evidence:
- evidence bundle zip + manifest (Phases 35-36)

This list is "denial-resistant": it is concrete, replayable, and reviewable.

---

## 3) Running KLayout Pack Directly (Batch Mode)

KLayout can run macros in batch mode:
- `-b` batch
- `-r` run macro
- `-rd key=value` runtime variables

PhotonTrust already provides a macro template expecting:
- `input_gds`
- `output_dir`
- layer mapping and rule settings

Macro:
- `tools/klayout/macros/pt_pic_extract_and_drc_lite.py`

Example (conceptual):

```powershell
klayout_app.exe -b -r tools\klayout\macros\pt_pic_extract_and_drc_lite.py `
  -rd input_gds=C:\path\to\layout.gds `
  -rd output_dir=C:\path\to\out `
  -rd wg_layer=1 -rd wg_datatype=0 `
  -rd label_layer=10 -rd label_datatype=0 `
  -rd label_prefix=PTPORT `
  -rd min_waveguide_width_um=0.45 `
  -rd endpoint_snap_tol_um=2.0
```

PhotonTrust wrapper:
- use `build_klayout_run_artifact_pack(...)` to run this deterministically and emit `klayout_run_artifact_pack.json`.

---

## 4) PhotonTrust Wrapper: Produce a KLayout Run Artifact Pack

The wrapper is designed to always emit a schema-valid pack, even if the tool is missing.

Code:
- `photonstrust/layout/pic/klayout_artifact_pack.py`

Key behaviors:
- deterministic ordering of `-rd` variables
- stdout/stderr captured to files
- input/output hashes captured
- status is `pass|fail|error|skipped`

This is the bridge between "external EDA tool" and "trustable artifact chain".

---

## 5) LVS-lite: Intent vs Layout Connectivity

PhotonTrust LVS-lite compares:
- intended connectivity from the compiled graph
- extracted connectivity from GDS (or KLayout extracted routes/ports)

Why this matters:
- it catches real bugs (missing connections, wrong port label, unintended short)
- it is explainable and can be exported in evidence bundles

Code:
- `photonstrust/verification/lvs_lite.py`

Acceptance demo:
- intentionally break a route or label and show LVS-lite fails.

---

## 6) SPICE Export: Interop Seam (Not Optical-Physics SPICE)

PhotonTrust exports a deterministic SPICE-like netlist:
- connectivity and instance mapping
- intended as an interop seam and audit artifact

Code:
- `photonstrust/spice/export.py`

Artifact contract:
- `netlist.sp`
- `spice_map.json`
- `spice_provenance.json`

Optional runner seam:
- `photonstrust/spice/ngspice_runner.py`

---

## 7) How This Maps Into the Managed Workflow Surface

The managed-service flow is:
- author (UI) -> run -> diff -> approve -> export evidence bundle

Artifacts served and diffed:
- layout + KLayout pack outputs
- performance DRC results
- LVS-lite mismatch summaries
- SPICE export outputs

This is where PhotonTrust beats "tool-only" competitors:
the workflow itself becomes the product.

---

## 8) Definition of Done (End-to-End Chain)

The "full chain including KLayout pack" is complete when:

1) One canonical PIC workflow produces:
- `layout.gds` (not just a placeholder)
- a passing `klayout_run_artifact_pack.json`
- `drc_lite.json` with `summary.status=pass`
- an LVS-lite report with zero mismatches
- a SPICE export bundle

2) Evidence bundle export includes all of the above and can be replayed

3) The run browser shows:
- pass/fail summary for KLayout pack, LVS-lite, performance DRC
- diff between two runs highlights changes

---

## Source Index (Web-validated, 2026-02-14)

- KLayout DRC basic concepts (batch runs): https://www.klayout.org/downloads/master/doc-qt5/manual/drc_basic.html
- KLayout command-line args: https://www.klayout.de/command_args.html
