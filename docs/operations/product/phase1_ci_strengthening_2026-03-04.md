# Phase 1 CI Strengthening (2026-03-04)

This runbook hardens PhotonTrust engineering execution for startup velocity while
keeping merge confidence high.

## What changed

1. Fixed pytest module-collision instability by setting import mode to
   `importlib` in `pyproject.toml`.
2. Split CI into two lanes:
   - PR/push smoke lane: `.github/workflows/ci.yml`
   - nightly/full lane: `.github/workflows/ci-nightly-full.yml`
3. Added branch-protection automation script:
   - `scripts/apply_branch_protection.py`
4. Added CI health scoreboard generation:
   - script: `scripts/compute_ci_health_metrics.py`
   - workflow: `.github/workflows/ci-health-dashboard.yml`

## Required checks profiles for `main`

Use `scripts/apply_branch_protection.py --profile <name>` to select required
checks.

If one or more `--required-check` arguments are provided, they override the
profile list.

`startup-fast` (default, startup-speed focused):

- `ci-smoke / core-smoke`
- `ci-smoke / api-contract-smoke`
- `security-baseline / pip-audit-runtime`

`strict` (higher confidence, still PR-compatible):

- `ci-smoke / core-smoke`
- `ci-smoke / api-contract-smoke`
- `Web Playwright Tests / playwright-ui`
- `cv-quick-verify / verify`
- `cv-quick-verify / Tapeout Gate Final`
- `security-baseline / pip-audit-runtime`
- `security-baseline / web-determinism-and-audit`

## Branch protection commands

Dry-run payload generation:

```bash
python scripts/apply_branch_protection.py \
  --repo <owner>/<repo> \
  --output-payload results/ci_health/branch_protection_payload.json
```

Apply and verify protections:

```bash
python scripts/apply_branch_protection.py \
  --repo <owner>/<repo> \
  --branch main \
  --apply
```

Apply strict profile instead of default:

```bash
python scripts/apply_branch_protection.py \
  --repo <owner>/<repo> \
  --branch main \
  --profile strict \
  --apply
```

## CI health scoreboard metrics

Generate local metrics from GitHub Actions:

```bash
python scripts/compute_ci_health_metrics.py \
  --repo <owner>/<repo> \
  --branch main \
  --workflow "ci-smoke" \
  --workflow "Web Playwright Tests" \
  --workflow "security-baseline" \
  --window-days 14 \
  --output-json results/ci_health/ci_history_metrics_real.json \
  --output-md results/ci_health/ci_health_summary.md
```

Scoreboard outputs:

- `results/ci_health/ci_history_metrics_real.json`
- `results/ci_health/ci_health_summary.md`

The JSON includes:

- build pass rate
- flaky rerun rate
- mean time to recovery (MTTR)
- red/green status versus thresholds
