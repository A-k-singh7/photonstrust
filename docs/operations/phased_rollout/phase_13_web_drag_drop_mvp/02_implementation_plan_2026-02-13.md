# Implementation Plan

## Metadata
- Work item ID: PT-PHASE-13
- Title: Web drag-drop MVP v0.1 (managed service surface)
- Date: 2026-02-13

## 1) Deliverables

### 1.1 Backend API (local dev server)
- Add:
  - `photonstrust/api/__init__.py`
  - `photonstrust/api/server.py`
- Optional dependency group:
  - add `api = ["fastapi", "uvicorn"]` to `pyproject.toml`
- Endpoints (v0):
  - `GET /healthz`
  - `POST /v0/graph/compile` -> returns compiled artifacts (in-memory)
  - `POST /v0/qkd/run` -> compiles + runs QKD preview, returns results + card JSON
  - `POST /v0/pic/simulate` -> compiles + simulates PIC netlist, returns results JSON

### 1.2 Web app (React Flow editor)
- Add `web/` as a Vite + React app:
  - palette of component nodes (QKD + PIC)
  - port-aware handles for PIC components
  - parameter inspector panel
  - export graph JSON and import graph JSON
  - compile and run buttons calling the backend API

### 1.3 Docs and demos
- Add:
  - `docs/operations/phased_rollout/phase_13_web_drag_drop_mvp/` build + validation artifacts
  - `README.md` instructions:
    - run backend API server
    - run web app dev server

## 2) Validation gates
- Unit tests still pass:
  - `py -m pytest -q`
- Manual MVP validation:
  1. start API server
  2. start web dev server
  3. build a QKD link graph in UI and run preview
  4. build a PIC graph (including a coupler/MZI) and run simulation

## 3) Non-goals (explicit)
- No auth/multi-tenant org model in v0.1.
- No persistent database in v0.1 (local artifacts only).
- No production deployment hardening yet.

