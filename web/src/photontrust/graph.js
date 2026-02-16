import { GRAPH_SCHEMA_VERSION } from "./kinds";

export function buildGraphPayload({
  profile,
  graphId,
  metadata,
  scenario,
  circuit,
  uncertainty,
  finiteKey,
  nodes,
  edges,
}) {
  const createdAt = new Date().toISOString().slice(0, 10);
  const m = {
    title: metadata?.title || graphId || "graph",
    description: metadata?.description || "",
    created_at: metadata?.created_at || createdAt,
  };

  const outNodes = (nodes || []).map((n) => {
    const kind = n?.data?.kind || "";
    const label = n?.data?.label;
    const params = n?.data?.params || {};
    return {
      id: String(n.id),
      kind: String(kind),
      label: label == null ? undefined : String(label),
      params: params && typeof params === "object" ? params : {},
      ui: {
        position: {
          x: Number(n?.position?.x ?? 0),
          y: Number(n?.position?.y ?? 0),
        },
      },
    };
  });

  const outEdges = (edges || []).map((e, idx) => {
    const fromPort = e.sourceHandle || undefined;
    const toPort = e.targetHandle || undefined;
    return {
      id: e.id || `e${idx + 1}`,
      from: String(e.source),
      from_port: fromPort ? String(fromPort) : undefined,
      to: String(e.target),
      to_port: toPort ? String(toPort) : undefined,
      kind: e?.data?.kind ? String(e.data.kind) : "optical",
      label: e.label == null ? undefined : String(e.label),
    };
  });

  const payload = {
    schema_version: GRAPH_SCHEMA_VERSION,
    graph_id: graphId || "graph",
    profile,
    metadata: m,
    nodes: outNodes,
    edges: outEdges,
  };

  if (profile === "qkd_link") {
    payload.scenario = scenario || {};
    payload.uncertainty = uncertainty && typeof uncertainty === "object" ? uncertainty : {};
    payload.finite_key = finiteKey && typeof finiteKey === "object" ? finiteKey : {};
  } else if (profile === "pic_circuit") {
    payload.circuit = circuit || {};
  }
  return payload;
}
