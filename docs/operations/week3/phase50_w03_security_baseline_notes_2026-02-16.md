# Phase 50 W03 Operations Notes (Security Baseline)

Date: 2026-02-16

## Week focus

Establish minimum security posture for the 365-day execution cycle by enabling
dependency governance automation, CI vulnerability scanning, and a documented
coordinated disclosure path.

## Refreshed risk table

| Risk ID | Risk | Owner | Likelihood | Impact | Mitigation | Gate trigger | Status |
|---|---|---|---|---|---|---|---|
| P50-R2 | Security scans run but fail to gate runtime dependency risk | TL | Medium | High | Added blocking `pip-audit` CI lane in `security-baseline` workflow | `pip-audit` job fails on push/PR | Mitigated |
| P50-R7 | Dependency drift accumulates due manual update cadence | QA | Medium | Medium | Added weekly Dependabot updates for `pip`, `npm` (`/web`), and GitHub Actions | Dependabot lane missing or disabled | Mitigated |
| P50-R8 | Frontend install behavior drifts from lockfile state | SIM | Medium | Medium | Enforced `npm ci` in security workflow and developer docs | `npm ci` failure in CI or lockfile missing | Mitigated |
| P50-R9 | Vulnerability reports arrive without clear handling expectations | DOC | Medium | High | Expanded `SECURITY.md` with response targets and disclosure protocol | No acknowledgement inside response target window | Mitigated |
| P50-R10 | Node runtime CVEs remain unseen between dependency upgrades | QA | Low | Medium | Added non-blocking `npm audit --omit=dev` baseline signal in security workflow | High/critical npm runtime finding appears | Open |

## Owner map confirmation

Security baseline streams (dependency governance, CI scanning, disclosure
process) remain explicitly owned with no accountable/responsible gaps.
