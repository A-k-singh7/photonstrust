# Phase 61: Adoption and Pilot Conversion (Implementation Plan)

Date: 2026-02-16

## Scope

Implement Phase 61 W45-W48 with adoption-facing operational hardening:
packaging/citation metadata completeness, benchmark index reproducibility checks,
pilot-cycle governance templates, and conversion handoff package validation.

## Owner map lock (release-critical workstreams)

Owner roles follow `docs/research/deep_dive/13_raci_matrix.md`.

| Workstream | Accountable | Responsible | Consulted | Backup |
|---|---|---|---|---|
| Packaging metadata + citation + issue intake templates | TL | DOC | QA | SIM |
| Open benchmark index refresh and drift checks | QA | SIM | TL | DOC |
| External pilot cycle packet and completeness checks | TL | DOC | QA | SIM |
| Pilot-to-paid conversion memo and support handoff assets | TL | DOC | QA | SIM |

## Implementation tasks

1. Add packaging readiness artifacts:
   - `CITATION.cff`
   - `pyproject.toml`
   - `.github/ISSUE_TEMPLATE/bug_report.yml`
   - `.github/ISSUE_TEMPLATE/feature_request.yml`
   - `scripts/measure_quickstart_timing.py`
   - `tests/test_phase61_packaging_readiness.py`
2. Add open benchmark index refresh/check path:
   - `photonstrust/benchmarks/open_index.py`
   - `scripts/refresh_open_benchmark_index.py`
   - `scripts/validation/check_open_benchmarks.py`
   - `datasets/benchmarks/open/index.json`
   - `tests/test_open_benchmark_index_refresh.py`
3. Add pilot cycle and conversion packet artifacts:
   - `docs/operations/pilot_readiness_packet/README.md`
   - `docs/operations/pilot_readiness_packet/05_external_pilot_cycle_outcome_template.md`
   - `docs/operations/pilot_readiness_packet/06_external_pilot_gate_log_template.md`
   - `docs/operations/pilot_readiness_packet/07_pilot_to_paid_conversion_memo_template.md`
   - `docs/operations/pilot_readiness_packet/08_support_runbook_handoff_checklist.md`
   - `docs/operations/pilot_readiness_packet/pilot_cycle_01_outcome_example.md`
   - `docs/operations/pilot_readiness_packet/pilot_cycle_02_outcome_example.md`
   - `scripts/check_pilot_packet.py`
   - `tests/test_pilot_packet_completeness.py`

## Acceptance gates

- Citation and package metadata are complete and parse cleanly in tests.
- Quickstart timing script executes and emits JSON payload with elapsed timing.
- Open benchmark index can be deterministically rebuilt and drift checks pass.
- Pilot packet checker confirms all required W47/W48 artifacts are present.
