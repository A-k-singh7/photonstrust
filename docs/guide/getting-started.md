# Getting Started with PhotonTrust

This guide is the exact first-run path for PhotonTrust's current wedge:
generate a QKD reliability card, inspect the report outputs, and compile a
graph into a runnable config.

## 1. Requirements

- Python `3.12+`
- Node.js only if you want the React product UI

The base QKD quickstart does not require QuTiP, Qiskit, or JAX.

## 2. Install from Source

```bash
git clone https://github.com/photonstrust/photonstrust.git
cd photonstrust
pip install -e .
```

If you want the local product UI as well:

```bash
pip install -e .[api]
cd web
npm ci
cd ..
```

## 3. First Working QKD Run

Inspect the available protocol surface:

```bash
photonstrust list protocols
```

Run the curated quick smoke config:

```bash
photonstrust run configs/quickstart/qkd_quick_smoke.yml --output results/smoke_quick
```

This produces a run registry plus a scenario/band output folder. The main files
to inspect are:

- `results/smoke_quick/run_registry.json`
- `results/smoke_quick/demo1_quick_smoke/nir_850/reliability_card.json`
- `results/smoke_quick/demo1_quick_smoke/nir_850/report.html`
- `results/smoke_quick/demo1_quick_smoke/nir_850/report.pdf`
- `results/smoke_quick/demo1_quick_smoke/nir_850/results.json`

Validate the generated reliability card:

```bash
photonstrust card validate results/smoke_quick/demo1_quick_smoke/nir_850/reliability_card.json
```

## 4. Compile a Graph into a Runnable Config

Compile the shipped QKD graph example:

```bash
photonstrust graph compile graphs/demo8_qkd_link_graph.json --output results/graphs_demo
```

The compiler writes:

- `results/graphs_demo/demo8_qkd_link/compiled_config.yml`
- `results/graphs_demo/demo8_qkd_link/assumptions.md`
- `results/graphs_demo/demo8_qkd_link/compile_provenance.json`
- `results/graphs_demo/demo8_qkd_link/graph.json`

This is the quickest way to see how PhotonTrust turns graph-level authoring into
a concrete engine config.

## 5. Optional Product UI Path

Launch the current React-first product surface:

```bash
py scripts/dev/start_product_local.py
```

Open:

- UI: `http://127.0.0.1:5173`
- API health: `http://127.0.0.1:8000/healthz`

Use `../user/product-ui.md` for the maintained UI walkthrough.

## 6. Optional Extras

Install extras only when you need them:

- `pip install -e .[api]`
  - FastAPI plus the local product workflow
- `pip install -e .[qutip]`
  - QuTiP-backed emitter or physics paths
- `pip install -e .[qiskit]`
  - Qiskit-dependent flows
- `pip install -e .[dev]`
  - contributor tooling and tests

JAX is not a base dependency. Install it only for the paths that explicitly
require it.

## 7. Next Docs

- `use-cases.md`
  - choose the right path for your role
- `reliability-card.md`
  - understand the central artifact
- `limitations.md`
  - understand assumptions and trust boundaries
- `../reference/cli.md`
  - concise command reference
- `../reference/config.md`
  - where configs live and what outputs they generate
