# PIC Foundry Readiness 9.5 Checklist

## Metadata
- Date: 2026-03-03
- Audience: PIC design, verification, product, quality, and release teams
- Scope: from pre-tapeout verification to foundry-grade release evidence
- Goal: provide a repeatable, auditable path to a practical 9.5/10 readiness score

## 1) What 9.5/10 Means (and What It Does Not Mean)
- 9.5/10 does not mean "perfect" or "100% physically correct forever".
- 9.5/10 means: the platform has hard gates, strong evidence, and low residual risk for production decisions.
- For this checklist, 9.5/10 requires:
  - all mandatory gate classes passing,
  - no unresolved critical findings,
  - foundry-sealed non-mock signoff evidence,
  - silicon correlation closure within declared tolerance bands,
  - deterministic reproducibility and traceable release packet evidence.

## 2) Scoring Model

Use weighted scoring plus hard-stop rules.

### 2.1 Weighted score
- Gate A: 35% (foundry signoff + policy)
- Gate B: 25% (model-to-silicon correlation)
- Gate C: 15% (process robustness and statistical closure)
- Gate D: 15% (security, provenance, and artifact integrity)
- Gate E: 10% (operational maturity and KPI stability)

### 2.2 Hard-stop rules
- Any A-critical item fail => release decision is HOLD.
- Any unresolved security/provenance fail in Gate D => HOLD.
- Any unwaived foundry fail in DRC/LVS/PEX => HOLD.
- Missing sealed evidence artifact for required stage => HOLD.

### 2.3 Readiness grade mapping
- 9.5/10 target: weighted score >= 95 and all hard-stop rules clear.
- 9.0-9.4: strong but missing one major closure item.
- <9.0: not foundry-grade.

## 3) Gate A: Foundry Signoff and Policy (Mandatory)

These are release-blocking by design.

| ID | Requirement | Pass Criteria | Evidence | Status |
|---|---|---|---|---|
| A1 | Required tapeout inputs exist | `inputs/graph.json`, `inputs/ports.json`, `inputs/routes.json`, `inputs/layout.gds` present | `scripts/check_pic_tapeout_gate.py` report | [ ] |
| A2 | Foundry DRC sealed summary valid | Schema-valid DRC summary, coherent `failed_check_ids`, mandatory DRC rules present | `foundry_drc_sealed_summary.json` + schema check | [ ] |
| A3 | Foundry LVS sealed summary valid | Schema-valid, status/check-count consistency, deterministic IDs | `foundry_lvs_sealed_summary.json` + schema check | [ ] |
| A4 | Foundry PEX sealed summary valid | Schema-valid, status/check-count consistency, deterministic IDs | `foundry_pex_sealed_summary.json` + schema check | [ ] |
| A5 | Foundry approval sealed summary valid | `GO/HOLD` and status consistent with source stage statuses and run IDs | `foundry_approval_sealed_summary.json` + cross-link check | [ ] |
| A6 | Non-mock backend policy enforced | `execution_backend != mock` for required foundry summaries | `--require-non-mock-backend` gate output | [ ] |
| A7 | Waiver policy strictness | only active approved waivers, no expired/invalid waivers used | waiver validation report + gate report | [ ] |
| A8 | Zero unwaived failures | no unresolved fail IDs after waiver resolution | tapeout gate report `all_passed=true` | [ ] |

### Gate A implementation anchors
- Gate script: `scripts/check_pic_tapeout_gate.py`
- Sealed runners:
  - `photonstrust/layout/pic/foundry_drc_sealed.py`
  - `photonstrust/layout/pic/foundry_lvs_sealed.py`
  - `photonstrust/layout/pic/foundry_pex_sealed.py`
- Schemas:
  - `schemas/photonstrust.pic_foundry_drc_sealed_summary.v0.schema.json`
  - `schemas/photonstrust.pic_foundry_lvs_sealed_summary.v0.schema.json`
  - `schemas/photonstrust.pic_foundry_pex_sealed_summary.v0.schema.json`
  - `schemas/photonstrust.pic_foundry_approval_sealed_summary.v0.schema.json`

## 4) Gate B: Model-to-Silicon Correlation (Mandatory)

