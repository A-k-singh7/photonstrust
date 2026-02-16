# Architecture Freeze Memo - Week 1 (2026-02-12)

Status: active freeze for M1 (`W1-W4`)  
Freeze ID: `AF-M1-2026-02-12`

## Purpose
This memo freezes module boundaries and contract surfaces for the first
milestone cycle so engineering can build without architecture churn.

## Frozen boundaries for M1
| Module | Responsibility (frozen) | Out of scope for M1 |
| --- | --- | --- |
| `photonstrust.config` | load config and expand scenario matrix | new config families or breaking shape changes |
| `photonstrust.physics` | emitter, memory, detector model outputs | new hardware model classes with incompatible output fields |
| `photonstrust.qkd` | point/sweep performance calculations | protocol-family expansion outside current QKD flow |
| `photonstrust.events` | event queue + basic topologies (link/chain/star) | mesh routing engine changes |
| `photonstrust.protocols` | Qiskit circuit builders (swap/purify/teleport) | protocol compiler redesign |
| `photonstrust.calibrate` | Bayesian fit helpers for emitter/detector/memory | backend replacement or non-Bayesian pipeline change |
| `photonstrust.optimize` | repeater spacing optimization output generation | multi-objective optimizer redesign |
| `photonstrust.report` | reliability card + HTML/PDF exporters | card schema major-version changes |
| `ui/` | run registry and comparison views | UI framework migration |

## Frozen public contracts for M1
- CLI entrypoint: `photonstrust.cli:main`
- Config contracts: `load_config(path)`, `build_scenarios(config)`
- Physics contracts:
  - `get_emitter_stats(source) -> dict`
  - `simulate_memory(memory_cfg, wait_time_ns) -> MemoryStats`
  - `simulate_detector(detector_cfg, arrival_times_ps) -> DetectionStats`
- Event contracts:
  - `EventKernel.schedule(event)`
  - `EventKernel.run(until_ns=None) -> list[Event]`
- Protocol circuit contracts:
  - `entanglement_swapping_circuit()`
  - `purification_circuit(method="DEJMPS")`
  - `teleportation_circuit()`
- Calibration contracts:
  - `fit_emitter_params(obs, priors=None, samples=2000)`
  - `fit_detector_params(obs, priors=None, samples=2000)`
  - `fit_memory_params(obs, priors=None, samples=2000)`
- Optimization contract: `run_optimization(config, output_dir) -> dict`
- Reporting contracts:
  - `build_reliability_card(...) -> dict`
  - `write_reliability_card(card, path)`
  - `write_html_report(card, path, plot_paths=None)`
  - `write_pdf_report(card, path)`

## Schema freeze for M1
Frozen schema/version artifacts:
- `schemas/photonstrust.config.demo1.schema.json`
- `schemas/photonstrust.reliability_card.v1.schema.json`

Rules for M1:
- additive fields only
- no required-field removals
- no CLI flag behavior breaks
- preserve fallback behavior for optional dependencies

## Change control during freeze
Any architecture-level change in M1 requires:
1. short ADR note under `docs/operations/week1/` (or follow-on week folder)
2. update to API contract table
3. explicit test impact plan
4. TL + QA + DOC sign-off

## Week 1 exit check (document state)
- No open architecture blockers identified on `2026-02-12`.
- Core modules have role-level owners in
  `docs/operations/week1/api_contract_table_2026-02-12.md`.

