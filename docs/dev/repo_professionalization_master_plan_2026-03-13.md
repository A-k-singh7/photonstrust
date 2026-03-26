# Repo Professionalization Master Plan (2026-03-13)

## Goal

Make the PhotonTrust repository feel extremely clean, deliberate, and
professional for public open-source use.

That means:

1. new users can find the right entry point quickly,
2. contributors can understand structure and naming without guessing,
3. generated artifacts are clearly separated from intentional evidence,
4. docs are obviously categorized into active guidance vs history,
5. code, tests, scripts, configs, and UI labels follow explicit naming rules.

## Current Audit Snapshot

### Top-level repository observations

Current root contains a mix of:

- core package code: `photonstrust/`
- product surfaces: `web/`, `ui/`
- docs and planning: `docs/`
- runnable inputs: `configs/`, `graphs/`, `examples/`
- automation: `scripts/`
- generated/evidence-like outputs: `results/`, `reports/`
- data and supporting assets: `datasets/`, `tools/`
- notebook and exploratory content: `notebooks/`
- legacy or separately managed content: `open_source/`, `photonstrust_rs/`
- local/private or questionable runtime areas: `local/`, `.venv/`, `.venv.production/`, `.benchmarks/`, `tmp_*.pdf`

Assessment:

1. the repo is now much better than before, but still carries too many mixed
   responsibilities at the root,
2. active public surfaces and historical/internal surfaces are not yet cleanly
   separated,
3. there is still ambiguity around what is source, what is evidence, what is
   generated, and what is private.

### Naming observations

#### Tests

There are at least these naming patterns in `tests/`:

- stable domain tests: `test_detector_model.py`, `test_graph_compiler.py`
- script tests: `test_build_pic_gate_e_packet_script.py`
- program-phase tests: `test_packaging_readiness.py`
- dated milestone style tests: `test_day10_tapeout_rehearsal.py`
- milestone shorthand tests: `test_m3_checkpoint.py`
- UI helper tests mixed into Python tree: `test_ui_data_helpers.py`, `test_ui_newcomer_flow_parity.py`

Assessment:

1. script-test naming is reasonably consistent,
2. domain-test naming is reasonably consistent,
3. phase/day/milestone naming is useful internally but not clean for a public
   repo unless grouped and documented,
4. `tests/` is too flat for the current scale.

#### Scripts

Current `scripts/` prefixes include:

- `run_*` (20 files)
- `build_*` (9 files)
- `check_*` (11 files)
- `generate_*` (8 files)
- `verify_*` (3 files)
- smaller groups like `init_*`, `publish_*`, `refresh_*`, `bundle_*`, `measure_*`

Assessment:

1. verb prefixes are mostly good,
2. the directory is too crowded,
3. script discoverability depends too much on already knowing internal language.

#### Configs

Top-level config names mix:

- demo-numbered configs: `demo1_*`, `demo11_*`, `demo13_*`
- generic examples: `calibration_example.yml`, `optimization_example.yml`
- pilot/program names: `pilot_day0_kickoff.yml`

Assessment:

1. demo numbering is not self-explanatory to new users,
2. some config names are user-friendly, others are internal-program friendly,
3. a catalog exists, but the naming system still looks historical rather than curated.

#### Docs

The docs tree is now better organized, but there are still hundreds of dated
Markdown files. A quick scan shows very heavy use of:

- dated filenames,
- numbered sequences like `00_*`, `01_*`, `02_*`,
- internal planning conventions,
- milestone shorthand (`M1`, `M7`, etc.),
- phase shorthand (`phase0`, `phase58`, etc.).

Assessment:

1. this is useful as a historical archive,
2. it is not yet ideal for public-facing discoverability,
3. stable canonical docs and archived historical docs still need stronger separation.

## Naming Standards To Adopt

### Python package files

Keep:

- `snake_case.py`
- explicit domain-oriented module names

Avoid adding new files named only by milestone or phase unless they are scoped
to a clearly documented program package.

### React files

Keep:

- `PascalCase.jsx` for components
- `camelCase.js` for hooks and state utilities where already established

Standardize:

- hooks must live under `web/src/hooks/` and start with `use`
- state helpers must live under `web/src/state/`
- feature folders should use domain names, not sprint/week labels

### Test files

Adopt this target standard:

- domain/unit/integration tests: `test_<subject>_<behavior>.py`
- script tests: `test_<script_name>_script.py`
- contract tests: `test_<surface>_contract.py`
- schema tests: `test_<artifact>_schema.py`

Group by folder instead of encoding too much program history into filenames.

### Docs

Adopt two doc classes:

1. stable docs
   - no date in filename unless genuinely needed
   - example: `quickstart.md`, `validation.md`, `frontend_architecture.md`
