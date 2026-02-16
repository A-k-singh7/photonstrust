# Phase 30 - KLayout Macro Templates + "KLayout Run Artifact Pack" Contract - Research Brief

## Metadata
- Work item ID: PT-PHASE-30
- Date: 2026-02-14
- Scope: Add a deterministic, reviewable, and tool-optional bridge from GDS -> extracted ports/routes -> DRC-lite checks, packaged as a provenance-rich "artifact pack" suitable for audits and partner workflows.

## Problem Statement
PhotonTrust already emits deterministic layout sidecars (`ports.json`, `routes.json`) and can optionally emit `layout.gds` (Phase 27). This enables CI-friendly verification (Performance DRC, LVS-lite), but it does not yet:
- provide a KLayout-consumable verification hook (batch macro template) aligned to common PDK workflows, nor
- define a trustable contract for capturing KLayout (or KLayout-like) verification runs as evidence artifacts.

For industry and many academic PDK stacks, KLayout is a common "verification runtime" for:
- PDK-provided DRC macros,
- pin/port conventions (labels/text layers),
- tech file semantics and layer maps.

PhotonTrust must treat KLayout as an **external tool seam** (optional), but still be able to:
- run a standard macro template in batch mode,
- extract minimal layout intent (ports, route spines) from GDS, and
- write a deterministic "run artifact pack" with hashes + logs so results survive scrutiny.

## Research Notes (Primary Sources)

### 1) KLayout batch invocation and runtime variables
KLayout supports batch execution of a script/macro and passing runtime variables on the command line:
- `-b` batch mode
- `-r <script>` run script/macro
- `-rd <name>=<value>` define runtime variables for the script

Reference:
- KLayout documentation: command line arguments (includes `-r` and `-rd` descriptions):
  https://www.klayout.de/doc-qt5/about/command_line.html

### 2) Macro development and Python scripting
KLayout supports macros/scripts written in Python (via the `pya` API), including database access for layouts (cells, layers, shapes).

References:
- KLayout documentation: macro development:
  https://www.klayout.de/doc-qt5/about/macro_development.html
- KLayout documentation: Python integration:
  https://www.klayout.de/doc-qt5/about/python.html

### 3) Licensing and the "external tool seam" posture
Even when the open-core remains permissively licensed, bundling or requiring GPL-licensed EDA runtimes can create licensing and distribution complexity. The preferred posture is:
- keep KLayout optional,
- capture tool provenance + outputs when used,
- never require KLayout for core correctness claims.

Reference (KLayout license notes):
- https://www.klayout.de/license.html

## Design Goals (Trust + Applicability)
- Deterministic artifacts:
  - same inputs (GDS + macro + variables) -> same extracted JSON, ignoring timestamps.
- Provenance capture:
  - record command, tool identity, runtime variables, input hashes, and logs.
- CI-safe by default:
  - when KLayout is missing, the system must fail clearly or emit a "skipped" artifact pack (policy-driven), never silently pass.
- Safe managed-service boundary:
  - do not accept arbitrary scripts from untrusted callers; restrict to built-in macro templates and known variables.

## Proposed Output Contracts

### A) Macro outputs (layout-derived)
- `ports_extracted.json`: port label extraction (prefix-based parsing, label layer spec)
- `routes_extracted.json`: waveguide PATH extraction (waveguide layer spec)
- `drc_lite.json`: minimal checks with explicit pass/fail and issue list
- `macro_provenance.json`: input path/hash, dbu, top cell selection, layer specs

### B) "KLayout run artifact pack" (wrapper-produced)
A single JSON manifest that binds together:
- inputs: GDS hash, macro hash, variable map
- execution record: command line, return code, stdout/stderr paths
- outputs: the macro-produced JSON artifacts (and their hashes)
- summary fields for UI and diffing

## Non-Goals (This Phase)
- Full foundry DRC deck execution and rule interpretation.
- Full photonics extraction (device recognition, parasitics).
- GUI integration beyond ensuring artifacts are machine-readable and serveable.

