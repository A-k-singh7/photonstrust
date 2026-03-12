# M10 Day-120 Execution Plan (Days 91-120)

Date: 2026-03-02
Window: Day 91 to Day 120
Parent: `M7_30_day_execution_master_plan.md`
Goal: Ship typed API v1 contracts, enforce security boundaries, and deliver operator/customer-facing visibility with evidence-grade trust.

## 1) Day-120 Mission

By Day 120, platform interfaces must be:
1. stable and typed (`/v1` contract layer),
2. secure by default (authn/authz and scoped access),
3. operationally observable through trusted dashboards,
4. release-governed by fail-closed API and evidence gates.

## 2) Non-Negotiable Rules (Inherited + Enforced)

1. No untyped production API payloads for new v1 endpoints.
2. No permissive access to run/job/artifact resources.
3. No hidden error paths; all errors use normalized response shape.
4. No customer-facing evidence view without verification status.
5. Unknown authz state => deny.

## 3) Deliverables Due by Day 120

1. API `/v1` typed contracts for core workflows.
2. Unified error model with request-id correlation.
3. Authz enforcement across sensitive simulation/export endpoints.
4. Tenant/project scoped data-access policy baseline.
5. Plotly-backed mission ops dashboards in Streamlit.
6. Customer evidence-view mode with immutable bundle verification indicators.
7. CI contract and security tests for v0/v1 compatibility and policy enforcement.

## 4) Scope and Boundaries

In scope:
1. API contract typing and compatibility framework.
2. access-control hardening for platform trust boundaries.
3. internal and customer-facing observability surfaces.

Out of scope for Day 120:
1. full commercial IAM federation rollout,
2. full billing/subscription product concerns,
3. advanced workflow orchestration features beyond Day-90 scope.

## 5) Workstreams

## WS1: API v1 Typed Model Foundation

Objective:
Make API contracts explicit and safe.

Tasks:
1. Add Pydantic v1/v2-compatible model layer for `/v1`.
2. Implement strict request/response validation.
3. Provide compatibility adapters to preserve `/v0` behavior.

Target touchpoints:
1. `photonstrust/api/models/v1/` (new)
2. `photonstrust/api/server.py`
3. `tests/test_api_contract_v1.py` (new)

Acceptance:
1. Core endpoints have typed request/response models.
2. Backward compatibility tests pass for key `/v0` flows.

## WS2: Error Model and Observability Contract

Objective:
Normalize failure behavior and diagnostics.

Tasks:
1. Define standard error envelope (`code`, `detail`, `request_id`, `retryable`).
2. Add request-id propagation in API responses/logs.
3. Add structured event fields for trust-critical API operations.

Target touchpoints:
1. `photonstrust/api/server.py`
2. `photonstrust/api/ui_metrics.py`
3. `tests/test_api_server_optional.py`

Acceptance:
1. Error schema is consistent across v1 endpoints.
2. Request correlation works end-to-end in tests.

## WS3: Security and Access Control Hardening

Objective:
Prevent unauthorized compute and data exposure.

Tasks:
1. Apply authz checks to run/sim/export/publish endpoints.
2. Enforce project/tenant scope checks in run/job/artifact reads.
3. Add explicit deny-by-default path for unknown roles.

Target touchpoints:
1. `photonstrust/api/server.py`
2. `photonstrust/api/runs.py`
3. `photonstrust/api/jobs.py`
4. `photonstrust/api/projects.py`
5. `tests/test_api_auth_rbac.py`

Acceptance:
1. Unauthorized and cross-scope access denied in tests.
2. Security gate fails on missing authz enforcement.

## WS4: Operator Dashboard Upgrade (Streamlit + Plotly)

Objective:
Provide real-time operational awareness tied to evidence-grade data.

Tasks:
1. Add Plotly views for run throughput, queue latency, failure taxonomy, and risk distributions.
2. Surface verification states for key artifacts.
3. Add role-aware internal views.

Target touchpoints:
1. `ui/app.py`
2. `ui/data.py`
3. `tests/test_ui_data_helpers.py`

