# Phase 49: Cross-Track Integration (Phases 46–48) — Validation Report

Date: 2026-02-16
Owner: Integration Lead

## Scope

Integrated overlapping outputs from recent build tracks:

- **Phase 46**: BBM92 coincidence model + reliability-card multipair semantics
- **Phase 47**: PIC scattering-network solver + cycle-aware compiler behavior
- **Phase 48**: PIC scattering realism pack (edge propagation, N-port Touchstone, isolator, tooling integration)

## Cross-Track Overlap Review

Reviewed shared/high-risk files for consistency:

- `photonstrust/qkd.py`
- `photonstrust/qkd_protocols/bbm92.py`
- `photonstrust/report.py`
- `photonstrust/components/pic/library.py`
- `photonstrust/pic/simulate.py`
- `photonstrust/graph/compiler.py`
- `photonstrust/components/pic/touchstone.py`
- `photonstrust/registry/kinds.py`
- `schemas/photonstrust.graph.v0_1.schema.json`

### Integration conclusions

1. **QKD dispatch + protocol modules are coherent**
   - `qkd.py` routes BBM92/E91 to `qkd_protocols.bbm92.compute_point_bbm92`.
   - Relay families (MDI/PM/TF) remain separated and unaffected.

2. **Reliability card semantics align with source-side multipair accounting**
   - `report.py` computes multipair proxy from source model (SPDC or emitter stats), consistent with Phase 46 intent.

3. **PIC solver/compiler/schema coupling is internally consistent**
   - Compiler allows cyclic PIC graphs only when `circuit.solver='scattering'`.
   - Simulator supports both DAG and scattering paths, with edge propagation parameters applied.
   - Schema and kind registry expose the required edge/node parameters for the new behavior.

4. **Touchstone ingestion path is complete across layers**
   - N-port parsing/interpolation exists in `touchstone.py`.
   - Component library supports `pic.touchstone_nport` including dynamic port mapping.
   - Registry includes `pic.touchstone_nport` metadata for UI/validation surfaces.

## Conflict/Overlap Resolution Performed

### Fixed integration artifact in `report.py`

Removed unreachable stray code block left after `_render_html()` return (duplicated multipair snippet with undefined `scenario` in local scope). This did not currently execute but was clear integration residue and maintenance risk.

- File updated: `photonstrust/report.py`
- Effect: codebase cleanup, reduced confusion/risk for future edits and static analysis.

## Validation Executed in Current Environment

### 1) Syntax/bytecode sanity

- Command: `python3 -m compileall -q photonstrust tests`
- Result: **PASS**

### 2) Test-suite feasibility check

Attempted full test execution, but environment lacks runtime dependencies/tools:

- `pytest` not installed
- `numpy` not installed
- no `pip`/`ensurepip` available in this runtime

As a result, full pytest validation could not be reproduced here despite prior phase reports indicating green runs.

## Known Environment Constraints

Current shell runtime is missing required dev/runtime stack from `pyproject.toml`:

- required runtime: `numpy`, `pyyaml`, `matplotlib`
- required dev: `pytest`, `jsonschema`, `cryptography`

## Next Fixes / Follow-ups

1. **Rehydrate reproducible test environment (highest priority)**
   - Create project venv and install `.[dev]` (+ optional extras used in CI lanes).
   - Re-run full `pytest -q` baseline.

2. **Add CI/pre-merge static guardrails**
   - Add `python -m compileall photonstrust tests` job.
   - Add linter/dead-code pass (e.g., Ruff/Flake8) to catch unreachable residue like removed block.

3. **Scattering solver robustness checks**
   - Add stress tests for ill-conditioned scattering systems (condition number thresholds and failure messaging).
   - Consider optional regularization policy for near-singular solves.

4. **Touchstone coverage extension**
   - Add explicit tests for odd-`n_ports` requiring manual `in_ports`/`out_ports`.
   - Add test vectors for extrapolation policy at both bounds.

5. **Documentation sync**
   - Add one cross-track “integration matrix” page summarizing: compiler rules, solver mode behavior, schema knobs, and registry exposure.

## Overall Status

- **Integration status**: COMPLETE for source-level overlap/conflict reconciliation.
- **Validation status in this environment**: PARTIAL (syntax pass; full pytest blocked by missing dependencies/tooling).
- **Risk level**: MODERATE until full dependency-backed test replay is executed.
