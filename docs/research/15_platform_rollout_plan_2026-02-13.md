# PhotonTrust Platform Rollout Plan (ChipVerify + OrbitVerify) (2026-02-13)

This document is the end-to-end build plan for expanding PhotonTrust into the
most trustable verification platform for:
- photonic chip workflows (`ChipVerify`), and
- free-space/satellite link workflows (`OrbitVerify`),

while keeping the physics core open-source for academic and university use.

It is written to be execution-grade: it defines the physics-engine expansion,
the product surfaces (drag-drop graph editor + managed execution), the trust
moats (uncertainty + diagnostics + provenance), and a strict multi-phase rollout
process.

---

## 0) What "Dominant and Trustable" Means (Non-negotiables)

PhotonTrust wins on trust by being falsifiable, reproducible, and auditable.
That implies the platform must enforce:
- Uncertainty on every externally consumable metric (not only point estimates).
- Diagnostics and "fit health" gates for every calibrated model.
- Provenance and replay: config hash, model version, seeds, and environment.
- Benchmark governance: drift detection, scenario versioning, and baselines.
- Mode semantics: explicit `preview` vs `certification` computation budgets,
  with the mode stored in exported artifacts.

Anything that cannot be made auditable must be labeled clearly as heuristic and
never presented as "certification quality".

---

## 1) Product Surfaces and Business Model (Open Core + Managed Service)

## Open core: `PhotonTrust OSS` (academic default)
- Python engine: physics models, channel models, protocol execution, calibration,
  uncertainty propagation, reliability card generation.
- CLI and reproducible run bundles.
- Public schemas (`schemas/`) and deterministic baseline tests (`tests/`).
- Benchmark fixtures and drift checks (at least for public scenarios).

## Managed service: ChipVerify/OrbitVerify (commercial)
- Drag-drop web app for component graphs.
- Managed execution (compute + caching + org projects).
- Controlled data capture (consent-based): run metadata + anonymized summaries,
  and optionally measurement datasets when customers opt in.
- Collaboration tooling: run registry, diffs, approvals, and audit trails.

Boundary rule: managed service adds operational leverage; it must not be
required for scientific validity.

---

## 2) Target Architecture (Engine, Compiler, UI, and Evidence)

## Engine (source of truth)
- Keep the engine in `photonstrust/` as the only place physics decisions live.
- Expand via additional component models and channel models, but keep interfaces
  stable and schema-validated.

## Graph compiler (UI -> scenarios)
- Introduce an explicit graph JSON schema ("component graph v0.1").
- Compiler maps graph nodes/edges into engine configs (`ScenarioConfig`-like
  dicts).
- The compiler is deterministic and versioned; it emits:
  - compiled config,
  - compiler version,
  - graph hash,
  - a human-readable "assumptions summary".

## UI (drag-drop authoring)
- Web editor (React + React Flow) for node/edge editing.
- Right-side panel shows:
  - component parameter definitions and units,
  - priors/uncertainties,
  - measured/calibrated values,
  - evidence tier and diagnostics.

## Evidence artifacts (what makes the platform "trustable")
- `reliability_card.json` (machine) + HTML/PDF (human).
- `performance.json` (mode/runtime and sampling settings).
- Provenance bundle: config, schema versions, model versions, seeds.
- Optional reproducibility pack: pinned environment spec + replay script.

---

## 3) Physics Core Expansion: What to Build Next (Scientist-first)

PhotonTrust's physics engine must expand along two axes:
1) more realistic components and channels, and
2) stronger evidence and calibration contracts around those models.

## 3.1 ChipVerify physics scope (PIC and packaging workflows)

The minimal set of "drag-drop chip verification" components should target
compact models used in real flows.

### Component families (v1)
- Passive linear components:
  - waveguide segment (loss, dispersion, polarization sensitivity),
  - coupler/splitter (coupling ratio, insertion loss, imbalance),
  - ring resonator (FSR, Q, coupling, thermal tuning),
  - interferometers (MZI blocks with phase shifters).
- I/O and packaging:
  - grating coupler / edge coupler,
  - fiber attach loss model,
  - packaging temperature drift model.
- Active components (as needed):
  - phase shifter (thermal / electro-optic), bandwidth, drift.
