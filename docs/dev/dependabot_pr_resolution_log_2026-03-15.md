# Dependabot PR Resolution Log (2026-03-15)

## Purpose

Record how the first GitHub Dependabot PR wave was handled so future maintainers
can distinguish between changes that were merged directly, changes resolved by
replacement, and changes intentionally deferred.

## Resolution Categories

### Merged directly

These PRs were safe as-is and were merged through GitHub:

| PR | Change | Outcome |
|---|---|---|
| `#1` | `pyyaml` -> `6.0.3` | merged |
| `#5` | `globals` -> `17.4.0` | merged |
| `#7` | `@xyflow/react` -> `12.10.1` | merged |

### Resolved by replacement commit

These PRs were not merged directly, but their useful changes were adopted in a
curated repo commit and the PRs were then closed as superseded.

| PR | Change | Replacement handling |
|---|---|---|
| `#2` | `actions/checkout` -> `v6` | applied in curated workflow update commit |
| `#3` | `dorny/paths-filter` -> `v4` | applied in curated workflow update commit |
| `#4` | `actions/setup-node` -> `v6` | applied in curated workflow update commit |
| `#6` | `actions/setup-python` -> `v6` | applied in curated workflow update commit |
| `#10` | `eslint-plugin-react-refresh` -> `0.5.2` | applied in curated frontend dependency refresh commit |

Why this path was used:

1. several dependency PRs touched overlapping workflow or frontend files,
2. batching the safe changes into reviewed commits produced a cleaner main branch,
3. it avoided merging multiple near-duplicate PRs that GitHub would still run
   separately.

### Intentionally deferred / declined for now

These PRs were closed because they are not safe as isolated updates.

| PR | Change | Reason for deferral |
|---|---|---|
| `#8` | `actions/upload-artifact` -> `v7` | not adopted into current stable workflow baseline |
| `#9` | `@vitejs/plugin-react` -> `6.0.1` | requires coordinated Vite 8 upgrade |
| `#11` | `@eslint/js` -> `10.0.1` | blocked by current ESLint/plugin compatibility |
| `#12` | `eslint` -> `10.0.3` | blocked by current ESLint/plugin compatibility |

## How to Handle Deferred PRs Later

### Workflow-only deferred items

- `upload-artifact@v7`

Recommended path:

1. create a dedicated workflow-maintenance branch,
2. update all workflow artifact actions together,
3. run GitHub workflow validation and smoke lanes,
4. merge as one coordinated workflow PR.

### Frontend-tooling deferred items

- `@vitejs/plugin-react@6`
- `eslint@10`
- `@eslint/js@10`

Recommended path:

1. create a dedicated frontend-toolchain upgrade PR,
2. upgrade Vite / plugin-react together,
3. upgrade ESLint stack only when peer dependencies align,
4. run:
   - `npm run build`
   - `npm run test:ui`
   - lint and determinism checks,
5. merge only after the whole toolchain is green.

## Maintainer Rule Going Forward

When Dependabot opens multiple overlapping PRs:

1. merge safe, isolated updates directly,
2. supersede overlapping safe updates with one curated commit if that produces a
   cleaner result,
3. close risky isolated updates with an explicit deferral reason,
4. track deferred upgrades in a dedicated upgrade plan rather than leaving the
   reason implicit.
