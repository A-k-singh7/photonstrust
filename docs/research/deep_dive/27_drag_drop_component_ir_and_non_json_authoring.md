# Drag-Drop at Component Level (Nazca-like UX, Better) + Non-JSON Authoring

Date: 2026-02-14

This document specifies how to evolve PhotonTrust's drag-drop graph editor
(Phase 13) into a component-level engineering surface comparable to PIC tooling
(Nazca/gdsfactory workflows), while keeping authoring:

- easy for humans (no JSON hand-editing)
- stable for version control (deterministic formatting)
- compilable into a strict internal IR (schema + hash + provenance)

---

## 0) Current State (Anchor)

Implemented:
- Phase 13: React Flow drag-drop MVP that exports/imports graph JSON and calls API endpoints

File format reality:
- JSON is fine as an internal wire format
- JSON is not fine as the primary human-authored artifact (your request)

So:
- keep canonical internal JSON (for deterministic hashing, transport, and schemas)
- add a human-first non-JSON authoring layer that round-trips cleanly

---

## 1) What "Nazca-like but Better" Really Means

Nazca-like:
- component library of parametric cells with ports
- composition via connectivity (ports/waveguides)
- design rule awareness

Better (PhotonTrust angle):
- same graph drives:
  - simulation
  - layout emission (GDS)
  - verification (DRC/LVS-lite/performance DRC)
  - evidence bundle export
  - run diff and approvals
- trust panel surfaces assumptions, applicability, and evidence tier
- multi-fidelity checks (optional QuTiP/Qiskit/external solver)

This is a workflow product, not only a CAD tool.

---

## 2) The Core Requirement: A Stable Internal IR

You already have a graph schema and compiler path (Phase 08).
The next step is to make the IR a first-class, versioned contract:

IR requirements:
- typed nodes and typed ports
- explicit units (um, nm, dB, Hz, s) and dimension checks
- hierarchical composition (subcircuits)
- deterministic ordering and canonicalization
- schema version and hash included in every run artifact

Recommended IR layering:

1) Authoring format (human-friendly, non-JSON)
2) Canonical JSON IR (machine-friendly, hashed, schema-validated)
3) Compiled execution artifacts (protocol-specific or backend-specific)

---

## 3) Non-JSON Authoring Options (Choose One, Support Two)

Constraints:
- must be human-editable
- must be deterministic in formatting
- must allow comments

Recommended:

Option A (primary): TOML "GraphSpec"
- stable, strict, less foot-gun than YAML
- great for configs and small hierarchical docs

Option B (secondary): YAML (interop with gdsfactory-style flows)
- gdsfactory discusses YAML-based design flow, so compatibility matters
- YAML is more error-prone; treat it as optional

Anchor:
- gdsfactory photonics paper mentions YAML-based design flow: https://gdsfactory.github.io/photonics_paper/

---

## 4) Proposed Authoring Contract: GraphSpec (TOML)

File extension:
- `.ptg.toml` (PhotonTrust Graph)

High-level sections:
- `[meta]` : name, schema_version, tags
- `[[nodes]]` : id, kind, params, pdk binding
- `[[edges]]` : from_node.port -> to_node.port
- `[constraints]` : DRC/performance constraints (min gap, max XT, etc.)
- `[modes.preview]`, `[modes.certification]` : runtime knobs

Example (minimal PIC graph):

```toml
[meta]
schema_version = "pt.graphspec.v1"
name = "mzi_demo"

[[nodes]]
id = "laser1"
kind = "pic.laser"
[nodes.params]
wavelength_nm = 1550
power_dbm = 0

[[nodes]]
id = "dc1"
kind = "pic.directional_coupler"
[nodes.params]
coupling_ratio = 0.5
loss_db = 0.2

[[nodes]]
id = "wg1"
kind = "pic.waveguide"
[nodes.params]
length_um = 2000
width_um = 0.45

[[nodes]]
id = "pd1"
kind = "pic.photodiode"
[nodes.params]
responsivity_a_per_w = 0.9

[[edges]]
from = "laser1:out"
to = "dc1:in1"

[[edges]]
from = "dc1:out1"
to = "wg1:in"

[[edges]]
from = "wg1:out"
to = "pd1:in"

[constraints]
min_waveguide_width_um = 0.45
min_bend_radius_um = 5.0
max_crosstalk_db = -30
```

Compiler behavior:
- parse TOML -> build canonical internal JSON graph
- validate schema
- canonicalize ordering (nodes by id, edges by (from,to))
- compute a `graph_hash` and include it in all downstream artifacts

---

## 5) Port Typing and Connection Rules (Prevents Garbage Graphs)

Every port must declare:
- domain: optical | electrical | thermal | clock | classical | quantum
- direction: in | out | bidir
- mode/type info:
  - optical: single-mode, polarization, wavelength band
  - electrical: analog/digital, impedance, bandwidth

Connection rules:
- optical only connects to optical
- domain mismatches are UI-blocked and compiler-failed
- unit mismatches are compiler-failed

Why:
- this is the difference between a "diagram editor" and an engineering tool

---

## 6) Component Library Contract (The Other Half of "Nazca-like")

Each component kind must ship with:
- parameter schema (names, units, ranges, defaults)
- port schema (names, types)
- layout hook (optional) with PDK binding
- simulation hook (compact model or S-parameter)
- verification hooks:
  - geometry DRC constraints
  - performance DRC checks (loss/crosstalk/bandwidth)
- documentation string and citations (if physics-based)

Store these in:
- `photonstrust/components/` and `photonstrust/pic/` (already present)
- plus a registry index used by UI palette and compiler

---

## 7) UI Requirements (What Makes It "Better")

The UI must not be a generic node editor.
It must be "trust + verification in the loop".

Required UI behaviors:
- inline constraint warnings (DRC + performance DRC) as you connect components
- parameter inspector with:
  - units and valid ranges
  - "assumption provenance" (default vs user-provided vs calibrated)
- "preview vs certification" toggle with clear runtime cost indicator
- run diff that highlights:
  - changed assumptions
  - changed outputs
  - changed applicability bounds

Optional power features (high leverage):
- "sweep parameter" UI that emits a sweep config artifact and plots results
- "design of experiments" templates for building calibration datasets

---

## 8) How This Connects to DRC/LVS and KLayout

PhotonTrust already has:
- layout emission (GDS) and layout feature extraction
- KLayout macro templates + artifact pack contract (Phase 30+)
- LVS-lite mismatch reporting

GraphSpec should be able to drive:
- layout generation (GDS)
- KLayout artifact pack run
- performance DRC checks
- evidence bundle export

So the authoring surface is the "front door" to the full verification chain.

---

## 9) Acceptance Criteria (Definition of Done)

GraphSpec (TOML) is "real" when:

1) Round-trip works:
- UI export -> TOML
- TOML -> compiler -> canonical JSON
- canonical JSON -> UI import
- no semantic changes

2) Deterministic formatting:
- `photonstrust fmt graphspec` produces stable TOML output

3) Schema and hashing:
- compiler emits `graph_hash` and it appears in artifacts and run registry

4) Typed connections:
- UI blocks invalid connections; compiler fails if forced

5) End-to-end demo:
- build a PIC graph -> emit `layout.gds` -> run KLayout pack -> run performance DRC -> export evidence bundle

---

## Source Index (Web-validated, 2026-02-14)

- gdsfactory paper (YAML design flow mention): https://gdsfactory.github.io/photonics_paper/
- Nazca license (context for why we avoid embedding AGPL into commercial core): https://github.com/nickersonm/nazca-design/blob/master/LICENSE.txt
