# PhotonTrust 30-Day Product Execution Board (2026-02-18)

This board converts the current engineering platform into a product users can adopt without founder hand-holding.

## Outcome Targets (30 days)

- `time_to_first_value` (TTFV): reduce to `< 10 min` for new users on local setup.
- First-run success rate (golden path): reach `>= 80%`.
- Golden-path run reliability: `>= 95%` successful runs (no manual payload edits).
- Pilot readiness: 1 reproducible hosted demo + 2 design partner conversations with concrete feedback.

## Scope Lock (Do Not Expand)

- Primary product wedge: **QKD run build -> run -> decision -> compare -> evidence**.
- Keep PIC/extra protocol expansion out of this sprint unless blocking the wedge.

## Week 1: Onboarding and Golden Path

### Deliverables

- Guided `Run Builder` with presets and protocol-aware fields.
- One-click golden-path demo run.
- Decision summary after each run (not raw numbers only).
- UI telemetry events for run success/failure and TTFV.

### Repo touchpoints

- `ui/app.py`
- `ui/components.py`
- `ui/data.py`
- `results/ui_metrics/events.jsonl` (runtime output)

### Acceptance checks

- `streamlit run ui/app.py` shows `Run Builder`, `Run Registry`, `Dataset Entries`.
- Golden-path button creates a valid run and displays decision summary.
- `results/ui_metrics/events.jsonl` records `qkd_run_succeeded` and `qkd_run_failed`.

## Week 2: Product Reliability and Error UX

### Deliverables

- Normalize and categorize API error messages (input validation vs backend failure vs auth scope).
- Add user-facing recovery hints directly in UI for common errors.
- Add deterministic run profile export/import for repeatability.

### Repo touchpoints

- `ui/data.py`
- `ui/app.py`
- `tests/test_api_server_optional.py` (contract checks)

### Acceptance checks

- Common failure paths produce actionable UI guidance in one step.
- Run profile export/import reproduces equivalent graph payload.

## Week 3: Decision Workflow and Collaboration Surface

### Deliverables

- Run comparison panel with clear deltas (`key_rate`, `qber`, `safe_use`).
- “Promote run” UX for candidate baseline in a project context.
- Reliability card quick viewer with essential fields first.

### Repo touchpoints

- `ui/components.py`
- `ui/app.py`
- `photonstrust/api/server.py` (if promotion endpoint needed)

### Acceptance checks

- Users can compare 2 runs and decide in under 2 minutes.
- Decision path is explicit (baseline vs candidate, changed metrics visible).

## Week 4: Packaging and Pilot-Ready Shipping

### Deliverables

- Single-command local product start (`API + UI`) documented.
- “10-minute quickstart” doc with copy-paste commands.
- Demo script for pilot calls (3 realistic scenarios).

### Repo touchpoints

- `README.md`
- `docs/operations/product/`
- optional: `scripts/` helper for local boot

### Acceptance checks

- A new machine can run API + UI + one golden-path run without manual debugging.
- Pilot demo flow runs from clean repo in one session.

## KPI Instrumentation Plan

- Source file: `results/ui_metrics/events.jsonl`.
- Required events:
  - `qkd_run_succeeded`
  - `qkd_run_failed`
  - `session_started`
- Required fields:
  - `trigger` (`manual` | `golden_path`)
  - `run_id`
  - `protocol_name`
  - `distance_km`
  - `time_to_first_value_s`

## 30-Day Backlog (Prioritized)

1. `P0` Golden-path reliability fixes from telemetry failures.
2. `P0` Error UX (all top 5 failure modes with direct hints).
3. `P1` Profile export/import.
4. `P1` Run comparison UX hardening.
5. `P1` Quickstart documentation polish.
6. `P2` Pilot demo templates and canned datasets.

## Release Gate for End of 30 Days

- Product release candidate only if all pass:
  - TTFV median `< 10 min`.
  - Golden-path success `>= 80%`.
  - At least one pilot demo executed end-to-end without code edits.
