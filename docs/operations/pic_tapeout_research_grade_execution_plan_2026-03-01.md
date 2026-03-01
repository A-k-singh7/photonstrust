# PIC Tapeout Research-Grade Execution Plan

## Metadata
- Date: 2026-03-01
- Program: Foundry-facing PIC tapeout hardening
- Scope: DRC, LVS, PDK, GDS, signoff, package, CI
- Planning method: Parallel sub-agent analysis across 7 workstreams

## 0. Reality Check and Success Definition
- "100% physics accurate" is not a scientifically defensible claim for fabrication workflows.
- Research-grade target for this plan:
  - Explicit physical assumptions and tolerances in machine-readable artifacts.
  - Deterministic geometry checks for all mandatory foundry rules in scope.
  - End-to-end traceability from schematic graph to GDS/signoff package.
  - Quantified pass/fail criteria with waiver policy and evidence hash chain.

## 1. Verified Starting Point
- Working now:
  - Graph-based compilation, S-parameter simulation, chip assembly report.
  - Tapeout gate checker and waiver flow.
- Gaps confirmed by code scan:
  - No production DRC geometry rule engine module at `photonstrust/pic/drc.py`.
  - No production LVS engine module at `photonstrust/pic/lvs.py`.
  - PDK runtime loading is minimal and lacks `configs/pdks/*.pdk.json` flow.
  - Dedicated `photonstrust/layout/gds_write.py` is absent; GDS emission is embedded and non-deterministic on timestamp metadata.
  - Signoff ladder is one-stage (`chip_assembly`) and not hash-chained across multiple required stages.
  - `scripts/build_tapeout_package.py` and `photonstrust/pic/tapeout_package.py` are absent.
  - CI has strong baseline workflows but no dedicated tapeout package gate workflow with PR path filtering.

## 2. Dependency State
- `gdstk` is already installed in this environment (`gdstk==0.9.62` observed).
- `pyproject.toml` already declares `layout = ["gdstk>=0.9"]`.
- Action: do not reinstall now; keep as optional extra and pin exact CI runtime in workflow job.

## 3. Execution Topology
- Phase 1 (parallel):
  - Workstream A1: DRC engine
  - Workstream A2: LVS engine
  - Workstream A3: PDK standardization
  - Workstream A4: GDS writer
- Phase 2 (sequential):
  - Workstream B1: multi-stage signoff ladder
  - Workstream B2: tapeout package builder
  - Workstream B3: CI/CD integration

## 4. Workstream Specs

### A1. DRC Engine (Rule-Deck Driven)
#### Deliverables
- New module: `photonstrust/pic/drc.py`
- New report artifact: `foundry_drc_sealed_summary.json` with per-rule result objects
- Gate integration updates in `scripts/check_pic_tapeout_gate.py`

#### Required rules (minimum)
- `DRC.WG.MIN_WIDTH`
- `DRC.WG.MIN_SPACING`
- `DRC.WG.MIN_BEND_RADIUS`
- `DRC.WG.MIN_ENCLOSURE`

#### Implementation tasks
1. Implement `check_min_width(routes, pdk)`:
   - Measure route segment width against `min_waveguide_width_um`.
2. Implement `check_min_spacing(routes, pdk)`:
   - Pairwise nearest-distance on same layer with sweep-line or indexed spatial search.
3. Implement `check_min_bend_radius(routes, pdk)`:
   - Compute local curvature from polyline triplets/arcs and extract minimum bend radius.
4. Implement `check_layer_enclosure(routes, pdk)`:
   - Verify cladding/keepout enclosure margins around core waveguide paths.
5. Emit deterministic `rule_results` and derive `failed_check_ids` from failed rules only.

#### Schema and gate changes
- Extend `schemas/photonstrust.pic_foundry_drc_sealed_summary.v0.schema.json`:
  - Require `rule_results` with the four mandatory keys.
  - Each rule payload includes `status`, `required_um`, `observed_um`, `violation_count`, `entity_refs`.
- Update `scripts/check_pic_tapeout_gate.py` to:
  - Validate mandatory DRC rule coverage.
  - Reject inconsistent `failed_check_ids` vs `rule_results`.
  - Surface per-rule waiver and fail details in output report.

