# Research Brief

## Metadata
- Work item ID: PT-PHASE-15
- Title: Graph validation + structured diagnostics (params, ports, kind support)
- Authors: PhotonTrust core team
- Date: 2026-02-13
- Related modules (planned/expected):
  - `photonstrust/graph/` (compiler + schema + new validation)
  - `photonstrust/components/pic/` (port truth)
  - `photonstrust/registry/` (param truth)
  - `photonstrust/api/` (expose validation endpoints)
  - `web/` (surface diagnostics in UI)

## 1) Problem and motivation

Phase 14 introduced a backend-owned parameter registry and a UI trust panel.
The remaining trust gap is that the system does not yet enforce or even
structure validation diagnostics for:
- parameter types and allowed ranges,
- enum membership (e.g., detector class),
- PIC port correctness (`from_port`/`to_port` must match component ports),
- unsupported component kinds (PIC execution).

Today, many invalid graphs fail late (during run) or fail silently (e.g., edges
connected to non-existent ports drop amplitude to zero in the v1 DAG solver).

For scientific credibility, validation must be:
- deterministic
- explicit (machine-readable diagnostics)
- rooted in backend truth (registry + engine ports)

## 2) Research questions

- RQ1: What validation should occur at **graph compile time** vs **run time**?
- RQ2: What is the minimal structured diagnostics format that supports:
  - UI display (human-scannable),
  - CI gating (machine-scannable),
  - future certification mode enforcement?
- RQ3: How do we validate PIC ports using engine truth (not UI assumptions)?

## 3) Proposed method

### 3.1 Backend diagnostics module
Add a validation module that produces:
- `errors[]` and `warnings[]` entries with stable `code` + `message`
  and references to node/edge ids.

Validation sources of truth:
- Parameter registry: `photonstrust.registry.kinds.build_kinds_registry()`
- PIC ports + supported kinds: `photonstrust.components.pic.library`

### 3.2 API endpoint
Expose:
- `POST /v0/graph/validate`
  - returns diagnostics without executing physics.

Optionally attach diagnostics to:
- `/v0/graph/compile` response (so compile always surfaces trust info).

### 3.3 UI surfacing
Add a “Diagnostics” block in the compile tab that highlights:
- errors (blocking issues)
- warnings (non-blocking issues)

## 4) Acceptance criteria

- Validation catches (at minimum):
  - PIC edge port names not in component ports (error)
  - PIC unsupported kinds (error or warning, explicit)
  - param type mismatches (error)
  - param range violations (error)
  - unknown params (warning)
- API returns deterministic diagnostics format.
- Existing automated gates pass.

## 5) Decision

- Decision: Proceed.

