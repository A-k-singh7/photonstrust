# Research Brief

## Metadata
- Work item ID: PT-PHASE-19
- Title: Run registry + artifact serving v0.1 (managed-service hardening, local dev)
- Authors: PhotonTrust core team
- Date: 2026-02-13
- Related modules (planned/expected):
  - `photonstrust/api/server.py` (extend with run registry endpoints)
  - `photonstrust/api/runs.py` (new helper module)
  - `web/` (optional: link to served artifacts)

## 1) Problem and motivation

PhotonTrust web workflows (Phases 13-18) can execute runs and write artifacts
to disk, but the UI currently receives only file paths. This blocks a central
platform goal: **trustable reproducibility and review**.

To behave like a serious verification platform, the system needs:
- a stable way to reference prior runs (a run registry),
- a safe way to retrieve artifacts (HTML/JSON/PDF) without asking users to
  browse local folders, and
- basic "audit trail" primitives (manifest with hashes, timestamps, provenance).

## 2) Key research questions

- RQ1: What is the minimum run registry that enables trust workflows without
  introducing heavy infra (DB/auth/object storage)?
- RQ2: How do we serve artifacts safely without turning the API into an
  arbitrary file server (path traversal / exfil risk)?
- RQ3: How do we keep this compatible with "open core" workflows (CLI remains
  valid; API is a thin managed surface)?

## 3) Decision and approach

Decision (v0.1): implement a **filesystem-backed run manifest** per run and a
**restricted artifact serving** endpoint.

Approach:
- Every API-generated run writes `run_manifest.json` in its run directory.
- The API exposes:
  - run listing (scan manifests under a configured runs root),
  - run detail (read manifest),
  - artifact retrieval (serve only files inside a specific run directory, via
    strict path validation + canonical path checks).
- The web UI can optionally show clickable links for "Open report" / "Open JSON"
  by targeting these endpoints.

## 4) Acceptance criteria

- API exposes:
  - `GET /v0/runs`
  - `GET /v0/runs/{run_id}`
  - `GET /v0/runs/{run_id}/artifact?path=<relative>`
- `qkd/run` and `orbit/pass/run` write `run_manifest.json`.
- Artifact serving is safe against path traversal and only serves files under
  the configured runs root.
- Automated gates pass:
  - `py -m pytest -q`
  - `py scripts/release/release_gate_check.py`
  - `cd web && npm run lint`
  - `cd web && npm run build`

## 5) Non-goals

- No auth, multi-user ACLs, or object storage integration.
- No long-term DB migration (SQLite/Postgres) in v0.1.
- No attempt to serve arbitrary files outside the runs root.
