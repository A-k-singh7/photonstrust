# Research Brief

## Metadata
- Work item ID: PT-PHASE-14
- Title: Trust panel v0.2 (parameter registry + units/ranges + validation surface)
- Authors: PhotonTrust core team
- Date: 2026-02-13
- Related modules (planned/expected):
  - `photonstrust/api/` (API surface for UI)
  - `photonstrust/registry/` (new: kind/parameter registry)
  - `web/` (editor UI)

## 1) Problem and motivation

Phase 13 delivered a working drag-drop editor that can author graph JSON and
execute runs via a local API. However, the current UI parameter editing is
mostly raw JSON. This is functional but not yet “trustable” in the sense that:

- parameter units and allowed ranges are not visible,
- invalid values are not caught early or explained in a structured way,
- the UI still “knows” some component metadata locally (risk of drift),
- academic users cannot easily see the meaning and validity of each knob.

To be the most trustable platform, parameter semantics must be explicit,
versioned, and owned by the backend physics core.

## 2) Research questions

- RQ1: What is the minimal contract that makes parameter semantics explicit
  (units, ranges, enums, defaults) without turning the UI into the scientific
  authority?
- RQ2: How should we represent “parameter schemas” so they can be consumed by:
  - the web editor (forms + tooltips),
  - compile/run validation (structured diagnostics),
  - documentation generation (academic-friendly reference tables)?
- RQ3: How do we keep this compatible with the open-science strategy:
  backend-owned semantics, thin clients, reproducible artifacts?

## 3) Proposed method (v0.2)

### 3.1 Backend-owned registry
Introduce a “kinds registry” that enumerates the supported component kinds for:
- `qkd_link` graphs (source/channel/detector/timing/protocol), and
- `pic_circuit` graphs (PIC primitives),
including:
- human name/title
- port definitions (where applicable)
- parameter definitions:
  - type (`number`/`string`/`bool`/`object`)
  - units (string, optional)
  - required/optional
  - default (optional)
  - min/max (optional)
  - enum set (optional)
  - short description

The registry is published over HTTP so the UI can render “trust panels” without
hardcoding scientific meaning.

### 3.2 Trust panel in the editor
Enhance the right-side inspector:
- show parameter schema (units, defaults, allowed ranges) for the selected node,
- allow safe editing via generated controls for common scalar params,
- keep a raw JSON editor for advanced/experimental use.

### 3.3 Validation surface
For v0.2, validation is “best-effort”:
- UI can warn about obvious type/range errors using the registry,
- backend remains authoritative and errors during compile/run are still
  surfaced to the UI.

## 4) Security and integrity considerations

- The registry must not expose filesystem paths or any dynamic server state.
- API must remain safe against “file read” attacks:
  - Touchstone file reads remain CLI-only unless explicitly enabled in a future
    service-mode hardening phase.

## 5) Acceptance criteria

- API serves a kinds registry:
  - endpoint returns stable, deterministic JSON.
- Web editor:
  - shows parameter schema (units/ranges/defaults) for selected nodes.
  - supports editing common scalar params via generated controls.
- Automated gates pass:
  - `py -m pytest -q`
  - `cd web && npm run lint`
  - `cd web && npm run build`

## 6) Decision

- Decision: Proceed.

