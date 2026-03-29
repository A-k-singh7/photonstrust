# User Quickstart

This is the shortest path to seeing PhotonTrust work.

## Option 1: Generate a Reliability Card

```bash
pip install -e .
photonstrust run configs/quickstart/qkd_quick_smoke.yml --output results/smoke_quick
photonstrust card validate results/smoke_quick/demo1_quick_smoke/nir_850/reliability_card.json
```

Expected outcome:

- `results/smoke_quick/run_registry.json`
- `results/smoke_quick/demo1_quick_smoke/nir_850/reliability_card.json`
- `results/smoke_quick/demo1_quick_smoke/nir_850/report.html`
- `results/smoke_quick/demo1_quick_smoke/nir_850/report.pdf`

## Option 2: Compile a QKD Graph

```bash
photonstrust graph compile graphs/demo8_qkd_link_graph.json --output results/graphs_demo
```

Expected outcome:

- `results/graphs_demo/demo8_qkd_link/compiled_config.yml`
- `results/graphs_demo/demo8_qkd_link/assumptions.md`

## Option 3: Launch the Product UI

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

Use `product-ui.md` for the maintained UI walkthrough.

## Where to Go Next

- `../guide/getting-started.md`
- `../guide/reliability-card.md`
- `../guide/limitations.md`
- `product-ui.md`
- `../../configs/README.md`
