# PhotonTrust v1 -> v3 Fast Execution Plan (Strongest Contender Path)

Date: 2026-02-13
Update: 2026-02-14 (Phase 32 completed: Run Registry-selected GDS -> KLayout artifact pack; Phase 33 completed: invdesign robustness + evidence pack + coupler ratio primitive; Phase 34 completed: invdesign workflow chaining -> layout + LVS-lite + optional KLayout pack + SPICE export; Phase 35 completed: workflow replay + evidence bundle export (zip) + run linking UX; Phase 36 completed: schema contracts for workflow report + evidence bundle manifest; Phase 37 completed: GDS + KLayout pack enablement; Phase 38 completed: config validation + CLI --validate-only; Phase 39 completed: QKD physics trust gates (PLOB/seed/airmass))

This document is a single, streamlined plan to take the current PhotonTrust repo
from "v1 (credible open-core engine + evidence)" to "v3 (photonic design control
plane)". It is designed to be fast, denial-resistant in demos, and compatible
with real PIC workflows (PDKs, compact models, DRC/LVS thinking, corner/yield).

It integrates:
- the repo's strict phased rollout discipline (`docs/operations/phased_rollout/`),
- the current ChipVerify/OrbitVerify platform plan,
- the QKD deployment realism pack (fiber),
- the chip inverse-design + open PDK strategy, and
- a commercial wedge aligned to 1.6T / 224G-per-lane interconnect scaling.

This is not a "perfect long-term roadmap". It is the highest-leverage path to
become a credible contender quickly by building:
1) performance DRC (physics checks inside layout/workflows),
2) evidence packs (trust artifacts that survive scrutiny),
3) calibration/data loops (model accuracy improves with partner data),
4) inverse design for selected blocks (not "optimize the whole chip"),
5) a workflow surface that engineers actually use (graph -> layout -> check -> iterate).

---

## 0) Definitions: What v1, v2, v3 Mean Here

### v1 (today's repo target): "Trustable Open Core"
v1 means:
- deterministic engine execution with seeds + config hash,
- versioned schemas for artifacts,
- benchmark drift governance + release gates,
- reproducibility pack / open benchmark ingestion,
- a usable CLI + viewer UI for results.

In practice, v1 is: the repo as it exists now plus any remaining "trust blockers"
that can invalidate external demos.

### v2: "Performance DRC + Control Surface"
v2 means:
- the engine becomes a control surface for PIC design decisions:
  - compact model import (S-parameters),
  - wavelength sweeps,
  - corner/yield sensitivity summaries,
  - layout-aware checks ("performance DRC").
- a web drag-drop MVP exists (Phase 13 complete) for authoring and comparison.
- a flagship demo exists that is hard to deny:
  "1.6T Interconnect Optimizer" (real-time crosstalk margin checks).

### v3: "Photonic Design Control Plane"
v3 means:
- inverse design is integrated as a first-class generator for selected blocks,
- PDK-aware layout generation + verification hooks exist (sidecar-first; optional KLayout/gdsfactory backends),
- EDA interop seams exist (SPICE netlist export + optional simulator runners),
- measurement ingestion + calibration loops are productized,
- enterprise posture is viable (private PDK plugins, on-prem runner, audit trail),
- a data flywheel exists (opt-in measurement bundles + benchmark packs).

---

## 1) Strategy: How to Be the Strongest Contender

The strongest contender in this space does NOT win by having the most detailed
solver. The strongest contender wins by being:
- fast enough to iterate,
- trustworthy enough to sign off decisions,
- integrated enough to become a required gate in workflows.

The defendable moat is the combination of:
- performance DRC (physics-based checks during layout and routing),
- evidence packs (reproducibility + provenance + benchmarks + drift governance),
- calibration loops (model improves with real data),
- and a component library that is manufacturable and robust.

This aligns with how PIC teams work (compact models + calibration + corners),
and with how big interconnect scaling teams evaluate risk (yield + margins).

---

## 2) Baseline: Where the Repo Is Today (v1 Snapshot)

Use the phased rollout protocol as truth:
- `docs/operations/phased_rollout/README.md`

