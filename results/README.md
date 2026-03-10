# Results Directory

PhotonTrust writes generated artifacts to `results/` by default.

## What goes here

- CLI run outputs
- API run stores
- UI telemetry and workspace state
- validation harness artifacts
- release and readiness reports
- local scratch artifacts created during development

## Important Notes

- Most content in `results/` is generated and local.
- Some checked-in artifacts are kept intentionally for release evidence,
  reproducibility, or documentation.
- If you are contributing, avoid committing new local scratch outputs unless
  they are explicitly part of a fixture, release artifact, or reproducibility
  record.

## Useful Subdirectories

- `release_gate/`
  - Checked-in release-gate evidence retained for milestone and audit references.
- `qutip_parity/`
  - Checked-in backend parity artifacts retained as historical validation evidence.
- `research_validation/`
  - Research-anchored validation and benchmark comparison outputs.
- `product_local/`
  - Local product launcher logs and API/UI state.
- `confirm_examples/`
  - Ad hoc example confirmation runs.
- `validation/`
  - Canonical validation harness outputs.

## Archive Guidance

- Prefer keeping long-lived explanatory context in `docs/archive/` rather than
  adding more standalone narrative files under `results/`.
- Keep checked-in `results/` artifacts only when they serve as explicit release,
  validation, or reproducibility evidence.
