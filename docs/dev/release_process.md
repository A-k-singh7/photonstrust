# Release Process

PhotonTrust uses explicit release-gate and evidence workflows. Treat release
work as a documentation task as much as a code task: the commands, evidence
paths, and user-facing notes must stay aligned.

## Pre-Release Checklist

Before cutting or validating a release branch:

1. Sync from `main` and confirm the working tree is clean.
2. Run the smallest relevant validation checks for the touched surfaces.
3. Update `CHANGELOG.md`.
4. Update `README.md` or `docs/guide/` if user-facing commands changed.
5. Update `scripts/README.md` if release or automation commands changed.
6. Run `git diff --check` to catch whitespace and merge-marker problems.

Use `git_and_docs_workflow.md` for the branch and PR side of this flow.

## Core Release Commands

```bash
python scripts/release/release_gate_check.py --output results/release_gate/release_gate_report.json
python scripts/release/build_release_gate_packet.py
python scripts/release/refresh_release_gate_packet.py
python scripts/refresh_repo_baselines.py --release-gate --normalize-milestones
python scripts/release/sign_release_gate_packet.py
python scripts/release/verify_release_gate_packet.py
python scripts/release/verify_release_gate_packet_signature.py
```

## Typical Flow

1. Run CI and targeted validation checks.
2. Run the release gate.
3. Build or refresh the release gate packet.
4. Sign and verify the packet.
5. Review tracked evidence under `reports/` and any intentionally versioned
   `results/` subtrees.
6. Confirm `CHANGELOG.md`, `README.md`, and `scripts/README.md` describe the
   release correctly before merge or tag creation.
7. Cut a named known-good baseline when `main` is repo-wide green.

## Release Documentation Surfaces

Review these files for every release-adjacent change:

- `../../CHANGELOG.md`
- `../../README.md`
- `../../scripts/README.md`
- `../../CONTRIBUTING.md` when contributor workflow changes
- `../README.md` when the documentation map changes

## Notes

- Do not check in local build noise, unsigned scratch packets, or temporary
  validation outputs.
- If a release changes a public contract, schema, or config workflow, update the
  relevant guide or reference document in `docs/guide/` during the same branch.