- Detectors/sources (already in scope, but must become "chip friendly"):
  - integrate existing detector/emitter models as nodes with explicit ports.

### Model interfaces (must support)
- "Compact model" interface: deterministic function or S-parameter-like mapping
  with uncertainties.
- Parameterization with process corners: nominal + variance and correlations.
- Optional CML-ish import surface:
  - treat imported compact models as black-box with declared validity range,
    and wrap them with uncertainty + provenance metadata.

### Verification flow (chip)
- Graph compiles to a composed model (e.g., cascaded transfer/scattering).
- Calibrate component parameters against measurement data (optional).
- Export error budget: contributions by component class + dominant sensitivities.

## 3.2 OrbitVerify physics scope (free-space + satellite)

OrbitVerify needs a free-space channel model that is:
- decomposed (so engineers can see loss contributors), and
- parameterized (so scenario assumptions are explicit and swappable).

### Required contributors
- geometric spreading (aperture, divergence),
- pointing loss (jitter, misalignment),
- atmospheric extinction (elevation dependence),
- turbulence proxy (scintillation attenuation model),
- background noise terms (day/night, stray light assumptions),
- detector behavior under background and saturation (already being modeled).

### Required "mission semantics" (even before full orbit mechanics)
- pass template types: "best case", "median", "worst case" envelopes,
- time window segmentation for elevation and background changes,
- weather/availability envelope as a scenario input (not hidden constants).

---

## 4) Trust Moat: Evidence Tiers, Gates, and Labels

PhotonTrust should institutionalize a quality ladder. Every card is labeled
with a tier and must carry the evidence required for that tier.

## Evidence quality tiers (recommended)
- Tier 0: exploratory (heuristic defaults, minimal benchmarking)
- Tier 1: benchmarked (passes internal reference scenarios)
- Tier 2: calibrated (passes diagnostics; includes measurement linkage)
- Tier 3: externally reproducible (independent replay + artifact pack)

## Calibration gates (required for Tier 2+)
- MCMC diagnostics thresholds (R-hat, ESS).
- Posterior predictive check acceptance.
- "Model mismatch" disclaimers if benchmarks disagree outside tolerance.

## Mode semantics (required on every run)
- `preview`: fast interactive iteration; clearly labeled "not certification".
- `standard`: default engine behavior for internal/normal work.
- `certification`: increased sampling/strict checks; required for external cards.

---

## 5) Multi-Phase Rollout (Strict Protocol)

PhotonTrust must follow the strict protocol in:
- `../operations/phased_rollout/README.md`

Each phase produces the mandatory artifact set:
- `01_research_brief_YYYY-MM-DD.md`
- `02_implementation_plan_YYYY-MM-DD.md`
- `03_build_log_YYYY-MM-DD.md`
- `04_validation_report_YYYY-MM-DD.md`

## 5.1) v1 -> v3 Fast Execution Overlay ("Strongest Contender Path")

The strict phase backlog below is the canonical execution record.

For a single-stream "fast path" overlay from "v1 (trustable open core)" to
"v3 (photonic design control plane)", use:
- `deep_dive/21_v1_to_v3_fast_execution_plan.md`

Integration rule:
- the fast-path document provides prioritization and demo strategy,
- the strict phase protocol provides the execution discipline and trust artifacts.

Mapping (recommended):
- v1: Phases 01-22 (complete; engine + managed-run governance)
- v2: Performance DRC wedge + calibration loop (next planned phases)
- v3: Control plane (inverse design + PDK-aware layout hooks + circuit solvers)

## Completed phases (engine foundation)
- Phase 01-06 are complete:
  - `../operations/phased_rollout/`

## Next phases (platform expansion backlog)

### Phase 07: Open benchmark ingestion + external reproducibility package
- Research:
  - define benchmark manifest format, versioning, and drift rules.
  - define reproducibility pack (env pins + replay script + artifact layout).
