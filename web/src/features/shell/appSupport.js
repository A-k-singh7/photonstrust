import { kindDef, portDomainFor } from "../../photontrust/kinds";
import { createOpaqueId, randomToken } from "../../state/randomId";
import { DEMO_SCENE_PLANS, GUIDED_STEP_ITEMS } from "./appDefaults";

export function _defaultGuidedProgress() {
  const steps = {};
  for (const step of GUIDED_STEP_ITEMS) {
    steps[String(step.id)] = false;
  }
  return {
    steps,
    completed: false,
    completed_at: null,
  };
}

export function _loadGuidedProgress() {
  try {
    const raw = localStorage.getItem("pt_guided_progress_v1");
    if (!raw) return _defaultGuidedProgress();
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return _defaultGuidedProgress();
    const out = _defaultGuidedProgress();
    const sourceSteps = parsed.steps && typeof parsed.steps === "object" ? parsed.steps : {};
    for (const step of GUIDED_STEP_ITEMS) {
      out.steps[String(step.id)] = sourceSteps[String(step.id)] === true;
    }
    out.completed = Boolean(parsed.completed === true);
    out.completed_at = parsed.completed_at ? String(parsed.completed_at) : null;
    return out;
  } catch {
    return _defaultGuidedProgress();
  }
}

export function _saveGuidedProgress(progress) {
  try {
    const safe = _defaultGuidedProgress();
    const source = progress && typeof progress === "object" ? progress : {};
    const sourceSteps = source.steps && typeof source.steps === "object" ? source.steps : {};
    for (const step of GUIDED_STEP_ITEMS) {
      safe.steps[String(step.id)] = sourceSteps[String(step.id)] === true;
    }
    safe.completed = source.completed === true;
    safe.completed_at = source.completed_at ? String(source.completed_at) : null;
    localStorage.setItem("pt_guided_progress_v1", JSON.stringify(safe));
    return safe;
  } catch {
    return _defaultGuidedProgress();
  }
}

export function _ensureNewcomerId() {
  const existing = String(localStorage.getItem("pt_newcomer_id") || "").trim();
  if (existing) return existing;
  const generated = createOpaqueId("anon");
  localStorage.setItem("pt_newcomer_id", generated);
  return generated;
}

export function _pretty(obj) {
  return JSON.stringify(obj ?? null, null, 2);
}

export function _cloneJson(obj) {
  return JSON.parse(JSON.stringify(obj ?? null));
}

export function _safeParseJson(text) {
  try {
    return { ok: true, value: JSON.parse(text) };
  } catch (err) {
    return { ok: false, error: String(err?.message || err) };
  }
}

export function _baseUrl(baseUrl) {
  const raw = String(baseUrl || "").trim();
  if (!raw) return "";
  return raw.endsWith("/") ? raw.slice(0, -1) : raw;
}

export function _runManifestUrl(baseUrl, runId) {
  const base = _baseUrl(baseUrl);
  return `${base}/v0/runs/${encodeURIComponent(String(runId || ""))}`;
}

export function _runArtifactUrl(baseUrl, runId, relPath) {
  const base = _baseUrl(baseUrl);
  return `${base}/v0/runs/${encodeURIComponent(String(runId || ""))}/artifact?path=${encodeURIComponent(String(relPath || ""))}`;
}

export function _runBundleUrl(baseUrl, runId) {
  const base = _baseUrl(baseUrl);
  return `${base}/v0/runs/${encodeURIComponent(String(runId || ""))}/bundle`;
}

export function _publishedBundleUrl(baseUrl, digest) {
  const base = _baseUrl(baseUrl);
  return `${base}/v0/evidence/bundle/by-digest/${encodeURIComponent(String(digest || ""))}`;
}

export function _nextNodeId(kind, existingNodes) {
  const slug0 = String(kind || "node").replace(/[^A-Za-z0-9_-]+/g, "_");
  const slug = slug0 && /[A-Za-z0-9]/.test(slug0[0]) ? slug0 : `n_${slug0}`;
  const taken = new Set((existingNodes || []).map((n) => String(n.id)));
  for (let i = 1; i <= 9999; i++) {
    const candidate = `${slug}_${i}`;
    if (!taken.has(candidate)) return candidate;
  }
  return `${slug}_${randomToken(4)}`;
}

export function _flowFromGraph(graph, registryByKind = null) {
  const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
  const edges = Array.isArray(graph?.edges) ? graph.edges : [];
  const byKind = registryByKind && typeof registryByKind === "object" ? registryByKind : {};
  const flowNodes = nodes.map((n, idx) => {
    const kind = String(n?.kind || "");
    const blueprint = _kindBlueprint(kind, byKind?.[kind]);
    const pos = n?.ui?.position || n?.ui || {};
    const x = Number(pos?.x ?? 80 + idx * 220);
    const y = Number(pos?.y ?? 90);
    return {
      id: String(n.id),
      type: "ptNode",
      position: { x, y },
      data: {
        id: String(n.id),
        kind,
        label: n.label || blueprint.title || kind,
        title: blueprint.title,
        category: blueprint.category,
        inPorts: blueprint.inPorts,
        outPorts: blueprint.outPorts,
        portDomains: blueprint.portDomains,
        params: n.params && typeof n.params === "object" ? n.params : {},
      },
    };
  });
  const flowEdges = edges.map((e, idx) => ({
    id: String(e.id || `e${idx + 1}`),
    source: String(e.from),
    target: String(e.to),
    sourceHandle: e.from_port == null ? undefined : String(e.from_port),
    targetHandle: e.to_port == null ? undefined : String(e.to_port),
    label: e.label == null ? undefined : String(e.label),
  }));
  return { nodes: flowNodes, edges: flowEdges };
}

