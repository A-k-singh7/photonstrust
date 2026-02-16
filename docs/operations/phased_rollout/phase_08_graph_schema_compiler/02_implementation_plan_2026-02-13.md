# Implementation Plan

## Metadata
- Work item ID: PT-PHASE-08
- Scope owner: Graph compiler + data contracts
- Target milestone: Graph schema v0.1 + compiler + CLI

## 1) Scope and non-scope

In scope:
- Graph JSON schema v0.1 covering both:
  - QKD link graphs (`qkd_link` profile)
  - PIC circuit graphs (`pic_circuit` profile)
- Deterministic compiler:
  - `qkd_link` -> existing YAML config structure
  - `pic_circuit` -> normalized netlist JSON (no physics yet)
- CLI command:
  - `photonstrust graph compile <graph.json> --output <dir>`
- Compile artifacts:
  - compiled output (config or netlist)
  - `compile_provenance.json`
  - `assumptions.md`
- Tests for schema validation and compiler determinism.

Out of scope (later phases):
- Full PIC physics and compact model execution (Phase 09).
- Full web UI (Phase 12).
- Graph-to-protocol compiler (Qiskit) integration.

## 2) File-level plan

### Step 1: Schema
- Add:
  - `schemas/photonstrust.graph.v0_1.schema.json`
- Add schema validation test entry:
  - update `tests/test_schema_validation.py`

### Step 2: Compiler module
- Add:
  - `photonstrust/graph/__init__.py`
  - `photonstrust/graph/schema.py` (optional jsonschema validation)
  - `photonstrust/graph/compiler.py`
- Implement:
  - compile `qkd_link` graphs into config dict:
    - `scenario`, `source`, `channel`, `detector`, `timing`, `protocol`, `uncertainty`
  - compile `pic_circuit` graphs into normalized netlist dict:
    - node/edge normalization, deterministic topological order, validity checks

### Step 3: CLI
- Update `photonstrust/cli.py` to add:
  - `photonstrust graph compile`

### Step 4: Demos + fixtures
- Add:
  - `graphs/demo8_qkd_link_graph.json`
  - `graphs/demo8_pic_circuit_graph.json`

### Step 5: Tests
- Add:
  - `tests/test_graph_compiler.py`:
    - QKD graph compiles and can be run through `build_scenarios(...)`
    - PIC graph compiles and produces deterministic node order
    - cycle detection and missing endpoint errors

### Step 6: Documentation updates
- Update:
  - `README.md` (graph compile commands)
  - `docs/research/02_architecture_and_interfaces.md` (graph module is now real)
  - `docs/research/15_platform_rollout_plan_2026-02-13.md` (Phase 08 implemented)

## 3) Validation plan
- Run:
  - `py -m pytest -q`
  - `py scripts/release_gate_check.py`
- Manual spot checks:
  - compile both demo graphs
  - run compiled QKD config via CLI to produce a reliability card

## 4) Done criteria
- [x] Graph schema exists and passes schema validation tests
- [x] Graph compiler supports `qkd_link` and `pic_circuit`
- [x] CLI `photonstrust graph compile` produces all artifacts
- [x] Demo graphs exist and compile
- [x] Tests pass and Phase 08 validation report is written
