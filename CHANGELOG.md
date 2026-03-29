# Changelog

## Unreleased
- OSS repo cleanup: added contributor/community files, repo indexes, and local cleanup tooling.
- License change: repository metadata and license text now use AGPL-3.0.
- Repo workflow refresh: added a git and docs maintenance guide, removed stale documentation references, and tightened GitHub template and pre-commit hygiene.
- Governance hardening: added a maintained `main-future-safe` branch-protection profile and repository governance documentation.
- Reproducibility hardening: added `scripts/refresh_repo_baselines.py` for fixture hash refresh, release packet refresh, and milestone normalization.
- UI maintainability: split `web/src/App.jsx` support logic into dedicated shell modules and ratcheted the App shell line budget back down.
- Product-story tightening: reinforced the QKD-first reliability wedge in the README, use-case docs, and landing copy while keeping PIC paths marked as advanced.

## v0.1.0-ga-cycle (2026-02-16)
- Platform scale-up: async jobs, compile cache, deterministic uncertainty parallel workers, detector fast-path, and RBAC/API governance hardening.
- Evidence hardening: SBOM in bundle manifests and publish/fetch/verify-by-digest flows.
- Adoption pipeline: citation/packaging metadata, open benchmark index refresh checks, pilot conversion packet templates.
- GA cycle controls: RC baseline lock manifest, external reviewer severity closure checks, release gate packet, and GA bundle verification replay.
- Post-GA hardening: packet hash/approval verification, Ed25519 packet signatures, replay matrix automation, and milestone archive completeness audits.

## v0.1.0
- Physics layer: emitter, memory, detector models with QuTiP fallback
- Event kernel and topology scaffolding
- Qiskit protocol circuit stubs (swap, purify, teleport)
- QKD, repeater, teleportation, and source benchmarking scenarios
- Reliability Card v1.0 schema + HTML/PDF reports
- Benchmark datasets, run registry, and Streamlit UI
- CI workflow and regression baselines
