# Phase 55 (W21-W24) GraphSpec Round-Trip Notes (2026-02-16)

## Delivered in this increment

- Added GraphSpec TOML parser and TOML-to-canonical-JSON bridge in `photonstrust/graph/spec.py`.
- Added deterministic GraphSpec formatter and stable semantic graph hash generation.
- Added CLI formatter surface: `photonstrust fmt graphspec` with `--check`, `--write`, `--output`, and `--print-hash` options.
- Extended `photonstrust graph compile` to accept GraphSpec TOML input files directly.
- Added typed port domain metadata in the backend kind registry (`port_domains`) while preserving existing `ports` shape.
- Enforced typed port domain checks in PIC compiler and semantic diagnostics (invalid domain/kind combinations now fail early).
- Added UI-side invalid connection blocking for PIC editor edges based on typed port domains.
- Added deterministic TOML fixture for QKD graph authoring: `graphs/demo8_qkd_link_graph.ptg.toml`.

## Round-trip and regression coverage

- New tests:
  - `tests/test_graph_spec.py`
  - Added TOML compile and typed-domain checks in `tests/test_graph_compiler.py`
  - Added typed-domain diagnostics check in `tests/test_graph_diagnostics.py`
- Core guarantees now covered:
  - TOML format idempotence.
  - Stable hash equivalence across JSON -> TOML -> JSON round-trip.
  - PIC edge defaults canonicalization in round-trip paths.

## Validation executed

- `py -3 -m pytest` -> `274 passed, 2 skipped, 1 warning`.
- `py -3 scripts/check_benchmark_drift.py` -> PASS.
- `py -3 scripts/release_gate_check.py` -> PASS.
- `py -3 scripts/ci_checks.py` -> PASS.
- `py -3 scripts/run_validation_harness.py --output-root results/validation` -> PASS (`case_count: 10`, `failed_cases: 0`).

## Remaining follow-ups

- Add explicit GraphSpec user-facing authoring guide in `docs/research` or `docs/operations` with TOML null-handling semantics (null fields are normalized as absent in canonical form).
- Expand UI edge metadata editing to expose non-optical edge kinds where compatible typed ports are introduced.
