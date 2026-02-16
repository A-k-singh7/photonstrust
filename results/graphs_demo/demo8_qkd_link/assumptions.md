# Graph Compile Assumptions

- profile: qkd_link
- graph_schema_version: 0.1
- Compilation output is a PhotonTrust YAML config dict consumable by `photonstrust run`.
- Node params are passed through without physics interpretation at compile time.
- Engine defaults/presets are applied later by `photonstrust.config.build_scenarios`.
- Edges are currently informational only for qkd_link graphs (not required for compilation).
