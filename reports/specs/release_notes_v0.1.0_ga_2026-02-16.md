# Release Notes v0.1.0 (GA Cycle)

## Highlights
- Phase 60: async jobs, compile cache, deterministic uncertainty parallelization, RBAC hardening, and SBOM publish-by-digest flow.
- Phase 61: packaging/adoption readiness assets, open benchmark index refresh checks, and pilot-to-paid conversion packet.
- Phase 62: RC baseline lock, external reviewer dry-run closure, signed release gate packet, and GA bundle verification replay.
- Phase 63: post-GA packet attestation verification, packet signatures, replay matrix automation, and archive completeness checks.

## Installation
```bash
pip install -e .
pip install -e .[qutip,qiskit]
```

## Key Commands
```bash
py -3 scripts/release/release_gate_check.py
py -3 scripts/check_external_reviewer_findings.py
py -3 scripts/release/build_release_gate_packet.py
py -3 scripts/release/verify_release_gate_packet.py
py -3 scripts/release/sign_release_gate_packet.py
py -3 scripts/release/verify_release_gate_packet_signature.py
py -3 scripts/publish_ga_release_bundle.py
py -3 scripts/verify_ga_release_bundle.py
py -3 scripts/run_ga_replay_matrix.py
py -3 scripts/check_milestone_archive.py
```

## Notes
- QuTiP/Qiskit remain optional; analytic fallback is preserved.
- Evidence and release-gate packet artifacts are archived under `reports/specs/milestones/`.
