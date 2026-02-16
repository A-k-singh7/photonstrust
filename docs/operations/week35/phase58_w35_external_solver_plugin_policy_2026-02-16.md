# Phase 58 W35 Policy: External Solver Plugin Boundary

Date: 2026-02-16

## Policy objective

Enable optional external/GPL inverse-design solver integration without exposing
sensitive execution details or destabilizing open-core deterministic evidence.

## Boundary rules

1. The open-core runtime records metadata only for plugin requests.
2. No plugin command lines, binary paths, environment variables, host details,
   or proprietary solver payloads are persisted in reports.
3. `execution.solver` captures only policy-safe fields:
   - requested backend
   - backend actually used
   - plugin ID/version
   - license class
   - applicability/fallback reason
   - policy flags (`metadata_only`, `allows_external_execution`)
4. When plugin runtime is unavailable, execution deterministically falls back to
   core solver with explicit fallback metadata.
5. Artifact contracts (`invdesign_report.json`, `optimized_graph.json`) remain
   unchanged across plugin and non-plugin requests.

## Validation expectations

- Plugin/no-plugin parity checks must hold for deterministic objective outputs.
- Schema validation must pass for all solver metadata combinations.
- Certification workflows remain evidence-complete regardless of plugin request.
