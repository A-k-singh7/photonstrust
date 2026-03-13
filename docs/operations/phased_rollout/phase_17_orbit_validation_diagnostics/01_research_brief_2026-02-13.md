# Research Brief

## Metadata
- Work item ID: PT-PHASE-17
- Title: OrbitVerify validation + diagnostics v0.1 (schema + validate endpoint + UI surfacing)
- Authors: PhotonTrust core team
- Date: 2026-02-13
- Related modules (planned/expected):
  - `photonstrust/orbit/pass_envelope.py` (existing engine executor)
  - `photonstrust/orbit/diagnostics.py` (new; semantic validation)
  - `photonstrust/orbit/schema.py` (new; JSON Schema validation)
  - `schemas/photonstrust.orbit_pass_envelope.v0_1.schema.json` (new)
  - `photonstrust/api/server.py` (extend)
  - `web/` (extend Orbit Pass mode with validate/diagnostics)

## 1) Problem and motivation

OrbitVerify v0.1 currently runs pass envelopes by executing a config dict and
writing artifacts. This is good for CLI workflows, but the web-runner added in
Phase 16 needs stronger **trust and UX contracts**:
- invalid configs should produce **structured, deterministic diagnostics**,
  not only runtime exceptions.
- configs should have a published schema so academic and industrial users can
  validate payloads and build tooling around the contract.

Phase 15 established structured diagnostics for graph workflows (params/ports
validation). OrbitVerify needs the same style of backend-owned validation to
avoid “pretty but untrusted” outputs.

## 2) Key research questions

- RQ1: What is the minimal validation surface that improves trust without
  forcing OrbitVerify into a graph schema prematurely?
- RQ2: What diagnostics format should OrbitVerify use so the UI can display it
  consistently with graph diagnostics?
- RQ3: How do we enforce schema validation without making runtime dependencies
  brittle for OSS users?

## 3) Decision and approach

Decision (v0.1): implement **config-first validation and diagnostics** for
OrbitVerify.

Approach:
- Publish an Orbit pass envelope JSON Schema (`v0.1`) under `schemas/`.
- Add a deterministic semantic diagnostics function that checks:
  - required fields,
  - known-sense numeric ranges (elevation, distance, non-negativity),
  - consistency checks (monotonic times, dt vs sample spacing) as warnings.
- Add API endpoints:
  - `POST /v0/orbit/pass/validate` returning diagnostics
  - `POST /v0/orbit/pass/run` includes diagnostics in the run response (for audit)
- Extend the web UI Orbit Pass mode to surface diagnostics in a dedicated tab.

## 4) Acceptance criteria

- JSON Schema exists for Orbit pass envelope config v0.1.
- API supports `POST /v0/orbit/pass/validate` and returns structured diagnostics.
- `POST /v0/orbit/pass/run` includes `diagnostics` in successful responses.
- Web Orbit Pass mode can:
  - validate current config and display diagnostics (errors + warnings),
  - run a valid config and show artifact paths + results JSON.
- Automated gates pass:
  - `py -m pytest -q`
  - `py scripts/release/release_gate_check.py`
  - `cd web && npm run lint`
  - `cd web && npm run build`

## 5) Non-goals (v0.1)

- No orbit propagator (still sample-envelope based).
- No authenticated artifact hosting / file serving.
- No conversion of OrbitVerify into a component graph profile yet.

