# Limitations and Trust Boundaries

PhotonTrust is strongest when it is treated as a reliability and evidence layer
for photonic quantum link workflows, not as an oracle.

## Product Scope

The current front-door product story is:

- QKD-oriented digital twin
- graph compile to runnable config
- reliability card plus report outputs

The repo also contains PIC, orbit, certification, and broader research
surfaces. Those are real, but they should be treated as expansion areas rather
than equal first-order product claims.

## Evidence Scope

A quickstart run proves that the workflow works. It does not prove deployment
readiness.

Typical quickstart characteristics:

- `evidence_quality_tier: simulated_only`
- `benchmark_coverage: internal_demo`
- no lab calibration gate pass
- no field validation

If you need stronger claims, the supporting evidence has to move beyond demo
configs and into calibrated, benchmarked, or field-backed inputs.

## Security Scope

Security-relevant fields are present, but you still need to read them.

In particular:

- `security_assumptions_metadata` is scenario-declared metadata
- `safe_use_label` is an interpretation aid, not a certification
- `finite_key_epsilon_ledger` may be incomplete or disabled on demo runs

Do not use a positive key rate alone as a deployment decision.

## Graph Compiler Scope

The shipped QKD graph example currently compiles under explicit assumptions:

- node parameters pass through without physics interpretation at compile time
- engine defaults are applied later during scenario building
- edges in `qkd_link` graphs are currently informational only

Those assumptions are written out to `assumptions.md` during graph compile and
should be reviewed alongside the compiled config.

## Dependency Scope

The base install is intentionally smaller than the full repo surface.

- base install covers the first QKD CLI path
- `.[api]` covers the local product UI workflow
- `.[qutip]` and `.[qiskit]` cover richer physics or interoperability lanes
- JAX is not a base dependency and should not be assumed present

If a path needs an extra dependency, the docs should say so explicitly.

## Documentation Scope

Not every document under `docs/` is equally current.

Use these as the maintained front door:

- `../../README.md`
- `getting-started.md`
- `use-cases.md`
- `reliability-card.md`
- `../reference/README.md`

Treat `../research/` as background and roadmap context unless a doc explicitly
describes a maintained execution surface.