#### Tests
- Add DRC rule-presence and consistency tests in `tests/test_pic_tapeout_gate.py`.
- Add signoff-coupled DRC fail/waive behavior in `tests/test_pic_signoff_core.py`.

### A2. LVS Engine (Schematic vs Physical)
#### Deliverables
- New module: `photonstrust/pic/lvs.py`
- New report artifact: `foundry_lvs_sealed_summary.json`
- Optional richer intermediate artifact: `pic_lvs_lite.json`

#### Implementation tasks
1. Parse schematic graph (`inputs/graph.json`) into canonical net adjacency.
2. Parse extracted routes (`inputs/routes.json`) into physical connectivity graph.
3. Canonicalize edges as undirected endpoint tuples for deterministic set comparison.
4. Detect and report:
   - missing edges
   - extra edges
   - port-role/port-map mismatches
   - unconnected ports
5. Produce foundry summary fields consistent with gate checks (`status`, `check_counts`, failed IDs/names, backend, timestamps).

#### Schema changes
- Tighten `schemas/photonstrust.pic_lvs_lite.v0.schema.json`:
  - Add item schema definitions for edge/mismatch arrays.
  - Add count consistency checks in code-level validator.

#### Tests
- Add `tests/test_pic_lvs_lite.py` for edge diff correctness.
- Add schema-consistency tests for mismatch counts and pass/fail derivation.

### A3. PDK Standardization
#### Deliverables
- Runtime loader: `photonstrust/pic/pdk_loader.py`
- Typed PDK models: `photonstrust/pdk/models.py`
- Runtime manifests: `configs/pdks/*.pdk.json`

#### Implementation tasks
1. Add deterministic loader precedence:
   - explicit `manifest_path` -> explicit `name` -> `configs/pdks/<name>.pdk.json` -> built-in fallback.
2. Extend PDK model with:
   - `layer_stack` (waveguide, cladding, metals),
   - `design_rules`,
   - `component_cells` (characterized cells/S-parameter refs),
   - optional `interop` (`siepic`, `aim` blocks).
3. Add AIM-compatible built-in profile as second production profile.
4. Keep backward compatibility for existing `generic_silicon_photonics`.

#### Schema changes
- Extend `schemas/photonstrust.pdk_manifest.v0.schema.json`:
  - Add foundry/process identity fields.
  - Add loader request `oneOf` rule (`name` xor `manifest_path`).
  - Add optional interop blocks for SiEPIC/AIM compatibility.

#### Tests
- Loader precedence and cache invalidation tests.
- Alias normalization tests (`siepic`, `ebeam`, `aim`, `aim_photonics`).
- Contract round-trip serialization tests.

### A4. GDS Generation
#### Deliverables
- New writer module: `photonstrust/layout/gds_write.py`
- API: `write_gds(netlist, pdk, output_path, *, timestamp=None, max_points=199)`

#### Implementation tasks
1. Build top-level cell using canonical naming (`run_id` + `graph_id`).
2. Map routes to `gdstk.FlexPath/RobustPath` on layers from `pdk.layer_stack`.
3. Place component references as `gdstk.Reference` with orientation transforms.
4. Add I/O port markers as annotation polygons/text labels on designated marker layer.
5. Write GDS with deterministic metadata:
   - pass fixed `timestamp` during CI/golden tests.
   - explicit `max_points`.

#### Tests
- Deterministic golden tests for stable GDS bytes under fixed timestamp.
- Geometry/layer mapping assertions for route and marker layers.
- Missing-optional-dependency behavior tests.

### B1. Signoff Ladder Expansion
#### Deliverables
- Expand `photonstrust/pic/signoff.py` from single-level to multi-level ladder.
- Extend signoff schema: `schemas/photonstrust.pic_signoff_ladder.v0.schema.json`.

#### Required stage order
1. `chip_assembly`
2. `drc`
3. `lvs`
4. `pex`
5. `foundry_approval`

#### Implementation tasks
1. Stage evaluator framework with fail-fast and stage prerequisites.
2. Per-stage waivers with explicit waived rule IDs.
3. Hash-chain:
   - stage `prev_stage_hash`
   - stage `stage_hash`
   - report `evidence_chain_root`
4. Final decision policy:
   - `GO` only if all mandatory stages are pass or fully waived.
   - `HOLD` otherwise.