2. historical snapshots
   - dated filename in archive only
   - example: `quickstart_2026-02-18.md`

### Configs

Target naming:

- quickstart: `qkd_quick_smoke.yml`, `orbit_pass_quickstart.yml`
- benchmark: `source_benchmark.yml`
- canonical: `canonical/<descriptive_name>.yml`
- product flows: `product/<descriptive_name>.yml`

If old `demoN_*` names must remain, maintain a compatibility layer and index.

## Repository Structure Target

### Keep at top level

- `photonstrust/`
- `web/`
- `ui/` (until officially deprecated)
- `tests/`
- `configs/`
- `graphs/`
- `examples/`
- `scripts/`
- `schemas/`
- `docs/`
- `datasets/`
- `reports/` only for intentional checked-in evidence
- `tools/`

### Review aggressively

- `results/`
  - should remain local/generated-first,
  - only explicitly documented evidence should be tracked.
- `open_source/`
  - either document as intentionally nested subprojects or remove from main repo.
- `notebooks/`
  - should either be curated or explicitly marked exploratory.
- `local/`
  - should never be a public-facing tracked area.
- `photonstrust_rs/`
  - either document as active sibling component or move/archive if experimental.

## Documentation Cleanup Plan

### Active doc categories that should remain easy to find

- `docs/user/`
- `docs/dev/`
- `docs/research/`
- `docs/operations/`
- `docs/templates/`
- `docs/archive/`

### Immediate doc tasks

1. Create canonical stable docs for the most important active topics:
   - user quickstart
   - frontend product guide
   - contributor setup
   - validation guide
   - release process
2. Move historical point-in-time versions into `docs/archive/`.
3. Mark dated docs as one of:
   - active reference
   - archived snapshot
   - superseded
4. Reduce the number of top-priority docs a new reader must inspect.

### Docs to classify explicitly

#### Keep as active guidance

- `README.md`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `SUPPORT.md`
- `docs/README.md`
- `docs/user/README.md`
- `docs/dev/README.md`
- `docs/operations/README.md`
- `docs/research/README.md`
- `configs/README.md`
- `scripts/README.md`
- `examples/README.md`

#### Archive or demote from main nav

- dated capability inventories
- dated implementation plans duplicated by later stable docs
- deeply internal work-item tracking files that do not help external readers
- redundant numbered research briefs once their conclusions are captured elsewhere

#### Review carefully before deleting

- milestone packets referenced by tests or release gates
- day/phase program docs used by scripts or governance checks
- validation baseline memos referenced by CI or release tooling

## Test Suite Cleanup Plan

### Current issue

`tests/` is too flat for 170 entries.

### Target folder structure

- `tests/unit/`
- `tests/integration/`
- `tests/contracts/`
- `tests/api/`
- `tests/scripts/`
- `tests/ui/`
- `tests/validation/`
- `tests/fixtures/`

### High-priority migrations

1. move script tests into `tests/scripts/`
2. move API tests into `tests/api/`
3. move contract tests into `tests/contracts/`
4. move validation/baseline phase tests into `tests/validation/`
5. move frontend-facing helper tests into `tests/ui/`

### Naming cleanup examples

These are technically fine but should be grouped/documented better:

- `test_packaging_readiness.py`
- `test_ga_release_cycle.py`
- `test_post_ga_hardening.py`
- `test_day10_tapeout_rehearsal.py`
- `test_m3_checkpoint.py`

Target approach:

- keep filenames if needed for traceability,
- but move them under `tests/validation/program/` or `tests/validation/milestones/`
- add a `README.md` explaining the milestone naming system.

## Script Cleanup Plan

### Target script folders

- `scripts/dev/`
- `scripts/validation/`
- `scripts/release/`
- `scripts/product/`
- `scripts/pic/`
- `scripts/satellite/`
- `scripts/ops/`

### Recommended grouping map

- dev:
  - `run_api_server.py`
  - `start_product_local.py`
  - `clean_local_workspace.py`
- validation:
  - `ci_checks.py`
  - `check_benchmark_drift.py`
  - `run_validation_harness.py`
  - `validate_recent_research_examples.py`
  - `compare_recent_research_benchmarks.py`
- release:
  - `release_gate_check.py`
  - `build_release_gate_packet.py`
  - `sign_release_gate_packet.py`
  - `verify_release_gate_packet.py`
- product:
  - `product_readiness_gate.py`
  - `run_product_pilot_demo.py`
  - `run_certify_demo.py`
- satellite:
  - `run_satellite_chain_*`
  - `run_orbit_provider_parity.py`
  - `generate_satellite_chain_reference.py`
- pic:
  - `build_pic_*`
  - `init_pic_*`
  - `refresh_pic_handoff_daily.py`
