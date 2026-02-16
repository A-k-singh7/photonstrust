# Network Kernel and Protocol Compiler

This document defines the event-driven kernel and protocol integration plan.

## Event Kernel
### Core
- Priority queue scheduling
- Event(time_ns, priority, type, node_id, payload)

### Event Types (minimum)
- emission, detection, herald
- memory_store, memory_retrieve
- swap, purify, teleport
- classical_message

### Timing
- Photon time-of-flight via fiber model
- Classical latency via config

## Topologies
- Link: two nodes
- Chain: repeater sequence
- Star: hub-and-spoke
- Mesh: optional for later

## Protocol Compiler (Qiskit)
- Swapping circuit: Bell measurement
- Purification circuit: DEJMPS/BBPSSW
- Teleportation circuit: Bell + feed-forward

## Integration Strategy
- Protocol executor uses measurement outcomes to schedule events
- Physics layer updates node states between events
- Fast mode supports approximate noise propagation

## Validation Plan
- Unit tests for event ordering
- Circuit equivalence tests for protocol correctness
- Compare outputs vs reference simulations

## Web Research Extension (2026-02-12)
See `12_web_research_update_2026-02-12.md` section `04 Network kernel and protocol compiler: protocol-grounded additions`.