#### Tests
- Multi-stage order and fail-fast semantics.
- Partial-vs-complete waiver behavior.
- Evidence hash-chain determinism and tamper detection.

### B2. Tapeout Package Builder
#### Deliverables
- New script: `scripts/build_tapeout_package.py`
- New module: `photonstrust/pic/tapeout_package.py`
- Package output:
  - `README.md`
  - `MANIFEST.sha256`
  - structured package manifest JSON

#### Required package structure
- `inputs/`:
  - `graph.json`, `ports.json`, `routes.json`, `layout.gds`
- `verification/`:
  - `foundry_drc_sealed_summary.json`
  - `foundry_lvs_sealed_summary.json`
  - `foundry_pex_sealed_summary.json` (stub allowed with explicit status)
- `signoff/`:
  - `signoff_ladder.json`
  - `waivers.json`

#### Implementation tasks
1. Build package from run directory with strict required-file checks.
2. Auto-generate README with provenance and verification command.
3. Generate deterministic SHA256 manifest:
   - sorted relative paths, stable separators, fixed line format.

#### Tests
- Required file presence and strict failure modes.
- Manifest determinism tests.
- Round-trip validation with tapeout gate checker.

### B3. CI/CD Integration
#### Deliverables
- New workflow: `.github/workflows/tapeout-gate.yml`
- Extend `.github/workflows/cv-quick-verify.yml` with `workflow_call`
- Optional README badge updates

#### Implementation tasks
1. Trigger on PR/path changes touching:
   - `graphs/**`
   - `configs/**`
   - `photonstrust/pic/**`
   - related scripts/schemas for tapeout
2. Job pipeline:
   - compile -> simulate -> assemble -> DRC -> LVS -> signoff -> package
3. Upload package as artifact for every run (`if: always()`).
4. Prevent duplicate CV execution by choosing one of:
   - reusable-only CV workflow, or
   - keep current triggers and do not call it as reusable.

#### Tests
- Workflow dry-run checks on sample PR.
- Artifact presence assertions.
- Non-mock backend policy behavior in CI lane.

## 5. Integration Milestones
- M1 (end of Phase 1): DRC/LVS/PDK/GDS all green in unit tests and produce compatible artifacts.
- M2 (end of Phase 2):
  - Multi-stage signoff produces GO/HOLD deterministically with hash-chain.
  - Tapeout package builder produces reproducible package + SHA manifest.
  - CI uploads package artifacts and enforces gate policy.

## 6. Physics Fidelity and Validation Envelope
- Geometry fidelity rules:
  - All measured quantities in um; no mixed-unit operations.
  - Explicit route sampling resolution and curvature approximation method.
  - Numeric tolerances documented in reports (`coord_tol_um`, `radius_tol_um`, etc.).
- Correlation policy:
  - Open-source DRC/LVS are pre-screeners, not foundry authority.
  - Final acceptance requires foundry-sealed summaries (`execution_backend != mock` for production signoff).
- Reproducibility policy:
  - Deterministic outputs for all generated JSON and CI-mode GDS metadata.
  - Hash-chain and manifest required for every signoff package.

## 7. Risks and Mitigations
- Risk: false confidence from synthetic/mock signoff.
  - Mitigation: explicit policy flag requiring non-mock backend for GO.
- Risk: schema drift across tools.
  - Mitigation: schema-first updates with compatibility adapters and contract tests.
- Risk: non-deterministic artifacts.
  - Mitigation: fixed timestamp/ordering in writer and manifest generation.
- Risk: long CI times from optional quantum deps.
  - Mitigation: separate tapeout lane dependency set and cache pip wheels.

## 8. Definition of Done
- [ ] New DRC engine enforces all four mandatory geometric rules and emits structured per-rule evidence.
- [ ] New LVS engine compares schematic vs extracted physical connectivity and emits sealed summary.
- [ ] PDK loader supports runtime manifests and at least two foundry-style profiles.
- [ ] GDS writer module exists and passes deterministic golden tests.
- [ ] Signoff ladder runs all five mandatory stages with waiver support and hash-chain evidence.
- [ ] Tapeout package builder outputs required directory, README, and SHA256 manifest.
- [ ] CI workflow executes full tapeout gate path and uploads package artifacts.
- [ ] All new and affected tests pass in local and CI runs.