The repo already has implemented v0.1 building blocks for:
- PIC component library + simulation (Phase 09),
- Touchstone/S-parameter import + wavelength sweeps (Phase 10),
- OrbitVerify pass envelopes + metadata (Phase 11),
- measurement bundle ingestion + artifact pack publishing (Phase 12),
- graph schema + compiler (Phase 08),
- open benchmark ingestion + reproducibility packs (Phase 07),
- release gate automation (`scripts/release_gate_check.py`).

Managed-service UI and governance surfaces are implemented through Phase 22:
- Phase 13: web drag-drop MVP (authoring surface)
- Phase 19: run registry + artifact serving
- Phase 20: run browser + run diff
- Phase 21: run output summaries + output diff scope
- Phase 22: project registry + approvals (append-only)

Trust blockers still pending (as of this plan):
- Fiber-QKD deployment realism pack from `deep_dive/16_qkd_deployment_realism_pack.md`
  is specified as a consolidated "deployment layer". The core physics hooks exist
  in code (Raman coexistence, misalignment/visibility floor, finite-key toggle,
  source visibility), but the pack still needs:
  - unified scenario templates/presets,
  - benchmark coverage that matches deployment regimes,
  - and a clear "what is assumed vs what is measured" narrative in artifacts.

Implication:
- You can sell ChipVerify/Interconnect value even if QKD realism is still in-flight,
  but if your demo includes QKD claims, you need the realism pack implemented.

### Integration: How This Maps to the Strict Phase Rollout

This document is the "fast path" overlay. Execution should still be done using
the strict phase protocol (research -> plan -> build -> validate -> doc updates),
so every increment ships with trustworthy artifacts.

Recommended mapping:
- v1: Phases 01-22 (complete)
- v2 (Performance DRC wedge): Phase 23-29 (implemented)
- v3 (Control plane): Phase 30+ (Phase 30-36 implemented; Phase 37+ planned)

---

## 3) The Flagship Wedge for Fast Impact

### v2 flagship: "1.6T Interconnect Optimizer"

The market is moving toward 1.6 Tb/s Ethernet and 224G electrical lanes, and
optical interconnect vendors are already shipping/announcing 1.6T-class DSPs.

The wedge:
- real-time prediction of crosstalk for parallel waveguides + couplers + routing,
- packaged as a "performance DRC" gate inside a layout-aware workflow,
- with a slider demo that is immediately comprehensible.

Why it is denial-resistant:
- it ties directly to yield and margin,
- it produces actionable constraints ("min gap for -X dB crosstalk at P99 corner"),
- and it is integrated into the design loop (not just a plot).

---

## 4) v1 -> v2 (Fast Path): 6-8 Week Execution Plan

Principle: ship one denial-resistant workflow end-to-end before expanding scope.

### Week 0-1: Lock the v2 flagship contract

Deliverables:
- A single JSON contract for "crosstalk check" requests and results:
  - geometry features extracted from layout (parallel length, gap, wavelength range),
  - requested corners (delta width/etch, temperature, wavelength),
  - outputs: crosstalk(dB) vs lambda, worst-case margin, recommended min gap.
- A repo-level evidence artifact contract for "Performance DRC" results:
  - `performance_drc_report.json`
  - `performance_drc_report.html`

Repo additions (implemented v0):
- `schemas/photonstrust.performance_drc.v0.schema.json`
- `photonstrust/verification/performance_drc.py`
- `photonstrust/reporting/performance_drc_report.py`

Gate:
- jsonschema validation + deterministic replay for identical inputs.

### Week 1-3: Implement Crosstalk Model v0 (analytic + calibration-friendly)

Physics target:
- start with coupled-mode / supermode approximation:
  - crosstalk is driven by coupling coefficient kappa(gap, width, lambda) and
    interaction length.

Implementation:
- implement a deterministic function:
  `predict_xt_db(gap_um, length_um, wavelength_nm, corner_params) -> xt_db`
- fit kappa(gap, lambda) using:
  - synthetic simulation dataset first,
  - then calibrated using measurement bundles when available.

Repo edits (implemented v0):
- `photonstrust/components/pic/crosstalk.py`
- `tests/test_pic_crosstalk_monotonicity.py`

Validation gates:
- monotonic sanity:
  - smaller gap => worse crosstalk (at fixed length),
  - longer parallel length => worse crosstalk (at fixed gap),
  - corner widening (tighter confinement) should move coupling directionally.
