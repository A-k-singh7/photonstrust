# Release Notes v0.1.0 (GA Cycle)

## Highlights
- Phase 60: async jobs, compile cache, deterministic uncertainty parallelization, RBAC hardening, and SBOM publish-by-digest flow.
- Phase 61: packaging/adoption readiness assets, open benchmark index refresh checks, and pilot-to-paid conversion packet.
- Phase 62: RC baseline lock, external reviewer dry-run closure, signed release gate packet, and GA bundle verification replay.

## Installation
```bash
pip install -e .
pip install -e .[qutip,qiskit]
```

## Key Commands
```bash
py -3 scripts/release_gate_check.py
py -3 scripts/check_external_reviewer_findings.py
py -3 scripts/build_release_gate_packet.py
py -3 scripts/publish_ga_release_bundle.py
py -3 scripts/verify_ga_release_bundle.py
```

## Notes
- QuTiP/Qiskit remain optional; analytic fallback is preserved.
- Evidence and release-gate packet artifacts are archived under `reports/specs/milestones/`.