- Build (implemented v0.1):
  - schemas:
    - `schemas/photonstrust.benchmark_bundle.v0.schema.json`
    - `schemas/photonstrust.repro_pack_manifest.v0.schema.json`
  - package modules:
    - `photonstrust/benchmarks/ingest.py`
    - `photonstrust/benchmarks/open_benchmarks.py`
    - `photonstrust/benchmarks/repro_pack.py`
  - scripts:
    - `scripts/check_open_benchmarks.py`
    - `scripts/generate_repro_pack.py`
    - `scripts/release_gate_check.py` includes `open_benchmarks`
  - seeded open benchmark:
    - `datasets/benchmarks/open/open_demo_qkd_analytic_001/`
  - tests:
    - `tests/test_benchmark_ingestion.py`
    - `tests/test_repro_pack_generation.py`
- Validation:
  - external replay from clean environment instructions.
  - drift check is enforced in CI for public benchmark sets.

### Phase 08: Component graph schema v0.1 + compiler (UI -> engine)
- Research:
  - define node/edge semantics and minimum component parameter schema.
  - decide units policy and validation constraints.
- Build (implemented v0.1):
  - schema:
    - `schemas/photonstrust.graph.v0_1.schema.json`
  - package modules:
    - `photonstrust/graph/compiler.py`
    - `photonstrust/graph/schema.py`
  - CLI:
    - `photonstrust graph compile <graph.json> --output <dir>`
  - demo graphs:
    - `graphs/demo8_qkd_link_graph.json`
    - `graphs/demo8_pic_circuit_graph.json`
  - tests:
    - `tests/test_graph_compiler.py`
- Validation:
  - `py -m pytest -q` (graph schema + compiler tests)
  - manual compile of both demo graphs
  - compiled QKD config runs via `photonstrust run ...`

### Phase 09: ChipVerify component library v1 (passives + I/O)
- Research:
  - choose composition math (transfer matrix vs scattering, and constraints).
  - choose import surface for S-parameters / Touchstone and uncertainty tags.
- Build (implemented v0.1):
  - PIC component library:
    - `photonstrust/components/pic/library.py`
      - `pic.waveguide`, `pic.grating_coupler`, `pic.edge_coupler`,
        `pic.phase_shifter`, `pic.coupler`, `pic.ring` (placeholder)
  - PIC netlist execution:
    - `photonstrust/pic/simulate.py`
      - chain solver (loss/phase budgets for 2-port chains)
      - DAG solver (feed-forward complex amplitude propagation; interference via couplers)
  - Graph edge port support (additive, backward-compatible):
    - `schemas/photonstrust.graph.v0_1.schema.json` (`from_port`/`to_port`)
    - `photonstrust/graph/compiler.py` emits/normalizes ports for PIC edges
  - CLI:
    - `photonstrust pic simulate <compiled_netlist.json> --output <dir>`
  - Tests:
    - `tests/test_pic_simulation.py` (chain loss accounting + MZI routing)
- Validation (v0.1):
  - `py -m pytest -q`
  - `py scripts/release_gate_check.py`
  - manual smoke:
    - compile: `photonstrust graph compile graphs/demo8_pic_circuit_graph.json --output results/graphs`
    - simulate: `photonstrust pic simulate results/graphs/demo8_pic_circuit/compiled_netlist.json --output results/pic/demo8_pic_circuit`

### Phase 10: ChipVerify compact model import (Touchstone/S-parameters) + sweeps
- Research:
  - define a Touchstone ingestion contract (file layout, metadata, validity range).
  - define uncertainty tags for imported black-box models.
  - decide optional dependency strategy (e.g., scikit-rf integration).
- Build (implemented v0.1):
  - Touchstone parsing + interpolation (conservative subset):
    - `photonstrust/components/pic/touchstone.py`
  - New PIC component kind:
    - `pic.touchstone_2port` in `photonstrust/components/pic/library.py`
  - Wavelength sweep runner:
    - `simulate_pic_netlist_sweep(...)` in `photonstrust/pic/simulate.py`
  - CLI sweep support:
    - `photonstrust pic simulate ... --wavelength-sweep-nm <nm1> <nm2> ...`
  - Tests + fixtures:
    - `tests/fixtures/touchstone_demo.s2p`
    - `tests/test_pic_touchstone_import.py`
    - `tests/test_pic_sweep.py`
- Validation (v0.1):
  - `py -m pytest -q`
  - `py scripts/release_gate_check.py`