- explicit applicability bounds:
  - if outside bounds, label as heuristic and require "certification mode" sim.

### Week 2-4: Connect it to layout extraction (gdsfactory/KLayout entry point)

Deliverables:
- a layout segment extractor that outputs "parallel run segments" from a route
  (initially from the graph/netlist + routing metadata; later from GDS).

MVP approach:
- perform this check at the netlist/routing level first (fast, deterministic),
  then add GDS extraction once KLayout/gdsfactory integration is mature.

Repo edits (implemented v0.1):
- `photonstrust/layout/route_extract.py`
- `photonstrust/verification/layout_features.py`
- `photonstrust/verification/performance_drc.py` (route-mode: worst-case envelope across extracted segments)
- `photonstrust/reporting/performance_drc_report.py` (surfaces extracted layout summary)

GDS seam (implemented v0.2, optional):
- optional dependency: `photonstrust[layout]` (adds `gdstk`)
- `photonstrust/layout/gds_extract.py` (GDS PATH spines -> `routes[*]` contract)
- `schemas/photonstrust.layout_parallel_runs.v0_1.schema.json` (format contract for extracted parallel runs)

Validation:
- golden fixtures for 3 routing cases:
  - `tests/test_layout_route_extract.py`
- schema validation still passes:
  - `tests/test_performance_drc_schema.py`
- API optional test covers route-mode:
  - `tests/api/test_api_server_optional.py`

### Week 3-6: Harden the control surface (web + run review) for denial-resistant demos

Goal:
- a user can:
  1) author or import a PIC graph,
  2) compile,
  3) simulate (Touchstone or library),
  4) run performance DRC checks,
  5) run inverse design primitives (v0),
  6) compare two runs and approve a reference run (project approvals).

Required UI behaviors:
- clear "preview vs certification" mode toggles,
- explicit assumption tables in the UI,
- served artifact links + bounded diffs (`outputs_summary`),
- project grouping + approvals (append-only audit trail),
- exportable evidence bundle for review.

Gate:
- reproduce the same results using CLI-only from the exported artifacts.

### Week 6-8: Data ingestion pilot loop (the start of the moat)

Use what already exists:
- measurement bundle ingestion + redaction scan + publish pack.

Deliverables:
- define a `kind: pic_crosstalk_sweep` measurement bundle schema variant (implemented v0.1):
  - sweep data schema: `schemas/photonstrust.pic_crosstalk_sweep.v0.schema.json`
  - bundle wrapper schema: `schemas/photonstrust.measurement_bundle.v0.schema.json`
- integrate calibration step (implemented v0.1, deterministic):
  - fit module: `photonstrust/calibrate/pic_crosstalk.py`
  - drift gate: `scripts/check_pic_crosstalk_calibration_drift.py`
  - baseline fixture: `tests/fixtures/pic_crosstalk_calibration_baseline.json`
  - reference bundle fixture: `tests/fixtures/measurement_bundle_pic_crosstalk/`

Gate:
- calibration run produces:
  - before/after error metrics,
  - updated model version tags,
  - and does not regress existing benchmarks.

Outcome:
- v2 demo becomes:
  "Here is our predictor; here is its calibration curve against real data;
   here is the drift governance and reproducibility."

---

## 5) v2 -> v3: 3-6 Month Plan (Inverse Design + Full Circuit Control)

### Track A: Inverse design for 1-2 high-leverage components

Pick components that:
- impact yield/margin in interconnect and PICs,
- are small enough to optimize,
- have clear port objectives.

Best first candidates:
- directional coupler variant optimized for bandwidth and tolerance,
- waveguide crossing with low loss and low crosstalk,
- mode converter.

Implementation policy:
- prototype with permissive solvers (MIT-style) to keep product flexibility,
- treat GPL solvers as optional research plugins (avoid license traps).

Deliverables:
- `photonstrust/invdesign/` package with:
  - backend abstraction,
  - constraint enforcement (min feature filters),
  - evidence pack export,
  - corner robustness sweep.

