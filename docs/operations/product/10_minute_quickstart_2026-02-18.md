# PhotonTrust 10-Minute Quickstart (Week 4)

This quickstart brings up the product wedge end-to-end:
`QKD run build -> run -> decision -> compare -> evidence`.

## 0) Prerequisites (1-2 min)

- Python 3.10+ available (`py -3 --version` on Windows).
- Clean clone of this repository.
- Terminal opened at repo root (`photonstrust/`).

## 1) Install React + API dependencies (2-3 min)

```bash
py -3 -m pip install -e .[api]
cd web
npm ci
cd ..
```

## 2) Start API + UI in one command (1 min)

```bash
py -3 scripts/dev/start_product_local.py
```

Expected startup output includes:
- API health URL: `http://127.0.0.1:8000/healthz`
- UI URL: `http://127.0.0.1:5173`

Keep this terminal running.

## 3) Run the golden path in UI (2-3 min)

In browser at `http://127.0.0.1:5173`:

1. Confirm the landing workspace appears and the sample project is prepared.
2. Click `Guided QKD quickstart` or `Continue to workspace`.
3. Confirm API health reaches `ok`.
4. Open `Compare` or `Certify` after selecting a run.
5. Confirm decision packet export/publish actions are available.

Telemetry is written to:
- `results/product_local/ui_metrics/events.jsonl`

## 4) Run pilot demo script (3 scenarios) (2-3 min)

Open a second terminal at repo root:

```bash
py -3 scripts/product/run_product_pilot_demo.py --project-id pilot_demo_week4
```

Outputs are written under:
- `results/product_pilot_demo/<timestamp>/pilot_demo_summary.json`
- `results/product_pilot_demo/<timestamp>/pilot_demo_summary.md`
- `results/product_pilot_demo/<timestamp>/raw/*.request.json`
- `results/product_pilot_demo/<timestamp>/raw/*.response.json`

## 5) Stop services

Press `Ctrl+C` in the launcher terminal running `start_product_local.py`.

## 6) Run automated readiness gate (optional, recommended)

This gate runs API health, one QKD run, PIC chain + MZI simulations, and the 3-case pilot script in fail-closed mode:

```bash
py -3 scripts/product/product_readiness_gate.py --spawn-api
```

Report output:
- `results/product_readiness/product_readiness_report.json`

## Troubleshooting

- API not reachable:
  - Re-run `py -3 scripts/dev/start_product_local.py`.
  - Confirm `http://127.0.0.1:8000/healthz` returns JSON.
- Web port already in use:
  - Re-run `py -3 scripts/dev/start_product_local.py --web-port 5174`.
- Streamlit surface needed instead:
  - Run `py -3 scripts/dev/start_product_local.py --surface streamlit`.
- Pilot demo health check fails:
  - Ensure launcher is still running and API host/port match `--api-base-url`.
