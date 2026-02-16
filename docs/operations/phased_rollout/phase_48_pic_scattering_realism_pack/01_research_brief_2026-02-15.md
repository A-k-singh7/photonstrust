# Phase 48 Research Brief: PIC Scattering Realism Pack (Edges + Reflections + Touchstone N-port)

## Motivation

Phase 47 introduced an opt-in bidirectional scattering-network solver for PIC circuits. Phase 48 extends that solver and the PIC compact-model ingestion pipeline to remove remaining “ideal wire / reflectionless / 2-port only” limitations:

- **Edge propagation realism**: edges can carry loss and phase/delay rather than being ideal connections.
- **Native reflections and non-reciprocity**: 2-port native components can model port reflections (return loss) and a simple non-reciprocal isolator-like 2-port is available.
- **Touchstone N-port ingestion**: import general `.sNp` Touchstone files (not just `.s2p`) with correct parameter ordering and deterministic interpolation.

These upgrades are aimed at making ChipVerify results materially closer to physics-accurate network behavior while keeping the system deterministic and testable.

## Key Models

### 1) Edge propagation as a reciprocal transfer

Edges represent propagation between two connected ports. We model an edge as a reciprocal, bidirectional complex transfer:

    g = sqrt(eta) * exp(i * phi)

where:

- `eta` is the power transmission from insertion loss / propagation loss,
- `phi` is the phase accumulated by the route, either explicitly (`phase_rad`) or inferred from `(n_eff, length_um, wavelength_nm)` or `delay_ps`.

In the scattering solver, this becomes a weighted connection matrix `C` so that incident waves are:

    a = C b + a_ext

instead of ideal pairings (`C` entries equal to 1).

### 2) Scattering-network solve

Per-component scattering is `b = S a`. Combined with connections, the global system is:

    b = S (C b + a_ext)
    (I - S C) b = S a_ext

We solve for `b` with a dense linear solve (`numpy.linalg.solve`) for v0.3; this supports feedback cycles and reflections.

### 3) Touchstone N-port ordering

Touchstone `.sNp` files list S-parameters per frequency point in the standard column-major ordering:

    S11, S21, ..., SN1, S12, S22, ..., SN2, ... , S1N, S2N, ..., SNN

This is consistent with the familiar 2-port ordering: `S11, S21, S12, S22`.

We parse multi-line records as a stream of tokens and reconstruct the `N x N` complex matrix deterministically.

## Primary Anchors

- D. M. Pozar, *Microwave Engineering*, multiport S-parameter network theory.
- Touchstone 1.x `.sNp` conventions (S-parameter ordering and data formats RI/MA/DB).

## Explicit Assumptions

- Edges are reciprocal. Directional/non-reciprocal edges are out of scope for Phase 48.
- Unconnected ports are treated as matched terminations in the scattering solve (no externally incident wave: `a_ext = 0`).
- Native reflection modeling is opt-in via `return_loss_db`; default remains reflectionless.