Implemented v0.1 (Phase 33):
- schema-validated invdesign report contract: `schemas/photonstrust.pic_invdesign_report.v0.schema.json`
- robustness cases + explicit aggregation rules (mean/max): `photonstrust/invdesign/_robust.py`
- additional deterministic primitive: `photonstrust/invdesign/coupler_ratio.py` + API/UI wiring

Gate:
- inverse-designed block must ship with:
  - DRC-clean layout (or DRC-lite checks),
  - corner robustness report,
  - deterministic replay artifacts.

### Track B: Circuit-level control (not just chains)

Current PIC simulation supports forward-only DAG and a simple coupler model.
To be a contender, v3 must support:
- resonator feedback (rings),
- wavelength-dependent models as first-class,
- and S-matrix composition beyond a single forward scalar.

Deliverables:
- implement ring transfer functions (all-pass/add-drop) with parameters:
  coupling, loss, round-trip phase, FSR proxies.
- implemented v0.2 (all-pass, 2-port):
  - `photonstrust/components/pic/library.py` (`pic.ring`)
  - `tests/test_pic_ring_resonance.py`
- implement a conservative network solver:
  - still v1-friendly (bounded complexity),
  - supports multiport S-matrix nodes.

Gate:
- ring + MZI + mux toy circuits have:
  - expected qualitative behavior,
  - regression baselines,
  - and bounded runtime in preview mode.

### Track C: PDK-aware layout generation + verification hooks

Goal:
- from compiled graph + params, generate GDS layout and run checks.

Start with public/no-NDA PDKs to prove the workflow:
- CORNERSTONE, VTT, Luxtelligence wrappers, SiEPIC EBeam.

Deliverables:
- deterministic layout hooks (sidecar-first; CI-friendly):
  - `photonstrust/layout/pic/build_layout.py` (ports/routes/provenance, optional GDS via `gdstk`)
  - `photonstrust/layout/pic/extract_connectivity.py` (snap route endpoints to ports)
  - `photonstrust/verification/lvs_lite.py` (expected vs observed mismatch summaries)
- optional KLayout runner seam (external tool posture):
  - `photonstrust/layout/pic/klayout_runner.py`
- KLayout macro templates + "run artifact pack" evidence contract (external tool posture):
  - `tools/klayout/macros/pt_pic_extract_and_drc_lite.py`
  - `photonstrust/layout/pic/klayout_artifact_pack.py`
  - `schemas/photonstrust.pic_klayout_run_artifact_pack.v0.schema.json`
- Managed workflow surface integration:
  - API: `POST /v0/pic/layout/klayout/run`
  - web: PIC tab `KLayout` (served artifact links)
  - Runs browser: run KLayout pack on a selected `.gds` artifact from the Run Registry (Phase 32)
- deferred (future): gdsfactory-first PDK routing/placement once contracts are stable.

Gate:
- "chip evidence pack" is generated and linked from the run registry.

---

### Track D: EDA interoperability (SPICE export + batch runners)

Goal:
- plug PhotonTrust artifacts into existing EDA/simulation flows without turning
  the open-core into a tool-dependent monolith.

Deliverables:
- deterministic SPICE-like netlist export:
  - `photonstrust/spice/export.py` (writes `netlist.sp` + `spice_map.json` + provenance)
- optional ngspice runner seam (external tool posture):
  - `photonstrust/spice/ngspice_runner.py`

Gate:
- exports are deterministic and schema-valid; runner fails clearly when missing.

## 6) Data Strategy: How We Get Data (Without Waiting for Big Tech)

You need data for:
- crosstalk calibration,
- compact model validation,
- yield corners and drift behavior.

Do it in layers:

1. Synthetic-first:
   - generate datasets by simulation (sweep gap/width/lambda/length).
2. Academic + shared facilities:
   - publish "test coupon" layouts and ask labs to measure them.
3. Industry pilots:
   - private ingestion via on-prem runner; export only aggregated fits.

India-specific pathway:
- Use INUP-i2i and top nano/photonics centers as the first measurement partners.
  They have an explicit mission to enable broader access to infrastructure.
- Offer them:
  - a free evidence pack generator,
  - co-authored benchmark packs,
  - and a reproducible publication pipeline.

The repo already supports:
- ingestion + redaction + publish packs.
Use this to make "sharing data" safe and structured.

---

## 7) Competitive Differentiation (Concrete)

