# M13 6-Week KPI Dashboard (Baseline vs After)

Date: 2026-03-02
Window: 2026-03-02 to 2026-04-12 (6 weeks)
Parent: `M6_market_readiness_integration_program.md`
Purpose: Quantify how much the platform helps physical photonics-chip programs and satellite-to-chip operations over the next 6 weeks.

## 1) Timeboxes and Decision Dates

1. Baseline capture week (Week 0): 2026-03-02 to 2026-03-08.
2. Improvement window (Weeks 1-5): 2026-03-09 to 2026-04-05.
3. Final measurement week (Week 6): 2026-04-06 to 2026-04-12.
4. Final readout date: 2026-04-13.

## 2) Dashboard Scope

This dashboard is the minimum scorecard needed to claim measurable value for chip-focused users:

1. Physics trust and parity.
2. Tapeout/signoff readiness.
3. Throughput and runtime gains.
4. Reproducibility and release governance.
5. Pilot readiness for external design partners.

## 3) KPI Catalog (12 Core KPIs)

Use `docs/work_items/kpi_6_week_metric_catalog.csv` as source of truth.

| KPI ID | Metric | Unit | Direction | Week-6 target |
|---|---|---|---|---|
| KPI-01 | Coverage floor (`pytest --cov`) | percent | higher is better | `>= 80` |
| KPI-02 | Flaky test rate | percent | lower is better | `<= 3` |
| KPI-03 | Release gate pass consistency | percent | higher is better | `>= 95` |
| KPI-04 | Median lead time for change | hours | lower is better | `< 24` |
| KPI-05 | Orbit parity pass rate (production vs validation lane) | percent | higher is better | `>= 99` |
| KPI-06 | Strict protocol parity lane pass rate (`qutip` + `qiskit`) | percent | higher is better | `>= 95` |
| KPI-07 | Uncertainty-budget breaches in GO candidates | count | lower is better | `0` |
| KPI-08 | PIC tapeout gate pass rate | percent | higher is better | `>= 95` |
| KPI-09 | Signed compliance envelope build time | hours | lower is better | `<= 4` |
| KPI-10 | Evidence/signature verification success | percent | higher is better | `100` |
| KPI-11 | P95 runtime for flagship satellite-chain scenario | seconds | lower is better | `>= 30%` faster vs Week-0 |
| KPI-12 | Sweep throughput (satellite scenarios/hour) | scenarios/hour | higher is better | `>= 25%` higher vs Week-0 |

## 4) How to Measure Each KPI (Repo-Aligned)

1. KPI-01:
   - Source: CI `pytest` coverage output.
   - Command: `py -3 scripts/ci_checks.py --pytest-args "-q --cov=photonstrust --cov-report=term --cov-fail-under=70"`.
2. KPI-02:
   - Source: repeated CI test runs.
   - Method: `flaky_rate = flaky_tests / total_tests`.
3. KPI-03:
   - Source: release gate report JSON.
   - Command: `py -3 scripts/release_gate_check.py --output results/release_gate/release_gate_report.json`.
4. KPI-04:
   - Source: PR metadata (`opened_at` to merge commit timestamp).
   - Method: median over merged PRs in week window.
5. KPI-05:
   - Source: orbit parity report artifacts from satellite workflow.
   - Method: passed_cases / total_cases.
6. KPI-06:
   - Source: strict lane reports.
   - Commands:
     - `py -3 scripts/run_qutip_parity_lane.py --strict --output-json results/qutip_parity/qutip_lane_report.json`
     - `py -3 scripts/run_qiskit_lane.py --strict --output-json results/qiskit_lane/qiskit_lane_report.json`
7. KPI-07:
   - Source: signoff/certificate payloads and GO/HOLD decisions.
   - Method: count GO candidates where uncertainty budget exceeds threshold.
8. KPI-08:
   - Source: tapeout gate report JSON.
   - Command: `py -3 scripts/check_pic_tapeout_gate.py --run-dir <tapeout_run_dir> --report-path results/pic_tapeout_gate/pic_tapeout_gate_report.json`.
9. KPI-09:
   - Source: start/end timestamps for release/tapeout/evidence bundle build.
   - Method: elapsed hours from start of release packaging to verified envelope.
10. KPI-10:
   - Source: signature verification reports.
   - Commands:
     - `py -3 scripts/verify_release_gate_packet.py`
     - `py -3 scripts/verify_release_gate_packet_signature.py`
11. KPI-11:
   - Source: timing report for flagship run.
   - Command: `py -3 scripts/measure_quickstart_timing.py --command "py -3 -m photonstrust.cli run configs/canonical/phase54_satellite_day_downlink_c_1550.yml --output results/kpi_runtime_weekX"`.
12. KPI-12:
   - Source: sweep summary JSON.
   - Command: `py -3 scripts/run_satellite_chain_sweep.py --backend local --output-root results/satellite_chain_sweep_weekX`.
   - Method: `throughput = run_count / elapsed_hours`.

## 5) Baseline vs After Computation

For each KPI:

1. Baseline value: metric from Week 0 (2026-03-02 to 2026-03-08).
2. After value: metric from Week 6 (2026-04-06 to 2026-04-12).
3. Delta:
   - Higher-is-better: `delta_pct = ((after - baseline) / baseline) * 100`.
   - Lower-is-better: `delta_pct = ((baseline - after) / baseline) * 100`.
4. Status:
   - Green: meets or exceeds Week-6 target.
   - Amber: within 10% of target.
   - Red: more than 10% away from target.

Use `docs/work_items/kpi_6_week_weekly_log_template.csv` to log all weekly values.

## 6) Weekly Operating Cadence

1. Monday:
   - Collect previous week values and evidence paths.
   - Update KPI log CSV and status colors.
2. Tuesday:
   - Root-cause analysis for all red metrics.
   - Assign corrective actions with owners and due dates.
3. Thursday:
   - Midweek rerun for risk metrics (`KPI-03`, `KPI-06`, `KPI-08`, `KPI-10`).
4. Friday:
   - GO/HOLD review packet with trend line and blocker list.

## 7) Scorecard Rule for Market-Readiness Claim

At end of Week 6 (2026-04-12), market-readiness claim is allowed only if:

1. All hard-gate KPIs are green: `KPI-03`, `KPI-05`, `KPI-08`, `KPI-10`.
2. At least 9 of 12 total KPIs are green.
3. No red KPI in security/compliance/tapeout domain.

If any hard gate fails, status is HOLD regardless of aggregate score.

## 8) Immediate Next Actions (This Week)

1. Populate Week-0 baseline values in both CSV files.
2. Add CI artifact retention for parity and tapeout gate reports.
3. Confirm owner role per KPI before 2026-03-06.
4. Run first Friday review on 2026-03-06 with real data, not estimates.
