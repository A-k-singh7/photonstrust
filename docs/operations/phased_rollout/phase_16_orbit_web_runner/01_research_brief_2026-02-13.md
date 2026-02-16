# Research Brief

## Metadata
- Work item ID: PT-PHASE-16
- Title: OrbitVerify web runner v0.1 (config-first pass envelopes)
- Authors: PhotonTrust core team
- Date: 2026-02-13
- Related modules (planned/expected):
  - `photonstrust/orbit/pass_envelope.py` (existing)
  - `photonstrust/api/server.py` (extend)
  - `web/` (extend editor UI with orbit runner mode)

## 1) Problem and motivation

PhotonTrust already supports OrbitVerify pass envelopes via CLI (`photonstrust run`
detecting `orbit_pass` configs) and generates:
- `orbit_pass_results.json`
- `orbit_pass_report.html`

Phase 13–15 established a web workflow for graph profiles (QKD + PIC) with:
- API endpoints,
- trust panel registry, and
- structured diagnostics.

OrbitVerify is not yet accessible through the web workflow. For adoption, teams
need a quick, reproducible **web-runner** that:
- edits a pass envelope config,
- runs it through the backend engine, and
- returns the same trust artifacts (assumptions/provenance + stable paths).

## 2) Key research questions

- RQ1: Should OrbitVerify be graph-first like QKD/PIC, or config-first?
- RQ2: What is the smallest web surface that preserves scientific integrity?
- RQ3: How do we return artifacts (HTML report, results JSON) without requiring
  production deployment assumptions (auth/storage) yet?

## 3) Decision and approach

Decision (v0.1): **config-first OrbitVerify runner**.

Rationale:
- OrbitVerify’s current model is already config-shaped and time-series oriented.
- A graph-first Orbit profile would require a schema/compiler expansion and a
  larger UI palette, which is better done after the runner is usable.

Approach:
- Add an API endpoint that accepts an Orbit pass config dict, executes
  `run_orbit_pass_from_config`, and returns:
  - output paths (results + HTML),
  - the parsed results JSON for immediate UI inspection.
- Add a new web UI mode “Orbit Pass” with a JSON editor and template, using the
  same topbar `Run` button and right-side output panel.

## 4) Acceptance criteria

- API supports `POST /v0/orbit/pass/run` and writes the same artifacts as CLI.
- Web can:
  - load a default pass envelope template,
  - run it via API,
  - display the returned results JSON and artifact paths.
- Automated gates pass:
  - `py -m pytest -q`
  - `py scripts/release_gate_check.py`
  - `cd web && npm run lint`
  - `cd web && npm run build`

## 5) Non-goals

- No Orbit graph schema/profile in v0.1.
- No authenticated artifact hosting.
- No orbit propagator (still envelope-based sampling).

## 6) Decision

- Decision: Proceed.

