# Day-0 Customer Kickoff Operator Runbook (Pilot)

Use this for the first live customer kickoff. Keep to timeline, run commands exactly, and treat acceptance gates as hard gates.

## Team (minimum 3 people)

- **Ops Lead (OL):** drives terminal + screen share
- **QA Witness (QA):** marks pass/fail gates
- **Customer Lead (CL):** confirms scope/success criteria + approves claim wording

---

## 0) Pre-call setup (T-30 to T-10)

```bash
cd "/mnt/c/Users/aksin/Desktop/Qutip+qskit projects/photonstrust"

# one-time if missing
[ -x ./.venv/bin/python ] || python3 -m venv .venv

./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/pip install -e ".[dev]"

# config sanity (must pass)
./.venv/bin/python -m photonstrust.cli run configs/product/pilot_day0_kickoff.yml --validate-only
```

**Gate G0 (must pass):** validate-only returns `{"ok": true, "scenarios": 1}`.

---

## 1) Live kickoff timeline (T+0 to T+60)

### T+0 to T+10 — scope lock (no terminal)

1. Complete `01_pilot_intake_checklist.md` sections A/B/C.
2. Fill `02_pilot_success_criteria_template.md` sections 1–4.
3. Confirm decision date + owners.

### T+10 to T+25 — produce day-0 artifact pack

```bash
cd "/mnt/c/Users/aksin/Desktop/Qutip+qskit projects/photonstrust"

PILOT_ID="<customer-pilot-id>"
RUN_LABEL="day0_${PILOT_ID}_$(date -u +%Y%m%dT%H%M%SZ)"

./.venv/bin/python scripts/run_phase2e_demo_pack.py \
  --config configs/product/pilot_day0_kickoff.yml \
  --band c_1550 \
  --seed 20260216 \
  --preview-uncertainty-samples 60 \
  --label "$RUN_LABEL"

PACK_DIR="results/demo_pack/$RUN_LABEL"
CARD_PATH="$(find "$PACK_DIR/run" -name reliability_card.json -print -quit)"

echo "PACK_DIR=$PACK_DIR"
echo "CARD_PATH=$CARD_PATH"
```

### T+25 to T+40 — acceptance checks (hard gates)

```bash
# G1: artifacts exist
test -f "$PACK_DIR/demo_pack.json"
test -f "$PACK_DIR/evidence/artifact_manifest.json"
test -f "$PACK_DIR/evidence/reliability_card_summary.json"
test -f "$CARD_PATH"

# G2: reliability card schema v1.1
./.venv/bin/python -m photonstrust.cli card validate "$CARD_PATH" --schema v1.1

# G3: trust metadata + safe-use label present
export CARD_PATH
./.venv/bin/python - <<'PY'
import json, os
card = json.load(open(os.environ["CARD_PATH"], "r", encoding="utf-8"))
required = [
    "evidence_quality",
    "operating_envelope",
    "security_assumptions_metadata",
    "finite_key_epsilon_ledger",
    "confidence_intervals",
    "model_provenance",
]
missing = [k for k in required if k not in card]
assert not missing, f"missing fields: {missing}"
assert card["safe_use_label"]["label"] in {
    "qualitative", "security_target_ready", "engineering_grade"
}
print("OK: trust metadata + safe_use_label")
PY

# G4: harness replay (customer confidence check)
./.venv/bin/python scripts/validation/run_validation_harness.py --output-root results/validation
HARNESS_SUMMARY="$(ls -1dt results/validation/*/summary.json | head -n 1)"
export HARNESS_SUMMARY
./.venv/bin/python - <<'PY'
import json, os
summary = json.load(open(os.environ["HARNESS_SUMMARY"], "r", encoding="utf-8"))
assert summary.get("ok") is True, summary
print("OK: validation harness", os.environ["HARNESS_SUMMARY"])
PY

# G5: benchmark drift governance (includes canonical satellite fixtures)
./.venv/bin/python scripts/validation/check_benchmark_drift.py
```

### T+40 to T+60 — closeout + decision framing

- Attach paths in meeting notes:
  - `$PACK_DIR/demo_pack.json`
  - `$CARD_PATH`
  - `$PACK_DIR/evidence/reliability_card_summary.json`
  - `$PACK_DIR/evidence/artifact_manifest.json`
  - `$HARNESS_SUMMARY`
  - latest benchmark drift artifact folder (`results/benchmark_drift/<timestamp>/`)
- Mark kickoff decision: **GO** only if G0–G5 all pass.
- If any gate fails, mark **HOLD** with owner/date.

---

## 2) Fallback handling (when a gate fails)

### F1 — Harness drift or baseline mismatch

Run once, then rerun G4 and G5:

```bash
cd "/mnt/c/Users/aksin/Desktop/Qutip+qskit projects/photonstrust"
./.venv/bin/python scripts/regenerate_baseline_fixtures.py
```

### F2 — Dependency/runtime failure

```bash
cd "/mnt/c/Users/aksin/Desktop/Qutip+qskit projects/photonstrust"
./.venv/bin/pip install -e ".[dev,qutip]"
```

Then rerun from G0.

### F3 — Still blocked after 30 minutes

Switch to **managed-run mode** for the call and state:

> “Validated in prepared dev environment; target-environment replay confirmation is pending.”

Do **not** mark GO until replay gates pass.

---

## 3) Claim-safe language (use verbatim)

Use at readout/proposal time:

- “PhotonTrust provides simulation-and-evidence-based reliability assessments for the scoped scenarios in this pilot.”
- “Results are valid within the documented operating envelope and evidence tier on each reliability card.”
- “This pilot output supports engineering decisions; it is not a substitute for formal certification or full field qualification.”

Never claim:

- formal certification,
- universal real-world guarantees,
- hardware performance guarantees without customer calibration,
- production readiness from a single local run.
