# Phase 0 Maintainability Freeze (2026-03-06)

This runbook establishes the pre-refactor guardrails for the maintainability
hardening program.

## Goals

1. Freeze further growth in the two highest-risk monolith files:
   - `photonstrust/api/server.py`
   - `web/src/App.jsx`
2. Capture a line-budget policy for adjacent modules so the refactor does not
   simply move complexity into new god files.
3. Define the characterization suites that must keep passing while the API and
   React shell are decomposed.
4. Resolve obvious governance drift so repo metadata matches the intended
   open-source and UI-testing posture.

## Freeze rules

Until Phase 1 and Phase 2 extraction work is complete:

1. Do not add new route families directly to `photonstrust/api/server.py`
   unless the change is a release blocker or incident fix.
2. Do not add new stateful workflow logic directly to `web/src/App.jsx`.
3. New extraction targets should land under:
   - `photonstrust/api/routers/`
   - `photonstrust/api/services/`
   - `web/src/hooks/`
   - `web/src/features/`
   - `web/src/state/` or `web/src/lib/` for pure helpers
4. Preserve API response shapes, request headers, localStorage keys, and UI test
   selectors during the decomposition.

## Budget policy

Policy file:

- `configs/maintainability/phase0_refactor_budgets.json`

Checker:

- `scripts/check_maintainability_budgets.py`

Current Phase 0 ceilings:

| Surface | Ceiling | Intent |
|---|---:|---|
| `photonstrust/api/server.py` | 4500 lines | Freeze monolith growth pending router extraction |
| `web/src/App.jsx` | 3600 lines | Freeze React shell growth pending hook extraction |
| `photonstrust/**/*.py` (excluding `photonstrust/api/server.py`) | 1400 lines | Prevent new package-level god modules |
| `web/src/features/**/*.jsx` | 1100 lines | Keep feature panels below the current largest panel |
| `web/src/state/*.js` | 300 lines | Keep browser-state helpers focused |
| `scripts/*.py` | 1250 lines | Prevent new operational monoliths |
| `tests/test_*.py` | 1300 lines | Keep large characterization tests reviewable |
| future `photonstrust/api/routers/**/*.py` | 900 lines | Target ceiling for extracted route families |
| future `photonstrust/api/services/**/*.py` | 900 lines | Target ceiling for extracted service modules |
| future `web/src/hooks/**/*.js[x]` | 450 lines | Target ceiling for extracted React hooks |

Run the policy checker locally:

```bash
python scripts/check_maintainability_budgets.py
```

Optional report artifact:

```bash
python scripts/check_maintainability_budgets.py \
  --output-json results/maintainability/phase0_budget_report.json
```

## Characterization suites

These are the minimum suites to preserve behavior while files are split.

API contract and auth baseline:

```bash
python -m pytest -q \
  tests/api/test_api_contract_v1.py \
  tests/api/test_api_auth_rbac.py \
  tests/api/test_api_server_optional.py
```

Bundle/evidence baseline:

```bash
python -m pytest -q \
  tests/test_evidence_bundle_manifest_schema.py \
  tests/test_evidence_bundle_publish_manifest_schema.py \
  tests/test_evidence_bundle_signature_schema.py \
  tests/test_evidence_bundle_signing_verify.py
```

Foundry and inverse-design API baseline:

```bash
python -m pytest -q \
  tests/api/test_api_phase57_pdk_manifest_and_foundry.py \
  tests/api/test_api_phase58_invdesign_wave3.py \
  tests/test_phase57_golden_chain_fixture.py \
  tests/test_phase58_w36_flagship_invdesign_fixture.py
```

Web baseline:

```bash
cd web
npm run build
npm run test:ui -- tests/ui.smoke.spec.js tests/ui.workspace.spec.js tests/ui.demo.spec.js tests/ui.a11y.spec.js
```

## Governance cleanup applied in Phase 0

1. Repository license text is aligned with the existing AGPL-3.0 metadata in
   `pyproject.toml` and `CITATION.cff`.
2. Playwright test docs in `web/tests/README.md` are aligned with the actual
   spec inventory.
3. The maintainability budget policy is executable and test-backed via
   `tests/scripts/test_check_maintainability_budgets_script.py`.