To avoid being crushed by large EDA/simulation vendors:

- Do not claim "we simulate everything".
- Claim:
  "We provide performance DRC + evidence packs + calibration loops + drift
   governance, and we plug into your existing PDK/compact model ecosystem."

This aligns with how compact model flows are positioned (calibration + reuse),
and makes PhotonTrust a required gate rather than a competing monolith.

---

## 8) KPIs and Release Gates (Non-negotiable)

### Technical KPIs
- Preview p95 runtime for flagship checks: < 2s (crosstalk slider).
- Certification runtime budget: documented and bounded per scenario class.
- Deterministic replay pass rate: 100% on flagship benchmarks.

### Trust KPIs
- Percentage of artifacts with complete provenance bundles: > 95%.
- Drift incidents per release: tracked and justified (never silent).
- Calibration quality: clear before/after error metrics, diagnostics in cards.

### Business KPIs (early)
- time-to-first-trusted-decision report: < 1 day for a new partner.
- pilot conversion: >= 1 paid pilot within 8-12 weeks of v2.

---

## 9) Risk Register (Hard Truths)

Risk: license traps from GPL inverse-design tooling.
Mitigation: keep GPL tools as optional plugins; build product core on permissive
interfaces. (Not legal advice.)

Risk: full-chip inverse design is intractable and brittle.
Mitigation: hierarchical block optimization + robust corners + evidence gates.

Risk: foundry PDK access is gated by NDA.
Mitigation: public PDK path + plugin adapter architecture for private PDKs.

Risk: model claims are dismissed as "toy".
Mitigation: performance DRC + calibration against real measurements + reproducibility
packs + drift governance.

---

## 10) Source index (web-validated anchors)

Market/standards signals:
- IEEE 802.3dj (1.6 Tb/s Ethernet task force overview):
  https://www.ieee802.org/3/dj/index.html
- IEEE SA article on 1.6 Tb/s Ethernet effort:
  https://standards.ieee.org/beyond-standards/ieee-802-3-1-6-terabits-per-second-ethernet-2/
- OIF CEI-224G project page (224G electrical lanes):
  https://www.oiforum.com/technical-work/hot-topics/cei-224g/
- Broadcom press release (1.6T optical interconnect DSP):
  https://www.broadcom.com/company/news/product-releases/61156

Open PIC toolchain and PDK ecosystem:
- gdsfactory (docs):
  https://gdsfactory.github.io/gdsfactory/
- gdsfactory open-source PDK list ("no NDA required"):
  https://github.com/gdsfactory/gdsfactory?tab=readme-ov-file#open-source-pdks-no-nda-required
- CORNERSTONE PDK wrapper:
  https://github.com/gdsfactory/cspdk
- VTT PDK:
  https://github.com/gdsfactory/vtt
- Luxtelligence PDK:
  https://github.com/gdsfactory/luxtelligence
- SiEPIC tools:
  https://siepic-tools.readthedocs.io/
- KLayout license notes (artwork you create is yours):
  https://www.klayout.de/license.html

Inverse design and adjoint optimization:
- SPINS-B (repo + GPL-3.0 license):
  https://github.com/stanfordnqp/spins-b
  https://github.com/stanfordnqp/spins-b/blob/master/LICENSE
- SPINS architecture paper:
  https://arxiv.org/abs/1910.04829
- Meep adjoint solver:
  https://meep.readthedocs.io/en/latest/Python_Tutorials/Adjoint_Solver/
- Ceviche (MIT):
  https://github.com/fancompute/ceviche
- Lumopt (MIT):
  https://github.com/chriskeraly/lumopt

Coupled-mode theory references (for crosstalk/coupling physics):
- Coupled-mode theory (handbook chapter):
  https://www.rp-photonics.com/coupled_mode_theory.html
- Minimizing crosstalk in waveguide couplers (example paper):
  https://doi.org/10.1364/AO.49.006199

India data partner entry points:
- INUP-i2i (national infrastructure program):
  https://inup.iisc.ac.in/
- IIT Madras CNNP (silicon photonics center):
  https://www.iitm.ac.in/research/institute-research-centres/centre-for-nems-and-nanophotonics
- IISc CeNSE (nanoscience/engineering center):
  https://cense.iisc.ac.in/
