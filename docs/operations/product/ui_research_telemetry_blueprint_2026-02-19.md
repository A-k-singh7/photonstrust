# PhotonTrust UI Research and Telemetry Blueprint (2026-02-19)

This blueprint links UX evidence and telemetry evidence to the north-star targets in `docs/operations/ui_8_week_execution_board_2026-02-19.md`.

## 1) Evidence model

- Weekly evidence is mixed-method: moderated usability findings plus telemetry-derived funnel and reliability metrics.
- Research uses the same three personas throughout execution: `Research Engineer`, `Platform Lead`, `Investor/Partner`.
- Weeks 1-3 are directional, Weeks 4-6 are convergent, Weeks 7-8 are acceptance-focused.

## 2) Persona usability scripts

### 2.1 Research Engineer script

Scenario: build a graph, run it, compare alternatives, and export an evidence packet.

Tasks:

1. Build a baseline from template and configure core params.
2. Run and interpret decision status (`pass`, `caution`, `fail`).
3. Tune one parameter and run a candidate.
4. Compare baseline vs candidate and choose one.
5. Export packet for team review.

Success criteria:

- No moderator intervention on primary path.
- Decision made in under 5 minutes after first successful run.
- Export packet contains provenance and assumptions.

### 2.2 Platform Lead script

Scenario: validate trust posture, inspect blockers, and approve or reject.

Tasks:

1. Open trust/provenance view for latest run.
2. Identify blockers from readiness checklist.
3. Review failure reason and suggested recovery path.
4. Execute approve or reject action with rationale.

Success criteria:

- User finds trust blockers in under 2 minutes.
- Approval decision aligns with displayed recommendation category.

### 2.3 Investor or Partner script

Scenario: consume product narrative and complete a 7-minute demo flow.

Tasks:

1. Navigate landing narrative and summarize value in one sentence.
2. Review benchmark/proof screens.
3. Confirm trust and decision evidence are visible.
4. Complete demo packet export.

Success criteria:

- Demo path completes with no code edits.
- User can explain product differentiation clearly.

## 3) Weekly study plan

| Week | Method | Sample size | Primary signal |
| --- | --- | --- | --- |
| Week 1 | Moderated comprehension sessions | 5 users | Value clarity in first 60 seconds |
| Week 2 | First-time guided flow usability | 6 users | Time to first credible result |
| Week 3 | Build/edit speed benchmark | 6 users | Task success and latency perception |
| Week 4 | Reviewer decision trial | 6 users | Run-to-decision speed |
| Week 5 | Trust and audit walkthrough | 6 users | Provenance and blocker findability |
| Week 6 | Multi-role simulation | 9 users (3 per role) | Team workflow integrity |
| Week 7 | Timed demo rehearsals | 10 runs | Demo completion reliability |
| Week 8 | Acceptance validation and keyboard audit | 6 users | RC readiness and accessibility |

## 4) Telemetry event contract

Required events to emit:

- `ui_session_started`
- `ui_guided_flow_started`
- `ui_guided_flow_completed`
- `ui_run_started`
- `ui_run_succeeded`
- `ui_run_failed`
- `ui_error_recovered`
- `ui_compare_completed`
- `ui_packet_exported`
- `ui_demo_mode_completed`

Required fields on each event:

- `timestamp_utc`
- `session_id`
- `user_mode` (`builder|reviewer|exec`)
- `profile` (`qkd_link|pic_circuit|orbit`)
- `run_id` (if available)
- `duration_ms` (if applicable)
- `outcome` (`success|failure|abandoned`)

Artifact path:

- `results/ui_metrics/events.jsonl`

## 5) North-star formulas

Use these formulas in Friday scorecards.

- `time_to_first_credible_result_min`: median minutes from first `ui_guided_flow_started` to first successful `ui_run_succeeded` in a session.
- `guided_flow_task_success_rate`: `count(ui_guided_flow_completed where outcome=success) / count(ui_guided_flow_started)`.
- `run_to_decision_time_min`: median minutes from `ui_run_succeeded` to first decision action (`ui_compare_completed` or `ui_packet_exported`) for same run/session.
- `critical_ui_error_recovery_rate`: `count(ui_error_recovered) / count(ui_run_failed)` for critical-flow sessions.
- `investor_demo_completion_rate`: `count(ui_demo_mode_completed where outcome=success and user_mode=exec) / count(ui_session_started where user_mode=exec)`.
- `a11y_keyboard_coverage`: `(critical steps fully keyboard-operable / total critical steps) * 100` from weekly audit checklist.

## 6) Data quality checks

Daily automated checks:

- Required-field completeness >= 98%.
- `timestamp_utc` parse success = 100%.
- No duplicate `session_id` plus timestamp plus event tuple collisions beyond 0.5%.
- Valid enum values for `user_mode`, `profile`, and `outcome`.
- `duration_ms >= 0` when present.

Weekly manual checks:

- Funnel sanity by persona and profile.
- Outlier review for long durations and abandoned sessions.
- Evidence trace from scorecard metric back to raw JSONL rows.

## 7) Friday scorecard workflow

1. Extract and validate weekly telemetry before 10:00 local.
2. Compute KPI metrics using formulas above.
3. Combine telemetry with that week usability findings.
4. Publish decision packet with top failures and next-week corrective actions.
5. Record `GO`, `GO-WITH-CONDITIONS`, or `NO-GO` and update board priorities.
