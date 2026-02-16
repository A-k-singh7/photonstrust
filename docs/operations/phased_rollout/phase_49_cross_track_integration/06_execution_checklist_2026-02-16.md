# Execution Checklist (Multi-Agent Build Follow-Up)

**Date:** 2026-02-16  
**Project:** PhotonTrust  
**Scope:** Convert current build outputs into a tested, release-ready, pilot-ready baseline.

**Closeout snapshot (2026-02-16):** Technical integration gates are complete; see
`10_phase49_closeout_report_2026-02-16.md` for final pass matrix and artifact references.

---

## 0) Roles (fill names)

- **Founder/PM (FND):** __________________
- **Physics Lead (PHY):** __________________
- **Platform Lead (PLT):** __________________
- **QA/Validation (QAV):** __________________
- **Security/Compliance (SEC):** __________________
- **GTM/Pilot Ops (GTM):** __________________

---

## 1) Hard Gates (must pass before pilot release)

- [ ] Full test suite passes in clean venv (`pytest -q`)  
  **Owner:** QAV  
  **Success criteria:** 0 failing tests on clean install

- [ ] Validation harness executes and outputs artifacts  
  **Owner:** QAV  
  **Success criteria:** `summary.json` status = pass for baseline set

- [ ] Reliability card v1.1 trust metadata fields present and schema-valid  
  **Owner:** PHY + QAV  
  **Success criteria:** schema + API summary tests green

- [ ] CORS/security defaults confirmed and documented  
  **Owner:** SEC + PLT  
  **Success criteria:** no wildcard default CORS in runtime config

- [ ] Final license selected and applied (replace placeholder)  
  **Owner:** FND + SEC  
  **Success criteria:** approved LICENSE + pyproject metadata aligned

---

## 2) Day-by-Day Plan (Next 14 Days)

## Day 1 — Environment Rehydration + Baseline
- [ ] Create clean venv and install dev deps
- [ ] Run `pytest -q`
- [ ] Run `python scripts/run_validation_harness.py --output-root results/validation`
- [ ] Log failing tests by module and severity

**Owner:** PLT + QAV  
**Success criteria:** reproducible local run command set + failure report committed to docs

---

## Day 2 — Fast Failure Burn-Down (P0 only)
- [ ] Fix all failing tests related to new BB84/finite-key, channel engine, PIC verification, reliability schema
- [ ] Re-run targeted test subsets per changed module
- [ ] Re-run full suite

**Owner:** PLT + PHY + QAV  
**Success criteria:** P0 failures = 0

---

## Day 3 — Protocol + Reliability Consistency Pass
- [ ] Verify BB84 decoy outputs include protocol metadata fields
- [ ] Verify finite-key epsilon fields are populated and coherent
- [ ] Validate reliability card + API summary structure end-to-end on sample runs

**Owner:** PHY + PLT  
**Success criteria:** one generated run artifact with complete trust metadata and schema pass

---

## Day 4 — Channel + UQ Confidence Pass
- [ ] Validate fiber/free-space/satellite decomposition invariants
- [ ] Validate uncertainty intervals for channel + key rate
- [ ] Confirm no regression in existing uncertainty consumers/reports

**Owner:** PHY + QAV  
**Success criteria:** channel invariants + interval tests green; sample report reviewed

---

## Day 5 — PIC Verification Gate Integration
- [ ] Integrate new PIC checks into verification flow used by demos/pipelines
- [ ] Add one consolidated PIC signoff report example (pass + fail)
- [ ] Validate violation formatting is actionable

**Owner:** PLT + PHY  
**Success criteria:** one reproducible PIC verification artifact with all 4 checks

---

## Day 6 — Security + Legal Baseline Closure
- [ ] Replace LICENSE placeholder with final approved license
- [ ] Add/update SECURITY disclosure contact/process details
- [ ] Verify CORS env override behavior in dev/staging config

**Owner:** SEC + FND + PLT  
**Success criteria:** legal/security baseline marked complete in release checklist

---

## Day 7 — CI Gate Wiring
- [ ] Add/confirm CI steps for:
  - compileall
  - pytest
  - validation harness smoke run
  - schema checks
- [ ] Add fail-fast policy for broken trust-metadata outputs

**Owner:** PLT + QAV  
**Success criteria:** CI pipeline passes on clean branch

---

## Day 8 — Integration Regression Sweep
- [ ] Execute full regression on canonical scenarios
- [ ] Compare against prior baseline artifacts
- [ ] Triage drift deltas (> threshold) with root-cause notes

**Owner:** QAV + PHY  
**Success criteria:** approved regression summary with pass/fail decision

---

## Day 9 — Demo Hardening (Customer-Facing)
- [ ] Build 10-minute deterministic demo script (CLI/API path)
- [ ] Include reliability card + uncertainty + evidence outputs
- [ ] Dry-run on fresh machine/environment

**Owner:** FND + PLT + GTM  
**Success criteria:** one-command demo reproducible by non-author

---

## Day 10 — Packaging + Install Reliability
- [ ] Validate install paths (local, virtualenv, container path if used)
- [ ] Write/update quickstart and known-issues section
- [ ] Check dependency pinning/lock strategy

**Owner:** PLT + QAV  
**Success criteria:** documented install success from scratch in <30 min

---

## Day 11 — Benchmark Credibility Pack v1
- [ ] Bundle canonical benchmark outputs + validation summary
- [ ] Attach run manifest + artifact references
- [ ] Add brief “claim boundaries” section for sales/use

**Owner:** PHY + QAV + FND  
**Success criteria:** publishable internal benchmark pack in docs/results

---

## Day 12 — Pilot Ops Readiness
- [ ] Finalize pilot intake checklist
- [ ] Finalize success criteria template (time-to-decision, reproducibility, report acceptance)
- [ ] Create troubleshooting/support runbook v1

**Owner:** GTM + FND + PLT  
**Success criteria:** pilot packet ready to send

---

## Day 13 — Full Dress Rehearsal
- [ ] Run end-to-end from sample input to signed/validated output artifact
- [ ] Simulate one failure scenario and resolution path
- [ ] Capture timing, blockers, and fixes

**Owner:** All leads  
**Success criteria:** end-to-end run under target time with no critical blocker

---

## Day 14 — Go/No-Go Review
- [ ] Review hard gates
- [ ] Decide: Pilot release / Hold
- [ ] If hold: assign owners/dates for unresolved blockers
- [ ] If go: tag release candidate + publish internal release notes

**Owner:** FND  
**Success criteria:** signed decision memo with next-step commitments

---

## 3) Daily Metrics Snapshot (fill each day)

- Test pass rate: ________
- Validation harness status: ________
- Open critical bugs: ________
- Reliability card schema/API parity: ________
- Security/legal blockers: ________
- Demo readiness score (1–10): ________

---

## 4) Command Block (copy/paste)

```bash
cd "/mnt/c/Users/aksin/Desktop/Qutip+qskit projects/photonstrust"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
pytest -q
python scripts/run_validation_harness.py --output-root results/validation
```

**Baseline fixture refresh + validation (demo + phase41, one command):**

```bash
cd "/mnt/c/Users/aksin/Desktop/Qutip+qskit projects/photonstrust" && ./.venv/bin/python scripts/regenerate_baseline_fixtures.py
```

---

## 5) Release Decision Rule

**Release only if all hard gates are checked and no open critical blocker remains.**
