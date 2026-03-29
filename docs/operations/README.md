# PhotonTrust Operations Docs

This directory is intentionally lightweight. Historical delivery-program
artifacts were consolidated elsewhere, so this index should point only at
current operational entry points.

## Current Operational Sources of Truth

- `../dev/release_process.md`
  - Release-gate, packet, and release-documentation workflow.
- `../dev/repository_governance.md`
  - Main branch protection, baseline tags, and reproducibility refresh rules.
- `../dev/testing.md`
  - Validation entry points used before release and merge.
- `../dev/git_and_docs_workflow.md`
  - Branch, PR, and documentation-sync rules for maintainers.
- `../../scripts/README.md`
  - Script inventory, including release and validation commands.
- `main_branch_protection_2026-03-29.json`
  - Snapshot payload for the maintained `main` branch protection profile.
- `main_green_baseline_2026-03-29.md`
  - Human-readable notes for the current known-good repository baseline.
- `../../README.md`
  - User-facing command examples and product startup paths.

## Historical and Program Context

- `../research/deep_dive/12_execution_program_24_weeks.md`
  - Delivery-program context and roadmap history.
- `../archive/README.md`
  - Historical documentation retained for provenance.
- `../../reports/specs/milestones/`
  - Milestone and acceptance artifacts that remain intentionally versioned.

## Maintenance Rule

If a release or operations change lands in the repo, update this index only when
the current operational source of truth changes. Do not add one-off historical
paths here unless they will remain maintained.
