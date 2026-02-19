# PhotonTrust Repository Capabilities (2026-02-18)

This document captures the implemented capabilities in this repo as of February 18, 2026.

Primary source files used:
- `README.md`
- `photonstrust/cli.py`
- `photonstrust/api/server.py`
- `photonstrust/qkd_protocols/registry.py`
- `photonstrust/registry/kinds.py`
- `ui/app.py`
- `scripts/*.py`

## 1. Core Product Scope

PhotonTrust is a photonic quantum-link digital twin focused on:
- QKD simulation and reliability evaluation.
- PIC simulation and design/verification workflows.
- Reliability card generation with provenance and policy metadata.
- Productized local workflows (API + UI + pilot/demo + readiness gates).

## 2. QKD Capabilities

### 2.1 Protocol Families

Implemented protocol surfaces in the dispatch registry:
- `BBM92` (with `E91` alias)
- `BB84 Decoy` (aliases include `BB84`)
- `MDI_QKD`
- `AMDI_QKD` (asynchronous / mode-pairing MDI family)
- `PM_QKD`
- `TF_QKD` (Twin-Field variant over PM core model path)

File: `photonstrust/qkd_protocols/registry.py`

### 2.2 Channel and Device Modeling

QKD channel/device stack supports:
- Fiber and free-space channel models.
- Source models: emitter-cavity and SPDC.
- Detector classes and timing models (registry-driven parameter schemas).
- Protocol-specific parameter sets for direct-link and relay-based protocols.

File: `photonstrust/registry/kinds.py`

### 2.3 Scenario and Sweep Execution

CLI and API support:
- Single scenario runs.
- Matrix sweeps and summary CSV outputs.
- Config validation (`--validate-only`).
- Repeater optimization, heralding comparison, teleportation, source benchmark flows via config paths.

Files:
- `photonstrust/cli.py`
- `photonstrust/sweep.py` (invoked by CLI/API)

## 3. Reliability Card and Evidence Outputs

### 3.1 Reliability Card Versions

Implemented card generations:
- Reliability Card `v1.0`
- Reliability Card `v1.1`

File: `photonstrust/report.py`

### 3.2 Card Metadata and Trust Fields

Generated cards include:
- Safe-use label and rationale.
- Confidence interval summaries.
- Finite-key surrogate metadata and epsilon ledger fields.
- Model provenance and protocol-family provenance.
- Security assumptions metadata.
- Operating envelope fields.

File: `photonstrust/report.py`

### 3.3 Evidence and Bundles

Implemented tooling:
- Evidence bundle export/sign/verify.
- Signature verification with Ed25519.
- Release packet refresh and verification checks.

Files:
- `photonstrust/cli.py` (`bundle` command family)
- `scripts/sign_release_gate_packet.py`
- `scripts/verify_release_gate_packet.py`
- `scripts/verify_release_gate_packet_signature.py`

## 4. PIC Capabilities

### 4.1 Simulation

PIC simulation supports:
- Simulate compiled netlist at single wavelength.
- Wavelength sweep simulation.
- Chain/DAG/scattering solver result surfaces (depending on circuit setup).

Files:
- `photonstrust/cli.py` (`pic simulate`)
- `photonstrust/api/server.py` (`POST /v0/pic/simulate`)

### 4.2 Inverse Design

Available inverse-design APIs:
- MZI phase optimization.
- Coupler-ratio optimization.
- Workflow chaining and replay for PIC inverse design flows.

Files:
- `photonstrust/api/server.py` endpoints:
  - `/v0/pic/invdesign/mzi_phase`
  - `/v0/pic/invdesign/coupler_ratio`
  - `/v0/pic/workflow/invdesign_chain`
  - `/v0/pic/workflow/invdesign_chain/replay`

### 4.3 Layout and Verification

Implemented PIC downstream flows:
- Layout build.
- LVS-lite.
- KLayout artifact pack run.
- Foundry DRC run surface.
- SPICE export.
- Crosstalk performance DRC.

Files:
- `photonstrust/api/server.py` endpoints:
  - `/v0/pic/layout/build`
  - `/v0/pic/layout/lvs_lite`
  - `/v0/pic/layout/klayout/run`
  - `/v0/pic/layout/foundry_drc/run`
  - `/v0/pic/spice/export`
  - `/v0/performance_drc/crosstalk`

### 4.4 API Safety Constraint

Security-relevant constraint:
- `pic.touchstone_2port` is intentionally disabled in API server mode (file-access prevention path); CLI workflows are expected for that lane.

File: `photonstrust/api/server.py`

## 5. Orbit / Mission Envelope Capabilities

Implemented orbit-pass flows:
- Orbit pass config validation.
- Orbit pass run and report generation.

Interfaces:
- CLI path via config (`orbit_pass` branch in `photonstrust/cli.py`)
- API endpoints:
  - `/v0/orbit/pass/validate`
  - `/v0/orbit/pass/run`

## 6. Graph and Schema Capabilities

Implemented graph tooling:
- Graph compile from JSON/TOML GraphSpec.
- Graph schema/semantic validation.
- GraphSpec canonical formatting and stable hash output.

Files:
- `photonstrust/cli.py` (`graph compile`, `fmt graphspec`)
- `photonstrust/api/server.py` (`/v0/graph/validate`, `/v0/graph/compile`)

