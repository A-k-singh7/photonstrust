# DRC + Performance DRC + LVS-lite: Full Verification Pipeline Spec

Date: 2026-02-14

This document turns "implement DRC fully" into an executable engineering spec.

Definitions:
- DRC: geometry/manufacturing rules (min width/space/enclosure/density, etc.)
- Performance DRC (PDRC): physics checks tied to layout features (loss, crosstalk, bandwidth, margin)
- LVS-lite: connectivity consistency between intended netlist and extracted layout connectivity

PhotonTrust goal:
- become the trustable verification layer producing reviewable evidence bundles
- integrate with KLayout for open flows and provide seams for foundry decks / vendor tools

---

## 0) Why This Is the Wedge (What Investors and Customers Believe)

PIC teams do not buy "another simulator" easily.
They pay for:
- fewer tapeout failures
- fewer lab iterations
- faster design review sign-off

DRC/LVS/PDRC is where sign-off thinking lives.

If PhotonTrust becomes the place where:
- checks run
- evidence is exported
- and diffs are reviewed and approved
it becomes sticky regardless of which EM solver a team prefers.

---

## 1) Current Repo Anchors (Already Implemented)

Implemented phases (check `docs/operations/phased_rollout/README.md`):
- Phase 23: route-level layout feature extraction -> performance DRC (route mode)
- Phase 24: GDS layout feature extraction
- Phase 27: PDK layout hooks
- Phase 28: SPICE + KLayout interop seams
- Phase 30-32: KLayout macro templates + "KLayout run artifact pack" contract + API/web surfaces
- Phase 34: workflow chaining -> layout + LVS-lite + optional KLayout pack + SPICE export
- Phase 37: layout emits PATH waveguides so KLayout macro sees correct geometry

Key code anchors:
- `photonstrust/verification/performance_drc.py`
- `photonstrust/verification/lvs_lite.py`
- `photonstrust/layout/gds_extract.py`
- `tools/klayout/macros/pt_pic_extract_and_drc_lite.py`

This doc specifies how to harden and extend these into a full verification pipeline.

---

## 2) The Verification Stack (Four Tiers)

Tier 0: Graph-level checks (instant, pre-layout)
- invalid connections (port typing)
- out-of-range parameters (schema)
- obvious violations (min width, forbidden bends) based on intended routing metadata

Tier 1: Route-mode checks (fast, pre-GDS, deterministic)
- Phase 23 style extraction from routes
- performance DRC crosstalk gate using extracted parallel runs
- acts as "lint" for routing before generating layout

Tier 2: GDS-based extraction + LVS-lite (medium cost)
- extract routes/ports/features from actual GDS
- compare intended netlist vs extracted connectivity
- run PDRC using measured geometry (not intended geometry)

Tier 3: External DRC decks and tool runners (highest trust, optional)
- foundry DRC decks (often under NDA) run in a customer-provided environment
- vendor solver runs (optional) for certification mode
- PhotonTrust captures artifacts and provenance, not the deck itself

Key product rule:
- Tier 3 is optional and isolated (tool seam / runner boundary)
- Tier 0-2 must provide meaningful value in open flows

---

## 3) DRC (Geometry Rule Checking) Design

### 3.1 DRC-lite (open-core, KLayout macro)

Purpose:
- catch fatal layout errors early
- provide a deterministic baseline that is always runnable

Examples of DRC-lite rules (already aligned with Phase 30 macro):
- PATH width >= min_waveguide_width_um
- Manhattan-only routes (v0 constraint)
- route endpoints snap to declared ports within tolerance
- unique port labels

Outputs:
- `drc_lite.json`
- annotated screenshots (next addition) for review UX

Evidence:
- macro provenance JSON (tool version, macro version, inputs, hashes)
- stdout/stderr logs

### 3.2 Foundry DRC (sealed deck runner)

Purpose:
- manufacturing sign-off in real tapeout flows

Constraints:
- decks are usually proprietary and cannot be redistributed
- rules and waivers are sensitive

PhotonTrust approach:
- do not ship decks
- ship a "runner contract" that executes decks in an isolated environment and exports:
  - pass/fail summaries
  - counts per rule
  - waiver references (IDs only)
  - deck hash and tool version

Artifact design:
- `foundry_drc_summary.json` (no proprietary geometry dumps)
- `foundry_drc_logs/` (access controlled; optional)

This is how you support enterprise without poisoning open-core.

---

## 4) Performance DRC (Physics Checks Tied to Layout)