- ops:
  - `run_prefect_flow.py`
  - `apply_branch_protection.py`
  - `compute_ci_health_metrics.py`

### Migration rule

Do not move scripts until:

1. import paths and docs references are audited,
2. CI workflow references are updated,
3. README and tests are updated in the same commit.

## Config Cleanup Plan

### Immediate issue

Top-level `configs/` still looks historical and demo-numbered.

### Target structure

- `configs/quickstart/`
- `configs/research/`
- `configs/product/`
- `configs/canonical/`
- `configs/satellite/`
- `configs/compliance/`
- `configs/pic/`

### Migration examples

- `demo1_quick_smoke.yml` -> `quickstart/qkd_quick_smoke.yml`
- `demo11_orbit_pass_envelope.yml` -> `quickstart/orbit_pass_envelope.yml`
- `pilot_day0_kickoff.yml` -> `product/pilot_day0_kickoff.yml`
- `optimization_example.yml` -> `research/optimization_example.yml`

### Compatibility recommendation

If external users may already rely on old paths:

1. keep old files temporarily as wrappers or duplicates,
2. document the new canonical locations,
3. remove old names in a later breaking cleanup release.

## Results and Evidence Policy

### Immediate issue

The repo still contains both local-style generated outputs and intentional
evidence-like outputs.

### Policy to enforce

1. `results/` is local/generated-first.
2. only explicitly documented evidence subtrees may be tracked.
3. milestone or release evidence should preferably live in `reports/` with a
   README and provenance explanation.

### Review targets

- `results/release_gate/`
- `results/qutip_parity/`
- `results/research_validation/`
- `results/confirm_examples/`

For each tracked subtree, decide:

- keep as intentional evidence,
- move to `reports/`,
- archive under docs,
- or stop tracking and regenerate on demand.

## Data Boundary Review

### Immediate risk area

- `datasets/measurements/`

Need explicit review for:

1. redistributability,
2. privacy/sensitivity,
3. whether any `private/` subfolders should remain public,
4. whether README and provenance exist for each data area.

### Target

Every dataset subtree should say:

- source,
- license,
- whether synthetic or real,
- whether safe to redistribute,
- which scripts/tests depend on it.

## Frontend Professionalization Tasks

### Naming and terminology

Continue replacing internal labels with user-facing ones.

Recently improved:

- `Setup`
- `Assumptions`
- `Decision Review`
- `Evidence`

Still review:

- `DRC`
- `LVS-lite`
- `InvDesign`
- `Graph JSON`
- `Profile`
- `Mode`

### Architecture tasks

1. continue shrinking `web/src/App.jsx`
2. move more panel-specific orchestration into hooks/components
3. create a frontend architecture doc for public contributors

## CI and Automation Cleanup

### Current issue

CI is stronger now, but workflow count and naming should still be reviewed for
public clarity.

### Tasks

1. audit each GitHub workflow for overlap and public value,
2. ensure workflow names read clearly in GitHub checks,
3. add a short CI map doc under `docs/dev/` or `.github/README.md`.

## Professionalization Execution Waves

### Wave 1: Legal and public-facing consistency

1. commit AGPL-3.0 switch cleanly,
2. add README license note,
3. verify no remaining MIT references.

### Wave 2: Inventory and classification

1. top-level folder inventory,
2. docs classification matrix,
3. test naming matrix,
4. script grouping matrix,
5. config renaming matrix,
6. results/evidence retention matrix.

### Wave 3: Low-risk cleanup

1. add missing READMEs,
2. update stale references,
3. clean no-value docs from active navigation,
4. standardize filenames where no code references break.

### Wave 4: Structural moves

1. reorganize `tests/` by folder,
2. reorganize `scripts/` by domain,
3. reorganize `configs/` by purpose,
4. archive superseded docs.

### Wave 5: Public polish

1. screenshots,
2. polished README capability matrix,
3. release checklist,
4. public beta launch checklist.

## Concrete Next Actions

### Immediate next commit candidates

1. `chore(repo): switch project license metadata to AGPL-3.0`
2. `docs(repo): add cleanup inventory and classification matrices`
3. `docs(repo): clarify tracked evidence and dataset boundaries`

### Files to create next

1. `docs/dev/repo_inventory_matrix_2026-03-13.md`
2. `docs/dev/docs_cleanup_matrix_2026-03-13.md`
3. `docs/dev/test_naming_cleanup_matrix_2026-03-13.md`
4. `docs/dev/scripts_and_configs_cleanup_matrix_2026-03-13.md`

## Success Criteria

The repo is professionally clean when:

1. active docs are obvious,
2. historical docs are clearly archived,
3. test and script naming patterns are predictable,
4. generated artifacts are not mixed with source without explanation,
5. new contributors do not need oral history to understand the structure,
6. the public README feels confident and curated rather than accumulated.
