# Research Brief

## Metadata
- Work item ID: PT-PHASE-20
- Title: Run browser + run diff v0.1 (managed-service hardening, local dev)
- Authors: PhotonTrust core team
- Date: 2026-02-13
- Related modules (planned/expected):
  - `photonstrust/api/server.py`
  - `photonstrust/api/runs.py`
  - `web/`

## 1) Problem and motivation

Phase 19 added a run registry and safe artifact serving endpoints, but the web UI
still treats these as incidental details (paths/links on a single run view).

To move toward a trustable verification platform, we need a first-class workflow
for:
- browsing prior runs (what exists, when it ran, what input it used),
- opening artifacts without filesystem access, and
- comparing two runs ("what changed?") in a structured, review-friendly way.

This phase adds a minimal run browser (web) and a minimal run diff surface (API
and web), without introducing DB/auth/object storage.

## 2) Key research questions

- RQ1: What is the smallest UI surface that makes runs reviewable and reusable?
- RQ2: What diff format is stable enough for "review artifacts" and future
  automation (approvals, regression checks, drift detection)?
- RQ3: How do we keep diffs bounded (avoid giant payloads) while still being
  decision-useful?

## 3) Decision and approach

Decision (v0.1):
- Add a `Runs` mode in the web UI that lists runs via `GET /v0/runs` and can
  fetch a full manifest via `GET /v0/runs/{run_id}`.
- Add an API endpoint that returns a structured diff between two run manifests,
  scoped to the `input` blocks by default (not the full artifacts/results).

Diff representation:
- Use JSON Pointer-like paths for field addressing (stable, machine readable).
- Represent changes as a list of `(path, lhs, rhs)` tuples plus counts.
- Keep diffs bounded: limit total changes returned (and allow a scope parameter).

## 4) Acceptance criteria

- API exposes:
  - `POST /v0/runs/diff`
    - returns a bounded, structured diff between two manifests.
- Web UI supports:
  - listing runs (`GET /v0/runs`)
  - viewing a run manifest (`GET /v0/runs/{run_id}`)
  - diffing two runs (via `POST /v0/runs/diff`)
- Automated gates pass:
  - `py -m pytest -q`
  - `py scripts/release_gate_check.py`
  - `cd web && npm run lint`
  - `cd web && npm run build`

## 5) Non-goals

- No authentication, multi-user identity, or org/project permissions in v0.1.
- No database-backed run indexing in v0.1.
- No "diff of physics results" in v0.1 (that requires stable output summaries
  and possibly domain-specific comparison semantics).

## 6) Primary references (standards anchors)

- JSON Pointer (RFC 6901):
  https://www.rfc-editor.org/rfc/rfc6901
- JSON Patch (RFC 6902):
  https://www.rfc-editor.org/rfc/rfc6902
- W3C PROV overview (provenance concepts):
  https://www.w3.org/TR/prov-overview/

