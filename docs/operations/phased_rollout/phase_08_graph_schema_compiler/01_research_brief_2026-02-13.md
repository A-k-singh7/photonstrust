# Research Brief

## Metadata
- Work item ID: PT-PHASE-08
- Title: Component graph schema v0.1 + compiler (UI -> engine configs)
- Authors: PhotonTrust core team
- Date: 2026-02-13
- Related modules (planned/expected):
  - `photonstrust/graph/` (new)
  - `photonstrust/config.py` (target of compilation)
  - `schemas/photonstrust.graph.v0_1.schema.json` (new)

## 1) Problem and motivation
PhotonTrust needs a trustworthy bridge between drag-drop authoring and the
scientific engine. Today, scenarios are authored as YAML configs. A production
graph editor will instead produce a graph JSON (nodes/edges), and we need:
- a versioned graph schema (so UI <-> engine stays stable),
- a deterministic compiler (graph -> engine configs), and
- compile provenance and "assumptions summaries" for auditability.

The system must support both product surfaces:
- `OrbitVerify` graphs for QKD link workflows (source/channel/detector/timing/protocol),
- `ChipVerify` graphs for photonic circuit workflows (PIC component netlists).

## 2) Research questions
- RQ1: What is the minimal graph schema that supports both QKD link graphs and
  PIC circuit graphs while remaining versionable and stable?
- RQ2: How do we guarantee deterministic compilation (same input -> same
  compiled outputs), especially for PIC graphs where multiple topological orders
  exist?
- RQ3: What "trust artifacts" must compilation emit (hashes, versions, warnings)
  so compiled configs can be audited?

## 3) Method design (v0.1)

### 3.1 Graph profiles
Use a single top-level schema with explicit `profile`:
- `qkd_link`: compile into existing PhotonTrust YAML config structure.
- `pic_circuit`: compile into a normalized netlist representation (for Phase 09
  PIC simulation work).

### 3.2 Determinism strategy
- Define stable graph IDs and node IDs.
- During compilation:
  - enforce unique node IDs
  - enforce edge endpoints exist
  - for PIC graphs, compute a deterministic topological order using a
    tie-break on node ID.
- Emit compile provenance:
  - graph hash
  - schema version
  - compiler version (PhotonTrust version when available)

### 3.3 Trust and evidence policy
Compilation is part of the "trust chain". It must:
- never silently invent physics parameters
- document defaults (e.g., presets applied later in `build_scenarios`)
- warn when optional validation (JSON Schema) is unavailable

## 4) Acceptance criteria
- `schemas/photonstrust.graph.v0_1.schema.json` exists and is validated in tests.
- `photonstrust graph compile` exists and produces:
  - a compiled QKD config (`qkd_link` profile), or
  - a normalized PIC netlist (`pic_circuit` profile),
  - a provenance JSON,
  - an assumptions summary.
- Compilation is deterministic and tested.
- Full `pytest` suite passes.

## 5) Decision
- Decision: Proceed.

