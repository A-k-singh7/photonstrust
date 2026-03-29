# Architecture and Interfaces

This document defines the technical architecture, core interfaces, and data
contracts required to keep the system modular and adoptable.

## High-Level Architecture
- Physics layer: QuTiP models and trajectories
- Network kernel: discrete-event simulation and topologies
- Protocol compiler: Qiskit circuits for swap/purify/teleport
- Calibration and uncertainty: Bayesian inference + propagation
- Optimization: multi-objective decision layer
- Reporting: Reliability Card + PDF/HTML outputs
- UI: run registry/comparisons + external drag-drop graph builder

## Module Boundaries
- photonstrust.physics: emitter, memory, detector models
- photonstrust.events: event kernel and scheduler
- photonstrust.channels: fiber and classical channel models
- photonstrust.protocols: Qiskit circuit library + executor hooks
- photonstrust.calibrate: posterior inference + priors
- photonstrust.optimize: spacing and resource optimization
- photonstrust.report: reliability card generation
- photonstrust.ui: run registry and comparisons
- photonstrust.graph: graph schema, validators, graph->scenario compiler
- photonstrust.components: component libraries (e.g., PIC primitives)
- photonstrust.pic: PIC netlist simulation and ChipVerify foundations
- photonstrust.layout: layout utilities (route-level extract; optional GDS seam)
- photonstrust.layout.pic: deterministic PIC layout artifacts (ports/routes/provenance) + optional GDS + optional KLayout runner seam
- photonstrust.orbit: OrbitVerify mission templates (pass envelopes + metadata)
- photonstrust.api: local dev API surface (compile/run/simulate endpoints for web UI)
- photonstrust.spice: SPICE export + optional simulator runner seams (ngspice)

## Data Contracts (Minimum)
### ScenarioConfig
- band, wavelength_nm
- source, memory, detector, channel, timing
- protocol settings
- random seed and backend selection

### Physics Stats
- EmissionStats: p_emit, g2_0, hist, variance
- MemoryStats: p_store, p_retrieve, fidelity, variance
- DetectionStats: p_click, p_false, hist, variance

### Reliability Card
- inputs, derived, outputs, error budget
- uncertainty bounds
- reproducibility metadata
- compliance metadata (planned): EAR/ITAR/FCC/qualification tags

### GraphConfig (v0.1)
- node and edge definitions
- component parameter payload per node
- scenario profile type (`qkd_link` | `pic_circuit`)
- `qkd_link` graphs require a top-level `scenario` object
- `pic_circuit` graphs require a top-level `circuit` object + `edges`
- compile diagnostics and validation warnings

### PICNetlist (v0.1)
- normalized node/edge list with optional port connectivity (`from_port`/`to_port`)
- explicit `circuit.wavelength_nm` and optional `circuit.inputs/outputs`
- deterministic topological order when required for execution

### PIC Layout Build Report (v0.1)
- deterministic artifacts for layout-aware verification:
  - `ports.json` (port markers + coordinates)
  - `routes.json` (Manhattan polylines)
  - `layout_provenance.json` (hashes + tool versions)
  - optional `layout.gds` when `gdstk` is installed (`photonstrust[layout]`)
- schema:
  - `schemas/photonstrust.pic_layout_build.v0.schema.json`

### PIC LVS-lite Report (v0.1)
- expected vs observed connectivity mismatch summaries (CI-friendly; not full foundry LVS)
- schema:
  - `schemas/photonstrust.pic_lvs_lite.v0.schema.json`

### PIC SPICE Export Report (v0.1)
- deterministic SPICE-like netlist export + mapping artifacts (interop seam)
- schema:
  - `schemas/photonstrust.pic_spice_export.v0.schema.json`

### OrbitPassEnvelope (v0.1)
- explicit time-segmented samples with:
  - `t_s`, `distance_km`, `elevation_deg`, `background_counts_cps`
- explicit `dt_s` for integrating key rate over a pass
- explicit `cases` for best/median/worst parameter overrides

### RunManifest (v0.1)
- run metadata: `run_id`, `run_type`, `generated_at`, `output_dir`
- `input`: stable identifiers/hashes for replay and review
  - includes `project_id` for grouping/filtering (managed-service governance)
- `outputs_summary`: small domain-aware summaries intended for review diffs
- `artifacts`: served relpaths (API artifact serving)
- `provenance`: engine/app version and environment

Graph schema and compiler (implemented, v0.1):
- Schema:
  - `schemas/photonstrust.graph.v0_1.schema.json`
- Demos:
  - `graphs/demo8_qkd_link_graph.json`
  - `graphs/demo8_pic_circuit_graph.json`
- CLI:
  - `photonstrust graph compile <graph.json> --output <dir>`

## Interface Contracts
- physics.simulate_emitter(source_cfg) -> EmissionStats
- physics.simulate_memory(memory_cfg, wait_time_ns) -> MemoryStats
- physics.simulate_detector(detector_cfg, arrival_times_ps) -> DetectionStats
- events.EventKernel.schedule/run
- protocols.compile_protocol(cfg) -> graph
- graph.compile(graph_cfg) -> ScenarioConfig
- api: HTTP endpoints for compile/run:
  - `GET /healthz`
  - `GET /v0/registry/kinds`
  - `GET /v0/runs`
  - `GET /v0/runs/{run_id}`
  - `GET /v0/runs/{run_id}/artifact?path=<relative>`
  - `POST /v0/runs/diff` (scope: `input` | `outputs_summary` | `all`)
  - `GET /v0/projects`
  - `GET /v0/projects/{project_id}/approvals`
  - `POST /v0/projects/{project_id}/approvals`
  - `POST /v0/performance_drc/crosstalk`
  - `POST /v0/graph/validate`
  - `POST /v0/graph/compile`
  - `POST /v0/qkd/run`
  - `POST /v0/orbit/pass/validate`
  - `POST /v0/orbit/pass/run`
  - `POST /v0/pic/simulate`
  - `POST /v0/pic/layout/build`
  - `POST /v0/pic/layout/lvs_lite`
  - `POST /v0/pic/spice/export`
  - `POST /v0/pic/invdesign/mzi_phase`

Note: `POST /v0/performance_drc/crosstalk` supports both:
- scalar mode: `gap_um` + `parallel_length_um`
- route mode: `routes` + optional `layout_extract` (extracts parallel-run segments and evaluates a worst-case envelope)

Optional layout ingestion (dev seam):
- `photonstrust[layout]` adds `gdstk` and enables `photonstrust.layout.gds_extract.extract_routes_from_gds()`
  to convert a GDS layout into the `routes[*]` contract (then reuse the route-level extractor).

Optional external EDA tool seams (dev posture):
- KLayout batch macro runner (no hard dependency):
  - `photonstrust/layout/pic/klayout_runner.py`
- ngspice batch runner (no hard dependency):
  - `photonstrust/spice/ngspice_runner.py`

## Backwards Compatibility
- Keep JSON schemas versioned
- Add new fields with default fallbacks
- Avoid breaking CLI behavior

## Adoption Checklist
- Provide stable APIs and documented schemas
- Maintain optional dependencies (QuTiP/Qiskit/ReportLab/Streamlit)
- Ensure CLI runs without full-fidelity backends
- Keep frontend/UI thin; enforce backend scientific source of truth

## Web Research Extension (2026-02-12)
See `12_web_research_update_2026-02-12.md` section `02 Architecture and interfaces: standards alignment`.
