# Repository Governance

Use this page when you need to lock `main`, refresh reproducibility baselines,
or cut a known-good repository checkpoint.

## Main Branch Protection

PhotonTrust uses the `main-future-safe` branch-protection profile as the
maintained `main` baseline.

Apply or verify it with:

```bash
python scripts/apply_branch_protection.py \
  --repo A-k-singh7/photonstrust \
  --branch main \
  --profile main-future-safe \
  --required-approvals 1 \
  --output-payload docs/operations/main_branch_protection_2026-03-29.json
```

To apply the rule instead of dry-running it:

```bash
python scripts/apply_branch_protection.py \
  --repo A-k-singh7/photonstrust \
  --branch main \
  --profile main-future-safe \
  --required-approvals 1 \
  --output-payload docs/operations/main_branch_protection_2026-03-29.json \
  --apply
```

Required checks in this profile:

- `CodeQL`
- `ci-smoke / core-smoke`
- `ci-smoke / api-contract-smoke`
- `Web Playwright Tests / playwright-ui`
- `cv-quick-verify / verify`
- `cv-quick-verify / Tapeout Gate Final`
- `security-baseline / pip-audit-runtime`
- `security-baseline / web-determinism-and-audit`
- `tapeout-gate / PIC Tapeout Gate`

## Reproducibility Refresh

Use the repo baseline refresher whenever fixture hashes, release artifacts, or
tracked milestone packets change.

```bash
python scripts/refresh_repo_baselines.py --all
```

Targeted examples:

```bash
python scripts/refresh_repo_baselines.py --measurement-fixtures
python scripts/refresh_repo_baselines.py --release-gate
python scripts/refresh_repo_baselines.py --normalize-milestones
```

`--all` performs three actions:

- refreshes measurement bundle fixture SHA256 entries,
- refreshes the tracked release gate packet and signature,
- runs `pre-commit` normalization across `reports/specs/milestones/`.

## Known-Good Baselines

When `main` is repo-wide green, cut a named checkpoint:

1. Confirm `main` is clean locally and green on GitHub.
2. Create an annotated tag or GitHub release from that commit.
3. Record the commit, tag, and active required checks in
   `docs/operations/`.

Suggested command:

```bash
gh release create main-green-YYYY-MM-DD \
  --target <main-commit> \
  --title "Main Green Baseline YYYY-MM-DD" \
  --notes-file docs/operations/main_green_baseline_YYYY-MM-DD.md \
  --prerelease
```

## Maintainer Checklist

Before merging a repo workflow, fixture, or release-adjacent change:

- run the smallest relevant tests first, then widen to the broader gate,
- refresh tracked baselines if fixture or release artifacts changed,
- update `README.md`, `CHANGELOG.md`, and maintainer docs in the same branch,
- run `git diff --check`,
- confirm the branch still satisfies the `main-future-safe` protection profile.
