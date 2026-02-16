# Protocol Validation Matrix

This document defines correctness and regression validation for protocols.

## Protocol set
- Entanglement swapping
- Purification (DEJMPS, BBPSSW)
- Teleportation

## Validation dimensions
- Circuit correctness
- Event-sequencing correctness
- Feed-forward latency correctness
- Physics integration correctness
- Numerical stability across seeds

## Swapping validation matrix
### Circuit-level
- Verify Bell measurement output mapping to correction operations.
- Check expected parity outcomes for known Bell pairs.

### Event-level
- Ensure measurement events trigger classical message events.
- Ensure correction events happen after latency delay.

### Integration-level
- Compare fast backend vs physics backend for consistency in trend.

## Purification validation matrix
### Correctness
- For low-noise initial pairs, purification should increase fidelity.
- For high-noise initial pairs, check expected failure rate.

### Throughput trade-off
- Confirm purification schedule reduces throughput but improves fidelity.

## Teleportation validation matrix
### Idealized baseline
- Zero-noise, zero-latency case should approach unit fidelity.

### Realistic case
- Added latency and memory decay lower fidelity in expected range.

## Test catalog
- Unit tests: circuit structure and measurement wiring.
- Integration tests: protocol + event kernel + physics for one topology.
- Regression tests: baseline output stability with tolerances.

## Tolerance policy
- Circuit deterministic checks: exact
- Stochastic metric checks: relative tolerance 1e-3 to 1e-2 depending on sample size

## Definition of done
- Validation matrix automated in CI for at least one scenario per protocol.
- Failures report protocol stage where mismatch occurred.


## Inline citations (web, verified 2026-02-12)
Applied to: protocol set, validation dimensions, and baseline/tolerance policies.
- Teleportation protocol foundation (Bennett et al., 1993): https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.70.1895
- Entanglement purification (BBPSSW, 1996): https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.76.722
- Quantum privacy amplification / DEJMPS lineage (1996): https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.77.2818
- MDI-QKD (Lo, Curty, Qi, 2012): https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.108.130503
- Quantum repeater baseline (Briegel et al., 1998): https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.81.5932
- Link layer protocol for quantum networks: https://arxiv.org/abs/1903.09778
- RFC 9340 architecture guidance: https://www.rfc-editor.org/info/rfc9340

