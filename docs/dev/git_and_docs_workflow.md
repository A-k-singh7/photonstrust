# Git and Documentation Workflow

Use this guide when opening, updating, reviewing, or merging changes in
PhotonTrust. It is the maintainer-facing source of truth for branch hygiene,
commit quality, pull request updates, and required documentation sync.

## Golden Rules

- Start every change from an up-to-date `main`.
- Keep one branch focused on one logical change.
- Ship documentation updates in the same branch as behavior changes.
- Do not commit generated artifacts, local scratch files, or secrets unless the
  repository explicitly versions them.
- Keep `README.md`, the relevant docs index, and `CHANGELOG.md` aligned with the
  current behavior of the repo.
- Prefer small pull requests that are easy to review and easy to revert.

## Standard Flow

1. Sync local `main`.

   ```bash
   git checkout main
   git pull --ff-only
   ```

2. Create a scoped branch.

   ```bash
   git checkout -b <type>/<short-scope>
   ```

   Recommended prefixes:

   - `docs/`
   - `fix/`
   - `feat/`
   - `refactor/`
   - `research/`
   - `release/`

3. Make the smallest coherent change that solves the problem.
4. Run the smallest relevant checks before widening to broader validation.
5. Update docs, examples, changelog entries, and indexes before opening the PR.
6. Review the diff for accidental files before pushing.

   ```bash
   git status --short
   git diff --stat
   git diff --check
   ```

7. Push the branch and open a PR only after the description matches the real
   scope of the branch.

## Documentation Sync Matrix

| If you change... | Minimum documentation updates |
| --- | --- |
| CLI commands, config semantics, or outputs | `README.md`, `docs/guide/config-reference.md`, relevant examples, `CHANGELOG.md` if user-visible |
| Scripts or maintainer automation | `scripts/README.md`, `docs/dev/README.md`, `docs/dev/release_process.md` if release-related |
| Contributor workflow or repo structure | `CONTRIBUTING.md`, `docs/README.md`, `docs/dev/README.md`, GitHub templates if review behavior changed |
| React UI flows or local product startup | `README.md`, `docs/user/README.md`, `docs/user/quickstart.md` when user steps changed |
| Research assumptions or validation policy | relevant files in `docs/research/`, `docs/templates/`, and any schema or benchmark references touched by the change |
| Ignore rules, generated artifacts, or file conventions | `.gitignore`, `.gitattributes`, `.editorconfig`, and this guide when the workflow itself changed |

## Commit Expectations

- Use short imperative commit subjects.
- Separate mechanical cleanup from behavior changes when practical.
- Mention schema, config, fixture, or benchmark updates in the commit body or PR
  body when they affect reproducibility.
- Do not mix unrelated cleanup into feature branches.

Examples:

- `docs: refresh contributor workflow and git hygiene`
- `fix: tighten QKD config validation for relay presets`
- `refactor: split graph sidebar sweep helpers`

## Pull Request Expectations

- Keep the PR description current as the branch evolves.
- Link the issue, discussion, or state clearly that the change is self-contained.
- Call out contract, schema, fixture, or output changes explicitly.
- List the docs updated, not just the code changed.
- Explain why any checked-in generated artifacts are intentional.

## Before Requesting Review

- `git diff --check` is clean.
- The branch contains only intended files.
- The smallest relevant validation commands were run and recorded in the PR.
- The documentation sync matrix above was applied.
- `CHANGELOG.md` is updated for user-visible behavior, workflow, or release
  changes.
- Screenshots or example commands are refreshed when the UX or run flow changed.

## Merging and Cleanup

- Prefer squash merges for small feature or fix branches.
- Use rebase or merge commits only when preserving branch history matters.
- After merge, sync local `main` and delete merged branches.

```bash
git checkout main
git pull --ff-only
git branch -d <branch>
git push origin --delete <branch>
```

## Release-Adjacent Changes

If a change affects release behavior, publication, or evidence handling, update
all of the following together:

- `CHANGELOG.md`
- `docs/dev/release_process.md`
- `scripts/README.md`
- relevant commands in `README.md`
- schemas, examples, or signed-artifact notes if the public workflow changed
