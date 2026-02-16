# Phase 47 Research Brief: PIC Scattering-Network Solver (Bidirectional, Cycles)

## Motivation

The existing PIC simulator in `photonstrust.pic.simulate` is explicitly forward-only (DAG) and rejects graph cycles. This blocks realistic modeling of:

- back-reflections (e.g., imperfect terminations, reflective S-parameter blocks),
- feedback loops (e.g., rings and resonators represented as connected multiports),
- general bidirectional interference in networks that are not strictly feed-forward.

To move the PIC stack toward physics-accurate composition, we add a scattering-network solver that treats each component as an S-parameter block and solves the global linear system induced by interconnections.

## Background / Standard Formulation

For a network composed of components with per-component scattering matrices, each component satisfies:

    b = S a

where `a` is the vector of incident waves and `b` is the vector of outgoing waves at the component ports.

Interconnections between ports impose linear constraints mapping outgoing waves at one port to incident waves at its connected partner. With ideal, lossless, zero-delay connections, this becomes a permutation relation.

Stacking all ports across all components gives the global system:

    b = S (C b + a_ext)
    (I - S C) b = S a_ext

where:

- `S` is block-diagonal over components,
- `C` is the connection (port-pairing) matrix,
- `a_ext` injects externally applied incident waves.

Solving for `b` yields outgoing port amplitudes including reflections and multi-pass feedback.

## Anchors

This is standard linear network theory for multiport scattering parameters:

- D. M. Pozar, *Microwave Engineering*, 4th ed., Wiley (multiport S-parameters; wave variables and network composition).
- Touchstone file format conventions for S-parameter ordering in 2-port files (S11, S21, S12, S22).

## Scope / Explicit Assumptions

- Edges are modeled as ideal connections (no extra propagation phase/loss). Propagation is expected to be modeled explicitly by waveguide components.
- Terminations are implicitly matched unless an external excitation is provided (ports with `a_ext = 0` behave as zero incident wave from the external side).
- v1 native component scattering uses a reflectionless reciprocal approximation for simple 2-port elements and a reflectionless reciprocal extension for the 2x2 coupler; Touchstone components use their full imported 2x2 S matrix.
