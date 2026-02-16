# PhotonTrust Web Editor (Phase 13 MVP)

This folder contains the PhotonTrust drag-drop graph editor (Vite + React Flow)
used for local development of the managed-service surface.

The UI edits **graph JSON** (`schemas/photonstrust.graph.v0_1.schema.json`) and
calls the local PhotonTrust API to compile + execute using the Python engine.

## Run (local dev)

Start the backend API (from repo root):

```bash
cd photonstrust
py scripts/run_api_server.py --reload
```

Start the web dev server (separate terminal):

```bash
cd photonstrust/web
npm ci
npm run dev
```

Open the URL printed by Vite (typically `http://127.0.0.1:5173`).

## Notes

- The API server is a **dev surface**. It enables:
  - `POST /v0/graph/compile`
  - `POST /v0/qkd/run`
  - `POST /v0/pic/simulate`
- For security, the API server rejects `pic.touchstone_2port` (it would require
  server-side file reads). Use the CLI Touchstone workflows for that.
