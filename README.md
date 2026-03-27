# PhotonTrust
[![tapeout-gate](https://github.com/photonstrust/photonstrust/actions/workflows/tapeout-gate.yml/badge.svg?branch=main)](https://github.com/photonstrust/photonstrust/actions/workflows/tapeout-gate.yml)
[![cv-quick-verify](https://github.com/photonstrust/photonstrust/actions/workflows/cv-quick-verify.yml/badge.svg?branch=main)](https://github.com/photonstrust/photonstrust/actions/workflows/cv-quick-verify.yml)

PhotonTrust is an open-source digital twin and reliability card generator for
teams evaluating photonic quantum links, starting with QKD scenarios and
producing shareable artifacts such as `reliability_card.json`, HTML/PDF reports,
and graph-compile assumptions.

## Status

- Status: public beta / research-grade engineering platform
- Python: `3.12+`
- License: `AGPL-3.0-only`
- Primary product wedge today: QKD link simulation to reliability evidence
- Expansion surfaces in the repo: graph compile, PIC simulation, orbit/satellite
  workflows, and certification/evidence tooling

## Why This Exists

PhotonTrust is trying to solve a specific problem: teams can simulate quantum
link behavior, but they often cannot turn those results into reviewable,
reproducible reliability evidence quickly enough to compare options or make
deployment decisions.

The repo therefore leads with one wedge:

- model a photonic quantum link
- generate a reliability card and report
- keep the assumptions, evidence quality, and provenance visible

## 5-Minute Proof

Install the repo locally:

```bash
pip install -e .
```

Inspect the currently registered protocol surface:

```bash
photonstrust list protocols
```

Run the shortest working QKD path:

```bash
photonstrust run configs/quickstart/qkd_quick_smoke.yml --output results/smoke_quick
photonstrust card validate results/smoke_quick/demo1_quick_smoke/nir_850/reliability_card.json
```

Compile a graph into a runnable QKD config:

```bash
photonstrust graph compile graphs/demo8_qkd_link_graph.json --output results/graphs_demo
```

Expected outputs:

- `results/smoke_quick/run_registry.json`
- `results/smoke_quick/demo1_quick_smoke/nir_850/reliability_card.json`
- `results/smoke_quick/demo1_quick_smoke/nir_850/report.html`
- `results/smoke_quick/demo1_quick_smoke/nir_850/report.pdf`
- `results/graphs_demo/demo8_qkd_link/compiled_config.yml`
- `results/graphs_demo/demo8_qkd_link/assumptions.md`

## Golden Paths

### Researcher

Use PhotonTrust when you want a runnable QKD scenario, explicit assumptions, and
an artifact you can compare or review.

Start here:

- `docs/guide/getting-started.md`
- `docs/guide/reliability-card.md`
- `configs/README.md`

Typical outcome:

- `reliability_card.json`
- `report.html`
- `report.pdf`
- `results.json`

### Product Evaluator

Use the React product surface when you want to inspect the current UX and
guided flows rather than work only from YAML and CLI outputs.

Start here:

```bash
pip install -e .[api]
cd web
npm ci
cd ..
py scripts/dev/start_product_local.py
```

Then use:

- `docs/user/quickstart.md`
- `docs/user/product-ui.md`

Typical outcome:

- local UI at `http://127.0.0.1:5173`
- local API health at `http://127.0.0.1:8000/healthz`
- the same run artifacts written under `results/`

### Maintainer

Use this path when you are changing behavior, docs, or workflow contracts and
need the repo to stay coherent.

Start here:

- `CONTRIBUTING.md`
- `docs/dev/git_and_docs_workflow.md`
- `docs/dev/testing.md`

Typical outcome:

- clean `git diff --check`
- passing docs smoke tests via `pytest -q tests/test_docs_experience.py`
- updated docs, examples, and changelog in the same branch

## UI Preview

![PhotonTrust landing](docs/assets/ui-landing.png)

![Decision review flow](docs/assets/ui-decision-review.png)

## Visible Proof

- Checked-in evidence pack:
  `docs/results/phase5b_rc_artifact_pack_20260216T075629Z/README.md`
- Curated UI screenshots:
  `docs/assets/README.md`
- Current config catalog:
  `configs/README.md`

## What It Is Not

- not a substitute for lab calibration, benchmark ingestion, or field
  validation
- not a full security proof for a deployed QKD system
- not yet a front-door "AI photonic chip design" product, even though the repo
  contains PIC and inverse-design adjacent building blocks
- not a guarantee that every research or historical document under `docs/`
  describes the current supported product surface

## Documentation Map

- `docs/guide/getting-started.md`
  - exact first run, outputs, and next steps
- `docs/guide/use-cases.md`
  - who should use which path
- `docs/guide/reliability-card.md`
  - what the central artifact means
- `docs/guide/limitations.md`
  - assumptions, fidelity, and when not to trust an output
- `docs/reference/README.md`
  - CLI and config references
- `docs/research/README.md`
  - background, deep technical context, and roadmap material
- `docs/README.md`
  - full documentation index

## Supported Surfaces Today

- `photonstrust run`
  - run QKD and related YAML-driven scenarios
- `photonstrust graph compile`
  - turn graph inputs into runnable QKD configs or PIC netlists
- `photonstrust pic simulate`
  - simulate compiled PIC netlists
- `photonstrust card validate`
  - validate generated reliability card artifacts
- `web/`
  - current React-first product surface
- `ui/`
  - legacy Streamlit surface retained for compatibility

## Optional Extras

Install only the extras needed for your path:

- `pip install -e .[api]`
  - local FastAPI + React product workflow
- `pip install -e .[qutip]`
  - QuTiP-backed physics paths
- `pip install -e .[qiskit]`
  - Qiskit-dependent flows
- `pip install -e .[dev]`
  - contributor tooling and test dependencies

JAX is not required for the base QKD quickstart. Install it only for the
specific flows that request it.

## Repository Layout

- `photonstrust/`
  - core Python package and CLI
- `web/`
  - React/Vite product surface
- `ui/`
  - legacy Streamlit UI
- `configs/`
  - runnable scenario definitions
- `graphs/`
  - graph compiler inputs
- `examples/`
  - lightweight code and notebook examples
- `scripts/`
  - validation, release, and maintainer automation
- `docs/`
  - maintained docs, research, assets, and checked-in evidence
- `schemas/`
  - JSON schemas for configs and artifacts
- `results/`
  - generated outputs and selected checked-in artifact packs