| ID | Requirement | Pass Criteria | Evidence | Status |
|---|---|---|---|---|
| B1 | Insertion loss correlation | MAE and P95 within declared band (example: MAE <= 0.30 dB, P95 <= 0.60 dB) | correlation report with lot split | [ ] |
| B2 | Resonance alignment correlation | MAE and P95 within declared band (example: MAE <= 10 pm, P95 <= 25 pm) | resonance correlation report | [ ] |
| B3 | Crosstalk correlation | MAE and P95 within declared band (example: MAE <= 3 dB, P95 <= 6 dB) | crosstalk correlation report | [ ] |
| B4 | Delay/RC correlation | trend and absolute tolerance closure by corner and temp band | PEX-vs-measurement report | [ ] |
| B5 | Drift stability | no statistically significant degradation vs prior accepted baseline | drift dashboard or statistical test report | [ ] |

### Notes for Gate B
- Tolerance bands must be set before evaluation and versioned in the release packet.
- Correlation must cover representative process corners and at least one stress condition.
- If a metric passes only via waiver, waiver must include risk impact and expiry.

## 5) Gate C: Process Robustness and Statistical Closure

| ID | Requirement | Pass Criteria | Evidence | Status |
|---|---|---|---|---|
| C1 | Monte Carlo yield closure | declared yield threshold met with confidence interval | corner/yield report | [ ] |
| C2 | Multi-corner closure | pass across nominal + process + temperature corners | corner matrix summary | [ ] |
| C3 | Route-level DRC robustness | no fragile pass behavior under small geometry perturbations | perturbation robustness report | [ ] |
| C4 | Netlist/layout consistency robustness | LVS pass under deterministic regeneration and replay | replay report | [ ] |
| C5 | Repeatability | repeated runs on identical inputs give identical decisions | deterministic replay logs | [ ] |

## 6) Gate D: Security, Provenance, and Artifact Integrity

| ID | Requirement | Pass Criteria | Evidence | Status |
|---|---|---|---|---|
| D1 | No deck leakage in summaries | no sensitive keys/paths/content in sealed outputs | redaction checks + tests | [ ] |
| D2 | Artifact schema integrity | all sealed artifacts schema-valid | validation logs | [ ] |
| D3 | Signature integrity | release packet signature verifies | signature verify output | [ ] |
| D4 | Hash/provenance integrity | digest chain and source run IDs consistent | packet verify output | [ ] |
| D5 | Repro lineage integrity | lineage and reproducibility checks pass | replay scripts output | [ ] |

## 7) Gate E: Operational Maturity and KPI Stability

| ID | Requirement | Pass Criteria | Evidence | Status |
|---|---|---|---|---|
| E1 | CI stability | target pass-rate over rolling window met | CI dashboard export | [ ] |
| E2 | Time-to-evidence SLA | gate packet generated within target SLA | release ops metric | [ ] |
| E3 | Failure triage quality | mean time to root cause under target | issue analytics | [ ] |
| E4 | Claim governance | each external claim mapped to evidence ID | claim-evidence matrix | [ ] |
| E5 | Change control | no unsigned/manual bypass of mandatory gates | audit log | [ ] |

## 8) Command Runbook (Audit Execution)

### 8.1 Fast local baseline (pre-foundry)
```bash
py -m pytest -q tests/test_pic*.py tests/test_pdk*.py tests/test_foundry*.py
py scripts/materialize_local_tapeout_run.py --run-dir results/pic_readiness/run --report-path results/pic_readiness/materialize_report.json --allow-ci
py scripts/run_foundry_smoke.py --use-local-backend --run-dir results/pic_readiness/run --allow-ci --output-json results/pic_readiness/foundry_smoke_report.json
py scripts/check_pic_tapeout_gate.py --run-dir results/pic_readiness/run --report-path results/pic_readiness/pic_tapeout_gate_report.json
```

### 8.2 Foundry-grade gate execution (release candidate)
```bash
py scripts/check_pic_tapeout_gate.py \
  --run-dir <tapeout_run_dir> \
  --require-foundry-signoff \
  --require-non-mock-backend \
  --report-path results/pic_readiness/pic_tapeout_gate_foundry_report.json
```