### Phase 11: OrbitVerify mission templates (pass envelopes + metadata)
- Research:
  - define minimal mission profile schema and pass envelope strategy.
  - align propagation assumptions with standards-aligned references where
    applicable (terrestrial FSO recommendations, turbulence proxies).
- Build (implemented v0.1):
  - Orbit pass results schema:
    - `schemas/photonstrust.orbit_pass_results.v0.schema.json`
  - Orbit pass execution:
    - `photonstrust/orbit/pass_envelope.py`
      - explicit `dt_s` pass envelope samples (no orbit propagation)
      - per-sample free-space decomposition + QKD point outputs
      - exports `orbit_pass_results.json` + `orbit_pass_report.html`
  - CLI integration:
    - `photonstrust run <config.yml>` detects `orbit_pass` and runs the pass runner
  - Scenario template:
    - `configs/demo11_orbit_pass_envelope.yml`
  - Tests:
    - `tests/test_orbit_pass_envelope.py` (known-sense invariants + schema validation)
- Validation (v0.1):
  - `py -m pytest -q`
  - `py scripts/release_gate_check.py`
  - manual smoke:
    - `photonstrust run configs/demo11_orbit_pass_envelope.yml --output results/orbit_demo11`

### Phase 12: Data contribution workflow (academic + industry safe)
- Research:
  - consent and IP-safe telemetry policy.
  - dataset schema for measurement ingestion (linking to calibration bundles).
- Build (implemented v0.1):
  - Measurement bundle schema:
    - `schemas/photonstrust.measurement_bundle.v0.schema.json`
  - Artifact pack manifest schema:
    - `schemas/photonstrust.artifact_pack_manifest.v0.schema.json`
  - Measurement ingestion + local registry:
    - `photonstrust/measurements/ingest.py` ingests into `datasets/measurements/open/<dataset_id>/`
    - `datasets/measurements/open/index.json` registry index (upsert)
  - Redaction scan + opt-in publish pack:
    - `photonstrust/measurements/redaction.py` (conservative secret scans)
    - `photonstrust/measurements/publish.py` (pack directory + optional zip)
  - Scripts:
    - `scripts/ingest_measurement_bundle.py`
    - `scripts/publish_artifact_pack.py`
  - Tests + fixtures:
    - `tests/test_measurement_ingestion.py`
    - `tests/test_redaction_scan.py`
    - `tests/fixtures/measurement_bundle_demo/`
    - `tests/fixtures/measurement_bundle_bad_secret/`
- Validation (v0.1):
  - `py -m pytest -q`
  - `py scripts/release_gate_check.py`
  - smoke:
    - `python scripts/ingest_measurement_bundle.py tests/fixtures/measurement_bundle_demo/measurement_bundle.json --open-root results/measurements_open_demo`
    - `python scripts/publish_artifact_pack.py tests/fixtures/measurement_bundle_demo/measurement_bundle.json results/artifact_pack_demo`

### Phase 13: Web drag-drop MVP (managed service surface)
- Research:
  - Phase 13 rollout folder:
    - `../operations/phased_rollout/phase_13_web_drag_drop_mvp/`
- Build (implemented v0.1):
  - Backend API (local dev surface):
    - `photonstrust/api/server.py`
    - `scripts/run_api_server.py`
    - `pyproject.toml` optional dependencies (`api = ["fastapi", "uvicorn"]`)
  - Web editor (React Flow):
    - `web/src/App.jsx` (palette, templates, inspector, compile/run wiring)
    - `web/src/photontrust/PtNode.jsx` (multi-port nodes)
    - `web/src/photontrust/api.js` (API client)
    - `web/src/photontrust/graph.js` (graph JSON payload builder; includes `node.ui.position`)
    - `web/src/photontrust/kinds.js` and `web/src/photontrust/templates.js`
  - Security posture:
    - API server rejects `pic.touchstone_2port` (file access stays CLI-only by default).
- Validation (v0.1):
  - `py -m pytest -q`
  - `py scripts/release_gate_check.py`
  - `cd web && npm run build`
  - `cd web && npm run lint`

