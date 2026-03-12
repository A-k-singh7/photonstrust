# PIC Gate B Correlation Packet Template

## Purpose
- Standardize the evidence packet for Gate B in `docs/operations/pic_foundry_readiness_95_checklist.md`.
- Keep correlations reproducible, auditable, and claim-safe.

## Required Inputs by Metric

| Metric | Required measured data | Required model output | Acceptance fields |
|---|---|---|---|
| B1 insertion loss | loss-vs-wavelength traces by lot/wafer/die | simulated insertion-loss traces on same sweep grid | MAE, P95 abs error, sample count |
| B2 resonance alignment | measured resonance peaks and centers | simulated resonance centers | MAE (pm), P95 (pm), sample count |
| B3 crosstalk | measured crosstalk sweep (`pic_crosstalk_sweep`) | fitted/predicted crosstalk from calibration model | RMSE (dB), max abs error (dB), fit params |
| B4 delay/RC | measured delay/RC per corner/temperature | PEX-predicted delay/RC for same conditions | MAE, P95, trend sign consistency |
| B5 drift stability | week-over-week or lot-over-lot repeats | prior accepted baseline packet | delta vs baseline, drift test result |

## Packet Layout (Recommended)

```text
results/pic_readiness/gate_b/
  packet.json
  b1_insertion_loss/
  b2_resonance/
  b3_crosstalk/
  b4_delay_rc/
  b5_drift/
```

## Execution Flow

1) Ingest measurement bundles into local open registry.
```bash
py scripts/ingest_measurement_bundle.py <bundle.json> --open-root results/pic_readiness/measurements_open --overwrite
```

2) Publish redaction-scanned artifact packs.
```bash
py scripts/publish_artifact_pack.py <bundle.json> results/pic_readiness/artifact_packs --pack-id <pack_id>
```

3) Run available deterministic drift/calibration gates (currently implemented for crosstalk).
```bash
py scripts/check_pic_crosstalk_calibration_drift.py --sweep <pic_crosstalk_sweep.json> --baseline <baseline.json>
```

4) Compute correlation metrics for each Bx metric and save reports under the packet tree.

5) Produce `packet.json` with status and evidence links.

6) Optional no-silicon bootstrap (for pipeline execution only): initialize synthetic template bundles.
```bash
py scripts/init_pic_gate_b_measurement_templates.py --root datasets/measurements/private --rc-id <rc_id> --force
```

7) Build packet via automation script.
```bash
py scripts/build_pic_gate_b_packet.py --run-dir <run_dir> --release-candidate <rc_id> --open-root results/pic_readiness/measurements_open --artifact-root results/pic_readiness/artifact_packs --b1-bundle <b1_measurement_bundle.json> --b2-bundle <b2_measurement_bundle.json> --b4-bundle <b4_measurement_bundle.json> --output results/pic_readiness/gate_b/packet_<rc_id>.json --overwrite-ingest
```

## `packet.json` Template

```json
{
  "schema_version": "0.1",
  "kind": "photonstrust.pic_gate_b_correlation_packet",
  "generated_at": "<ISO-8601>",
  "candidate": {
    "run_dir": "<path>",
    "release_candidate": "<id>"
  },
  "tolerances": {
    "b1_mae_db_max": 0.30,
    "b1_p95_db_max": 0.60,
    "b2_mae_pm_max": 10.0,
    "b2_p95_pm_max": 25.0,
    "b3_mae_db_max": 3.0,
    "b3_p95_db_max": 6.0
  },
  "metrics": {
    "b1_insertion_loss": {
      "status": "pending",
      "mae": null,
      "p95": null,
      "sample_count": 0,
      "evidence": []
    },
    "b2_resonance_alignment": {
      "status": "pending",
      "mae": null,
      "p95": null,
      "sample_count": 0,
      "evidence": []
    },
    "b3_crosstalk": {
      "status": "pending",
      "rmse_db": null,
      "max_abs_error_db": null,
      "fit_params": {},
      "sample_count": 0,
      "evidence": []
    },
    "b4_delay_rc": {
      "status": "pending",
      "mae": null,
      "p95": null,
      "sample_count": 0,
      "evidence": []
    },
    "b5_drift": {
      "status": "pending",
      "drift_pass": null,
      "delta_summary": {},
      "evidence": []
    }
  },
  "overall_gate_b_status": "pending",
  "notes": []
}
```

## Current Practical Note
- In this branch, B1/B2/B3/B4 packet automation exists and is runnable.
- B1/B2/B4 production closure still requires measured silicon datasets (template bundles are for workflow bootstrapping only).
- B5 remains tied to real drift history and cannot be closed by synthetic templates.
