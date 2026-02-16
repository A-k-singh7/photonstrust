# Research Brief

## Metadata
- Work item ID: PT-PHASE-13
- Title: Web drag-drop MVP v0.1 (managed service surface)
- Authors: PhotonTrust core team
- Date: 2026-02-13
- Related modules (planned/expected):
  - `schemas/photonstrust.graph.v0_1.schema.json` (existing)
  - `photonstrust/graph/` (compiler, existing)
  - `photonstrust/api/` (new; local run/compile API)
  - `web/` (new; React Flow editor)

## 1) Problem and motivation
PhotonTrust has a versioned graph schema + compiler and executable engines for:
- QKD link scenarios (`qkd_link`), and
- PIC netlists (`pic_circuit`),
plus OrbitVerify pass envelopes and a safe data ingestion workflow.

The missing product surface is a dedicated drag-drop editor that:
- produces schema-valid graph JSON,
- shows component details (params, units, defaults, evidence tier),
- compiles to engine configs/netlists with provenance,
- executes preview runs quickly (mode semantics), and
- surfaces trust artifacts (assumptions, diagnostics, reproducibility pointers).

This phase creates a web MVP that can be used locally (developer mode) and is
structured to evolve into a managed service.

## 2) Research questions
- RQ1: What is the smallest UI surface that demonstrates the end-to-end value
  (drag-drop -> compile -> run -> trust artifacts) without locking us into a
  premature design system?
- RQ2: What is the correct boundary between UI and engine so the UI cannot
  silently change scientific meaning?
- RQ3: What minimal API surface is required for the editor to remain thin and
  for runs to be reproducible (hashes, seeds, mode labels)?
- RQ4: What security posture is required even for an MVP (no secrets leakage,
  no unsafe file access, explicit run sandboxing)?

## 3) Method design (v0.1)

### 3.1 Graph-first authoring
The UI edits graph JSON (v0.1 schema) as the source of truth. Every run stores:
- the graph payload,
- compiled artifacts,
- provenance (hashes, engine version).

### 3.2 Two profiles, one editor
Support both profiles in MVP:
- `qkd_link` (OrbitVerify/QKD links)
- `pic_circuit` (ChipVerify PIC netlists)

UI differences are handled via component palettes and port handles.

### 3.3 Trust panel
The side panel must show:
- parameter units and defaults,
- explicit assumptions (per component + per run),
- evidence tier label (preview vs certification).

### 3.4 Minimal backend API
Provide a local API wrapper that exposes:
- compile graph
- run QKD link (preview)
- simulate PIC netlist (preview)

The backend is the only place physics decisions occur.

## 4) Acceptance criteria
- Web app can:
  - add nodes and connect edges (drag-drop),
  - edit node parameters,
  - export graph JSON,
  - compile via backend and display compiled artifacts + assumptions.
- MVP supports executing:
  - QKD link preview run (returns key-rate curve + reliability card summary),
  - PIC netlist simulation (returns chain + DAG solver outputs).
- Outputs include config/graph hashes and explicit mode labels.

## 5) Decision
- Decision: Proceed.