### Phase 14: Trust panel v0.2 (parameter registry + units/ranges)
- Research:
  - Phase 14 rollout folder:
    - `../operations/phased_rollout/phase_14_trust_panel_param_registry/`
- Build (implemented v0.2):
  - Backend-owned registry:
    - `photonstrust/registry/kinds.py`
  - API endpoint:
    - `GET /v0/registry/kinds` (in `photonstrust/api/server.py`)
  - Web trust panel:
    - registry-backed palette titles + per-node schema panel in `web/src/App.jsx`
    - quick-edit scalar params via generated controls (units/ranges/defaults visible)
- Validation (v0.2):
  - `py -m pytest -q`
  - `py scripts/release_gate_check.py`
  - `cd web && npm run build`
  - `cd web && npm run lint`

### Phase 15: Graph validation + structured diagnostics (params, ports, kind support)
- Research:
  - Phase 15 rollout folder:
    - `../operations/phased_rollout/phase_15_graph_validation_diagnostics/`
- Build (implemented v0.1):
  - Diagnostics module:
    - `photonstrust/graph/diagnostics.py`
  - API:
    - `POST /v0/graph/validate`
    - `/v0/graph/compile` now includes `diagnostics`
  - Web:
    - compile tab surfaces diagnostics blocks (errors + warnings)
- Validation:
  - `py -m pytest -q`
  - `py scripts/release_gate_check.py`
  - `cd web && npm run build`
  - `cd web && npm run lint`

### Phase 16: OrbitVerify web runner v0.1 (config-first pass envelopes)
- Research:
  - Phase 16 rollout folder:
    - `../operations/phased_rollout/phase_16_orbit_web_runner/`
- Build (implemented v0.1):
  - API:
    - `POST /v0/orbit/pass/run` (executes config-first Orbit pass envelopes)
  - Web:
    - `Mode: Orbit Pass` in `web/src/App.jsx`
    - config JSON editor seeded with a pass-envelope template
    - `Run` triggers Orbit pass execution and returns artifact paths + parsed results JSON
- Validation:
  - `py -m pytest -q`
  - `py scripts/release_gate_check.py`
  - `cd web && npm run build`
  - `cd web && npm run lint`

### Phase 17: OrbitVerify validation + diagnostics v0.1 (schema + validate endpoint)
- Research:
  - Phase 17 rollout folder:
    - `../operations/phased_rollout/phase_17_orbit_validation_diagnostics/`
- Build (implemented v0.1):
  - Schema:
    - `schemas/photonstrust.orbit_pass_envelope.v0_1.schema.json`
  - Engine:
    - `photonstrust/orbit/schema.py` (schema validator helper)
    - `photonstrust/orbit/diagnostics.py` (semantic diagnostics)
  - API:
    - `POST /v0/orbit/pass/validate`
    - `/v0/orbit/pass/run` includes `diagnostics` in response
  - Web:
    - Orbit Pass mode adds `Validate` action + diagnostics tab
- Validation:
  - `py -m pytest -q`
  - `py scripts/release_gate_check.py`
  - `cd web && npm run build`
  - `cd web && npm run lint`

### Phase 18: OrbitVerify evidence hardening v0.2 (availability envelope + standards anchors)
- Research:
  - Phase 18 rollout folder:
    - `../operations/phased_rollout/phase_18_orbit_availability_standards/`
- Build (implemented v0.2):
  - Config semantics:
    - optional `orbit_pass.availability.clear_fraction` availability assumption
  - Results/reporting:
    - per-case `summary.expected_total_keys_bits` (expected keys under availability)
    - standards anchors surfaced in results and HTML report (references only)
  - Diagnostics:
    - semantic validation for `clear_fraction` range
- Validation:
  - `py -m pytest -q`
  - `py scripts/release_gate_check.py`
  - `cd web && npm run build`
  - `cd web && npm run lint`

### Phase 19: Run registry + artifact serving v0.1 (managed-service hardening, local dev)
- Research:
  - Phase 19 rollout folder:
    - `../operations/phased_rollout/phase_19_run_registry_artifact_serving/`
