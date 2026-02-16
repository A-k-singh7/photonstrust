# Upgrade Ideas: PIC + Verification (DRC/PDRC/LVS + KLayout/GDS/SPICE + UX)

Date: 2026-02-14

This file is the consolidated upgrade map for:
- PIC workflow dominance (drag-drop -> layout -> verify -> evidence)
- DRC + performance DRC + LVS-lite hardening
- KLayout/GDS/SPICE interop improvements
- inverse design as a component generator with evidence

---

## P0 (Next)

### UPG-PIC-001: Non-JSON authoring (TOML GraphSpec) + round-trip guarantees

Why:
- engineers refuse to hand-edit JSON
- stable formatting makes graphs reviewable in git

Deliver:
- `.ptg.toml` GraphSpec parser -> canonical JSON graph IR
- deterministic formatter: `photonstrust fmt graphspec`
- UI import/export supports both JSON and TOML without semantic drift

Source:
- `../research/deep_dive/27_drag_drop_component_ir_and_non_json_authoring.md`

### UPG-PIC-002: Make verification outputs "reviewable" (images + coordinates)

Why:
- DRC/PDRC outputs must be actionable, not just counts

Deliver:
- KLayout pack also emits:
  - annotated screenshots (or at minimum: bbox coordinates per issue)
- run diff highlights:
  - new violations, resolved violations
  - changed constraints and applicability bounds

Sources:
- `../research/deep_dive/28_drc_pdrc_lvs_evidence_pipeline.md`
- `../research/deep_dive/30_klayout_gds_spice_end_to_end_workflow.md`

---

## P1 (Planned)

### UPG-PIC-010: Performance DRC expansion beyond crosstalk

Why:
- "timing closure" analogy: loss + bandwidth + resonance + packaging checks

Deliver (v0.2 targets):
- waveguide loss budget checks (length + bends + crossings) with applicability bounds
- simple resonance sanity checks (if rings exist)
- packaging constraint checks (pitch/keepouts) as rule hooks

Sources:
- `../research/deep_dive/28_drc_pdrc_lvs_evidence_pipeline.md`
- `../research/deep_dive/21_v1_to_v3_fast_execution_plan.md`

### UPG-PIC-011: gdsfactory interop (adapter, not a dependency lock-in)

Why:
- gdsfactory is the dominant open-source PIC ecosystem

Deliver:
- optional extra `photonstrust[gdsfactory]`
- import gdsfactory Component -> PhotonTrust layout feature contracts
- export PhotonTrust graphs -> gdsfactory scripts (optional)

Source:
- `../audit/10_competitive_positioning.md`

### UPG-PIC-012: Foundry DRC runner seam (enterprise posture)

Why:
- real sign-off uses proprietary decks; PhotonTrust must integrate without redistributing them

Deliver:
- "sealed deck runner contract" that exports:
  - summary counts + pass/fail
  - deck hash, tool version, waiver IDs
- include these artifacts into evidence bundles

Source:
- `../research/deep_dive/28_drc_pdrc_lvs_evidence_pipeline.md`

---

## Inverse Design (Component Generator, Not Full Chip)

### UPG-INV-001: Treat inverse design as "evidence-first"

Why:
- inverse-designed devices are dismissed unless they are reproducible, robust, and manufacturable

Deliver:
- required evidence pack fields and robustness sweeps become gates
- certification mode fails without robustness evidence

Sources:
- `../research/deep_dive/19_inverse_design_engine_architecture.md`
- `../research/deep_dive/29_inverse_design_adjoint_strategy_licensing_and_evidence.md`

### UPG-INV-002: External solver runner seam (license isolation)

Why:
- avoid copyleft tool lock-in for the open-core + commercial product surface

Deliver:
- plugin runner boundary for GPL solvers (optional)
- permissive backend default for product surface

Sources:
- `../research/deep_dive/17_chip_inverse_design_and_open_pdk_strategy.md`
- `../research/deep_dive/29_inverse_design_adjoint_strategy_licensing_and_evidence.md`

---

## KLayout/GDS/SPICE Chain (Hardening)

### UPG-CHAIN-001: Canonical end-to-end "golden chain" fixture

Why:
- you need a single fixture that proves the full chain works and stays working

Deliver:
- one canonical PIC graph that:
  - emits `layout.gds`
  - passes KLayout DRC-lite
  - passes LVS-lite
  - exports SPICE
  - exports evidence bundle
- add a CI job that runs this in "optional tool present" mode

Source:
- `../research/deep_dive/30_klayout_gds_spice_end_to_end_workflow.md`

---

## Expanded Backlog (PhD-Grade, Execution-Oriented)

Use this section when you are ready to convert an idea into a strict phase.
Each item is written to be "small-slice buildable" with evidence gates.

