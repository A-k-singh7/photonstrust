# Docs Cleanup Matrix (2026-03-13)

## Purpose

This matrix defines which docs are active guidance, which are archive material,
and which require a keep/move/review decision.

## Current State

The docs tree is now categorized, but still contains a very large historical
surface with hundreds of dated files.

That is useful for provenance, but not yet ideal for public readability.

## Canonical Active Docs

These should remain stable and easy to find:

- `README.md`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `SUPPORT.md`
- `docs/README.md`
- `docs/user/README.md`
- `docs/dev/README.md`
- `docs/operations/README.md`
- `docs/research/README.md`
- `configs/README.md`
- `scripts/README.md`
- `examples/README.md`

## Docs Classification Rules

### Keep active

- stable user guides
- current contributor guides
- current operations runbooks
- active research overviews

### Move to archive

- dated point-in-time capability snapshots
- superseded implementation plans
- old quickstarts replaced by stable current quickstarts
- one-off planning notes that are no longer active guidance

### Review before archiving

- phase/day milestone docs referenced by release or CI tooling,
- program plans still used to drive current execution,
- validation baselines referenced by tests or scripts.

## High-Priority Docs To Review

| Area | Current pattern | Action |
|---|---|---|
| `docs/work_items/` | `M1`, `M7`, `M10` style filenames | Keep, but document this is a program-planning namespace |
| `docs/operations/product/` | many dated UI/product execution docs | classify active vs archived |
| `docs/research/` | very large number of dated briefs/plans | create a curated canonical reading path |
| `docs/audit/` | mixed active and historical audits | move old ones to archive if superseded |

## Output We Still Need

1. a canonical `docs/user/quickstart.md`
2. a canonical `docs/dev/testing.md`
3. a canonical `docs/dev/frontend_architecture.md`
4. a canonical `docs/dev/release_process.md`
5. a curated `docs/research/start_here.md`
