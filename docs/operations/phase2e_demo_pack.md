# Phase 2E Deterministic 10-Minute Demo Pack

This runbook provides one canonical, deterministic demo flow for customer/pilot sessions.

## Goal

Run a single end-to-end scenario and produce:

- reliability card (`reliability_card.json`)
- uncertainty artifact (`uncertainty.json`)
- evidence artifacts (hash manifest + summaries)

The script is intentionally non-invasive: it adds a dedicated wrapper without changing existing CLI behavior.

## Canonical command

From repo root:

```bash
python scripts/run_phase2e_demo_pack.py
```

Optional explicit parameters:

```bash
python scripts/run_phase2e_demo_pack.py \
  --config configs/demo1_default.yml \
  --band c_1550 \
  --seed 20260216 \
  --preview-uncertainty-samples 60
```

## Runtime target

The run is configured for `execution_mode=preview` and a single band (`c_1550`), intended to complete comfortably within a ~10-minute demo window on a typical laptop/dev VM.

## Output layout

Artifacts are written under:

- `results/demo_pack/<run_label>/`

Expected tree:

- `demo_pack.json` (top-level index and deterministic fingerprint)
- `run/<scenario_id>/<band>/results.json`
- `run/<scenario_id>/<band>/uncertainty.json`
- `run/<scenario_id>/<band>/reliability_card.json`
- `run/<scenario_id>/<band>/report.html`
- `run/<scenario_id>/<band>/report.pdf` (best effort; may be absent if PDF engine unavailable)
- `evidence/artifact_manifest.json` (SHA256 + size for key artifacts)
- `evidence/reliability_card_summary.json`
- `evidence/uncertainty_summary.json`

## Determinism notes

The wrapper enforces deterministic knobs for demo reproducibility:

- fixed seed (`--seed`, default `20260216`)
- fixed execution mode (`preview`)
- fixed uncertainty sample count (`--preview-uncertainty-samples`, default `60`)
- stable canonical band (`c_1550` by default)

`demo_pack.json` includes `determinism.fingerprint_sha256`, computed from stable scenario/output fields to support quick drift checks between demo runs.

## Quick acceptance checks

1. `demo_pack.json` exists and points to all artifact paths.
2. `reliability_card.json` exists and contains `outputs.key_rate_bps` and `safe_use_label`.
3. `uncertainty.json` exists (non-empty) for the canonical run.
4. `evidence/artifact_manifest.json` lists checksums for card + uncertainty + results.

## Cleanup

Demo packs are additive and timestamped by default. Remove old run folders manually if needed.