Performance DRC should be treated like "timing closure" in digital:
- geometry affects physics
- checks are actionable constraints for designers

PDRC categories:

1) Crosstalk checks (already implemented at v0)
- parallel-run extraction
- worst-case envelope vs wavelength
- output: recommended min gap and flagged segments

2) Loss budget checks
- waveguide length -> propagation loss estimate
- bend count and bend radii -> bend loss estimate (bounded model)
- crossing count -> crossing loss estimate
- coupler insertion loss and imbalance

3) Bandwidth / resonance checks
- ring resonator sensitivity to fabrication and temperature (if rings are modeled)
- wavelength-dependent transfer function checks

4) Packaging-aware checks
- fiber array pitch constraints, edge coupler placement windows
- keepout zones, metal density (if relevant)

Implementation policy (scientific defensibility):
- each PDRC model must declare:
  - applicability bounds (geometry range, wavelength, PDK)
  - calibration status (theory-only vs calibrated)
  - uncertainty propagation method

---

## 5) LVS-lite (Connectivity and Intent Verification)

Goal:
- prevent "schematic says connected" while "layout is not actually connected"

In PIC workflows, full LVS is not always available in open-source tooling.
PhotonTrust should provide LVS-lite as:
- graph intent (netlist) vs layout extraction (connectivity graph)

Inputs:
- intended netlist from compiled graph
- extracted connectivity from:
  - KLayout macro artifacts, or
  - Python GDS extractor for PATH centerlines + label anchors

Outputs:
- mismatch report:
  - missing nets
  - unexpected nets/shorts
  - missing ports
  - ambiguous connectivity due to label issues

Evidence:
- extracted ports/routes JSON (stable ordering)
- hashes of the input GDS and extractor version

This is essential for denial-resistant demos:
show that the tool can catch a real wiring error.

---

## 6) Evidence Pipeline: What Must Be Exported (Non-Negotiable)

Every verification run must export a pack with:

Inputs:
- `layout.gds` (or reference to it in run registry)
- PDK metadata (public PDK version or private adapter ID)
- rule settings (min width, snap tol, layer mapping)

Tool execution:
- tool binary ID and version (KLayout version string)
- exact command line / macro ID
- stdout/stderr logs

Outputs:
- DRC-lite JSON + (optional) images
- PDRC report JSON + HTML
- LVS-lite mismatch report JSON + HTML

Provenance:
- SHA256 hashes of inputs and outputs
- schema versions
- run ID and graph hash linkage

Signing/publishing:
- attach signatures in Phase 40 (separate doc/phase)

This is the "trust product" you sell.

---

## 7) UI Requirements (Verification Must Be Usable)

To beat competitors, checks must be reviewable and actionable:

Required:
- show pass/fail summaries in the run browser
- show rule counts and top violations
- show "where" (annotated screenshot or coordinate references)
- show diffs between runs: new violations, resolved violations
- show waivers with justification and expiry (enterprise track)

The UI is where you win adoption, because it turns verification into a workflow.

---

## 8) CI/CD Integration (Make Regressions Impossible)

Mandatory gates:
- schema validation for every generated report JSON
- deterministic replay checks for canonical fixtures
- "no new violations" gate on golden layouts (when fixtures exist)

Optional gates:
- performance budget thresholds (p95 runtime)
- PDRC regression curves and drift detection

---

## 9) Acceptance Criteria (Definition of Done)

The DRC/PDRC/LVS pipeline is "full" when:

1) End-to-end:
- graph -> layout -> GDS -> KLayout pack -> extracted features -> PDRC -> LVS-lite -> evidence bundle

2) Denial-resistant demo case exists:
- intentionally introduce a connectivity bug and show LVS-lite catches it
- intentionally introduce a min-width violation and show DRC-lite catches it
- intentionally tighten a gap and show PDRC flags crosstalk risk

3) Artifacts are replayable:
- a third party can re-run the verification and get identical JSON outputs (within tolerance)

4) Upgrade path exists:
- foundry DRC deck runner seam for enterprise without contaminating open-core

---

## Source Index (Web-validated, 2026-02-14)

- KLayout DRC manual (batch DRC concepts): https://www.klayout.org/downloads/master/doc-qt5/manual/drc_basic.html
- KLayout command-line args: https://www.klayout.de/command_args.html
- SiEPIC Tools (KLayout photonics workflow ecosystem): https://github.com/SiEPIC/SiEPIC-Tools
