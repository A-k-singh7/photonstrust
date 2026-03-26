# API Contract Table with Owners - Week 1 (2026-02-12)

This table freezes owner accountability for public interfaces during M1
(`W1-W4`) and maps each contract to validation coverage.

## Role legend
- `TL`: Technical Lead
- `PHY`: Quantum Physics Engineer
- `SIM`: Simulation/Kernel Engineer
- `PROT`: Protocol/Qiskit Engineer
- `CAL`: Calibration/Inference Engineer
- `OPT`: Optimization Engineer
- `UX`: Product/UI Engineer
- `QA`: Quality/CI Engineer
- `DOC`: Documentation/Developer Experience

## Contract ownership table
| Area | Contract | Owner | Backup | Validation anchor |
| --- | --- | --- | --- | --- |
| CLI | `photonstrust.cli:main` | TL | QA | CLI integration paths via `pytest -q` |
| Config | `load_config(path)` | TL | SIM | config/default tests in runtime flows |
| Config | `build_scenarios(config)` | TL | QA | matrix and scenario execution paths |
| Physics | `get_emitter_stats(source)` | PHY | QA | emitter trend tests (`g2_0`) |
| Physics | `simulate_memory(memory_cfg, wait_time_ns)` | PHY | QA | `tests/test_physics_memory.py` |
| Physics | `simulate_detector(detector_cfg, arrival_times_ps)` | PHY | QA | `tests/test_detector_model.py` |
| QKD engine | `compute_point(scenario, distance_km)` | PHY | SIM | `tests/test_qkd_smoke.py` |
| QKD engine | `compute_sweep(scenario, include_uncertainty=True)` | PHY | CAL | QKD + uncertainty path tests |
| Events | `EventKernel.schedule(event)` | SIM | QA | `tests/test_event_kernel.py` |
| Events | `EventKernel.run(until_ns=None)` | SIM | QA | `tests/test_event_kernel.py` |
| Protocols | `entanglement_swapping_circuit()` | PROT | QA | circuit import/smoke checks |
| Protocols | `purification_circuit(method="DEJMPS")` | PROT | QA | circuit import/smoke checks |
| Protocols | `teleportation_circuit()` | PROT | QA | circuit import/smoke checks |
| Calibration | `fit_emitter_params(...)` | CAL | QA | calibration command output checks |
| Calibration | `fit_detector_params(...)` | CAL | QA | calibration command output checks |
| Calibration | `fit_memory_params(...)` | CAL | QA | calibration command output checks |
| Optimization | `run_optimization(config, output_dir)` | OPT | QA | optimization output checks |
| Reporting | `build_reliability_card(...)` | DOC | QA | schema validation and report tests |
| Reporting | `write_reliability_card(card, path)` | DOC | QA | `tests/test_schema_validation.py` |
| Reporting | `write_html_report(card, path, ...)` | DOC | UX | `tests/test_golden_report.py` |
| Reporting | `write_pdf_report(card, path)` | DOC | UX | PDF smoke in release workflow |
| Datasets | `generate_dataset(config_path, output_dir)` | QA | DOC | dataset schema and fixture checks |
| UI | `ui/app.py` run registry + compare views | UX | QA | UI smoke run before release |
| Schema | `photonstrust.reliability_card.v1.schema.json` | DOC | QA | `tests/test_schema_validation.py` |

## Ownership policy for M1
- Owner approves contract changes.
- Backup reviewer required for interface-impact PRs.
- QA can block merges when validation anchor fails.
- Any owner changes must update this file in the same PR.

