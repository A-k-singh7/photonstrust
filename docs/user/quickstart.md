# User Quickstart

This is the shortest path to seeing PhotonTrust work.

## Option 1: CLI quick smoke

```bash
pip install -e .
photonstrust run configs/quickstart/qkd_quick_smoke.yml --output results/smoke_quick
```

Expected outcome:

- a successful QKD run
- artifacts written under `results/smoke_quick/`

## Option 2: React product UI

```bash
pip install -e .[api]
cd web
npm ci
cd ..
py scripts/dev/start_product_local.py
```

Open:

- UI: `http://127.0.0.1:5173`
- API health: `http://127.0.0.1:8000/healthz`

Recommended first actions:

1. `Guided QKD quickstart`
2. `Guided PIC quickstart`
3. `Open compare lab`

## Option 3: Orbit quickstart

```bash
photonstrust run configs/quickstart/orbit_pass_envelope.yml --output results/orbit_demo11
```

## Where to go next

- Config catalog: `../../configs/README.md`
- Examples: `../../examples/README.md`
- Product walkthrough: `../operations/product/10_minute_quickstart_2026-02-18.md`