- Build (implemented v0.1):
  - Run store (filesystem-backed manifest):
    - `photonstrust/api/runs.py`
      - runs root (`PHOTONTRUST_API_RUNS_ROOT` override for tests/dev)
      - `run_manifest.json` writer/reader
      - safe artifact path resolution (anti-traversal)
  - API:
    - `GET /v0/runs`
    - `GET /v0/runs/{run_id}`
    - `GET /v0/runs/{run_id}/artifact?path=<relative>`
    - `POST /v0/qkd/run` writes `run_manifest.json`
    - `POST /v0/orbit/pass/run` writes `run_manifest.json` and returns `artifact_relpaths`
  - Web:
    - Orbit Pass run view surfaces served artifact links (report/results/manifest)
  - Tests:
    - API optional tests cover run listing, manifest retrieval, and artifact serving
- Validation:
  - `py -m pytest -q`
  - `py scripts/release_gate_check.py`
  - `cd web && npm run build`
  - `cd web && npm run lint`

### Phase 20: Run browser + run diff v0.1 (managed-service hardening, local dev)
- Research:
  - Phase 20 rollout folder:
    - `../operations/phased_rollout/phase_20_run_browser_diff/`
- Build (implemented v0.1):
  - API:
    - `POST /v0/runs/diff` (bounded diff; default scope: manifest `input`)
    - `photonstrust/api/diff.py` (JSON Pointer escaped paths; bounded output)
  - Web:
    - `Mode: Runs` in `web/src/App.jsx`
      - list runs (`GET /v0/runs`)
      - load manifest (`GET /v0/runs/{run_id}`)
      - diff two runs (`POST /v0/runs/diff`)
      - open served artifacts from manifest relpaths (`/v0/runs/{run_id}/artifact?path=...`)
  - Tests:
    - API optional tests cover `POST /v0/runs/diff` bounded behavior
- Validation:
  - `py -m pytest -q`
  - `py scripts/release_gate_check.py`
  - `cd web && npm run build`
  - `cd web && npm run lint`

### Phase 21: Run output summaries + output diff scope v0.1 (managed-service hardening, local dev)
- Research:
  - Phase 21 rollout folder:
    - `../operations/phased_rollout/phase_21_run_output_summary_diff/`
- Build (implemented v0.1):
  - Run manifests now include a stable `outputs_summary` block:
    - QKD runs: `outputs_summary.qkd.cards[]` (scenario_id, band, key_rate_bps, qber, safe_use)
    - Orbit pass runs: `outputs_summary.orbit_pass.cases[]` (per-case summary metrics)
  - API:
    - `POST /v0/runs/diff` supports `scope=input|outputs_summary|all` (default: `input`)
  - Web:
    - Runs mode adds a diff scope selector
  - Tests:
    - API optional tests assert `outputs_summary` exists and `scope=outputs_summary` diffs report changes when outputs differ
- Validation:
  - `py -m pytest -q`
  - `py scripts/release_gate_check.py`
  - `cd web && npm run build`
  - `cd web && npm run lint`

### Phase 22: Project registry + approvals v0.1 (managed-service governance, local dev)
- Research:
  - Phase 22 rollout folder:
    - `../operations/phased_rollout/phase_22_project_registry_approvals/`
- Build (implemented v0.1):
  - Run manifests now store `input.project_id` (default `default`).
  - API:
    - `GET /v0/projects` (project inference from stored run manifests)
    - `GET /v0/runs?project_id=<id>` (project filter)
    - `POST /v0/projects/{project_id}/approvals` (append-only approvals log)
    - `GET /v0/projects/{project_id}/approvals`
  - Web:
    - Runs mode adds a project selector and approvals panel on the manifest view
  - Tests:
    - API optional tests cover project listing, run filtering, and approvals append/list behavior
- Validation:
  - `py -m pytest -q`
  - `py scripts/release_gate_check.py`
  - `cd web && npm run build`
  - `cd web && npm run lint`

### v2/v3 wedge primitives already implemented (performance DRC + inverse design)

These primitives are the core of the "Strongest Contender Path" and are already
present in the repo (see `deep_dive/21_v1_to_v3_fast_execution_plan.md`).