### 8.3 Release evidence integrity
```bash
py scripts/release/verify_release_gate_packet.py
py scripts/release/verify_release_gate_packet_signature.py
```

## 9) Evidence Inventory for Review Pack

Minimum evidence package for 9.5 review:
- Tapeout gate report:
  - `results/.../pic_tapeout_gate_report.json`
- Foundry stage summaries:
  - `foundry_drc_sealed_summary.json`
  - `foundry_lvs_sealed_summary.json`
  - `foundry_pex_sealed_summary.json`
  - `foundry_approval_sealed_summary.json`
- Correlation packet:
  - insertion loss, resonance, crosstalk, RC correlation reports
- Statistical closure packet:
  - corner matrix, yield distributions, repeatability logs
- Security/provenance packet:
  - release packet json + signature json + verify outputs

## 10) Waiver Governance Rules

- Waivers are exceptions, not a normal pass path.
- Every waiver must include:
  - rule ID,
  - scope/entity reference,
  - reviewer,
  - justification,
  - expiry date,
  - residual risk note.
- Expired or invalid waivers are treated as fail.
- Critical safety/reliability waivers require explicit leadership signoff.

## 11) Review Cadence and Exit Criteria

### Weekly readiness review
- Review gate deltas and trend movement.
- Confirm no new unresolved critical findings.
- Track each open gap with owner and due date.

### Exit criteria for 9.5 declaration
- All A-critical checks pass with non-mock foundry evidence.
- Correlation bands met for all B metrics on required scope.
- C, D, E gate minima satisfied and no hard-stop violations.
- Final review board signs off with evidence packet hash and date.

## 12) Current Branch Snapshot (as of 2026-03-03)

This is a non-binding snapshot to seed the checklist, not the final foundry declaration.

- PIC/PDK/foundry test battery: `222 passed`
- Local smoke run status: pass
- Local tapeout gate status: pass
- Current consolidated preflight scorecard: `82.5` (`<9.0` band) with no hard-stop HOLD.
- Remaining gap to claim 9.5: full silicon-correlation closure packet (Gate B) plus non-synthetic rolling telemetry closure for Gate E.

## 13) Audit Worksheet Template

Use this table per release candidate.

| Release Candidate | Gate ID | Status (pass/fail/waived) | Evidence Path | Reviewer | Date | Notes |
|---|---|---|---|---|---|---|
| RC-<id> | A1 |  |  |  |  |  |
| RC-<id> | A2 |  |  |  |  |  |
| RC-<id> | A3 |  |  |  |  |  |
| RC-<id> | A4 |  |  |  |  |  |
| RC-<id> | A5 |  |  |  |  |  |
| RC-<id> | A6 |  |  |  |  |  |
| RC-<id> | A7 |  |  |  |  |  |
| RC-<id> | A8 |  |  |  |  |  |
| RC-<id> | B1 |  |  |  |  |  |
| RC-<id> | B2 |  |  |  |  |  |
| RC-<id> | B3 |  |  |  |  |  |
| RC-<id> | B4 |  |  |  |  |  |
| RC-<id> | B5 |  |  |  |  |  |
| RC-<id> | C1 |  |  |  |  |  |
| RC-<id> | C2 |  |  |  |  |  |
| RC-<id> | C3 |  |  |  |  |  |
| RC-<id> | C4 |  |  |  |  |  |
| RC-<id> | C5 |  |  |  |  |  |
| RC-<id> | D1 |  |  |  |  |  |
| RC-<id> | D2 |  |  |  |  |  |
| RC-<id> | D3 |  |  |  |  |  |
| RC-<id> | D4 |  |  |  |  |  |
| RC-<id> | D5 |  |  |  |  |  |
| RC-<id> | E1 |  |  |  |  |  |
| RC-<id> | E2 |  |  |  |  |  |
| RC-<id> | E3 |  |  |  |  |  |
| RC-<id> | E4 |  |  |  |  |  |
| RC-<id> | E5 |  |  |  |  |  |

## 14) Signoff Statement Template

"This release candidate is declared PIC foundry readiness score <score>/10 under this checklist version. All hard-stop rules are clear, and attached evidence artifacts are complete and signature-verified as of <date>."
