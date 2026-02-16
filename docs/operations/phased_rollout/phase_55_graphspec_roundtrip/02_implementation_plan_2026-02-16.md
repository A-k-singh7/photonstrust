# Phase 55: GraphSpec TOML + Round-Trip Guarantees (Implementation Plan)

Date: 2026-02-16

## Scope

Implement Phase 55 W21-W24 by shipping GraphSpec TOML authoring,
deterministic formatting + stable hashing, typed port-domain connection
enforcement, and round-trip equivalence tests.

## Owner map lock (release-critical workstreams)

Owner roles follow `docs/research/deep_dive/13_raci_matrix.md`.

| Workstream | Accountable | Responsible | Consulted | Backup |
|---|---|---|---|---|
| GraphSpec TOML parser + canonical loader bridge | TL | SIM | QA | DOC |
| Deterministic formatter + stable semantic hashing | TL | SIM | QA | DOC |
| Typed port-domain connection enforcement (compiler/diagnostics/UI) | TL | SIM | QA | DOC |
| Round-trip fixtures/tests + rollout documentation | QA | DOC | TL | SIM |

## Implementation tasks

1. Add GraphSpec parsing and canonicalization module:
   - `photonstrust/graph/spec.py`
   - `photonstrust/graph/__init__.py`
2. Extend graph compile/CLI input and formatter command surface:
   - `photonstrust/cli.py`
   - `photonstrust/graph/compiler.py`
3. Add typed port-domain metadata and enforcement:
   - `photonstrust/registry/kinds.py`
   - `photonstrust/graph/compiler.py`
   - `photonstrust/graph/diagnostics.py`
   - `web/src/photontrust/kinds.js`
   - `web/src/photontrust/graph.js`
   - `web/src/App.jsx`
4. Add round-trip fixtures/tests:
   - `graphs/demo8_qkd_link_graph.ptg.toml`
   - `tests/test_graph_spec.py`
   - `tests/test_graph_compiler.py`
   - `tests/test_graph_diagnostics.py`
5. Add phase/week operations documentation:
   - `docs/operations/week21/phase55_w21_graphspec_parser_notes_2026-02-16.md`
   - `docs/operations/week22/phase55_w22_formatter_hash_notes_2026-02-16.md`
   - `docs/operations/week23/phase55_w23_typed_ports_notes_2026-02-16.md`
   - `docs/operations/week24/phase55_w24_roundtrip_guarantee_notes_2026-02-16.md`

## Acceptance gates

- TOML GraphSpec files compile through existing graph compile path.
- `fmt graphspec` is deterministic and idempotent.
- Stable graph hash is invariant across equivalent JSON/TOML inputs.
- Invalid PIC port-domain connections are blocked by UI and backend checks.
- Full tests, drift checks, release gate, CI checks, and harness pass.