- Performance DRC (crosstalk check, v0):
  - schema: `schemas/photonstrust.performance_drc.v0.schema.json`
  - engine: `photonstrust/components/pic/crosstalk.py`
  - check runner: `photonstrust/verification/performance_drc.py`
  - HTML report: `photonstrust/reporting/performance_drc_report.py`
  - API: `POST /v0/performance_drc/crosstalk` (writes `run_manifest.json` + artifacts)
  - web: Graph mode "DRC" tab (served artifact links)
  - tests: `tests/test_pic_crosstalk_monotonicity.py`, `tests/test_performance_drc_schema.py`
  - route-level layout extraction (implemented v0.1): `routes` + `layout_extract` (worst-case envelope across extracted segments)
  - GDS seam (implemented v0.2, optional): `photonstrust/layout/gds_extract.py` (`photonstrust[layout]` adds `gdstk`)
  - layout extraction schema: `schemas/photonstrust.layout_parallel_runs.v0_1.schema.json`
  - calibration loop (implemented v0.1): `photonstrust/calibrate/pic_crosstalk.py` + `scripts/check_pic_crosstalk_calibration_drift.py`

- Inverse design (deterministic synthesis primitive, v0):
  - engine: `photonstrust/invdesign/mzi_phase.py`
  - API: `POST /v0/pic/invdesign/mzi_phase` (writes `run_manifest.json` + artifacts)
  - web: Graph mode "Invdesign" tab (updates graph and surfaces artifacts)

Planned follow-ons to reach a denial-resistant v2 flagship:
- layout feature extraction (route-level implemented; GDS-level planned)
- calibration loop from measurement bundles (fit -> evidence -> drift governance)
- stronger PDK plugin interface (private PDK manifests + on-prem runner posture)

### Draft phase map for v2 -> v3 (fast execution integration)

Use the strict rollout protocol to execute the fast-path document:
- `deep_dive/21_v1_to_v3_fast_execution_plan.md`

Draft phase slicing (v2 wedge -> v3 control plane):
- Phase 23 (implemented): Performance DRC flagship hardening v0.2 (route-level layout extraction + API tests + evidence surface)
- Phase 24 (implemented): GDS-level layout feature extraction v0.2 (optional seam via `gdstk`; route-level done)
- Phase 25 (implemented): Crosstalk calibration loop v0.1 (measurement bundles -> deterministic fit -> drift gate; model tagging planned)
- Phase 26 (implemented): PIC solver extensions v0.2 (ring resonator transfer; sweeps; multiport S-matrix composition planned)
- Phase 27 (implemented): PDK-aware layout hooks v0.1 (deterministic sidecars + LVS-lite + optional KLayout runner seam)
- Phase 28 (implemented): SPICE + KLayout interop v0.1 (SPICE export + optional ngspice runner seam)
- Phase 29 (implemented): PIC layout + LVS-lite + SPICE v0.1 (API + web tabs integration)
- Phase 30 (implemented): KLayout macro templates + run artifact pack contract v0.1 (EDA seam hardening)
- Phase 31 (implemented): KLayout artifact pack API + web integration v0.1 (managed workflow surface)
- Phase 32 (implemented): KLayout pack run registry source selection v0.1 (Runs picker -> selected GDS)
- Phase 33 (implemented): Inverse design robustness + evidence pack v0.1 (schema contract + corner cases + coupler ratio primitive)
- Phase 34 (implemented): Invdesign workflow chaining v0.1 (invdesign -> layout -> LVS-lite -> KLayout pack -> SPICE export)
- Phase 35 (implemented): Workflow replay + evidence bundle export v0.1 (zip + replay + run linking UX)
- Phase 36 (implemented): Evidence bundle attestation + schema contracts v0.1 (workflow report + bundle manifest)

---

## 6) "Physics Engine First" Build Priorities (Immediate Work Order)