Acceptance:
1. Dashboard charts are fed by real API data paths.
2. Health/risk visuals match run registry and evidence states.

## WS5: Customer Evidence View Mode

Objective:
Expose trust outputs without internal debug leakage.

Tasks:
1. Add read-only evidence-centric UI mode.
2. Show signature/hash verification status and provenance timeline.
3. Restrict customer mode to approved fields and artifacts.

Target touchpoints:
1. `web/src/photontrust/api.js`
2. `web/src/App.jsx`
3. `photonstrust/api/server.py` evidence endpoints

Acceptance:
1. Customer mode only displays verified, policy-approved fields.
2. Missing verification state blocks “trusted” badge.

## WS6: CI Contract and Security Gates

Objective:
Make API and access policy regressions unmergeable.

Tasks:
1. Add dedicated v1 contract lane.
2. Add authz regression lane.
3. Add compatibility checks across v0/v1 for priority endpoints.

Target touchpoints:
1. `.github/workflows/ci.yml`
2. `.github/workflows/security-baseline.yml`
3. `tests/test_api_*`

Acceptance:
1. Any contract break or authz hole fails CI.
2. Required lanes trigger on API/schema/UI path changes.

## 6) Week-by-Week Execution (Day 91-120)

## Week 13 (Day 91-97): Contract Scaffolding

1. Build v1 model scaffolding and endpoint adapters.
2. Add error envelope helpers.
3. Add initial contract tests.

Exit:
1. First v1 endpoints pass validation and tests.

## Week 14 (Day 98-104): Security Hardening

1. Apply authz to sensitive endpoints.
2. Add scope checks for run/job/artifact retrieval.
3. Add deny-by-default tests.

Exit:
1. Authz regression suite passes.

## Week 15 (Day 105-111): Dashboard and Evidence Views

1. Add Plotly internal ops views.
2. Add customer evidence mode with verification status.
3. Add UI contract tests and API integration checks.

Exit:
1. Dashboards reflect real runtime/evidence state.

## Week 16 (Day 112-120): Hardening and Day-120 Rehearsal

1. Add CI required lanes for API/security.
2. Run full Day-120 rehearsal.
3. Publish Day-120 trust/readiness report.

Exit:
1. Day-120 acceptance gates pass.
2. Rehearsal packet is signed and auditable.

## 7) Day-120 Acceptance Gates

1. `contract_gate`:
   - v1 typed contract tests pass.
2. `security_gate`:
   - authz and scope tests pass.
3. `compat_gate`:
   - critical v0 behavior remains compatible.
4. `observability_gate`:
   - request-id and error envelope validated.
5. `evidence_view_gate`:
   - customer-facing trust state reflects real verification data.

Fail any gate => HOLD.

## 8) Metrics for Day-120 Review

1. API contract test pass rate = 100% for v1 lanes.
2. Unauthorized access success rate = 0%.
3. Security regression MTTR < 24h.
4. Dashboard data mismatch incidents = 0 in rehearsal period.
5. Evidence view verification completeness = 100%.

## 9) Risks and Mitigations (Day-120 Specific)

1. Contract churn breaks clients:
   - Mitigation: adapter-based transition and compatibility tests.
2. Incomplete auth coverage:
   - Mitigation: centralized dependency checks and endpoint coverage map.
3. UI trust misrepresentation:
   - Mitigation: derived trust state only from verified API fields.
4. Performance regressions from strict validation:
   - Mitigation: profile and optimize hot serialization paths.
5. Security policy drift:
   - Mitigation: required CI lanes and policy snapshot tests.

## 10) Artifacts Required at Day-120 Close

1. API v1 contract specification and changelog.
2. Security coverage matrix and authz test report.
3. Dashboard validation report with source-to-view traceability.
4. Customer evidence view policy note.
5. Day-120 release rehearsal report and signed evidence packet.

## 11) Immediate Start Sequence

1. Implement v1 model and error envelope foundation.
2. Enforce authz/scope checks on sensitive endpoints.
3. Add contract/security CI lanes.
4. Add Plotly mission dashboards.
5. Run Day-120 rehearsal and sign evidence.
