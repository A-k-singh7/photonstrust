# Open PDK + KLayout + gdsfactory Playbook (Build Guide)

Date: 2026-02-13

This document is a practical build guide for using public/open PDK resources to:
- generate PIC layouts programmatically,
- validate them using a foundry-like toolchain,
- and structure the result as reproducible artifacts that PhotonTrust can turn
  into trustable evidence packs.

It is written to support the ChipVerify track in:
- `docs/research/15_platform_rollout_plan_2026-02-13.md`
- `docs/research/deep_dive/17_chip_inverse_design_and_open_pdk_strategy.md`

---

## 1) Terminology (Minimal)

PDK (Process Design Kit):
- A bundle defining:
  - layer maps and technology file,
  - parameterized cells (PCells),
  - DRC (design rule checking) rules,
  - LVS (layout vs schematic) extraction rules,
  - device libraries and model validity ranges.

Foundry "open-source PDK" vs "public PDK":
- "Open-source PDK" usually means the kit itself is licensed for redistribution.
- "Public/no-NDA PDK" can be usable without an NDA, but may still have usage
  constraints (read the license/terms).

---

## 2) Your Practical Toolchain (Recommended Default)

### Layout generation
- gdsfactory (Python, composable PCells, routing, packaging).
  - https://github.com/gdsfactory/gdsfactory

### Layout viewing + rule checks
- KLayout (layout editor; DRC macros; Python scripting; PCells).
  - https://www.klayout.de/

KLayout scripting and PCells:
- Python API docs (macros, scripts, PCells):
  https://www.klayout.de/doc-qt5/code/class_PCellDeclarationHelper.html

KLayout licensing notes:
- KLayout is GPL v2 or later. Its docs explicitly note that using KLayout itself
  in your design flow does not affect the licensing of your produced chips, and
  discuss licensing for scripts/macros separately.
  - https://www.klayout.de/about/license/index.html

---

## 3) Public/Open PDK Targets You Can Start With (Photonics)

These are useful for startup prototyping because they are accessible without
direct foundry NDA gating.

### 3.1 CORNERSTONE PDK (gdsfactory integration)
- Source:
  https://github.com/gdsfactory/cspdk
- Package:
  https://pypi.org/project/cspdk/

Use case:
- fastest path to a manufacturable-looking PIC PDK integrated into Python layout.

### 3.2 VTT photonics PDK (gdsfactory)
- Source:
  https://github.com/gdsfactory/vtt
- Docs:
  https://gdsfactory.github.io/vtt/

Use case:
- open-source photonics PDK structure, good for reproducible demo pipelines.

### 3.3 Luxtelligence GlobalFoundries PDK (gdsfactory)
- Source:
  https://github.com/gdsfactory/luxtelligence

Use case:
- demonstrates a "foundry PDK wrapper" approach that is compatible with
  enterprise PIC workflows.

### 3.4 SiEPIC / EBeam PDK (KLayout ecosystem)
- Overview:
  https://siepic.ubc.ca/ebeam-pdk/

Use case:
- KLayout-first PDK workflow: PCells + technology files + DRC macros.

Note:
- This is not "a foundry you can copy". It is a toolkit you can use to design
  within the rules of a process that has its own manufacturing availability.

---

## 4) Reference PDK Targets (Useful Even If Not Photonics)

Sometimes you need a strong example of:
- DRC deck structure,
- packaging a PDK for install,
- KLayout integration mechanics.

Sky130 is a well-documented reference for KLayout PDK packaging:
- Sky130 KLayout PDK:
  https://github.com/efabless/sky130_klayout_pdk

This repo is also a good example of a PDK that uses gdsfactory-generated PCells
for KLayout:
- https://github.com/efabless/sky130_klayout_pdk

---

## 5) Minimal "ChipVerify Alpha" Workflow (Step-by-Step)

### Step 1: Choose a PDK target
Decision criteria:
- install friction (pip installable),
- documentation completeness,
- ability to generate DRC-clean layouts,
- clear licensing/terms.

Recommended first target:
- CORNERSTONE PDK (`cspdk`) because it is designed for Python integration.

### Step 2: Build a deterministic layout generator
Goal:
- from a small JSON spec (later: compiled graph), generate a GDS that includes:
  - 2-5 components,
  - waveguide routing between them,
  - IO ports (gratings/edge couplers),
  - label/metadata layer.

Implementation strategy:
- implement a pure function:
  `build_layout(spec) -> gdsfactory.Component`
- hash the spec (and PDK version) and embed the hash in:
  - GDS metadata (text label),
  - a sidecar `layout_provenance.json`.

### Step 3: Open the GDS in KLayout
Goal:
- verify the GDS loads cleanly, layer mapping is correct, ports are where
  expected, no accidental layer misuse.

### Step 4: Run DRC (or "DRC-lite")
Best case:
- use the foundry/PDK DRC deck.

Fallback (DRC-lite):
- implement a small set of checks to catch fatal errors early:
  - minimum width/spacing on critical layers,
  - polygon self-intersection,
  - missing pin markers and labels.

Outcome:
- a machine-readable `drc_report.json` (even if your first DRC-lite is homegrown).

### Step 5: Extract a netlist / connectivity
If full LVS is not available:
- implement connectivity checks at the routing level:
  - graph extraction from the intended connections,
  - verify all intended nets are connected.

Outcome:
- a `connectivity_report.json` listing:
  - expected nets,
  - extracted nets,
  - mismatches.

### Step 6: Create a "chip evidence pack"
Bundle:
- layout GDS,
- spec JSON,
- DRC report,
- connectivity report,
- PDK versions and environment hash,
- thumbnails/plots.

PhotonTrust output policy:
- this becomes a new artifact type that can be referenced from Reliability Cards.

---

## 6) Where This Fits in PhotonTrust Code

Use Phase 08 (graph compiler) to feed this pipeline:
- compiled PIC graph -> normalized netlist JSON
- normalized netlist -> gdsfactory layout builder

Recommended folder layout:
- `photonstrust/layout/pic/`
  - `pdk_registry.py`
  - `build_layout.py`
  - `drc.py` (pluggable backend; supports KLayout runs)
  - `connectivity.py`
- `photonstrust/artifacts/`
  - evidence pack bundler + manifest schema

---

## 7) Licensing and IP Reality (Non-Legal)

You can build a startup around open-source tools and PDKs, but:
- do not assume "public PDK" implies redistribution rights,
- do not embed foundry NDA content in your open-source core.

The safest product pattern is:
- open core provides the "compiler + evidence + verification framework",
- PDK adapters are pluggable and can be either open (public PDKs) or private
  (NDA PDKs installed by customers).

---

## 8) Source index

- gdsfactory main repo + open-source PDK list:
  https://github.com/gdsfactory/gdsfactory
- CORNERSTONE PDK wrapper:
  https://github.com/gdsfactory/cspdk
  https://pypi.org/project/cspdk/
- VTT PDK:
  https://github.com/gdsfactory/vtt
  https://gdsfactory.github.io/vtt/
- Luxtelligence PDK:
  https://github.com/gdsfactory/luxtelligence
- SiEPIC EBeam PDK:
  https://siepic.ubc.ca/ebeam-pdk/
- KLayout PCell and macro docs:
  https://www.klayout.de/doc-qt5/code/class_PCellDeclarationHelper.html
- KLayout licensing page:
  https://www.klayout.de/about/license/index.html
- Sky130 KLayout PDK (reference packaging structure):
  https://github.com/efabless/sky130_klayout_pdk