export function _defaultGraphIdForProfile(profile) {
  if (profile === "pic_circuit") return "ui_pic_circuit";
  return "ui_qkd_link";
}

function _normalizeStringList(items) {
  if (!Array.isArray(items)) return [];
  return items
    .map((v) => String(v || "").trim())
    .filter(Boolean);
}

function _defaultDomainForKind(kind, category) {
  const k = String(kind || "");
  const cat = String(category || "");
  if (cat === "pic" || k.startsWith("pic.")) return "optical";
  return "control";
}

function _mergePortDomains(kind, category, inPorts, outPorts, ...domainSpecs) {
  const fallback = _defaultDomainForKind(kind, category);
  const out = { in: {}, out: {} };
  for (const spec of domainSpecs) {
    if (!spec || typeof spec !== "object") continue;
    for (const dir of ["in", "out"]) {
      const byPort = spec?.[dir];
      if (!byPort || typeof byPort !== "object") continue;
      for (const [port, domain] of Object.entries(byPort)) {
        const p = String(port || "").trim();
        const d = String(domain || "").trim();
        if (!p || !d) continue;
        out[dir][p] = d;
      }
    }
  }
  for (const p of inPorts) {
    if (!Object.prototype.hasOwnProperty.call(out.in, p)) out.in[p] = fallback;
  }
  for (const p of outPorts) {
    if (!Object.prototype.hasOwnProperty.call(out.out, p)) out.out[p] = fallback;
  }
  return out;
}

export function _kindBlueprint(kind, kindRegistryEntry = null) {
  const kindId = String(kind || "").trim();
  const def = kindDef(kindId);
  const meta = kindRegistryEntry && typeof kindRegistryEntry === "object" ? kindRegistryEntry : null;
  const categoryGuess = kindId.startsWith("pic.") ? "pic" : kindId.startsWith("qkd.") ? "qkd" : "custom";
  const category = String(meta?.category || def?.category || categoryGuess);
  const metaInPorts = _normalizeStringList(meta?.in_ports);
  const metaOutPorts = _normalizeStringList(meta?.out_ports);
  const defInPorts = _normalizeStringList(def?.ports?.in);
  const defOutPorts = _normalizeStringList(def?.ports?.out);
  const inPorts = metaInPorts.length ? metaInPorts : defInPorts;
  const outPorts = metaOutPorts.length ? metaOutPorts : defOutPorts;
  const defaultParams = def?.defaultParams && typeof def.defaultParams === "object" ? { ...def.defaultParams } : {};
  if (Array.isArray(meta?.params)) {
    for (const p of meta.params) {
      if (!p || typeof p !== "object") continue;
      const key = String(p?.name || "").trim();
      if (!key) continue;
      if (Object.prototype.hasOwnProperty.call(defaultParams, key)) continue;
      if (Object.prototype.hasOwnProperty.call(p, "default") && p.default !== undefined) {
        defaultParams[key] = p.default;
      } else if (p.required) {
        defaultParams[key] = null;
      }
    }
  }
  const portDomains = _mergePortDomains(kindId, category, inPorts, outPorts, def?.portDomains, meta?.port_domains);
  return {
    kind: kindId,
    title: String(meta?.title || def?.title || kindId || "Node"),
    category,
    inPorts,
    outPorts,
    defaultParams,
    portDomains,
    meta,
    def,
  };
}

export function _kindAvailability(kind, kindRegistryEntry = null) {
  const kindId = String(kind || "").trim();
  const def = kindDef(kindId);
  const meta = kindRegistryEntry && typeof kindRegistryEntry === "object" ? kindRegistryEntry : null;
  const apiEnabled =
    typeof meta?.availability?.api_enabled === "boolean"
      ? meta.availability.api_enabled
      : typeof def?.availability?.api_enabled === "boolean"
        ? def.availability.api_enabled
        : true;
  const cliEnabled =
    typeof meta?.availability?.cli_enabled === "boolean"
      ? meta.availability.cli_enabled
      : typeof def?.availability?.cli_enabled === "boolean"
        ? def.availability.cli_enabled
        : true;
  return { apiEnabled, cliEnabled };
}

export function _nodePortDomain(node, direction, portName) {
  const dir = String(direction || "").toLowerCase() === "in" ? "in" : "out";
  const port = String(portName || "").trim();
  const byPort = node?.data?.portDomains?.[dir];
  if (byPort && typeof byPort === "object") {
    const d = String(byPort?.[port] || "").trim();
    if (d) return d;
  }
  return portDomainFor(String(node?.data?.kind || ""), dir, port);
}

export function _demoScenePlan(sceneId) {
  const key = String(sceneId || "benchmark").trim().toLowerCase();
  return DEMO_SCENE_PLANS[key] || DEMO_SCENE_PLANS.benchmark;
}

export function _rolePresetBehavior(roleId) {
  const role = String(roleId || "builder");
  if (role === "reviewer") return { stage: "compare", mode: "runs", tab: "diff" };
  if (role === "exec") return { stage: "export", mode: "runs", tab: "manifest" };
  return { stage: "build", mode: "graph", tab: "inspect" };
}
