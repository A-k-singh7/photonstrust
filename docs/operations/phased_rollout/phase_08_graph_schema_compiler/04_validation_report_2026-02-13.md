# Validation Report

## Metadata
- Work item ID: PT-PHASE-08
- Date: 2026-02-13
- Reviewer: Internal QA

## Status
- Completed (validation gates passed).

## 1) Test evidence
- Full suite: `py -m pytest -q` -> `57 passed`
- Schema validation:
  - `tests/test_schema_validation.py` validates:
    - `schemas/photonstrust.graph.v0_1.schema.json`
- Compiler tests:
  - `tests/test_graph_compiler.py` -> PASS

## 2) Manual workflow checks
- Compile QKD graph:
  - `py -m photonstrust.cli graph compile graphs/demo8_qkd_link_graph.json --output results/graphs_demo`
  - Produced:
    - `compiled_config.yml`
    - `compile_provenance.json`
    - `assumptions.md`
- Execute compiled QKD config:
  - `py -m photonstrust.cli run results/graphs_demo/demo8_qkd_link/compiled_config.yml --output results/graphs_demo/demo8_qkd_link/run_outputs`
  - Produced per-band artifacts including `reliability_card.json` and `performance.json`.

- Compile PIC graph:
  - `py -m photonstrust.cli graph compile graphs/demo8_pic_circuit_graph.json --output results/graphs_demo`
  - Produced:
    - `compiled_netlist.json`
    - deterministic `topology.topological_order`

## 3) Acceptance criteria check
- Graph schema exists + tested: PASS
- Compiler supports both `qkd_link` and `pic_circuit`: PASS
- CLI produces compile artifacts and provenance: PASS
- Deterministic compilation tested (PIC topo order): PASS

## 4) Known limitations (v0.1)
- QKD `edges` are informational only (compiler uses required node kinds).
- PIC compilation produces a normalized netlist only; physics execution is
  delivered in Phase 09.