### UPG-PIC-020: PDK adapter interface + capability matrix

Why:
- prevents PDK-specific glue from leaking everywhere (layout, DRC-lite, LVS-lite, SPICE)

Risk if ignored:
- verification logic becomes a tangle of special cases; portability to a new PDK becomes expensive

Minimal viable slice:
- define a PDK adapter contract:
  - layer map + layer purposes
  - design rules (min width/space, bend radius)
  - pin/port conventions
- implement for one public/no-NDA PDK and one "toy" PDK

Validation gates:
- adapter conformance tests (required fields + units)
- one canonical layout builds and verifies under both adapters

Anchors:
- gdsfactory PDK patterns: https://gdsfactory.github.io/gdsfactory/
- KLayout PCell/macro docs: https://www.klayout.de/doc-qt5/code/class_PCellDeclarationHelper.html

### UPG-PIC-021: PDK version pinning + reproducibility manifest in artifacts

Why:
- DRC/LVS results are meaningless without immutable PDK/deck identity

Minimal viable slice:
- add a `pdk_manifest.json` artifact to every layout/verification run:
  - PDK name/version/hash, deck hash, KLayout version, schema versions

Validation gates:
- certification-mode run fails if manifest is missing
- run diff surfaces PDK manifest deltas prominently

### UPG-PIC-030: DRC deck metadata: rule graph + severity + waiver policy

Why:
- DRC outputs must be auditable; waivers must be explicit with evidence

Minimal viable slice:
- define rule metadata: id, category, severity, applicability, fix hint
- define waiver format: rule id, geometry selector, justification, expiry, reviewer

Validation gates:
- CI fails if waiver has no justification or is expired
- deck lint: no duplicate IDs; all rules have docs

### UPG-PIC-031: LVS-lite connectivity equivalence (layout vs intended netlist)

Why:
- photonics rarely has full LVS; but connectivity mismatches are still catastrophic

Minimal viable slice:
- extract connectivity graph from layout pins/waveguide layers
- compare to expected graph from compiled netlist

Validation gates:
- canonical circuits (MZI, ring, splitter) pass graph-equivalence tests
- mismatch report contains actionable deltas (missing net, short, wrong port)

### UPG-PIC-032: Performance DRC (PDRC) expansion beyond crosstalk

Why:
- yield and margin failures are often parametric (bend loss, proximity, heaters/metal, resonance sensitivity)

Minimal viable slice:
- add 3-5 PDRC rules tied to layout-extracted proxies:
  - min bend radius, max parallel run length, waveguide-to-metal keepout

Validation gates:
- proxy monotonicity tests + runtime budget
- evidence report includes applicability bounds (what regime the proxy was calibrated for)

### UPG-PIC-040: Device recognition registry (layout -> device instances)

Why:
- export to SPICE/compact models requires recognizing devices and extracting parameters

Minimal viable slice:
- create a device signature registry per PDK:
  - how to detect (cell name, layer markers, geometry signature)
  - which parameters to extract

Validation gates:
- golden layout fixtures recognized correctly; near-miss negative tests included

### UPG-PIC-041: SPICE-like export tightening + model library binding

Why:
- interoperability wedge: you do not replace EDA tools, you plug into them with evidence

Minimal viable slice:
- export netlist + sidecar mapping to compact models
- pin model library identity (version/hash) into evidence pack

Anchors:
- Compact Model Library (CML) positioning (workflow anchor): https://optics.ansys.com/hc/en-us/articles/360055701453-CML-Compiler-overview

### UPG-INV-010: Inverse design evidence pack as a gate (not optional)

Why:
- inverse-designed devices are dismissed without reproducibility, robustness, and manufacturability evidence

Minimal viable slice:
- required artifacts per inverse-designed cell:
  - objective + constraints + seed
  - iteration trace
  - corner sweep summary
  - DRC / DRC-lite output

Validation gates:
- deterministic replay for fixed seed
- robustness threshold enforced in certification mode

### UPG-INV-011: Robust optimization knobs (corners + fabrication constraints)

Minimal viable slice:
- min feature size filter/projection policy
- etch bias perturbation corner set

Validation gates:
- constraints satisfied across corners
- DRC-clean (or DRC-lite clean) final geometry

### UPG-WEB-010: Verification-aware web editor overlays

Why:
- constraint-driven editing compresses the iteration loop dramatically

Minimal viable slice:
- show ports/nets/keepouts
- run a small subset of fast checks live (grid, min width, min bend radius)

Validation gates:
- overlay agrees with offline verification outputs on canonical graphs

### UPG-WEB-011: Phase-gated export UX (make strict rollout visible)

Minimal viable slice:
- show phase checklist in UI
- block "export tapeout evidence" unless gates pass
