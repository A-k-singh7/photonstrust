# Phase 60 W43 Operations Notes (RBAC AuthN/AuthZ Hardening)

Date: 2026-02-16

## Week focus

Introduce role and project-scope controls for governance endpoints while keeping
default local-dev behavior backward compatible.

## Refreshed risk table

| Risk ID | Risk | Owner | Likelihood | Impact | Mitigation | Gate trigger | Status |
|---|---|---|---|---|---|---|---|
| P60-R9 | Governance endpoints are callable without identity in hardened mode | TL | Medium | High | Header auth mode with explicit 401 checks | Missing-header tests fail | Mitigated |
| P60-R10 | Unauthorized role can approve runs | QA | Medium | High | `approver`/`admin` role gate on approvals write path | 403 role tests fail | Mitigated |
| P60-R11 | Cross-project data leakage through runs/artifacts | SIM | Low | High | Project-scope checks on runs, bundles, jobs, approvals | 403 scope tests fail | Mitigated |
| P60-R12 | Hardening breaks existing local workflows | TL | Low | Medium | `PHOTONTRUST_API_AUTH_MODE=off` default compatibility mode | Existing API tests fail | Mitigated |

## Owner map confirmation

Accountable/responsible mapping remained explicit with no unresolved role gaps.
