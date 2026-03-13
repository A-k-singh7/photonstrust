# PhotonTrust React Product Surface

This folder contains the React/Vite product shell for PhotonTrust. It now covers
the main self-serve workflow:

- seeded project bootstrap
- graph editing and execution against the local API
- run registry, compare, certify, and export flows
- project-backed workspace persistence for restore across reloads
- publish + verify evidence bundle actions

## Run (local dev)

Recommended: use the repo-level launcher from the project root:

```bash
pip install -e .[api]
cd web
npm ci
cd ..
py scripts/dev/start_product_local.py
```

Manual split-terminal flow:

```bash
cd photonstrust
py scripts/dev/run_api_server.py --reload

cd web
npm ci
npm run dev
```

Open the URL printed by Vite (typically `http://127.0.0.1:5173`).

## Notes

- The API server enables:
  - `POST /v0/graph/compile`
  - `POST /v0/qkd/run`
  - `POST /v0/pic/simulate`
  - `POST /v0/projects/bootstrap`
  - `GET/PUT /v0/projects/{project_id}/workspace`
  - approvals, bundle publish, and published-bundle verify routes
- For security, the API server rejects `pic.touchstone_2port` (it would require
  server-side file reads). Use the CLI Touchstone workflows for that.