## 7. API Capabilities

### 7.1 Core Service Endpoints

Implemented endpoint families:
- Health and kind registry.
- Runs and artifacts retrieval.
- Jobs and async run status.
- Run diff.
- Project approvals.
- QKD run / async run / external import.
- Orbit pass.
- PIC simulation and workflow chain endpoints.
- Evidence/bundle retrieval and verification.

Primary file: `photonstrust/api/server.py`

### 7.2 Auth and Scope Controls

Implemented auth modes:
- `PHOTONTRUST_API_AUTH_MODE=off|header`
- Header mode supports actor/roles/project scope enforcement.
- Project-scope deny logic for non-admin roles.

File: `photonstrust/api/server.py`

### 7.3 CORS Controls

Implemented CORS allow-list configuration:
- `PHOTONTRUST_API_CORS_ALLOW_ORIGINS` env variable.
- Localhost defaults when unset.

File: `photonstrust/api/server.py`

## 8. User Interfaces

### 8.1 Streamlit Workbench

Current Streamlit tabs:
- `Capabilities Console`
- `Run Builder`
- `PIC`
- `Run Registry`
- `Dataset Entries`

Implemented Capabilities Console features:
- Full API and CLI capability matrix (domain, endpoint/command, startup value, UI coverage).
- Live platform snapshot (health, registry, run/project visibility).
- Runnable demo launcher for core flows:
  - platform smoke checks,
  - QKD sync/async runs,
  - external result import,
  - orbit validation + run,
  - PIC simulation and workflow chain,
  - performance DRC,
  - evidence bundle publish + verify.
- Captured run/job/digest IDs for evidence workflows and direct bundle download links.
- Capability catalog JSON export for investor/demo material packaging.

Implemented Run Builder features:
- API health check.
- Golden path run button.
- Decision summary rendering.
- Error diagnosis and recovery hints.
- Deterministic run profile export/import.
- UI telemetry emission.

Implemented Run Registry features:
- Multi-run comparison with delta metrics.
- Baseline promotion and candidate decision workflow.

Implemented PIC tab features:
- Template loading (PIC chain and PIC MZI).
- JSON graph editing and simulate calls.
- Single wavelength and sweep execution.
- Save PIC result bundle to `results/ui_pic_runs`.
- Download latest saved PIC bundle as ZIP.

File: `ui/app.py`

### 8.2 React Web Editor (Vite + React Flow)

Implemented web editor supports local dev graph editing and API execution for:
- Graph compile.
- QKD run.
- PIC simulate.

Files:
- `web/README.md`
- `web/src/App.jsx`

## 9. Product Packaging and Pilot Operations

Implemented Week-4 product scripts:
- `scripts/start_product_local.py`
  - One-command local boot for API + Streamlit.
  - Port preflight checks.
  - API health wait and smoke-mode auto stop.
- `scripts/run_product_pilot_demo.py`
  - 3-scenario pilot pack run with JSON/Markdown summary outputs.
- `scripts/product_readiness_gate.py`
  - Fail-closed product gate for API + QKD + PIC + pilot flow.
  - Machine-readable report output.

Related docs:
- `docs/operations/product/30_day_product_execution_board_2026-02-18.md`
- `docs/operations/product/10_minute_quickstart_2026-02-18.md`

## 10. Verification, QA, and Release Gates

Implemented verification tooling includes:
- CI checks orchestration (`scripts/ci_checks.py`).
- Production readiness isolated gate (`scripts/production_readiness_check.py`).
- Release gate checks and packet verification scripts.
- QuTiP parity lane and Qiskit lane scripts.
- Baseline generation and drift checks.
- Validation harness and recent-research comparison scripts.

Representative scripts:
- `scripts/ci_checks.py`
- `scripts/production_readiness_check.py`
- `scripts/release_gate_check.py`
- `scripts/run_qutip_parity_lane.py`
- `scripts/run_qiskit_lane.py`
- `scripts/check_benchmark_drift.py`
- `scripts/run_validation_harness.py`
- `scripts/compare_recent_research_benchmarks.py`

## 11. Data and Benchmark Operations

Implemented data operations:
- Benchmark dataset generation.
- Open benchmark checks.
- Measurement bundle ingestion.
- Artifact pack publication.
- Repro pack generation.

Representative scripts:
- `python -m photonstrust.datasets.generate ...`
- `scripts/check_open_benchmarks.py`
- `scripts/ingest_measurement_bundle.py`
- `scripts/publish_artifact_pack.py`
- `scripts/generate_repro_pack.py`

## 12. Artifact Locations

Default artifact conventions:
- General run outputs: `results/`
- UI telemetry: `results/ui_metrics/events.jsonl`
- UI run profiles: `results/ui_profiles/`
- UI baseline state: `results/ui_product_state/state.json`
- UI PIC bundles: `results/ui_pic_runs/`
- Product readiness report: `results/product_readiness/product_readiness_report.json`

## 13. Practical Capability Summary

If treated as a platform, the repo currently supports:
- Physics-grounded QKD and PIC simulation workflows.
- Multi-interface operation (CLI, API, Streamlit UI, React editor).
- Reliability/evidence generation and signed release-gate artifacts.
- Pilot/demo operation paths with machine-checkable readiness gates.
- Regression and quality controls suitable for ongoing hardening.