If the goal is scientific dominance (and a denial-resistant business wedge), the fastest path is:
1. benchmark ingestion + reproducibility pack (Phase 07)
2. graph schema + compiler (Phase 08)
3. chip component library v1 with uncertainty semantics (Phase 09)
4. compact model import + sweeps (Phase 10)
5. OrbitVerify mission envelopes and standards-anchored assumptions (Phase 11)
6. data contribution workflow (Phase 12)
7. managed drag-drop MVP (Phase 13) only after engine contracts are stable
8. OrbitVerify web runner v0.1 (Phase 16) to make mission envelopes usable from the same managed workflow surface
9. OrbitVerify validation + diagnostics v0.1 (Phase 17) to make Orbit results auditable and UI-friendly
10. OrbitVerify evidence hardening v0.2 (Phase 18) to expose availability assumptions and standards anchors explicitly
11. run registry + artifact serving v0.1 (Phase 19) so every managed run is reviewable and reproducible without filesystem access
12. run browser + run diff v0.1 (Phase 20) so reviewers can inspect and compare runs without touching the filesystem
13. run output summaries + output diff scope v0.1 (Phase 21) so reviewers can diff run outputs quickly without diffing large artifacts
14. project registry + approvals v0.1 (Phase 22) so teams can review and bless a specific run for publication/design reviews
15. performance DRC wedge: crosstalk check v0 (already implemented) and flagship demo packaging ("1.6T Interconnect Optimizer")
16. layout feature extraction for performance DRC (route-level first; GDS-level later)
17. calibration loop for performance DRC from measurement bundles (fit -> evidence pack -> drift governance)
18. PIC circuit solver extensions (rings + multiport S-matrix composition)
19. PDK-aware layout hooks + LVS-lite mismatch summaries (sidecar-first; optional KLayout runner seam)
20. SPICE/EDA interop seams (SPICE netlist export + optional simulator runners)
21. inverse design expansion beyond parameter tuning (block-level generators + corner robustness + evidence packs)

Reason: UI without falsifiable physics + evidence creates "pretty but untrusted"
results. The platform's moat comes from trust artifacts.

---

## References (primary anchors)

Quantum tooling:
- QuTiP download/releases (v5.2.3 listed, 2026-01-26): https://qutip.org/download.html
- Qiskit 2.3 release notes (IBM Quantum): https://quantum.cloud.ibm.com/docs/en/api/qiskit/release-notes/2.3

PIC verification ecosystem:
- Ansys CML overview: https://optics.ansys.com/hc/en-us/articles/360055701453-CML-Compiler-overview
- Luceda Photonic CML: https://academy.lucedaphotonics.com/docs/ipkiss/4.0/real_cml.html
- gdsfactory (open PIC layout + PDK workflows): https://gdsfactory.github.io/gdsfactory/
- SiEPIC-Tools: https://github.com/SiEPIC/SiEPIC-Tools
- SAX (S-matrix based photonic circuit simulation): https://flaport.github.io/sax/
- scikit-rf (Touchstone/S-parameters; Python network composition): https://scikit-rf.readthedocs.io/

Free-space optical propagation:
- ITU-R P.1814 (terrestrial FSO attenuation): https://www.itu.int/rec/R-REC-P.1814/en
- ITU-R P.1817 (FSO availability): https://www.itu.int/rec/R-REC-P.1817/en
- Gamma-Gamma turbulence model (Al-Habash et al., 2001): https://stars.library.ucf.edu/facultybib2000/3934/

Recent integrated photonics signal:
- Integrated photonic trusted-node TF-QKD network (Nature, 2026-02-11):
  https://www.nature.com/articles/s41586-026-08816-0

QKD network standards signals:
- ITU-T Y.3800 (Overview on networks supporting quantum key distribution, 2019): https://www.itu.int/rec/T-REC-Y.3800/en
- ETSI ISG QKD (industry group landing page): https://www.etsi.org/committee/qkd
- ETSI GS QKD 004 (QKD interface specification; ETSI deliverable PDF): https://www.etsi.org/deliver/etsi_gs/QKD/001_099/004/02.01.01_60/gs_qkd004v020101p.pdf

Satellite programs:
- ESA EAGLE-1: https://connectivity.esa.int/projects/eagle-1
- CSA QEYSSat: https://www.asc-csa.gc.ca/eng/satellites/qeyssat/default.asp

Optical comm space signals:
- NASA LCRD overview: https://www.nasa.gov/mission/laser-communications-relay-demonstration-lcrd/
- CCSDS Optical High Data Rate Communication 1064 nm (CCSDS 141.11-O-1): https://public.ccsds.org/Pubs/141x11o1.pdf

Internal research update:
- `16_web_research_update_2026-02-13.md`
