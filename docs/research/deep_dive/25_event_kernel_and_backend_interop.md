# Event Kernel + Backend Interop (Deep Research)

Date: 2026-02-14

This document expands `docs/research/04_network_kernel_and_protocols.md` into an
implementation-grade research spec.

It defines:

- what the event kernel must guarantee (determinism, scalability, traceability)
- how protocol execution should be represented (Qiskit/QASM-friendly, but not
  coupled to one circuit tool)
- how PhotonTrust should interoperate with external quantum network simulators
  without trying to clone them

The goal is to make PhotonTrust "trust closure" work even when the physics is
computed by different backends.

---

## 0) Why This Matters (Positioning)

Most quantum-network simulators compete on:
- depth of event simulation and protocol coverage

PhotonTrust must compete on:
- turning simulations into audit-ready evidence bundles and decision artifacts

That implies:

1) the kernel must be deterministic and explainable
2) protocol steps must be inspectable (and replayable)
3) interop must be first-class (import results, export evidence)

---

## 1) Core Requirements for the Event Kernel

### 1.1 Determinism as a contract

Given:
- identical config inputs
- identical seeds
- identical code version

The kernel must produce:
- identical event traces and summary metrics (within numeric tolerances)

Determinism pitfalls to avoid:

- unstable ordering of "simultaneous" events
- iteration over dicts/sets without sorting
- non-deterministic parallelism

Kernel requirement:
- every event must have a deterministic total ordering key:
  - time_ns
  - priority
  - sequence_id (monotonic counter)

### 1.2 Traceability: record what happened

Every run should be able to optionally emit an event trace artifact:

- `event_trace.jsonl` (streamable) or `event_trace.json` (small runs)

Minimum fields per event:
- t_ns
- type
- actor (node/link identifier)
- payload summary (bounded size)
- causal references (parent event id(s) where relevant)

This is not just debugging; it is part of the evidence pack.

### 1.3 Scalability: budgeted trace modes

Do not require a full trace for every run.

Define trace modes:
- off
- summary (counts by type; top N slowest; top N longest queues)
- sampled (probabilistic sampling of events)
- full (for small canonical scenarios)

---

## 2) Event Types and Semantics

Kernel event taxonomy (minimum stable set):

- emission
- propagation_arrival
- detection
- herald
- memory_store
- memory_retrieve
- swap (entanglement swapping)
- purify
- teleport
- classical_message

Important: event types are *semantic*. They should not embed solver-specific
details.

---

## 3) Protocol Representation: "Protocol Step Log" vs "Circuit"

PhotonTrust needs two layers:

1) Protocol step log (required)
- a backend-independent representation of what operations occurred
- suitable for evidence packs and replay

2) Circuit representation (optional)
- for protocols that naturally map to circuits (swap/teleport/purify)
- can be implemented via Qiskit or another circuit tool

### 3.1 Protocol step log (recommended canonical form)

Represent each protocol action as:

- step_id
- t_ns
- operation (e.g., "bell_measurement", "apply_correction", "purify_round")
- qubits/resources involved
- measurement outcomes (if any)
- classical messages emitted

Key point:
- the step log is what you sign/attest in an evidence bundle
- the circuit is supporting detail

### 3.2 Circuit integration (Qiskit as a tool, not the architecture)

When circuits are used:

- define a canonical circuit id per operation (swap/purify/teleport)
- store the circuit description artifact:
  - OpenQASM 3 (preferred interchange)
  - plus a Qiskit serialization if you want convenience

The kernel should never depend on Qiskit runtime to execute the simulation.
Instead:
- use circuit tools for validation, cross-checks, and pedagogy

---

## 4) Multi-Fidelity Strategy (Kernel-Level)

PhotonTrust should explicitly support multiple fidelity layers:

- analytic propagation of a small set of state parameters (fast)
- density-matrix evolution for small subsystems (medium)
- trajectory or higher fidelity for emitter/detector components (slow)

Kernel-level policy:

- allow per-scenario fidelity profile:
  - preview: fast approximations, bounded runtime
  - certification: slower, stricter gates, optional high-fidelity cross-check

The kernel should be the orchestrator of which layer is used where.

---

## 5) Backend Interop: How PhotonTrust Avoids Becoming a Simulator Clone

### 5.1 Interop principle

PhotonTrust should not compete by rewriting NetSquid/SeQUeNCe.
PhotonTrust should interoperate by importing traces/metrics and generating
reliability/evidence artifacts.

### 5.2 Define an "External Simulation Result" contract

Propose a schema for imported results:

- `external_sim_result.json`
  - simulator_name
  - simulator_version
  - scenario_description (minimal)
  - metrics (key rate, fidelity, latency, etc.)
  - optional event trace pointer
  - provenance (hashes, seeds if known)

This contract enables:
- ingestion -> Reliability Card generation
- cross-simulator comparisons in the UI

### 5.3 Trace ingestion (optional)

If a simulator can export an event trace:

- write an adapter that maps it into PhotonTrust's canonical event trace format
- generate trace-derived diagnostics:
  - event counts by type
  - queue depth
  - time spent in each phase

The key is that PhotonTrust can then:
- attest the trace integrity
- store it in evidence bundles
- diff it across changes

---

## 6) Validation Gates

### 6.1 Kernel determinism gates

- identical inputs -> identical event trace hash
- stable ordering when events share timestamps

### 6.2 Protocol gates

- circuit equivalence tests for swap/teleport primitives (when circuit artifacts exist)
- invariants:
  - probability normalization
  - physical bounds (QBER in [0, 0.5])

### 6.3 Interop gates

- importing an external sim result produces a schema-valid Reliability Card
- evidence bundle links imported artifacts and preserves hashes

---

## 7) Evidence Artifacts (What to Export)

For kernel/protocol runs (beyond existing Reliability Card outputs), add:

- `protocol_steps.json` (bounded step log)
- `event_trace.jsonl` (optional, mode-controlled)
- `circuit_swap.qasm` / `circuit_teleport.qasm` (optional)

These should appear in:
- run artifact list
- evidence bundles (Phase 35)
- signing/attestation pipeline (Phase 40)

---

## 8) Source Index (Primary anchors)

- RFC 9340 (Architectural Principles for a Quantum Internet): https://www.rfc-editor.org/info/rfc9340
- SeQUeNCe (open-source quantum network simulator): https://arxiv.org/abs/2008.05119
- NetSquid paper (Communications Physics, 2021): https://www.nature.com/articles/s42005-021-00647-8
- OpenQASM 3 specification: https://openqasm.com/
