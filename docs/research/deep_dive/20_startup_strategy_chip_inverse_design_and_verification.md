# Startup Strategy: Chip Inverse Design + Verification (PhotonTrust)

Date: 2026-02-13

This document translates the technical plan from this thread into a startup
strategy, explicitly acknowledging the constraints of:
- photonic foundry ecosystems (PDKs, NDAs, MPWs),
- compute cost (inverse design),
- trust (reproducibility, yield robustness),
- and sales reality (long-cycle enterprise/research buyers).

It is intended to be critical and execution-oriented.

---

## 1) Thesis

The startup is not "we can do inverse design".

The startup is:
"We generate foundry-ready photonic designs and provide auditable evidence
bundles that compress the design -> lab -> decision loop."

PhotonTrust's unique angle is to fuse:
- device-level evidence (layout, DRC, corner robustness),
- system-level evidence (reliability cards, uncertainty, outage probability),
- and a governance pipeline (drift checks, release gates).

---

## 2) What You Sell (Wedges)

### Wedge A: Component IP + Evidence Packs
Deliverable:
- inverse-designed component (GDS + compact model),
- robustness report and corner sweeps,
- reproducibility pack.

Buyer:
- PIC designers and teams doing tapeouts.

Why they pay:
- fewer manual iterations,
- performance vs footprint wins,
- reduced risk at design review time.

### Wedge B: Design Review as a Service (then productize)
Deliverable:
- a paid "verification engagement" generating:
  - evidence packs,
  - design deltas,
  - risk register,
  - and a plan to improve yield.

This is realistic early revenue and produces proprietary datasets that become
your product moat.

### Wedge C: Foundry-Adapter Platform (Enterprise)
Deliverable:
- on-prem or isolated deployment that:
  - runs inverse design workflows,
  - integrates private NDA PDKs,
  - stores evidence artifacts and audit trails.

This is the "platform" sale; do not start here without design partners.

---

## 3) Why Open-Source PDKs Matter (and What They Don't Do)

Open/public PDKs let you:
- build a toolchain people can run without NDAs,
- create reproducible reference demos,
- publish benchmarks and drift checks.

They do not let you:
- copy a foundry process,
- claim manufacturability on someone else's node without a tapeout context.

Public/no-NDA photonics PDK examples:
- CORNERSTONE (`cspdk`):
  https://github.com/gdsfactory/cspdk
  https://pypi.org/project/cspdk/
- VTT PDK:
  https://github.com/gdsfactory/vtt
- Luxtelligence GF PDK wrapper:
  https://github.com/gdsfactory/luxtelligence
- SiEPIC EBeam PDK:
  https://siepic.ubc.ca/ebeam-pdk/

---

## 4) Moat: What Will Be Hard to Copy

If you only ship an optimizer, you will be copied.

Hard-to-copy moat components:
- Evidence pipeline:
  - deterministic runs,
  - provenance,
  - benchmark governance and drift alerts.
- Robustness and yield:
  - corner sweeps,
  - sensitivity analysis,
  - stability claims with triggers.
- Data:
  - calibration datasets and measurement linkage,
  - failure-mode catalogs,
  - customer-specific priors/corners (handled privately).
- Interoperability:
  - plugs into gdsfactory/KLayout flows,
  - supports multiple PDK adapters.
- System linkage:
  - tie device performance to system/network decisions using the same trust
    artifacts (PhotonTrust reliability card story).

---

## 5) Competitive Reality (Critical)

Inverse design is not empty whitespace:
- The SPINS creators already commercialized the approach:
  https://spinsphotonics.com/
- Large EDA/photonic simulation vendors exist, and many customers already use
  their flows.

So your differentiation must be:
- operational trust and reproducibility (evidence packs),
- constraints-first yield robustness,
- and fast integration with PDK workflows.

Do not try to win by claiming "better physics plots".

---

## 6) Business Model (Pragmatic)

Recommended pattern:
- Open core:
  - evidence schemas, reproducibility tooling, benchmark governance,
  - public-PDK demo adapters,
  - basic component library.
- Paid:
  - managed runs + collaboration,
  - private PDK adapters and deployment support,
  - calibration and measurement ingestion,
  - premium inverse-designed IP library,
  - enterprise security and audit features.

Reality:
- first dollars likely come from services, not SaaS.

---

## 7) Technical Roadmap (Tied to Revenue)

### Next 4-6 weeks: "Investor demo" is not the goal
Goal:
- secure 1-2 design partners for a paid evaluation.

Technical outputs that matter:
- DRC-clean demo layouts from a public PDK.
- One inverse-designed component with robustness report.
- Evidence bundles and deterministic replay.

### Next 3 months: "pilot-to-paid"
Goal:
- deliver at least one component improvement in a partner flow.

Technical outputs:
- PDK adapter abstraction hardened.
- Corner robustness and yield reporting.
- Integration with partner's measurement data (even if minimal).

### Next 12 months: "platform"
Goal:
- expand to multiple PDKs and a larger component library.

Technical outputs:
- scalable compute pipeline,
- governance and review workflow,
- strong reproducibility across environments.

---

## 8) Key Risks and Mitigations

Risk: licensing constraints block commercialization.
Mitigation:
- pick permissive backend for the product surface (prototype with MIT-licensed
  stacks), keep GPL tools as optional research plugins. (Not legal advice.)

Risk: designs are fragile and don't yield.
Mitigation:
- treat corners/robustness as a gate, not an afterthought.

Risk: sales cycle is too long.
Mitigation:
- sell services and paid evaluations early, use those to build your dataset moat.

Risk: foundry PDK access is gated.
Mitigation:
- make PDK adapters pluggable, start with public PDKs, partner with groups that
  already have foundry access.

---

## 9) Source index

- SPINS-B and documentation:
  https://github.com/stanfordnqp/spins-b
  https://spins-b.readthedocs.io/en/latest/introduction.html
- SPINS Photonics (commercialization reference point):
  https://spinsphotonics.com/
- gdsfactory and PDK list:
  https://github.com/gdsfactory/gdsfactory
- CORNERSTONE PDK wrapper:
  https://github.com/gdsfactory/cspdk
  https://pypi.org/project/cspdk/
- VTT PDK:
  https://github.com/gdsfactory/vtt
- Luxtelligence PDK:
  https://github.com/gdsfactory/luxtelligence
- SiEPIC EBeam PDK:
  https://siepic.ubc.ca/ebeam-pdk/

