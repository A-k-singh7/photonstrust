# Main Green Baseline 2026-03-29

This note captures the known-good repository baseline observed on `main` at
commit `8ce43a3e69ba4786dcae55b1aa8b2c89f463ae01`.

## Repository State

- Branch: `main`
- Commit: `8ce43a3e69ba4786dcae55b1aa8b2c89f463ae01`
- Baseline tag/release: `main-green-2026-03-29`
- Release URL: `https://github.com/A-k-singh7/photonstrust/releases/tag/main-green-2026-03-29`
- Observed date: `2026-03-29`
- Open code-scanning alerts at capture time: `0`
- Open Dependabot alerts at capture time: `0`

## Green Workflow Set

The following workflows completed successfully on the baseline commit:

- `security-baseline`
- `Web Playwright Tests`
- `ci-smoke`
- `CodeQL Advanced`
- `ci-nightly-full`
- `cv-quick-verify`

## Protected-Main Target

The maintained `main` target profile is `main-future-safe`, documented in
`docs/dev/repository_governance.md` and mirrored in
`docs/operations/main_branch_protection_2026-03-29.json`.

Required checks in that profile:

- `CodeQL`
- `ci-smoke / core-smoke`
- `ci-smoke / api-contract-smoke`
- `Web Playwright Tests / playwright-ui`
- `cv-quick-verify / verify`
- `cv-quick-verify / Tapeout Gate Final`
- `security-baseline / pip-audit-runtime`
- `security-baseline / web-determinism-and-audit`
- `tapeout-gate / PIC Tapeout Gate`

## Baseline Use

Use this checkpoint when you need a concrete rollback/reference point for:

- branch-protection drift,
- workflow regressions,
- security posture comparisons,
- release-gate refresh validation.
