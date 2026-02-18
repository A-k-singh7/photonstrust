import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  addEdge,
  useEdgesState,
  useNodesState,
  useReactFlow,
} from "@xyflow/react";

import "./App.css";

import { BAND_OPTIONS, KIND_DEFS, PROFILE_OPTIONS, kindDef, portDomainFor } from "./photontrust/kinds";
import { templatePicChain, templatePicMzi, templateQkdLink } from "./photontrust/templates";
import { buildGraphPayload } from "./photontrust/graph";
import PtNode from "./photontrust/PtNode";
import {
  apiCompileGraph,
  apiRunCrosstalkDrc,
  apiBuildPicLayout,
  apiRunPicLvsLite,
  apiRunPicKlayoutPack,
  apiExportPicSpice,
  apiInvdesignMziPhase,
  apiInvdesignCouplerRatio,
  apiRunPicInvdesignWorkflowChain,
  apiReplayPicInvdesignWorkflowChain,
  apiCreateProjectApproval,
  apiDiffRuns,
  apiGetKindRegistry,
  apiGetRunManifest,
  apiHealthz,
  apiListProjectApprovals,
  apiListProjects,
  apiListRuns,
  apiRunOrbitPass,
  apiRunQkd,
  apiSimulatePic,
  apiValidateOrbitPass,
} from "./photontrust/api";

const DEFAULT_QKD_SCENARIO = {
  id: "ui_qkd_link",
  distance_km: 10,
  band: "c_1550",
  wavelength_nm: 1550,
  execution_mode: "preview",
};

const DEFAULT_PIC_CIRCUIT = {
  id: "ui_pic_circuit",
  wavelength_nm: 1550,
};

const DEFAULT_ORBIT_PASS_CONFIG = {
  orbit_pass: {
    id: "ui_orbit_pass_envelope",
    band: "c_1550",
    dt_s: 30,
    samples: [
      { t_s: 0, distance_km: 1200, elevation_deg: 20, background_counts_cps: 5000 },
      { t_s: 30, distance_km: 900, elevation_deg: 40, background_counts_cps: 2000 },
      { t_s: 60, distance_km: 600, elevation_deg: 70, background_counts_cps: 300 },
      { t_s: 90, distance_km: 900, elevation_deg: 40, background_counts_cps: 2000 },
      { t_s: 120, distance_km: 1200, elevation_deg: 20, background_counts_cps: 5000 },
    ],
    cases: [
      {
        id: "best",
        label: "Best case (night-like, low turbulence)",
        channel_overrides: {
          atmospheric_extinction_db_per_km: 0.01,
          pointing_jitter_urad: 1.0,
          turbulence_scintillation_index: 0.08,
          background_counts_cps_scale: 0.3,
        },
      },
      { id: "median", label: "Median", channel_overrides: {} },
      {
        id: "worst",
        label: "Worst case (day-like, high turbulence)",
        channel_overrides: {
          atmospheric_extinction_db_per_km: 0.05,
          pointing_jitter_urad: 3.0,
          turbulence_scintillation_index: 0.25,
          background_counts_cps_scale: 2.0,
        },
      },
    ],
  },
  source: {
    type: "emitter_cavity",
    physics_backend: "analytic",
    rep_rate_mhz: 150,
    collection_efficiency: 0.38,
    coupling_efficiency: 0.62,
    radiative_lifetime_ns: 1.0,
    purcell_factor: 5,
    dephasing_rate_per_ns: 0.5,
    g2_0: 0.02,
    pulse_window_ns: 5.0,
  },
  channel: {
    model: "free_space",
    connector_loss_db: 1.0,
    dispersion_ps_per_km: 0.0,
    tx_aperture_m: 0.12,
    rx_aperture_m: 0.3,
    beam_divergence_urad: 12.0,
    pointing_jitter_urad: 1.5,
    atmospheric_extinction_db_per_km: 0.02,
    turbulence_scintillation_index: 0.15,
    background_counts_cps: 0.0,
    elevation_deg: 45.0,
  },
  detector: {
    class: "snspd",
    pde: 0.3,
    dark_counts_cps: 100,
    jitter_ps_fwhm: 30,
    dead_time_ns: 100,
    afterpulsing_prob: 0.001,
  },
  timing: {
    sync_drift_ps_rms: 10,
    coincidence_window_ps: 250,
  },
  protocol: {
    name: "BBM92",
    sifting_factor: 0.5,
    ec_efficiency: 1.16,
  },
  uncertainty: {},
};

function _pretty(obj) {
  return JSON.stringify(obj ?? null, null, 2);
}

function _cloneJson(obj) {
  return JSON.parse(JSON.stringify(obj ?? null));
}

function _safeParseJson(text) {
  try {
    return { ok: true, value: JSON.parse(text) };
  } catch (err) {
    return { ok: false, error: String(err?.message || err) };
  }
}

function _baseUrl(baseUrl) {
  const raw = String(baseUrl || "").trim();
  if (!raw) return "";
  return raw.endsWith("/") ? raw.slice(0, -1) : raw;
}

function _runManifestUrl(baseUrl, runId) {
  const base = _baseUrl(baseUrl);
  return `${base}/v0/runs/${encodeURIComponent(String(runId || ""))}`;
}

function _runArtifactUrl(baseUrl, runId, relPath) {
  const base = _baseUrl(baseUrl);
  return `${base}/v0/runs/${encodeURIComponent(String(runId || ""))}/artifact?path=${encodeURIComponent(String(relPath || ""))}`;
}

function _runBundleUrl(baseUrl, runId) {
  const base = _baseUrl(baseUrl);
  return `${base}/v0/runs/${encodeURIComponent(String(runId || ""))}/bundle`;
}

function _nextNodeId(kind, existingNodes) {
  const slug0 = String(kind || "node").replace(/[^A-Za-z0-9_-]+/g, "_");
  const slug = slug0 && /[A-Za-z0-9]/.test(slug0[0]) ? slug0 : `n_${slug0}`;
  const taken = new Set((existingNodes || []).map((n) => String(n.id)));
  for (let i = 1; i <= 9999; i++) {
    const candidate = `${slug}_${i}`;
    if (!taken.has(candidate)) return candidate;
  }
  return `${slug}_${Math.floor(Math.random() * 1e9)}`;
}

function _violationSampleLabel(v) {
  if (!v || typeof v !== "object") return "(invalid)";
  const code = String(v.code || "").trim();
  const entityRef = String(v.entity_ref || "").trim();
  const message = String(v.message || "").trim();
  const applicability = String(v.applicability || "").trim();
  const head = [code || "unknown", entityRef || "n/a"].join(" @ ");
  return applicability ? `${head} [${applicability}] - ${message || "(no message)"}` : `${head} - ${message || "(no message)"}`;
}

function _violationSamples(items, limit = 2) {
  if (!Array.isArray(items) || !items.length) return [];
  return items.slice(0, Math.max(1, Number(limit) || 1));
}

function _flowFromGraph(graph) {
  const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
  const edges = Array.isArray(graph?.edges) ? graph.edges : [];
  const flowNodes = nodes.map((n, idx) => {
    const def = kindDef(n.kind);
    const pos = n?.ui?.position || n?.ui || {};
    const x = Number(pos?.x ?? 80 + idx * 220);
    const y = Number(pos?.y ?? 90);
    return {
      id: String(n.id),
      type: "ptNode",
      position: { x, y },
      data: {
        id: String(n.id),
        kind: String(n.kind),
        label: n.label || (def ? def.title : String(n.kind)),
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

function _defaultGraphIdForProfile(profile) {
  if (profile === "pic_circuit") return "ui_pic_circuit";
  return "ui_qkd_link";
}

export default function App() {
  const nodeTypes = useMemo(() => ({ ptNode: PtNode }), []);

  const [apiBase, setApiBase] = useState(() => localStorage.getItem("pt_api_base") || "http://127.0.0.1:8000");
  const [apiHealth, setApiHealth] = useState({ status: "unknown", version: null, error: null });
  const [kindRegistry, setKindRegistry] = useState({
    status: "unknown",
    registryHash: null,
    error: null,
    kinds: [],
    byKind: {},
  });

  const [mode, setMode] = useState(() => localStorage.getItem("pt_mode") || "graph");

  const [profile, setProfile] = useState("qkd_link");
  const [graphId, setGraphId] = useState("ui_qkd_link");
  const [metadata, setMetadata] = useState({ title: "PhotonTrust Graph", description: "" });
  const [requireSchema, setRequireSchema] = useState(true);

  const [scenario, setScenario] = useState({ ...DEFAULT_QKD_SCENARIO });
  const [uncertainty, setUncertainty] = useState({});
  const [finiteKey, setFiniteKey] = useState({
    enabled: false,
    signals_per_block: 1.0e10,
    security_epsilon: 1.0e-10,
    parameter_estimation_fraction: 0.1,
  });
  const [circuit, setCircuit] = useState({ ...DEFAULT_PIC_CIRCUIT });
  const [qkdExecutionMode, setQkdExecutionMode] = useState("preview");
  const [picSweepNmText, setPicSweepNmText] = useState("");

  const [xtGapUm, setXtGapUm] = useState(0.6);
  const [xtLengthUm, setXtLengthUm] = useState(1000.0);
  const [xtTargetDb, setXtTargetDb] = useState(-40.0);
  const [xtLive, setXtLive] = useState(true);
  const [xtResult, setXtResult] = useState(null);
  const xtDebounceTimer = useRef(null);
  const xtHasRunOnce = useRef(false);

  const [invPhaseNodeId, setInvPhaseNodeId] = useState("");
  const [invKind, setInvKind] = useState("mzi_phase");
  const [invCouplerNodeId, setInvCouplerNodeId] = useState("");
  const [invOutputNode, setInvOutputNode] = useState("cpl_out");
  const [invOutputPort, setInvOutputPort] = useState("out1");
  const [invTargetFraction, setInvTargetFraction] = useState(0.9);
  const [invWavelengthObjectiveAgg, setInvWavelengthObjectiveAgg] = useState("mean");
  const [invCaseObjectiveAgg, setInvCaseObjectiveAgg] = useState("mean");
  const [invRobustnessCases, setInvRobustnessCases] = useState([{ id: "nominal", label: "Nominal", overrides: {} }]);
  const [invResult, setInvResult] = useState(null);
  const [workflowResult, setWorkflowResult] = useState(null);
  const [runsWorkflowReplayResult, setRunsWorkflowReplayResult] = useState(null);

  const [layoutPdk, setLayoutPdk] = useState({ name: "generic_silicon_photonics" });
  const [layoutSettings, setLayoutSettings] = useState({
    grid_um: 50.0,
    ui_scale_um_per_unit: 1.0,
    port_offset_um: 10.0,
    port_pitch_um: 10.0,
    component_box_w_um: 20.0,
    component_box_h_um: 10.0,
    coord_tol_um: 1.0e-6,
  });
  const [layoutBuildResult, setLayoutBuildResult] = useState(null);
  const [lvsSettings, setLvsSettings] = useState({ coord_tol_um: 1.0e-6 });
  const [lvsResult, setLvsResult] = useState(null);
  const [klayoutPackSettings, setKlayoutPackSettings] = useState({
    waveguide_layer: { layer: 1, datatype: 0 },
    label_layer: { layer: 10, datatype: 0 },
    label_prefix: "PTPORT",
    min_waveguide_width_um: 0.5,
    endpoint_snap_tol_um: 2.0,
  });
  const [klayoutPackResult, setKlayoutPackResult] = useState(null);

  const [spiceSettings, setSpiceSettings] = useState({ top_name: "PT_TOP", subckt_prefix: "PT", include_stub_subckts: true });
  const [spiceResult, setSpiceResult] = useState(null);
  const [orbitConfig, setOrbitConfig] = useState(() => _cloneJson(DEFAULT_ORBIT_PASS_CONFIG));
  const [orbitRequireSchema, setOrbitRequireSchema] = useState(true);

  const [runsIndex, setRunsIndex] = useState({
    status: "idle",
    error: null,
    generatedAt: null,
    runsRoot: null,
    projectId: null,
    runs: [],
  });
  const [projectsIndex, setProjectsIndex] = useState({
    status: "idle",
    error: null,
    generatedAt: null,
    projects: [],
  });
  const [selectedProjectId, setSelectedProjectId] = useState(() => localStorage.getItem("pt_project_id") || "");
  const [selectedRunId, setSelectedRunId] = useState(null);
  const [selectedRunManifest, setSelectedRunManifest] = useState(null);
  const [runsKlayoutGdsArtifactPath, setRunsKlayoutGdsArtifactPath] = useState("");
  const [runsKlayoutPackResult, setRunsKlayoutPackResult] = useState(null);
  const [diffLhsRunId, setDiffLhsRunId] = useState("");
  const [diffRhsRunId, setDiffRhsRunId] = useState("");
  const [diffScope, setDiffScope] = useState("input");
  const [runsDiffResult, setRunsDiffResult] = useState(null);
  const [approvalActor, setApprovalActor] = useState(() => localStorage.getItem("pt_approval_actor") || "ui");
  const [approvalNote, setApprovalNote] = useState("");
  const [approvalResult, setApprovalResult] = useState(null);
  const [projectApprovals, setProjectApprovals] = useState({
    status: "idle",
    error: null,
    projectId: null,
    approvals: [],
  });

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const selectedNode = useMemo(() => nodes.find((n) => String(n.id) === String(selectedNodeId)), [nodes, selectedNodeId]);

  const [activeRightTab, setActiveRightTab] = useState("inspect");
  const [exportOpen, setExportOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [importText, setImportText] = useState("");

  const [compileResult, setCompileResult] = useState(null);
  const [orbitValidateResult, setOrbitValidateResult] = useState(null);
  const [runResult, setRunResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [statusText, setStatusText] = useState("Ready.");
  const statusTimer = useRef(null);

  const reactFlowInstance = useReactFlow();

  const graphPayload = useMemo(() => {
    return buildGraphPayload({
      profile,
      graphId,
      metadata,
      scenario,
      circuit,
      uncertainty,
      finiteKey,
      nodes,
      edges,
    });
  }, [profile, graphId, metadata, scenario, circuit, uncertainty, finiteKey, nodes, edges]);

  const selectedRunGdsArtifacts = useMemo(() => {
    const arts = selectedRunManifest?.artifacts && typeof selectedRunManifest.artifacts === "object" ? selectedRunManifest.artifacts : null;
    if (!arts) return [];
    const out = [];
    for (const [k, v] of Object.entries(arts)) {
      if (typeof v !== "string") continue;
      const p = String(v || "").trim();
      if (!p) continue;
      if (!p.toLowerCase().endsWith(".gds")) continue;
      out.push({ key: String(k || ""), path: p });
    }

    // Unique by path (case-insensitive), stable ordering.
    const seen = new Set();
    const uniq = [];
    for (const a of out) {
      const key = String(a.path || "").toLowerCase();
      if (!key || seen.has(key)) continue;
      seen.add(key);
      uniq.push(a);
    }
    uniq.sort((a, b) => {
      const aCanon = String(a.key || "") === "layout_gds";
      const bCanon = String(b.key || "") === "layout_gds";
      if (aCanon !== bCanon) return aCanon ? -1 : 1;
      return String(a.path || "").localeCompare(String(b.path || ""), undefined, { sensitivity: "base" });
    });
    return uniq;
  }, [selectedRunManifest]);

  const kindOptions = useMemo(() => {
    const cat = profile === "pic_circuit" ? "pic" : "qkd";
    if (kindRegistry.status === "ok" && Array.isArray(kindRegistry.kinds) && kindRegistry.kinds.length) {
      return kindRegistry.kinds
        .filter((k) => String(k?.category || "") === cat)
        .map((k) => String(k.kind))
        .sort((a, b) => String(a).localeCompare(String(b)));
    }
    return Object.keys(KIND_DEFS)
      .filter((k) => KIND_DEFS[k]?.category === cat)
      .sort((a, b) => String(a).localeCompare(String(b)));
  }, [profile, kindRegistry.status, kindRegistry.kinds]);

  const phaseNodeIds = useMemo(() => {
    if (profile !== "pic_circuit") return [];
    return (nodes || [])
      .filter((n) => String(n?.data?.kind || "") === "pic.phase_shifter")
      .map((n) => String(n.id))
      .sort((a, b) => String(a).localeCompare(String(b)));
  }, [nodes, profile]);

  const couplerNodeIds = useMemo(() => {
    if (profile !== "pic_circuit") return [];
    return (nodes || [])
      .filter((n) => String(n?.data?.kind || "") === "pic.coupler")
      .map((n) => String(n.id))
      .sort((a, b) => String(a).localeCompare(String(b)));
  }, [nodes, profile]);

  useEffect(() => {
    if (profile !== "pic_circuit") return;
    if (invPhaseNodeId) return;
    if (phaseNodeIds.length) setInvPhaseNodeId(phaseNodeIds[0]);
  }, [profile, invPhaseNodeId, phaseNodeIds]);

  useEffect(() => {
    if (profile !== "pic_circuit") return;
    if (invCouplerNodeId) return;
    if (couplerNodeIds.length) setInvCouplerNodeId(couplerNodeIds[0]);
  }, [profile, invCouplerNodeId, couplerNodeIds]);

  useEffect(() => {
    const rid = String(selectedRunManifest?.run_id || "").trim();
    const paths = (selectedRunGdsArtifacts || []).map((a) => String(a?.path || "")).filter(Boolean);
    const cur = String(runsKlayoutGdsArtifactPath || "").trim();

    if (!rid || !paths.length) {
      if (cur) setRunsKlayoutGdsArtifactPath("");
      return;
    }
    if (cur && paths.includes(cur)) return;
    setRunsKlayoutGdsArtifactPath(paths[0]);
  }, [selectedRunGdsArtifacts, selectedRunManifest, runsKlayoutGdsArtifactPath]);

  const _setStatus = useCallback((msg) => {
    setStatusText(String(msg || ""));
    if (statusTimer.current) clearTimeout(statusTimer.current);
    statusTimer.current = setTimeout(() => setStatusText("Ready."), 7000);
  }, []);

  const pingApi = useCallback(async () => {
    setApiHealth({ status: "checking", version: null, error: null });
    setKindRegistry((r) => ({ ...r, status: "checking", error: null }));
    try {
      const payload = await apiHealthz(apiBase);
      setApiHealth({ status: "ok", version: payload?.version || null, error: null });
      try {
        const reg = await apiGetKindRegistry(apiBase);
        const kinds = Array.isArray(reg?.registry?.kinds) ? reg.registry.kinds : [];
        const byKind = {};
        for (const k of kinds) {
          if (!k || typeof k !== "object") continue;
          if (!k.kind) continue;
          byKind[String(k.kind)] = k;
        }
        setKindRegistry({
          status: "ok",
          registryHash: reg?.registry_hash || null,
          error: null,
          kinds,
          byKind,
        });
      } catch (err) {
        setKindRegistry((r) => ({ ...r, status: "error", error: String(err?.message || err) }));
      }
      _setStatus(`API ok (v${payload?.version || "?"}).`);
    } catch (err) {
      setApiHealth({ status: "error", version: null, error: String(err?.message || err) });
      setKindRegistry((r) => ({ ...r, status: "error", error: String(err?.message || err) }));
      _setStatus(`API error: ${String(err?.message || err)}`);
    }
  }, [apiBase, _setStatus]);

  const refreshProjects = useCallback(async () => {
    setProjectsIndex((p) => ({ ...(p || {}), status: "checking", error: null }));
    try {
      const payload = await apiListProjects(apiBase, { limit: 200 });
      const projects = Array.isArray(payload?.projects) ? payload.projects : [];
      setProjectsIndex({
        status: "ok",
        error: null,
        generatedAt: payload?.generated_at || null,
        projects,
      });
    } catch (err) {
      setProjectsIndex((p) => ({ ...(p || {}), status: "error", error: String(err?.message || err) }));
      _setStatus(`Projects load failed: ${String(err?.message || err)}`);
    }
  }, [apiBase, _setStatus]);

  const refreshRuns = useCallback(async (overrideProjectId = null) => {
    const pid = overrideProjectId != null ? String(overrideProjectId || "").trim() : String(selectedProjectId || "").trim();
    setBusy(true);
    setRunsIndex((r) => ({ ...(r || {}), status: "checking", error: null }));
    try {
      const payload = await apiListRuns(apiBase, { limit: 200, projectId: pid || null });
      const runs = Array.isArray(payload?.runs) ? payload.runs : [];
      setRunsIndex({
        status: "ok",
        error: null,
        generatedAt: payload?.generated_at || null,
        runsRoot: payload?.runs_root || null,
        projectId: payload?.project_id || null,
        runs,
      });
      _setStatus(`Loaded ${runs.length} runs${pid ? ` (project=${pid}).` : "."}`);
    } catch (err) {
      setRunsIndex((r) => ({ ...(r || {}), status: "error", error: String(err?.message || err) }));
      _setStatus(`Runs load failed: ${String(err?.message || err)}`);
    } finally {
      setBusy(false);
    }
  }, [apiBase, selectedProjectId, _setStatus]);

  const loadRunManifest = useCallback(
    async (runId) => {
      const rid = String(runId || "").trim();
      if (!rid) return;
      setBusy(true);
      setSelectedRunId(rid);
      setSelectedRunManifest(null);
      setRunsKlayoutPackResult(null);
      setRunsKlayoutGdsArtifactPath("");
      try {
        const payload = await apiGetRunManifest(apiBase, rid);
        setSelectedRunManifest(payload);
        const pid = String(payload?.input?.project_id || "default");
        setProjectApprovals((p) => ({ ...(p || {}), projectId: pid, status: "checking", error: null }));
        try {
          const approvalsPayload = await apiListProjectApprovals(apiBase, pid, { limit: 50 });
          const approvals = Array.isArray(approvalsPayload?.approvals) ? approvalsPayload.approvals : [];
          setProjectApprovals({ status: "ok", error: null, projectId: pid, approvals });
        } catch (err) {
          setProjectApprovals((p) => ({ ...(p || {}), status: "error", error: String(err?.message || err) }));
        }
        _setStatus(`Loaded manifest (${rid}).`);
      } catch (err) {
        setSelectedRunManifest({ error: String(err?.message || err) });
        _setStatus(`Manifest load failed: ${String(err?.message || err)}`);
      } finally {
        setBusy(false);
      }
    },
    [apiBase, _setStatus],
  );

  const approveSelectedRun = useCallback(async () => {
    const rid = String(selectedRunManifest?.run_id || "").trim();
    if (!rid) return;
    const pid = String(selectedRunManifest?.input?.project_id || "default").trim() || "default";
    setBusy(true);
    setApprovalResult(null);
    try {
      const payload = await apiCreateProjectApproval(apiBase, pid, rid, {
        actor: String(approvalActor || "ui"),
        note: String(approvalNote || ""),
      });
      setApprovalResult(payload);
      _setStatus(`Approved run (${rid}) in project=${pid}.`);
      try {
        const approvalsPayload = await apiListProjectApprovals(apiBase, pid, { limit: 50 });
        const approvals = Array.isArray(approvalsPayload?.approvals) ? approvalsPayload.approvals : [];
        setProjectApprovals({ status: "ok", error: null, projectId: pid, approvals });
      } catch (err) {
        setProjectApprovals((p) => ({ ...(p || {}), status: "error", error: String(err?.message || err) }));
      }
    } catch (err) {
      setApprovalResult({ error: String(err?.message || err) });
      _setStatus(`Approve failed: ${String(err?.message || err)}`);
    } finally {
      setBusy(false);
    }
  }, [apiBase, selectedRunManifest, approvalActor, approvalNote, _setStatus]);

  const diffRuns = useCallback(async () => {
    const lhs = String(diffLhsRunId || "").trim();
    const rhs = String(diffRhsRunId || "").trim();
    if (!lhs || !rhs) return;
    setBusy(true);
    setRunsDiffResult(null);
    try {
      const payload = await apiDiffRuns(apiBase, lhs, rhs, { scope: String(diffScope || "input"), limit: 200 });
      setRunsDiffResult(payload);
      _setStatus(`Diff computed (${lhs} vs ${rhs}).`);
    } catch (err) {
      setRunsDiffResult({ error: String(err?.message || err) });
      _setStatus(`Diff failed: ${String(err?.message || err)}`);
    } finally {
      setBusy(false);
    }
  }, [apiBase, diffLhsRunId, diffRhsRunId, diffScope, _setStatus]);

  useEffect(() => {
    localStorage.setItem("pt_api_base", String(apiBase));
  }, [apiBase]);

  useEffect(() => {
    localStorage.setItem("pt_mode", String(mode));
  }, [mode]);

  useEffect(() => {
    localStorage.setItem("pt_project_id", String(selectedProjectId));
  }, [selectedProjectId]);

  useEffect(() => {
    localStorage.setItem("pt_approval_actor", String(approvalActor));
  }, [approvalActor]);

  useEffect(() => {
    // Seed with a useful default template.
    const t = templateQkdLink();
    setNodes(t.nodes);
    setEdges(t.edges);
    setScenario({ ...DEFAULT_QKD_SCENARIO });
    setUncertainty({});
    setFiniteKey({
      enabled: false,
      signals_per_block: 1.0e10,
      security_epsilon: 1.0e-10,
      parameter_estimation_fraction: 0.1,
    });
    setCircuit({ ...DEFAULT_PIC_CIRCUIT });
  }, [setNodes, setEdges]);

  useEffect(() => {
    // Best-effort API ping on load.
    pingApi();
  }, [pingApi]);

  useEffect(() => {
    if (mode !== "runs") return;
    if (projectsIndex.status === "idle") refreshProjects();
    if (runsIndex.status === "idle") refreshRuns();
  }, [mode, projectsIndex.status, runsIndex.status, refreshProjects, refreshRuns]);

  const onConnect = useCallback(
    (params) => {
      const sourceId = String(params?.source || "").trim();
      const targetId = String(params?.target || "").trim();
      if (!sourceId || !targetId) {
        _setStatus("Invalid connection: missing source or target.");
        return;
      }

      const sourceNode = (nodes || []).find((n) => String(n?.id) === sourceId);
      const targetNode = (nodes || []).find((n) => String(n?.id) === targetId);
      const sourceKind = String(sourceNode?.data?.kind || "");
      const targetKind = String(targetNode?.data?.kind || "");
      const fromPort = String(params?.sourceHandle || "out");
      const toPort = String(params?.targetHandle || "in");
      const edgeKind = "optical";
      if (profile === "pic_circuit") {
        const fromDomain = portDomainFor(sourceKind, "out", fromPort);
        const toDomain = portDomainFor(targetKind, "in", toPort);

        if (fromDomain !== toDomain) {
          _setStatus(
            `Blocked connection: ${sourceId}.${fromPort} (${fromDomain}) -> ${targetId}.${toPort} (${toDomain}).`,
          );
          return;
        }
        if (fromDomain !== edgeKind) {
          _setStatus(
            `Blocked connection: edge kind ${edgeKind} incompatible with ${fromDomain} ports.`,
          );
          return;
        }
      }

      setEdges((eds) =>
        addEdge(
          {
            ...params,
            type: "smoothstep",
            animated: profile === "qkd_link",
            data: { kind: edgeKind },
          },
          eds,
        ),
      );
    },
    [setEdges, profile, nodes, _setStatus],
  );

  const loadTemplate = useCallback(
    (templateId) => {
      setCompileResult(null);
      setRunResult(null);
      setXtResult(null);
      setInvResult(null);
      setLayoutBuildResult(null);
      setLvsResult(null);
      setSpiceResult(null);
      setActiveRightTab("inspect");
      if (templateId === "qkd") {
        setProfile("qkd_link");
        setGraphId("ui_qkd_link");
        setScenario({ ...DEFAULT_QKD_SCENARIO });
        setUncertainty({});
        setFiniteKey({
          enabled: false,
          signals_per_block: 1.0e10,
          security_epsilon: 1.0e-10,
          parameter_estimation_fraction: 0.1,
        });
        const t = templateQkdLink();
        setNodes(t.nodes);
        setEdges(t.edges);
        _setStatus("Loaded template: QKD link.");
        return;
      }
      if (templateId === "pic_chain") {
        setProfile("pic_circuit");
        setGraphId("ui_pic_circuit");
        setCircuit({ ...DEFAULT_PIC_CIRCUIT });
        const t = templatePicChain();
        setNodes(t.nodes);
        setEdges(t.edges);
        _setStatus("Loaded template: PIC chain.");
        return;
      }
      if (templateId === "pic_mzi") {
        setProfile("pic_circuit");
        setGraphId("ui_pic_circuit");
        setCircuit({
          ...DEFAULT_PIC_CIRCUIT,
          inputs: [
            { node: "cpl_in", port: "in1", amplitude: 1.0 },
            { node: "cpl_in", port: "in2", amplitude: 0.0 },
          ],
        });
        const t = templatePicMzi();
        setNodes(t.nodes);
        setEdges(t.edges);
        _setStatus("Loaded template: PIC MZI.");
        return;
      }
    },
    [setNodes, setEdges, _setStatus, setCompileResult, setRunResult, setActiveRightTab],
  );

  const addKind = useCallback(
    (kind, overridePosition) => {
      const def = kindDef(kind);
      const meta = kindRegistry?.byKind?.[kind];
      const title = meta?.title || def?.title || kind;
      if (profile === "qkd_link") {
        // qkd_link compiler expects exactly one of each required kind.
        const already = nodes.find((n) => String(n?.data?.kind) === String(kind));
        if (already) {
          setSelectedNodeId(already.id);
          _setStatus(`Already present: ${title}.`);
          return;
        }
      }

      const id = _nextNodeId(kind, nodes);
      const x = overridePosition ? overridePosition.x : 120 + (nodes.length % 4) * 240;
      const y = overridePosition ? overridePosition.y : 100 + Math.floor(nodes.length / 4) * 170;
      const params = def ? { ...def.defaultParams } : {};
      if (meta && Array.isArray(meta.params)) {
        for (const p of meta.params) {
          if (!p || typeof p !== "object") continue;
          if (!p.required) continue;
          if (!p.name) continue;
          const key = String(p.name);
          if (Object.prototype.hasOwnProperty.call(params, key)) continue;
          if (Object.prototype.hasOwnProperty.call(p, "default")) {
            params[key] = p.default;
          } else {
            params[key] = null;
          }
        }
      }
      setNodes((nds) =>
        nds.concat({
          id,
          type: "ptNode",
          position: { x, y },
          data: {
            id,
            kind,
            label: title,
            params,
          },
        }),
      );
      setSelectedNodeId(id);
      _setStatus(`Added: ${title}.`);
    },
    [nodes, profile, setNodes, _setStatus, kindRegistry],
  );

  const deleteSelected = useCallback(() => {
    if (!selectedNodeId) return;
    setNodes((nds) => nds.filter((n) => String(n.id) !== String(selectedNodeId)));
    setEdges((eds) => eds.filter((e) => String(e.source) !== String(selectedNodeId) && String(e.target) !== String(selectedNodeId)));
    setSelectedNodeId(null);
    _setStatus("Deleted selected node.");
  }, [selectedNodeId, setNodes, setEdges, _setStatus]);

  const onCanvasDrop = useCallback(
    (e) => {
      e.preventDefault();
      setIsDragOver(false);
      const kind = e.dataTransfer.getData("application/reactflow-kind");
      if (!kind || !KIND_DEFS[kind]) return;
      if (!reactFlowInstance) return;
      const position = reactFlowInstance.screenToFlowPosition({ x: e.clientX, y: e.clientY });
      addKind(kind, position);
    },
    [reactFlowInstance, addKind],
  );

  const onCanvasDragOver = useCallback((e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    setIsDragOver(true);
  }, []);

  const onCanvasDragLeave = useCallback(() => {
    setIsDragOver(false);
  }, []);

  const compileGraph = useCallback(async () => {
    setBusy(true);
    setCompileResult(null);
    setRunResult(null);
    try {
      const payload = await apiCompileGraph(apiBase, graphPayload, { requireSchema });
      setCompileResult(payload);
      setActiveRightTab("compile");
      _setStatus(`Compiled (${payload?.profile || "?"}).`);
    } catch (err) {
      setCompileResult({ error: String(err?.message || err) });
      setActiveRightTab("compile");
      _setStatus(`Compile failed: ${String(err?.message || err)}`);
    } finally {
      setBusy(false);
    }
  }, [apiBase, graphPayload, requireSchema, _setStatus]);

  const validateOrbit = useCallback(async () => {
    setBusy(true);
    setOrbitValidateResult(null);
    try {
      const payload = await apiValidateOrbitPass(apiBase, orbitConfig, { requireSchema: orbitRequireSchema });
      setOrbitValidateResult(payload);
      setActiveRightTab("validate");
      _setStatus("Validated orbit pass config.");
    } catch (err) {
      setOrbitValidateResult({ error: String(err?.message || err) });
      setActiveRightTab("validate");
      _setStatus(`Validate failed: ${String(err?.message || err)}`);
    } finally {
      setBusy(false);
    }
  }, [apiBase, orbitConfig, orbitRequireSchema, _setStatus]);

  const runGraph = useCallback(async () => {
    setBusy(true);
    setRunResult(null);
    try {
      if (mode === "orbit") {
        const payload = await apiRunOrbitPass(apiBase, orbitConfig, { requireSchema: orbitRequireSchema, projectId: selectedProjectId || null });
        setRunResult(payload);
        setActiveRightTab("run");
        _setStatus(`Ran orbit pass (${payload?.run_id || "run"}).`);
        return;
      }
      if (profile === "qkd_link") {
        const payload = await apiRunQkd(apiBase, graphPayload, { executionMode: qkdExecutionMode, projectId: selectedProjectId || null });
        setRunResult(payload);
        setActiveRightTab("run");
        _setStatus(`Ran QKD (${payload?.run_id || "run"}).`);
      } else {
        const sweep = String(picSweepNmText || "")
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean)
          .map((s) => Number(s))
          .filter((x) => Number.isFinite(x));
        const payload = await apiSimulatePic(apiBase, graphPayload, { sweepNm: sweep.length ? sweep : null });
        setRunResult(payload);
        setActiveRightTab("run");
        _setStatus("Simulated PIC netlist.");
      }
    } catch (err) {
      setRunResult({ error: String(err?.message || err) });
      setActiveRightTab("run");
      _setStatus(`Run failed: ${String(err?.message || err)}`);
    } finally {
      setBusy(false);
    }
  }, [apiBase, graphPayload, profile, qkdExecutionMode, picSweepNmText, orbitConfig, orbitRequireSchema, mode, selectedProjectId, _setStatus]);

  const runCrosstalkDrc = useCallback(
    async ({ reason = "manual" } = {}) => {
      if (mode !== "graph" || profile !== "pic_circuit") return;
      setBusy(true);
      try {
        const sweep = String(picSweepNmText || "")
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean)
          .map((s) => Number(s))
          .filter((x) => Number.isFinite(x) && x > 0);
        const wavelengths = sweep.length ? sweep : [Number(circuit?.wavelength_nm ?? 1550)];

        const payload = await apiRunCrosstalkDrc(apiBase, {
          gapUm: xtGapUm,
          parallelLengthUm: xtLengthUm,
          wavelengthSweepNm: wavelengths,
          targetXtDb: xtTargetDb,
          projectId: selectedProjectId || null,
        });
        setXtResult(payload);
        xtHasRunOnce.current = true;
        if (reason !== "live") setActiveRightTab("drc");
        _setStatus(`Crosstalk DRC: ${payload?.report?.results?.status || "ok"}.`);
      } catch (err) {
        setXtResult({ error: String(err?.message || err) });
        if (reason !== "live") setActiveRightTab("drc");
        _setStatus(`DRC failed: ${String(err?.message || err)}`);
      } finally {
        setBusy(false);
      }
    },
    [apiBase, mode, profile, picSweepNmText, circuit, xtGapUm, xtLengthUm, xtTargetDb, selectedProjectId, _setStatus],
  );

  const runInvdesign = useCallback(async () => {
    if (mode !== "graph" || profile !== "pic_circuit") return;
    setBusy(true);
    setInvResult(null);
    try {
      const sweep = String(picSweepNmText || "")
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean)
        .map((s) => Number(s))
        .filter((x) => Number.isFinite(x) && x > 0);
      const wavelengths = sweep.length ? sweep : [Number(circuit?.wavelength_nm ?? 1550)];

      const common = {
        targetOutputNode: invOutputNode,
        targetOutputPort: invOutputPort,
        targetPowerFraction: invTargetFraction,
        wavelengthSweepNm: wavelengths,
        robustnessCases: invRobustnessCases,
        wavelengthObjectiveAgg: invWavelengthObjectiveAgg,
        caseObjectiveAgg: invCaseObjectiveAgg,
        projectId: selectedProjectId || null,
      };

      const payload =
        invKind === "coupler_ratio"
          ? await apiInvdesignCouplerRatio(apiBase, graphPayload, { ...common, couplerNodeId: invCouplerNodeId })
          : await apiInvdesignMziPhase(apiBase, graphPayload, { ...common, phaseNodeId: invPhaseNodeId });
      setInvResult(payload);
      if (payload?.optimized_graph) {
        const flow = _flowFromGraph(payload.optimized_graph);
        setNodes(flow.nodes);
        setEdges(flow.edges);
        setSelectedNodeId(null);
      }
      setActiveRightTab("invdesign");
      _setStatus(`Inverse design complete (${String(invKind || "invdesign")}).`);
    } catch (err) {
      setInvResult({ error: String(err?.message || err) });
      setActiveRightTab("invdesign");
      _setStatus(`Inverse design failed: ${String(err?.message || err)}`);
    } finally {
      setBusy(false);
    }
  }, [
    apiBase,
    graphPayload,
    mode,
    profile,
    invKind,
    invPhaseNodeId,
    invCouplerNodeId,
    invOutputNode,
    invOutputPort,
    invTargetFraction,
    invRobustnessCases,
    invWavelengthObjectiveAgg,
    invCaseObjectiveAgg,
    picSweepNmText,
    circuit,
    selectedProjectId,
    setNodes,
    setEdges,
    _setStatus,
  ]);

  const runInvdesignWorkflow = useCallback(async () => {
    if (mode !== "graph" || profile !== "pic_circuit") return;
    setBusy(true);
    setWorkflowResult(null);
    try {
      const sweep = String(picSweepNmText || "")
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean)
        .map((s) => Number(s))
        .filter((x) => Number.isFinite(x) && x > 0);
      const wavelengths = sweep.length ? sweep : [Number(circuit?.wavelength_nm ?? 1550)];

      const payload = await apiRunPicInvdesignWorkflowChain(apiBase, graphPayload, {
        invKind,
        phaseNodeId: invPhaseNodeId,
        couplerNodeId: invCouplerNodeId,
        targetOutputNode: invOutputNode,
        targetOutputPort: invOutputPort,
        targetPowerFraction: invTargetFraction,
        wavelengthSweepNm: wavelengths,
        robustnessCases: invRobustnessCases,
        wavelengthObjectiveAgg: invWavelengthObjectiveAgg,
        caseObjectiveAgg: invCaseObjectiveAgg,
        layoutPdk,
        layoutSettings,
        lvsSettings,
        klayoutSettings: klayoutPackSettings,
        spiceSettings,
        requireSchema,
        projectId: selectedProjectId || null,
      });
      setWorkflowResult(payload);
      if (payload?.optimized_graph) {
        const flow = _flowFromGraph(payload.optimized_graph);
        setNodes(flow.nodes);
        setEdges(flow.edges);
        setSelectedNodeId(null);
      }
      setActiveRightTab("invdesign");
      _setStatus(`Workflow complete (${payload?.run_id || "run"}): ${String(payload?.status || "ok")}.`);
    } catch (err) {
      setWorkflowResult({ error: String(err?.message || err) });
      setActiveRightTab("invdesign");
      _setStatus(`Workflow failed: ${String(err?.message || err)}`);
    } finally {
      setBusy(false);
    }
  }, [
    apiBase,
    graphPayload,
    mode,
    profile,
    picSweepNmText,
    circuit,
    invKind,
    invPhaseNodeId,
    invCouplerNodeId,
    invOutputNode,
    invOutputPort,
    invTargetFraction,
    invRobustnessCases,
    invWavelengthObjectiveAgg,
    invCaseObjectiveAgg,
    layoutPdk,
    layoutSettings,
    lvsSettings,
    klayoutPackSettings,
    spiceSettings,
    requireSchema,
    selectedProjectId,
    setNodes,
    setEdges,
    _setStatus,
  ]);

  const replaySelectedWorkflowRun = useCallback(async () => {
    const rid = String(selectedRunManifest?.run_id || "").trim();
    if (!rid) return;
    if (String(selectedRunManifest?.run_type || "") !== "pic_workflow_invdesign_chain" && !selectedRunManifest?.outputs_summary?.pic_workflow) return;
    setBusy(true);
    setRunsWorkflowReplayResult(null);
    try {
      const payload = await apiReplayPicInvdesignWorkflowChain(apiBase, rid, { projectId: selectedProjectId || null });
      setRunsWorkflowReplayResult(payload);
      const newId = payload?.workflow?.run_id ? String(payload.workflow.run_id) : "";
      if (newId) {
        await refreshRuns(selectedProjectId || null);
        await loadRunManifest(newId);
        setActiveRightTab("manifest");
      }
      _setStatus(`Workflow replay complete (${newId || "run"}).`);
    } catch (err) {
      setRunsWorkflowReplayResult({ error: String(err?.message || err) });
      _setStatus(`Workflow replay failed: ${String(err?.message || err)}`);
    } finally {
      setBusy(false);
    }
  }, [apiBase, selectedRunManifest, selectedProjectId, refreshRuns, loadRunManifest, _setStatus]);

  const runLayoutBuild = useCallback(async () => {
    if (mode !== "graph" || profile !== "pic_circuit") return;
    setBusy(true);
    setLayoutBuildResult(null);
    try {
      const payload = await apiBuildPicLayout(apiBase, graphPayload, {
        pdk: layoutPdk,
        settings: layoutSettings,
        requireSchema,
        projectId: selectedProjectId || null,
      });
      setLayoutBuildResult(payload);
      setActiveRightTab("layout");
      _setStatus(`Layout build complete (${payload?.run_id || "run"}).`);
    } catch (err) {
      setLayoutBuildResult({ error: String(err?.message || err) });
      setActiveRightTab("layout");
      _setStatus(`Layout build failed: ${String(err?.message || err)}`);
    } finally {
      setBusy(false);
    }
  }, [apiBase, graphPayload, layoutPdk, layoutSettings, mode, profile, requireSchema, selectedProjectId, _setStatus]);

  const runLvsLite = useCallback(async () => {
    if (mode !== "graph" || profile !== "pic_circuit") return;
    setBusy(true);
    setLvsResult(null);
    try {
      const layoutRunId = layoutBuildResult?.run_id ? String(layoutBuildResult.run_id) : null;
      const payload = await apiRunPicLvsLite(apiBase, graphPayload, {
        layoutRunId,
        settings: lvsSettings,
        requireSchema,
        projectId: selectedProjectId || null,
      });
      setLvsResult(payload);
      setActiveRightTab("lvs");
      _setStatus(`LVS-lite complete (${payload?.run_id || "run"}).`);
    } catch (err) {
      setLvsResult({ error: String(err?.message || err) });
      setActiveRightTab("lvs");
      _setStatus(`LVS-lite failed: ${String(err?.message || err)}`);
    } finally {
      setBusy(false);
    }
  }, [apiBase, graphPayload, layoutBuildResult, lvsSettings, mode, profile, requireSchema, selectedProjectId, _setStatus]);

  const runKlayoutPack = useCallback(async () => {
    if (mode !== "graph" || profile !== "pic_circuit") return;
    setBusy(true);
    setKlayoutPackResult(null);
    try {
      const layoutRunId = layoutBuildResult?.run_id ? String(layoutBuildResult.run_id) : null;
      const gdsArtifactPath = layoutBuildResult?.artifact_relpaths?.layout_gds ? String(layoutBuildResult.artifact_relpaths.layout_gds) : null;
      const payload = await apiRunPicKlayoutPack(apiBase, {
        layoutRunId,
        settings: klayoutPackSettings,
        projectId: selectedProjectId || null,
        gdsArtifactPath,
      });
      setKlayoutPackResult(payload);
      setActiveRightTab("klayout");
      _setStatus(`KLayout pack complete (${payload?.run_id || "run"}).`);
    } catch (err) {
      setKlayoutPackResult({ error: String(err?.message || err) });
      setActiveRightTab("klayout");
      _setStatus(`KLayout pack failed: ${String(err?.message || err)}`);
    } finally {
      setBusy(false);
    }
  }, [apiBase, klayoutPackSettings, layoutBuildResult, mode, profile, selectedProjectId, _setStatus]);

  const runSelectedRunKlayoutPack = useCallback(async () => {
    if (mode !== "runs") return;
    const rid = String(selectedRunManifest?.run_id || "").trim();
    if (!rid) return;

    const pid = String(selectedRunManifest?.input?.project_id || selectedProjectId || "default").trim() || "default";
    const gdsArtifactPath =
      String(runsKlayoutGdsArtifactPath || "").trim() || String(selectedRunGdsArtifacts?.[0]?.path || "").trim() || null;

    setBusy(true);
    setRunsKlayoutPackResult(null);
    try {
      const payload = await apiRunPicKlayoutPack(apiBase, {
        sourceRunId: rid,
        gdsArtifactPath,
        settings: klayoutPackSettings,
        projectId: pid,
      });
      setRunsKlayoutPackResult(payload);
      _setStatus(`KLayout pack complete (${payload?.run_id || "run"}).`);
    } catch (err) {
      setRunsKlayoutPackResult({ error: String(err?.message || err) });
      _setStatus(`KLayout pack failed: ${String(err?.message || err)}`);
    } finally {
      setBusy(false);
    }
  }, [
    apiBase,
    klayoutPackSettings,
    mode,
    runsKlayoutGdsArtifactPath,
    selectedProjectId,
    selectedRunGdsArtifacts,
    selectedRunManifest,
    _setStatus,
  ]);

  const runSpiceExport = useCallback(async () => {
    if (mode !== "graph" || profile !== "pic_circuit") return;
    setBusy(true);
    setSpiceResult(null);
    try {
      const payload = await apiExportPicSpice(apiBase, graphPayload, {
        settings: spiceSettings,
        requireSchema,
        projectId: selectedProjectId || null,
      });
      setSpiceResult(payload);
      setActiveRightTab("spice");
      _setStatus(`SPICE export complete (${payload?.run_id || "run"}).`);
    } catch (err) {
      setSpiceResult({ error: String(err?.message || err) });
      setActiveRightTab("spice");
      _setStatus(`SPICE export failed: ${String(err?.message || err)}`);
    } finally {
      setBusy(false);
    }
  }, [apiBase, graphPayload, mode, profile, requireSchema, selectedProjectId, spiceSettings, _setStatus]);

  const applySelectedParams = useCallback(
    (text) => {
      if (!selectedNode) return { ok: false, error: "No node selected." };
      const parsed = _safeParseJson(text);
      if (!parsed.ok) return parsed;
      if (!parsed.value || typeof parsed.value !== "object" || Array.isArray(parsed.value)) {
        return { ok: false, error: "Params must be a JSON object." };
      }
      setNodes((nds) =>
        nds.map((n) => {
          if (String(n.id) !== String(selectedNode.id)) return n;
          return { ...n, data: { ...n.data, params: parsed.value } };
        }),
      );
      return { ok: true };
    },
    [selectedNode, setNodes],
  );

  const setSelectedParamValue = useCallback(
    (name, value) => {
      if (!selectedNodeId) return;
      const key = String(name || "").trim();
      if (!key) return;
      setNodes((nds) =>
        nds.map((n) => {
          if (String(n.id) !== String(selectedNodeId)) return n;
          const cur = n?.data?.params && typeof n.data.params === "object" ? n.data.params : {};
          const next = { ...cur, [key]: value };
          return { ...n, data: { ...n.data, params: next } };
        }),
      );
    },
    [selectedNodeId, setNodes],
  );

  const applyScenarioText = useCallback(
    (text) => {
      const parsed = _safeParseJson(text);
      if (!parsed.ok) return parsed;
      if (!parsed.value || typeof parsed.value !== "object" || Array.isArray(parsed.value)) {
        return { ok: false, error: "Scenario must be a JSON object." };
      }
      setScenario(parsed.value);
      return { ok: true };
    },
    [setScenario],
  );

  const applyUncertaintyText = useCallback(
    (text) => {
      const parsed = _safeParseJson(text);
      if (!parsed.ok) return parsed;
      if (!parsed.value || typeof parsed.value !== "object" || Array.isArray(parsed.value)) {
        return { ok: false, error: "Uncertainty must be a JSON object." };
      }
      setUncertainty(parsed.value);
      return { ok: true };
    },
    [setUncertainty],
  );

  const applyFiniteKeyText = useCallback(
    (text) => {
      const parsed = _safeParseJson(text);
      if (!parsed.ok) return parsed;
      if (!parsed.value || typeof parsed.value !== "object" || Array.isArray(parsed.value)) {
        return { ok: false, error: "Finite key must be a JSON object." };
      }
      setFiniteKey(parsed.value);
      return { ok: true };
    },
    [setFiniteKey],
  );

  const applyCircuitText = useCallback(
    (text) => {
      const parsed = _safeParseJson(text);
      if (!parsed.ok) return parsed;
      if (!parsed.value || typeof parsed.value !== "object" || Array.isArray(parsed.value)) {
        return { ok: false, error: "Circuit must be a JSON object." };
      }
      setCircuit(parsed.value);
      return { ok: true };
    },
    [setCircuit],
  );

  const applyOrbitConfigText = useCallback(
    (text) => {
      const parsed = _safeParseJson(text);
      if (!parsed.ok) return parsed;
      if (!parsed.value || typeof parsed.value !== "object" || Array.isArray(parsed.value)) {
        return { ok: false, error: "Orbit config must be a JSON object." };
      }
      setOrbitConfig(parsed.value);
      return { ok: true };
    },
    [setOrbitConfig],
  );

  const exportText = useMemo(() => _pretty(graphPayload), [graphPayload]);

  const importGraph = useCallback(() => {
    const parsed = _safeParseJson(importText);
    if (!parsed.ok) {
      _setStatus(`Import JSON error: ${parsed.error}`);
      return;
    }
    const graph = parsed.value;
    if (!graph || typeof graph !== "object") {
      _setStatus("Import expects a graph JSON object.");
      return;
    }

    const p = String(graph.profile || "");
    if (p !== "qkd_link" && p !== "pic_circuit") {
      _setStatus("Import graph.profile must be qkd_link or pic_circuit.");
      return;
    }

    setProfile(p);
    setGraphId(String(graph.graph_id || _defaultGraphIdForProfile(p)));
    setMetadata(graph.metadata && typeof graph.metadata === "object" ? graph.metadata : { title: "Imported Graph", description: "" });
    if (p === "qkd_link") {
      setScenario(graph.scenario && typeof graph.scenario === "object" ? graph.scenario : { ...DEFAULT_QKD_SCENARIO });
      setUncertainty(graph.uncertainty && typeof graph.uncertainty === "object" ? graph.uncertainty : {});
      setFiniteKey(graph.finite_key && typeof graph.finite_key === "object" ? graph.finite_key : { enabled: false });
    } else {
      setCircuit(graph.circuit && typeof graph.circuit === "object" ? graph.circuit : { ...DEFAULT_PIC_CIRCUIT });
    }

    const flow = _flowFromGraph(graph);
    setNodes(flow.nodes);
    setEdges(flow.edges);
    setSelectedNodeId(null);
    setCompileResult(null);
    setRunResult(null);
    setXtResult(null);
    setInvResult(null);
    setImportOpen(false);
    setActiveRightTab("inspect");
    _setStatus("Imported graph into editor.");
  }, [importText, setNodes, setEdges, _setStatus]);

  return (
    <div className="ptApp">
      <header className="ptTopbar">
        <div className="ptBrand">
          <div className="ptBrandTitle">PhotonTrust</div>
          <div className="ptBrandSub">
            {mode === "graph" ? "graph -> compile -> run" : mode === "orbit" ? "config -> validate -> run" : "run registry -> diff"}
          </div>
        </div>

        <div className="ptTopControls">
          <label className="ptField">
            <span>Mode</span>
            <select
              value={mode}
              onChange={(e) => {
                const next = String(e.target.value);
                setMode(next);
                setCompileResult(null);
                setOrbitValidateResult(null);
                setRunResult(null);
                setSelectedNodeId(null);
                setSelectedRunId(null);
                setSelectedRunManifest(null);
                setRunsDiffResult(null);
                setDiffLhsRunId("");
                setDiffRhsRunId("");
                setDiffScope("input");
                setActiveRightTab(next === "orbit" ? "orbit" : next === "runs" ? "manifest" : "inspect");
                _setStatus(next === "orbit" ? "Switched to Orbit Pass mode." : next === "runs" ? "Switched to Runs mode." : "Switched to Graph Editor mode.");
              }}
            >
              <option value="graph">Graph Editor</option>
              <option value="orbit">Orbit Pass</option>
              <option value="runs">Runs</option>
            </select>
          </label>

          {mode === "graph" ? (
            <>
              <label className="ptField">
                <span>Profile</span>
                <select
                  value={profile}
                  onChange={(e) => {
                    const next = String(e.target.value);
                    setProfile(next);
                    setGraphId(_defaultGraphIdForProfile(next));
                    setCompileResult(null);
                    setRunResult(null);
                    if (next === "qkd_link") {
                      setScenario({ ...DEFAULT_QKD_SCENARIO });
                      loadTemplate("qkd");
                    } else {
                      setCircuit({ ...DEFAULT_PIC_CIRCUIT });
                      loadTemplate("pic_mzi");
                    }
                  }}
                >
                  {PROFILE_OPTIONS.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="ptField">
                <span>graph_id</span>
                <input value={graphId} onChange={(e) => setGraphId(String(e.target.value))} />
              </label>
            </>
          ) : null}

          <label className="ptField ptFieldWide">
            <span>API</span>
            <input value={apiBase} onChange={(e) => setApiBase(String(e.target.value))} placeholder="http://127.0.0.1:8000" />
          </label>

          <button className="ptBtn ptBtnGhost" onClick={pingApi} disabled={busy}>
            Ping
          </button>

          {mode === "graph" ? (
            <button className="ptBtn" onClick={compileGraph} disabled={busy}>
              Compile
            </button>
          ) : mode === "orbit" ? (
            <button className="ptBtn" onClick={validateOrbit} disabled={busy}>
              Validate
            </button>
          ) : (
            <button className="ptBtn" onClick={refreshRuns} disabled={busy}>
              Refresh
            </button>
          )}

          {mode === "runs" ? (
            <button className="ptBtn ptBtnPrimary" onClick={diffRuns} disabled={busy || !diffLhsRunId || !diffRhsRunId}>
              Diff
            </button>
          ) : (
            <button className="ptBtn ptBtnPrimary" onClick={runGraph} disabled={busy}>
              Run
            </button>
          )}

          {mode === "graph" && profile === "pic_circuit" ? (
            <button className="ptBtn ptBtnGhost" onClick={() => runCrosstalkDrc({ reason: "manual" })} disabled={busy}>
              DRC
            </button>
          ) : null}
        </div>

        <div className={`ptApiPill ${apiHealth.status}`} title={apiHealth.error || ""}>
          API: {apiHealth.status === "ok" ? `ok (v${apiHealth.version || "?"})` : apiHealth.status}
        </div>
      </header>

      <div className="ptMain">
        <aside className="ptSidebar ptSidebarLeft">
          {mode === "graph" ? (
            <>
              <div className="ptSidebarSection">
                <div className="ptSidebarTitle">Templates</div>
                <div className="ptBtnRow">
                  <button className="ptBtn ptBtnGhost" onClick={() => loadTemplate("qkd")} disabled={busy}>
                    QKD Link
                  </button>
                  <button className="ptBtn ptBtnGhost" onClick={() => loadTemplate("pic_chain")} disabled={busy}>
                    PIC Chain
                  </button>
                  <button className="ptBtn ptBtnGhost" onClick={() => loadTemplate("pic_mzi")} disabled={busy}>
                    PIC MZI
                  </button>
                </div>
              </div>

              <div className="ptSidebarSection">
                <div className="ptSidebarTitle">Palette <span className="ptPaletteHint">drag or click</span></div>
                {[
                  { label: "QKD", prefix: "qkd." },
                  { label: "PIC", prefix: "pic." },
                ].map(({ label, prefix }) => {
                  const group = kindOptions.filter((k) => k.startsWith(prefix));
                  if (!group.length) return null;
                  return (
                    <div key={label} className="ptPaletteGroup">
                      <div className={`ptPaletteGroupLabel ptPaletteGroupLabel--${label.toLowerCase()}`}>{label}</div>
                      <div className="ptPaletteGrid">
                        {group.map((k) => {
                          const meta = kindRegistry?.byKind?.[k];
                          const def = kindDef(k);
                          const apiEnabled = meta?.availability?.api_enabled;
                          return (
                            <div
                              key={k}
                              className={`ptPaletteItem ptPaletteItem--${label.toLowerCase()}`}
                              draggable
                              onDragStart={(e) => {
                                e.dataTransfer.setData("application/reactflow-kind", k);
                                e.dataTransfer.effectAllowed = "move";
                              }}
                              onClick={() => addKind(k)}
                              role="button"
                              tabIndex={0}
                              onKeyDown={(e) => e.key === "Enter" && addKind(k)}
                            >
                              <div className="ptPaletteTitle">{meta?.title || def?.title || k}</div>
                              <div className="ptPaletteKind">{k}</div>
                              {apiEnabled === false ? <div className="ptPaletteKind">CLI-only</div> : null}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="ptSidebarSection">
                <div className="ptSidebarTitle">Export / Import</div>
                <div className="ptBtnRow">
                  <button className="ptBtn ptBtnGhost" onClick={() => setExportOpen(true)}>
                    Export JSON
                  </button>
                  <button className="ptBtn ptBtnGhost" onClick={() => setImportOpen(true)}>
                    Import JSON
                  </button>
                </div>

                <label className="ptCheck">
                  <input type="checkbox" checked={requireSchema} onChange={(e) => setRequireSchema(Boolean(e.target.checked))} />
                  <span>Require JSON Schema on compile</span>
                </label>
              </div>
            </>
          ) : mode === "orbit" ? (
            <>
              <div className="ptSidebarSection">
                <div className="ptSidebarTitle">Templates</div>
                <div className="ptBtnRow">
                  <button
                    className="ptBtn ptBtnGhost"
                    onClick={() => {
                      setOrbitConfig(_cloneJson(DEFAULT_ORBIT_PASS_CONFIG));
                      setRunResult(null);
                      setCompileResult(null);
                      setOrbitValidateResult(null);
                      setActiveRightTab("orbit");
                      _setStatus("Loaded template: Orbit pass envelope.");
                    }}
                    disabled={busy}
                  >
                    Pass Envelope
                  </button>
                </div>
                <div className="ptHint">OrbitVerify v0.1 uses explicit samples over time (not orbit propagation).</div>

                <label className="ptCheck">
                  <input type="checkbox" checked={orbitRequireSchema} onChange={(e) => setOrbitRequireSchema(Boolean(e.target.checked))} />
                  <span>Require JSON Schema on validate/run</span>
                </label>
              </div>
            </>
          ) : (
            <>
              <div className="ptSidebarSection">
                <div className="ptSidebarTitle">Run Registry</div>
                <div className="ptHint">Browse and diff run manifests served by the API.</div>
                {runsIndex?.runsRoot ? (
                  <div className="ptHint">
                    runs_root: <span className="ptMono">{String(runsIndex.runsRoot)}</span>
                  </div>
                ) : null}

                <label className="ptField">
                  <span>Project</span>
                  <select
                    value={selectedProjectId}
                    onChange={(e) => {
                      const pid = String(e.target.value);
                      setSelectedProjectId(pid);
                      setSelectedRunId(null);
                      setSelectedRunManifest(null);
                      setDiffLhsRunId("");
                      setDiffRhsRunId("");
                      setRunsDiffResult(null);
                      setApprovalResult(null);
                      setApprovalNote("");
                      setProjectApprovals({ status: "idle", error: null, projectId: null, approvals: [] });
                      refreshRuns(pid || null);
                    }}
                    disabled={busy || projectsIndex?.status === "checking"}
                  >
                    <option value="">(all)</option>
                    {(projectsIndex?.projects || []).map((p) => {
                      const pid = String(p?.project_id || "");
                      if (!pid) return null;
                      const count = Number(p?.run_count ?? 0);
                      const label = Number.isFinite(count) && count > 0 ? `${pid} (${count})` : pid;
                      return (
                        <option key={`proj:${pid}`} value={pid}>
                          {label}
                        </option>
                      );
                    })}
                  </select>
                </label>

                {projectsIndex?.status === "error" ? <div className="ptError">{String(projectsIndex.error || "Failed to load projects.")}</div> : null}
                {runsIndex?.status === "error" ? <div className="ptError">{String(runsIndex.error || "Failed to load runs.")}</div> : null}
                <div className="ptBtnRow">
                  <button
                    className="ptBtn ptBtnGhost"
                    onClick={() => {
                      refreshProjects();
                      refreshRuns();
                    }}
                    disabled={busy}
                  >
                    Refresh
                  </button>
                </div>
              </div>

              <div className="ptSidebarSection">
                <div className="ptSidebarTitle">Diff</div>
                <label className="ptField">
                  <span>LHS run</span>
                  <select value={diffLhsRunId} onChange={(e) => setDiffLhsRunId(String(e.target.value))}>
                    <option value="">(select)</option>
                    {(runsIndex?.runs || []).map((r) => {
                      const rid = String(r?.run_id || "");
                      if (!rid) return null;
                      const pid = String(r?.project_id || "");
                      const label = `${String(r?.run_type || "run")} | ${rid}`;
                      return (
                        <option key={`lhs:${rid}`} value={rid}>
                          {pid ? `${String(r?.run_type || "run")} | ${pid} | ${rid}` : label}
                        </option>
                      );
                    })}
                  </select>
                </label>

                <label className="ptField">
                  <span>RHS run</span>
                  <select value={diffRhsRunId} onChange={(e) => setDiffRhsRunId(String(e.target.value))}>
                    <option value="">(select)</option>
                    {(runsIndex?.runs || []).map((r) => {
                      const rid = String(r?.run_id || "");
                      if (!rid) return null;
                      const pid = String(r?.project_id || "");
                      const label = `${String(r?.run_type || "run")} | ${rid}`;
                      return (
                        <option key={`rhs:${rid}`} value={rid}>
                          {pid ? `${String(r?.run_type || "run")} | ${pid} | ${rid}` : label}
                        </option>
                      );
                    })}
                  </select>
                </label>

                <label className="ptField">
                  <span>Scope</span>
                  <select value={diffScope} onChange={(e) => setDiffScope(String(e.target.value))}>
                    <option value="input">input</option>
                    <option value="outputs_summary">outputs_summary</option>
                    <option value="all">all</option>
                  </select>
                </label>

                <div className="ptBtnRow">
                  <button className="ptBtn ptBtnPrimary" onClick={diffRuns} disabled={busy || !diffLhsRunId || !diffRhsRunId}>
                    Diff
                  </button>
                </div>
              </div>
            </>
          )}
        </aside>

        {mode === "graph" ? (
          <section
            className={`ptCanvas${isDragOver ? " ptCanvas--dragover" : ""}`}
            aria-label="Graph editor canvas"
            onDrop={onCanvasDrop}
            onDragOver={onCanvasDragOver}
            onDragLeave={onCanvasDragLeave}
          >
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              nodeTypes={nodeTypes}
              fitView
              onSelectionChange={(sel) => {
                const picked = sel?.nodes?.[0]?.id;
                setSelectedNodeId(picked ? String(picked) : null);
              }}
            >
              <Background variant="dots" gap={18} size={1} />
              <Controls />
              <MiniMap pannable zoomable />
            </ReactFlow>
          </section>
        ) : mode === "orbit" ? (
          <section className="ptCanvas" aria-label="Orbit pass configuration editor">
            <div style={{ padding: 14 }}>
              <div className="ptRightSection">
                <div className="ptRightTitle">Orbit Pass Config</div>
                <div className="ptHint">
                  Edit the config and click <span className="ptMono">Run</span> to generate <span className="ptMono">orbit_pass_results.json</span>{" "}
                  and <span className="ptMono">orbit_pass_report.html</span>.
                </div>
                <JsonBox
                  key={`orbit:${JSON.stringify(orbitConfig || {})}`}
                  title="config (JSON)"
                  value={orbitConfig}
                  onApply={applyOrbitConfigText}
                  textareaClassName="ptTextarea"
                />
              </div>
            </div>
          </section>
        ) : (
          <section className="ptCanvas" aria-label="Run registry browser">
            <div style={{ padding: 14 }}>
              <div className="ptRightSection">
                <div className="ptRightTitle">Runs</div>
                <div className="ptHint">Select a run to load its manifest. Use Diff to compare the manifest inputs.</div>

                {runsIndex?.status === "idle" ? <div className="ptHint">Click Refresh to load runs from the API.</div> : null}
                {runsIndex?.status === "checking" ? <div className="ptHint">Loading...</div> : null}
                {runsIndex?.status === "error" ? <div className="ptError">{String(runsIndex?.error || "Failed to load runs.")}</div> : null}

                {runsIndex?.status === "ok" && Array.isArray(runsIndex?.runs) && runsIndex.runs.length ? (
                  <div className="ptPaletteGrid">
                    {runsIndex.runs.map((r) => {
                      const rid = String(r?.run_id || "");
                      if (!rid) return null;
                      const typ = String(r?.run_type || "run");
                      const pid = String(r?.project_id || "default");
                      const ts = r?.generated_at ? String(r.generated_at) : "";
                      const h = r?.input_hash ? String(r.input_hash) : "";
                      const hShort = h && h.length > 14 ? `${h.slice(0, 12)}...` : h;
                      const protocolSelected = String(r?.protocol_selected || "").trim();
                      const multifidelityPresent = Boolean(r?.multifidelity_present);
                      const selected = String(selectedRunId || "") === rid;

                      return (
                        <button
                          key={rid}
                          className="ptPaletteItem"
                          style={selected ? { borderColor: "rgba(46, 230, 214, 0.55)" } : null}
                          onClick={() => {
                            loadRunManifest(rid);
                            setActiveRightTab("manifest");
                            if (!diffLhsRunId) setDiffLhsRunId(rid);
                            else if (!diffRhsRunId && String(diffLhsRunId) !== rid) setDiffRhsRunId(rid);
                          }}
                        >
                          <div className="ptPaletteTitle">{typ}</div>
                          <div className="ptPaletteKind">{rid}</div>
                          {pid ? <div className="ptPaletteKind">{pid}</div> : null}
                          {ts ? <div className="ptPaletteKind">{ts}</div> : null}
                          {protocolSelected ? <div className="ptPaletteKind">protocol: {protocolSelected}</div> : null}
                          {hShort ? <div className="ptPaletteKind">input: {hShort}</div> : null}
                          {multifidelityPresent ? <div className="ptPaletteKind">multifidelity: present</div> : null}
                        </button>
                      );
                    })}
                  </div>
                ) : null}

                {runsIndex?.status === "ok" && (!Array.isArray(runsIndex?.runs) || !runsIndex.runs.length) ? <div className="ptHint">No runs found.</div> : null}
              </div>
            </div>
          </section>
        )}

        <aside className="ptSidebar ptSidebarRight">
          <div className="ptTabs">
            {mode === "graph" ? (
              <>
                <button className={`ptTab ${activeRightTab === "inspect" ? "active" : ""}`} onClick={() => setActiveRightTab("inspect")}>
                  Inspect
                </button>
                <button className={`ptTab ${activeRightTab === "compile" ? "active" : ""}`} onClick={() => setActiveRightTab("compile")}>
                  Compile
                </button>
                <button className={`ptTab ${activeRightTab === "run" ? "active" : ""}`} onClick={() => setActiveRightTab("run")}>
                  Run
                </button>
                {profile === "pic_circuit" ? (
                  <button className={`ptTab ${activeRightTab === "drc" ? "active" : ""}`} onClick={() => setActiveRightTab("drc")}>
                    DRC
                  </button>
                ) : null}
                {profile === "pic_circuit" ? (
                  <button className={`ptTab ${activeRightTab === "invdesign" ? "active" : ""}`} onClick={() => setActiveRightTab("invdesign")}>
                    InvDesign
                  </button>
                ) : null}
                {profile === "pic_circuit" ? (
                  <button className={`ptTab ${activeRightTab === "layout" ? "active" : ""}`} onClick={() => setActiveRightTab("layout")}>
                    Layout
                  </button>
                ) : null}
                {profile === "pic_circuit" ? (
                  <button className={`ptTab ${activeRightTab === "lvs" ? "active" : ""}`} onClick={() => setActiveRightTab("lvs")}>
                    LVS-lite
                  </button>
                ) : null}
                {profile === "pic_circuit" ? (
                  <button className={`ptTab ${activeRightTab === "klayout" ? "active" : ""}`} onClick={() => setActiveRightTab("klayout")}>
                    KLayout
                  </button>
                ) : null}
                {profile === "pic_circuit" ? (
                  <button className={`ptTab ${activeRightTab === "spice" ? "active" : ""}`} onClick={() => setActiveRightTab("spice")}>
                    SPICE
                  </button>
                ) : null}
                <button className={`ptTab ${activeRightTab === "graph" ? "active" : ""}`} onClick={() => setActiveRightTab("graph")}>
                  Graph JSON
                </button>
              </>
            ) : mode === "orbit" ? (
              <>
                <button className={`ptTab ${activeRightTab === "orbit" ? "active" : ""}`} onClick={() => setActiveRightTab("orbit")}>
                  Config
                </button>
                <button className={`ptTab ${activeRightTab === "validate" ? "active" : ""}`} onClick={() => setActiveRightTab("validate")}>
                  Validate
                </button>
                <button className={`ptTab ${activeRightTab === "run" ? "active" : ""}`} onClick={() => setActiveRightTab("run")}>
                  Run
                </button>
              </>
            ) : (
              <>
                <button className={`ptTab ${activeRightTab === "manifest" ? "active" : ""}`} onClick={() => setActiveRightTab("manifest")}>
                  Manifest
                </button>
                <button className={`ptTab ${activeRightTab === "diff" ? "active" : ""}`} onClick={() => setActiveRightTab("diff")}>
                  Diff
                </button>
              </>
            )}
          </div>

          {mode === "graph" && activeRightTab === "inspect" && (
            <div className="ptRightBody">
              <div className="ptRightSection">
                <div className="ptRightTitle">Selection</div>
                {selectedNode ? (
                  <>
                    <div className="ptKeyVal">
                      <div>id</div>
                      <div>{String(selectedNode.id)}</div>
                    </div>
                    <div className="ptKeyVal">
                      <div>kind</div>
                      <div>{String(selectedNode?.data?.kind)}</div>
                    </div>
                    <div className="ptKeyVal">
                      <div>label</div>
                      <div>{String(selectedNode?.data?.label || "")}</div>
                    </div>
                    <KindTrustPanel
                      kind={String(selectedNode?.data?.kind || "")}
                      kindMeta={kindRegistry?.byKind?.[String(selectedNode?.data?.kind || "")]}
                      params={selectedNode?.data?.params}
                      registryStatus={kindRegistry?.status}
                      onSetParam={setSelectedParamValue}
                    />
                    <div className="ptBtnRow">
                      <button className="ptBtn ptBtnGhost" onClick={deleteSelected}>
                        Delete node
                      </button>
                    </div>
                    <JsonBox
                      key={`params:${String(selectedNode.id)}:${JSON.stringify(selectedNode?.data?.params || {})}`}
                      title="params"
                      value={selectedNode?.data?.params}
                      onApply={applySelectedParams}
                    />
                  </>
                ) : (
                  <div className="ptHint">Click a node to edit its parameters.</div>
                )}
              </div>

              {profile === "qkd_link" ? (
                <div className="ptRightSection">
                  <div className="ptRightTitle">Scenario</div>
                  <label className="ptField">
                    <span>Band</span>
                    <select
                      value={String(scenario?.band || "c_1550")}
                      onChange={(e) => {
                        const b = String(e.target.value);
                        const opt = BAND_OPTIONS.find((x) => x.id === b);
                        const wl = b === "nir_795" ? 795 : b === "nir_850" ? 850 : b === "o_1310" ? 1310 : 1550;
                        setScenario((s) => ({ ...(s || {}), band: b, wavelength_nm: wl, id: s?.id || "ui_qkd_link" }));
                        _setStatus(`Scenario band: ${opt?.label || b}.`);
                      }}
                    >
                      {BAND_OPTIONS.map((b) => (
                        <option key={b.id} value={b.id}>
                          {b.label}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className="ptField">
                    <span>Distance (km)</span>
                    <input
                      value={String(scenario?.distance_km ?? 10)}
                      onChange={(e) => {
                        const v = Number(String(e.target.value));
                        setScenario((s) => ({ ...(s || {}), distance_km: Number.isFinite(v) ? v : 10, id: s?.id || "ui_qkd_link" }));
                      }}
                    />
                  </label>

                  <label className="ptField">
                    <span>Execution mode</span>
                    <select value={qkdExecutionMode} onChange={(e) => setQkdExecutionMode(String(e.target.value))}>
                      <option value="preview">preview</option>
                      <option value="certification">certification</option>
                    </select>
                  </label>

                  <JsonBox
                    key={`scenario:${JSON.stringify(scenario || {})}`}
                    title="scenario (advanced)"
                    value={scenario}
                    onApply={applyScenarioText}
                  />

                  <JsonBox
                    key={`uncertainty:${JSON.stringify(uncertainty || {})}`}
                    title="uncertainty (advanced)"
                    value={uncertainty}
                    onApply={applyUncertaintyText}
                  />

                  <JsonBox
                    key={`finite_key:${JSON.stringify(finiteKey || {})}`}
                    title="finite_key (advanced)"
                    value={finiteKey}
                    onApply={applyFiniteKeyText}
                  />
                </div>
              ) : (
                <div className="ptRightSection">
                  <div className="ptRightTitle">Circuit</div>
                  <label className="ptField">
                    <span>Wavelength (nm)</span>
                    <input
                      value={String(circuit?.wavelength_nm ?? 1550)}
                      onChange={(e) => {
                        const v = Number(String(e.target.value));
                        setCircuit((c) => ({ ...(c || {}), wavelength_nm: Number.isFinite(v) ? v : 1550, id: c?.id || "ui_pic_circuit" }));
                      }}
                    />
                  </label>

                  <label className="ptField ptFieldWide">
                    <span>Sweep nm (comma)</span>
                    <input value={picSweepNmText} onChange={(e) => setPicSweepNmText(String(e.target.value))} placeholder="1540, 1550, 1560" />
                  </label>

                  <JsonBox
                    key={`circuit:${JSON.stringify(circuit || {})}`}
                    title="circuit (advanced)"
                    value={circuit}
                    onApply={applyCircuitText}
                  />
                </div>
              )}

              {profile === "pic_circuit" ? (
                <div className="ptRightSection">
                  <div className="ptRightTitle">Performance DRC (Crosstalk)</div>

                  <label className="ptField ptFieldWide">
                    <span>Gap (um)</span>
                    <input
                      type="range"
                      min="0.2"
                      max="2.0"
                      step="0.01"
                      value={Number(xtGapUm)}
                      onChange={(e) => {
                        const v = Number(String(e.target.value));
                        const next = Number.isFinite(v) ? v : 0.6;
                        setXtGapUm(next);
                        if (xtLive && xtHasRunOnce.current) {
                          if (xtDebounceTimer.current) clearTimeout(xtDebounceTimer.current);
                          xtDebounceTimer.current = setTimeout(() => runCrosstalkDrc({ reason: "live" }), 140);
                        }
                      }}
                    />
                    <input
                      value={String(xtGapUm)}
                      onChange={(e) => {
                        const v = Number(String(e.target.value));
                        setXtGapUm(Number.isFinite(v) ? v : 0.6);
                      }}
                    />
                  </label>

                  <label className="ptField">
                    <span>Parallel length (um)</span>
                    <input
                      value={String(xtLengthUm)}
                      onChange={(e) => {
                        const v = Number(String(e.target.value));
                        setXtLengthUm(Number.isFinite(v) ? v : 1000.0);
                      }}
                    />
                  </label>

                  <label className="ptField">
                    <span>Target XT (dB)</span>
                    <input
                      value={String(xtTargetDb)}
                      onChange={(e) => {
                        const v = Number(String(e.target.value));
                        setXtTargetDb(Number.isFinite(v) ? v : -40.0);
                      }}
                    />
                  </label>

                  <label className="ptCheck">
                    <input type="checkbox" checked={xtLive} onChange={(e) => setXtLive(Boolean(e.target.checked))} />
                    <span>Live update (after first run)</span>
                  </label>

                  <div className="ptBtnRow">
                    <button className="ptBtn ptBtnPrimary" onClick={() => runCrosstalkDrc({ reason: "manual" })} disabled={busy}>
                      Run Crosstalk DRC
                    </button>
                  </div>
                </div>
              ) : null}

              {profile === "pic_circuit" ? (
                <div className="ptRightSection">
                  <div className="ptRightTitle">Inverse Design</div>

                  <label className="ptField">
                    <span>Kind</span>
                    <select value={String(invKind || "mzi_phase")} onChange={(e) => setInvKind(String(e.target.value))}>
                      <option value="mzi_phase">MZI Phase (tune phase_rad)</option>
                      <option value="coupler_ratio">Coupler Ratio (tune coupling_ratio)</option>
                    </select>
                  </label>

                  {invKind === "mzi_phase" ? (
                    phaseNodeIds.length ? (
                      <label className="ptField">
                        <span>Phase node</span>
                        <select value={String(invPhaseNodeId || "")} onChange={(e) => setInvPhaseNodeId(String(e.target.value))}>
                          {phaseNodeIds.map((nid) => (
                            <option key={nid} value={nid}>
                              {nid}
                            </option>
                          ))}
                        </select>
                      </label>
                    ) : (
                      <div className="ptHint">
                        Add a <span className="ptMono">pic.phase_shifter</span> node to enable inverse design.
                      </div>
                    )
                  ) : couplerNodeIds.length ? (
                    <label className="ptField">
                      <span>Coupler node</span>
                      <select value={String(invCouplerNodeId || "")} onChange={(e) => setInvCouplerNodeId(String(e.target.value))}>
                        {couplerNodeIds.map((nid) => (
                          <option key={nid} value={nid}>
                            {nid}
                          </option>
                        ))}
                      </select>
                    </label>
                  ) : (
                    <div className="ptHint">
                      Add a <span className="ptMono">pic.coupler</span> node to enable inverse design.
                    </div>
                  )}

                  <label className="ptField">
                    <span>Target output node</span>
                    <input value={String(invOutputNode || "")} onChange={(e) => setInvOutputNode(String(e.target.value))} placeholder="cpl_out" />
                  </label>

                  <label className="ptField">
                    <span>Target output port</span>
                    <input value={String(invOutputPort || "")} onChange={(e) => setInvOutputPort(String(e.target.value))} placeholder="out1" />
                  </label>

                  <label className="ptField ptFieldWide">
                    <span>Target power fraction</span>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.01"
                      value={Number(invTargetFraction)}
                      onChange={(e) => {
                        const v = Number(String(e.target.value));
                        setInvTargetFraction(Number.isFinite(v) ? v : 0.9);
                      }}
                    />
                    <input
                      value={String(invTargetFraction)}
                      onChange={(e) => {
                        const v = Number(String(e.target.value));
                        setInvTargetFraction(Number.isFinite(v) ? v : 0.9);
                      }}
                    />
                  </label>

                  <label className="ptField">
                    <span>Wavelength objective</span>
                    <select value={String(invWavelengthObjectiveAgg || "mean")} onChange={(e) => setInvWavelengthObjectiveAgg(String(e.target.value))}>
                      <option value="mean">mean</option>
                      <option value="max">max (worst-case)</option>
                    </select>
                  </label>

                  <label className="ptField">
                    <span>Case objective</span>
                    <select value={String(invCaseObjectiveAgg || "mean")} onChange={(e) => setInvCaseObjectiveAgg(String(e.target.value))}>
                      <option value="mean">mean</option>
                      <option value="max">max (worst-case)</option>
                    </select>
                  </label>

                  <JsonBox
                    key={`inv_robust_cases:${JSON.stringify(invRobustnessCases || [])}`}
                    title="robustness cases (advanced)"
                    value={invRobustnessCases}
                    onApply={(text) => {
                      const parsed = _safeParseJson(text);
                      if (!parsed.ok) return parsed;
                      if (!Array.isArray(parsed.value)) return { ok: false, error: "Robustness cases must be a JSON array." };
                      setInvRobustnessCases(parsed.value);
                      return { ok: true };
                    }}
                  />

                  <div className="ptBtnRow">
                    <button
                      className="ptBtn ptBtnPrimary"
                      onClick={runInvdesign}
                      disabled={busy || (invKind === "coupler_ratio" ? !couplerNodeIds.length : !phaseNodeIds.length)}
                    >
                      Run Inverse Design
                    </button>
                    <button
                      className="ptBtn"
                      onClick={runInvdesignWorkflow}
                      disabled={busy || (invKind === "coupler_ratio" ? !couplerNodeIds.length : !phaseNodeIds.length)}
                      title="Runs: invdesign -> layout build -> LVS-lite -> (optional) KLayout pack -> SPICE export"
                    >
                      Run Full Workflow
                    </button>
                  </div>
                </div>
              ) : null}

              <div className="ptRightSection">
                <div className="ptRightTitle">Metadata</div>
                <label className="ptField">
                  <span>Title</span>
                  <input value={String(metadata?.title || "")} onChange={(e) => setMetadata((m) => ({ ...(m || {}), title: String(e.target.value) }))} />
                </label>
                <label className="ptField">
                  <span>Description</span>
                  <input value={String(metadata?.description || "")} onChange={(e) => setMetadata((m) => ({ ...(m || {}), description: String(e.target.value) }))} />
                </label>
              </div>
            </div>
          )}

          {mode === "graph" && activeRightTab === "compile" && (
            <div className="ptRightBody">
              <div className="ptRightSection">
                <div className="ptRightTitle">Compile Result</div>
                {compileResult?.assumptions_md ? (
                  <pre className="ptPre">{String(compileResult.assumptions_md)}</pre>
                ) : (
                  <div className="ptHint">Compile to see assumptions, compiled artifacts, and provenance.</div>
                )}
                {compileResult?.diagnostics?.errors?.length ? (
                  <div className="ptError">
                    <div className="ptCalloutTitle">Diagnostics (errors)</div>
                    <ul className="ptList">
                      {compileResult.diagnostics.errors.map((d, idx) => (
                        <li key={idx}>
                          <span className="ptMono">{String(d.code || "error")}</span>: {String(d.message || "")}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                {compileResult?.diagnostics?.warnings?.length ? (
                  <div className="ptCallout">
                    <div className="ptCalloutTitle">Diagnostics (warnings)</div>
                    <ul className="ptList">
                      {compileResult.diagnostics.warnings.map((d, idx) => (
                        <li key={idx}>
                          <span className="ptMono">{String(d.code || "warn")}</span>: {String(d.message || "")}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                {compileResult?.warnings?.length ? (
                  <div className="ptCallout">
                    <div className="ptCalloutTitle">Warnings</div>
                    <ul className="ptList">
                      {compileResult.warnings.map((w, idx) => (
                        <li key={idx}>{String(w)}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                {compileResult ? <pre className="ptPre">{_pretty(compileResult)}</pre> : null}
              </div>
            </div>
          )}

          {mode !== "runs" && activeRightTab === "run" && (
            <div className="ptRightBody">
              <div className="ptRightSection">
                <div className="ptRightTitle">Run Result</div>
                {mode === "orbit" && runResult?.results_path ? (
                  <div className="ptHint">
                    results: <span className="ptMono">{String(runResult.results_path)}</span>
                    <br />
                    report: <span className="ptMono">{String(runResult.report_html_path || "")}</span>
                  </div>
                ) : null}
                {mode === "orbit" && runResult?.run_id ? (
                  <div className="ptCallout">
                    <div className="ptCalloutTitle">Artifacts (served)</div>
                    <div className="ptHint">
                      {runResult?.artifact_relpaths?.orbit_pass_report_html ? (
                        <>
                          <a
                            href={_runArtifactUrl(apiBase, runResult.run_id, runResult.artifact_relpaths.orbit_pass_report_html)}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Open report (HTML)
                          </a>{" "}
                          <span className="ptMono">[{String(runResult.artifact_relpaths.orbit_pass_report_html)}]</span>
                          <br />
                        </>
                      ) : null}
                      {runResult?.artifact_relpaths?.orbit_pass_results_json ? (
                        <>
                          <a
                            href={_runArtifactUrl(apiBase, runResult.run_id, runResult.artifact_relpaths.orbit_pass_results_json)}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Open results (JSON)
                          </a>{" "}
                          <span className="ptMono">[{String(runResult.artifact_relpaths.orbit_pass_results_json)}]</span>
                          <br />
                        </>
                      ) : null}
                      <a href={_runManifestUrl(apiBase, runResult.run_id)} target="_blank" rel="noreferrer">
                        Open run manifest (JSON)
                      </a>
                    </div>
                  </div>
                ) : null}
                {mode === "orbit" && runResult?.diagnostics?.errors?.length ? (
                  <div className="ptError">
                    <div className="ptCalloutTitle">Diagnostics (errors)</div>
                    <ul className="ptList">
                      {runResult.diagnostics.errors.map((d, idx) => (
                        <li key={idx}>
                          <span className="ptMono">{String(d.code || "error")}</span>: {String(d.message || "")}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                {mode === "orbit" && runResult?.diagnostics?.warnings?.length ? (
                  <div className="ptCallout">
                    <div className="ptCalloutTitle">Diagnostics (warnings)</div>
                    <ul className="ptList">
                      {runResult.diagnostics.warnings.map((d, idx) => (
                        <li key={idx}>
                          <span className="ptMono">{String(d.code || "warn")}</span>: {String(d.message || "")}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                {runResult ? <pre className="ptPre">{_pretty(runResult)}</pre> : <div className="ptHint">Run to see outputs.</div>}
              </div>
            </div>
          )}

          {mode === "graph" && activeRightTab === "drc" && (
            <div className="ptRightBody">
              <div className="ptRightSection">
                <div className="ptRightTitle">Performance DRC Result</div>
                {xtResult?.run_id && xtResult?.artifact_relpaths ? (
                  <div className="ptCallout">
                    <div className="ptCalloutTitle">Artifacts (served)</div>
                    <div className="ptHint">
                      {xtResult?.artifact_relpaths?.performance_drc_report_html ? (
                        <>
                          <a
                            href={_runArtifactUrl(apiBase, xtResult.run_id, xtResult.artifact_relpaths.performance_drc_report_html)}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Open report (HTML)
                          </a>{" "}
                          <span className="ptMono">[{String(xtResult.artifact_relpaths.performance_drc_report_html)}]</span>
                          <br />
                        </>
                      ) : null}
                      {xtResult?.artifact_relpaths?.performance_drc_report_json ? (
                        <>
                          <a
                            href={_runArtifactUrl(apiBase, xtResult.run_id, xtResult.artifact_relpaths.performance_drc_report_json)}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Open report (JSON)
                          </a>{" "}
                          <span className="ptMono">[{String(xtResult.artifact_relpaths.performance_drc_report_json)}]</span>
                          <br />
                        </>
                      ) : null}
                      <a href={_runManifestUrl(apiBase, xtResult.run_id)} target="_blank" rel="noreferrer">
                        Open run manifest (JSON)
                      </a>
                    </div>
                  </div>
                ) : null}
                {xtResult ? <pre className="ptPre">{_pretty(xtResult)}</pre> : <div className="ptHint">Run DRC to see outputs.</div>}
              </div>
            </div>
          )}

          {mode === "graph" && activeRightTab === "invdesign" && (
            <div className="ptRightBody">
              <div className="ptRightSection">
                <div className="ptRightTitle">Inverse Design Result</div>
                {invResult?.run_id && invResult?.artifact_relpaths ? (
                  <div className="ptCallout">
                    <div className="ptCalloutTitle">Artifacts (served)</div>
                    <div className="ptHint">
                      {invResult?.artifact_relpaths?.invdesign_report_json ? (
                        <>
                          <a
                            href={_runArtifactUrl(apiBase, invResult.run_id, invResult.artifact_relpaths.invdesign_report_json)}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Open report (JSON)
                          </a>{" "}
                          <span className="ptMono">[{String(invResult.artifact_relpaths.invdesign_report_json)}]</span>
                          <br />
                        </>
                      ) : null}
                      {invResult?.artifact_relpaths?.optimized_graph_json ? (
                        <>
                          <a
                            href={_runArtifactUrl(apiBase, invResult.run_id, invResult.artifact_relpaths.optimized_graph_json)}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Open optimized graph (JSON)
                          </a>{" "}
                          <span className="ptMono">[{String(invResult.artifact_relpaths.optimized_graph_json)}]</span>
                          <br />
                        </>
                      ) : null}
                      <a href={_runManifestUrl(apiBase, invResult.run_id)} target="_blank" rel="noreferrer">
                        Open run manifest (JSON)
                      </a>
                    </div>
                  </div>
                ) : null}
                {invResult ? <pre className="ptPre">{_pretty(invResult)}</pre> : <div className="ptHint">Run inverse design to see outputs.</div>}
              </div>

              <div className="ptRightSection">
                <div className="ptRightTitle">Workflow Chain Result</div>
                {workflowResult?.run_id && workflowResult?.artifact_relpaths ? (
                  <div className="ptCallout">
                    <div className="ptCalloutTitle">Artifacts (served)</div>
                    <div className="ptHint">
                      {workflowResult?.artifact_relpaths?.workflow_report_json ? (
                        <>
                      <a
                        href={_runArtifactUrl(apiBase, workflowResult.run_id, workflowResult.artifact_relpaths.workflow_report_json)}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Open workflow report (JSON)
                      </a>{" "}
                      <span className="ptMono">[{String(workflowResult.artifact_relpaths.workflow_report_json)}]</span>
                      <br />
                    </>
                  ) : null}
                  {workflowResult?.run_id ? (
                    <>
                      <a href={_runBundleUrl(apiBase, workflowResult.run_id)} target="_blank" rel="noreferrer">
                        Download evidence bundle (zip)
                      </a>
                      <br />
                    </>
                  ) : null}
                  <a href={_runManifestUrl(apiBase, workflowResult.run_id)} target="_blank" rel="noreferrer">
                    Open workflow run manifest (JSON)
                  </a>
                  <br />
                      {workflowResult?.steps?.invdesign?.run_id ? (
                        <>
                          <a href={_runManifestUrl(apiBase, workflowResult.steps.invdesign.run_id)} target="_blank" rel="noreferrer">
                            Open invdesign child run manifest (JSON)
                          </a>
                          <br />
                        </>
                      ) : null}
                      {workflowResult?.steps?.layout_build?.run_id ? (
                        <>
                          <a href={_runManifestUrl(apiBase, workflowResult.steps.layout_build.run_id)} target="_blank" rel="noreferrer">
                            Open layout build child run manifest (JSON)
                          </a>
                          <br />
                        </>
                      ) : null}
                      {workflowResult?.steps?.lvs_lite?.run_id ? (
                        <>
                          <a href={_runManifestUrl(apiBase, workflowResult.steps.lvs_lite.run_id)} target="_blank" rel="noreferrer">
                            Open LVS-lite child run manifest (JSON)
                          </a>
                          <br />
                        </>
                      ) : null}
                      {workflowResult?.steps?.klayout_pack?.run_id ? (
                        <>
                          <a href={_runManifestUrl(apiBase, workflowResult.steps.klayout_pack.run_id)} target="_blank" rel="noreferrer">
                            Open KLayout child run manifest (JSON)
                          </a>
                          <br />
                        </>
                      ) : null}
                      {workflowResult?.steps?.spice_export?.run_id ? (
                        <>
                          <a href={_runManifestUrl(apiBase, workflowResult.steps.spice_export.run_id)} target="_blank" rel="noreferrer">
                            Open SPICE export child run manifest (JSON)
                          </a>
                          <br />
                        </>
                      ) : null}
                    </div>
                  </div>
                ) : null}
                {workflowResult ? <pre className="ptPre">{_pretty(workflowResult)}</pre> : <div className="ptHint">Run full workflow to see chained evidence.</div>}
              </div>
            </div>
          )}

          {mode === "graph" && activeRightTab === "layout" && (
            <div className="ptRightBody">
              <div className="ptRightSection">
                <div className="ptRightTitle">Layout Build</div>

                <JsonBox
                  key={`layout_pdk:${JSON.stringify(layoutPdk || {})}`}
                  title="pdk (advanced)"
                  value={layoutPdk}
                  onApply={(text) => {
                    const parsed = _safeParseJson(text);
                    if (!parsed.ok) return parsed;
                    if (!parsed.value || typeof parsed.value !== "object" || Array.isArray(parsed.value)) return { ok: false, error: "PDK must be a JSON object." };
                    setLayoutPdk(parsed.value);
                    return { ok: true };
                  }}
                />

                <JsonBox
                  key={`layout_settings:${JSON.stringify(layoutSettings || {})}`}
                  title="layout settings (advanced)"
                  value={layoutSettings}
                  onApply={(text) => {
                    const parsed = _safeParseJson(text);
                    if (!parsed.ok) return parsed;
                    if (!parsed.value || typeof parsed.value !== "object" || Array.isArray(parsed.value)) return { ok: false, error: "Settings must be a JSON object." };
                    setLayoutSettings(parsed.value);
                    return { ok: true };
                  }}
                />

                <div className="ptBtnRow">
                  <button className="ptBtn ptBtnPrimary" onClick={runLayoutBuild} disabled={busy}>
                    Build Layout Artifacts
                  </button>
                </div>
                <div className="ptHint">
                  Emits <span className="ptMono">ports.json</span> + <span className="ptMono">routes.json</span> always.{" "}
                  <span className="ptMono">layout.gds</span> is emitted only when <span className="ptMono">gdstk</span> is installed.
                </div>
              </div>

              <div className="ptRightSection">
                <div className="ptRightTitle">Layout Build Result</div>
                {layoutBuildResult?.run_id && layoutBuildResult?.artifact_relpaths ? (
                  <div className="ptCallout">
                    <div className="ptCalloutTitle">Artifacts (served)</div>
                    <div className="ptHint">
                      {layoutBuildResult?.artifact_relpaths?.layout_build_report_json ? (
                        <>
                          <a
                            href={_runArtifactUrl(apiBase, layoutBuildResult.run_id, layoutBuildResult.artifact_relpaths.layout_build_report_json)}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Open layout report (JSON)
                          </a>{" "}
                          <span className="ptMono">[{String(layoutBuildResult.artifact_relpaths.layout_build_report_json)}]</span>
                          <br />
                        </>
                      ) : null}
                      {layoutBuildResult?.artifact_relpaths?.ports_json ? (
                        <>
                          <a
                            href={_runArtifactUrl(apiBase, layoutBuildResult.run_id, layoutBuildResult.artifact_relpaths.ports_json)}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Open ports (JSON)
                          </a>{" "}
                          <span className="ptMono">[{String(layoutBuildResult.artifact_relpaths.ports_json)}]</span>
                          <br />
                        </>
                      ) : null}
                      {layoutBuildResult?.artifact_relpaths?.routes_json ? (
                        <>
                          <a
                            href={_runArtifactUrl(apiBase, layoutBuildResult.run_id, layoutBuildResult.artifact_relpaths.routes_json)}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Open routes (JSON)
                          </a>{" "}
                          <span className="ptMono">[{String(layoutBuildResult.artifact_relpaths.routes_json)}]</span>
                          <br />
                        </>
                      ) : null}
                      {layoutBuildResult?.artifact_relpaths?.layout_provenance_json ? (
                        <>
                          <a
                            href={_runArtifactUrl(apiBase, layoutBuildResult.run_id, layoutBuildResult.artifact_relpaths.layout_provenance_json)}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Open provenance (JSON)
                          </a>{" "}
                          <span className="ptMono">[{String(layoutBuildResult.artifact_relpaths.layout_provenance_json)}]</span>
                          <br />
                        </>
                      ) : null}
                      {layoutBuildResult?.artifact_relpaths?.layout_gds ? (
                        <>
                          <a
                            href={_runArtifactUrl(apiBase, layoutBuildResult.run_id, layoutBuildResult.artifact_relpaths.layout_gds)}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Open layout (GDS)
                          </a>{" "}
                          <span className="ptMono">[{String(layoutBuildResult.artifact_relpaths.layout_gds)}]</span>
                          <br />
                        </>
                      ) : null}
                      <a href={_runManifestUrl(apiBase, layoutBuildResult.run_id)} target="_blank" rel="noreferrer">
                        Open run manifest (JSON)
                      </a>
                    </div>
                  </div>
                ) : null}
                {layoutBuildResult ? <pre className="ptPre">{_pretty(layoutBuildResult)}</pre> : <div className="ptHint">Build to see outputs.</div>}
              </div>
            </div>
          )}

          {mode === "graph" && activeRightTab === "lvs" && (
            <div className="ptRightBody">
              <div className="ptRightSection">
                <div className="ptRightTitle">LVS-lite</div>

                <JsonBox
                  key={`lvs_settings:${JSON.stringify(lvsSettings || {})}`}
                  title="lvs settings (advanced)"
                  value={lvsSettings}
                  onApply={(text) => {
                    const parsed = _safeParseJson(text);
                    if (!parsed.ok) return parsed;
                    if (!parsed.value || typeof parsed.value !== "object" || Array.isArray(parsed.value)) return { ok: false, error: "Settings must be a JSON object." };
                    setLvsSettings(parsed.value);
                    return { ok: true };
                  }}
                />

                <div className="ptBtnRow">
                  <button className="ptBtn ptBtnPrimary" onClick={runLvsLite} disabled={busy || !layoutBuildResult?.run_id}>
                    Run LVS-lite (uses last Layout run)
                  </button>
                </div>
                {!layoutBuildResult?.run_id ? <div className="ptHint">Run <span className="ptMono">Layout</span> build first to generate ports/routes.</div> : null}
              </div>

              <div className="ptRightSection">
                <div className="ptRightTitle">LVS-lite Result</div>
                {lvsResult?.run_id && lvsResult?.artifact_relpaths ? (
                  <div className="ptCallout">
                    <div className="ptCalloutTitle">Artifacts (served)</div>
                    <div className="ptHint">
                      {lvsResult?.artifact_relpaths?.lvs_lite_report_json ? (
                        <>
                          <a
                            href={_runArtifactUrl(apiBase, lvsResult.run_id, lvsResult.artifact_relpaths.lvs_lite_report_json)}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Open LVS-lite report (JSON)
                          </a>{" "}
                          <span className="ptMono">[{String(lvsResult.artifact_relpaths.lvs_lite_report_json)}]</span>
                          <br />
                        </>
                      ) : null}
                      <a href={_runManifestUrl(apiBase, lvsResult.run_id)} target="_blank" rel="noreferrer">
                        Open run manifest (JSON)
                      </a>
                    </div>
                  </div>
                ) : null}
                {lvsResult ? <pre className="ptPre">{_pretty(lvsResult)}</pre> : <div className="ptHint">Run LVS-lite to see mismatches.</div>}
              </div>
            </div>
          )}

          {mode === "graph" && activeRightTab === "klayout" && (
            <div className="ptRightBody">
              <div className="ptRightSection">
                <div className="ptRightTitle">KLayout Artifact Pack (DRC-lite)</div>

                <JsonBox
                  key={`klayout_pack_settings:${JSON.stringify(klayoutPackSettings || {})}`}
                  title="klayout pack settings (advanced)"
                  value={klayoutPackSettings}
                  onApply={(text) => {
                    const parsed = _safeParseJson(text);
                    if (!parsed.ok) return parsed;
                    if (!parsed.value || typeof parsed.value !== "object" || Array.isArray(parsed.value)) return { ok: false, error: "Settings must be a JSON object." };
                    setKlayoutPackSettings(parsed.value);
                    return { ok: true };
                  }}
                />

                <div className="ptBtnRow">
                  <button
                    className="ptBtn ptBtnPrimary"
                    onClick={runKlayoutPack}
                    disabled={busy || !layoutBuildResult?.run_id || !layoutBuildResult?.artifact_relpaths?.layout_gds}
                  >
                    Run KLayout Pack (uses last Layout run)
                  </button>
                </div>
                {!layoutBuildResult?.run_id ? (
                  <div className="ptHint">
                    Run <span className="ptMono">Layout</span> build first to create a layout run.
                  </div>
                ) : null}
                {layoutBuildResult?.run_id && !layoutBuildResult?.artifact_relpaths?.layout_gds ? (
                  <div className="ptHint">
                    This environment did not emit <span className="ptMono">layout.gds</span>. Install <span className="ptMono">gdstk</span> (e.g.{" "}
                    <span className="ptMono">pip install 'photonstrust[layout]'</span>) and rebuild layout.
                  </div>
                ) : null}
                <div className="ptHint">
                  Runs the repo-owned KLayout macro template in batch mode and captures stdout/stderr + output hashes as a reviewable artifact pack.
                </div>
              </div>

              <div className="ptRightSection">
                <div className="ptRightTitle">KLayout Pack Result</div>
                {klayoutPackResult?.run_id && klayoutPackResult?.artifact_relpaths ? (
                  <div className="ptCallout">
                    <div className="ptCalloutTitle">Artifacts (served)</div>
                    <div className="ptHint">
                      {klayoutPackResult?.artifact_relpaths?.klayout_run_artifact_pack_json ? (
                        <>
                          <a
                            href={_runArtifactUrl(apiBase, klayoutPackResult.run_id, klayoutPackResult.artifact_relpaths.klayout_run_artifact_pack_json)}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Open artifact pack (JSON)
                          </a>{" "}
                          <span className="ptMono">[{String(klayoutPackResult.artifact_relpaths.klayout_run_artifact_pack_json)}]</span>
                          <br />
                        </>
                      ) : null}
                      {klayoutPackResult?.artifact_relpaths?.drc_lite_json ? (
                        <>
                          <a
                            href={_runArtifactUrl(apiBase, klayoutPackResult.run_id, klayoutPackResult.artifact_relpaths.drc_lite_json)}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Open DRC-lite report (JSON)
                          </a>{" "}
                          <span className="ptMono">[{String(klayoutPackResult.artifact_relpaths.drc_lite_json)}]</span>
                          <br />
                        </>
                      ) : null}
                      {klayoutPackResult?.artifact_relpaths?.ports_extracted_json ? (
                        <>
                          <a
                            href={_runArtifactUrl(apiBase, klayoutPackResult.run_id, klayoutPackResult.artifact_relpaths.ports_extracted_json)}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Open extracted ports (JSON)
                          </a>{" "}
                          <span className="ptMono">[{String(klayoutPackResult.artifact_relpaths.ports_extracted_json)}]</span>
                          <br />
                        </>
                      ) : null}
                      {klayoutPackResult?.artifact_relpaths?.routes_extracted_json ? (
                        <>
                          <a
                            href={_runArtifactUrl(apiBase, klayoutPackResult.run_id, klayoutPackResult.artifact_relpaths.routes_extracted_json)}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Open extracted routes (JSON)
                          </a>{" "}
                          <span className="ptMono">[{String(klayoutPackResult.artifact_relpaths.routes_extracted_json)}]</span>
                          <br />
                        </>
                      ) : null}
                      {klayoutPackResult?.artifact_relpaths?.macro_provenance_json ? (
                        <>
                          <a
                            href={_runArtifactUrl(apiBase, klayoutPackResult.run_id, klayoutPackResult.artifact_relpaths.macro_provenance_json)}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Open macro provenance (JSON)
                          </a>{" "}
                          <span className="ptMono">[{String(klayoutPackResult.artifact_relpaths.macro_provenance_json)}]</span>
                          <br />
                        </>
                      ) : null}
                      {klayoutPackResult?.artifact_relpaths?.klayout_stdout_txt ? (
                        <>
                          <a
                            href={_runArtifactUrl(apiBase, klayoutPackResult.run_id, klayoutPackResult.artifact_relpaths.klayout_stdout_txt)}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Open stdout (txt)
                          </a>{" "}
                          <span className="ptMono">[{String(klayoutPackResult.artifact_relpaths.klayout_stdout_txt)}]</span>
                          <br />
                        </>
                      ) : null}
                      {klayoutPackResult?.artifact_relpaths?.klayout_stderr_txt ? (
                        <>
                          <a
                            href={_runArtifactUrl(apiBase, klayoutPackResult.run_id, klayoutPackResult.artifact_relpaths.klayout_stderr_txt)}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Open stderr (txt)
                          </a>{" "}
                          <span className="ptMono">[{String(klayoutPackResult.artifact_relpaths.klayout_stderr_txt)}]</span>
                          <br />
                        </>
                      ) : null}
                      <a href={_runManifestUrl(apiBase, klayoutPackResult.run_id)} target="_blank" rel="noreferrer">
                        Open run manifest (JSON)
                      </a>
                    </div>
                  </div>
                ) : null}
                {klayoutPackResult ? <pre className="ptPre">{_pretty(klayoutPackResult)}</pre> : <div className="ptHint">Run KLayout pack to see outputs.</div>}
              </div>
            </div>
          )}

          {mode === "graph" && activeRightTab === "spice" && (
            <div className="ptRightBody">
              <div className="ptRightSection">
                <div className="ptRightTitle">SPICE Export</div>

                <JsonBox
                  key={`spice_settings:${JSON.stringify(spiceSettings || {})}`}
                  title="spice settings (advanced)"
                  value={spiceSettings}
                  onApply={(text) => {
                    const parsed = _safeParseJson(text);
                    if (!parsed.ok) return parsed;
                    if (!parsed.value || typeof parsed.value !== "object" || Array.isArray(parsed.value)) return { ok: false, error: "Settings must be a JSON object." };
                    setSpiceSettings(parsed.value);
                    return { ok: true };
                  }}
                />

                <div className="ptBtnRow">
                  <button className="ptBtn ptBtnPrimary" onClick={runSpiceExport} disabled={busy}>
                    Export SPICE Netlist
                  </button>
                </div>
                <div className="ptHint">This is a deterministic connectivity export and mapping seam (not optical-physics signoff).</div>
              </div>

              <div className="ptRightSection">
                <div className="ptRightTitle">SPICE Export Result</div>
                {spiceResult?.run_id && spiceResult?.artifact_relpaths ? (
                  <div className="ptCallout">
                    <div className="ptCalloutTitle">Artifacts (served)</div>
                    <div className="ptHint">
                      {spiceResult?.artifact_relpaths?.spice_export_report_json ? (
                        <>
                          <a
                            href={_runArtifactUrl(apiBase, spiceResult.run_id, spiceResult.artifact_relpaths.spice_export_report_json)}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Open export report (JSON)
                          </a>{" "}
                          <span className="ptMono">[{String(spiceResult.artifact_relpaths.spice_export_report_json)}]</span>
                          <br />
                        </>
                      ) : null}
                      {spiceResult?.artifact_relpaths?.netlist_sp ? (
                        <>
                          <a
                            href={_runArtifactUrl(apiBase, spiceResult.run_id, spiceResult.artifact_relpaths.netlist_sp)}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Open netlist (SPICE)
                          </a>{" "}
                          <span className="ptMono">[{String(spiceResult.artifact_relpaths.netlist_sp)}]</span>
                          <br />
                        </>
                      ) : null}
                      {spiceResult?.artifact_relpaths?.spice_map_json ? (
                        <>
                          <a
                            href={_runArtifactUrl(apiBase, spiceResult.run_id, spiceResult.artifact_relpaths.spice_map_json)}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Open mapping (JSON)
                          </a>{" "}
                          <span className="ptMono">[{String(spiceResult.artifact_relpaths.spice_map_json)}]</span>
                          <br />
                        </>
                      ) : null}
                      {spiceResult?.artifact_relpaths?.spice_provenance_json ? (
                        <>
                          <a
                            href={_runArtifactUrl(apiBase, spiceResult.run_id, spiceResult.artifact_relpaths.spice_provenance_json)}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Open provenance (JSON)
                          </a>{" "}
                          <span className="ptMono">[{String(spiceResult.artifact_relpaths.spice_provenance_json)}]</span>
                          <br />
                        </>
                      ) : null}
                      <a href={_runManifestUrl(apiBase, spiceResult.run_id)} target="_blank" rel="noreferrer">
                        Open run manifest (JSON)
                      </a>
                    </div>
                  </div>
                ) : null}
                {spiceResult ? <pre className="ptPre">{_pretty(spiceResult)}</pre> : <div className="ptHint">Export to see netlist + mapping.</div>}
              </div>
            </div>
          )}

          {mode === "graph" && activeRightTab === "graph" && (
            <div className="ptRightBody">
              <div className="ptRightSection">
                <div className="ptRightTitle">Graph Payload</div>
                <pre className="ptPre">{exportText}</pre>
                <div className="ptBtnRow">
                  <button
                    className="ptBtn ptBtnGhost"
                    onClick={async () => {
                      try {
                        await navigator.clipboard.writeText(exportText);
                        _setStatus("Copied graph JSON to clipboard.");
                      } catch (err) {
                        _setStatus(`Copy failed: ${String(err?.message || err)}`);
                      }
                    }}
                  >
                    Copy
                  </button>
                </div>
              </div>
            </div>
          )}

          {mode === "orbit" && activeRightTab === "validate" && (
            <div className="ptRightBody">
              <div className="ptRightSection">
                <div className="ptRightTitle">Orbit Config Validation</div>
                {orbitValidateResult?.diagnostics?.errors?.length ? (
                  <div className="ptError">
                    <div className="ptCalloutTitle">Diagnostics (errors)</div>
                    <ul className="ptList">
                      {orbitValidateResult.diagnostics.errors.map((d, idx) => (
                        <li key={idx}>
                          <span className="ptMono">{String(d.code || "error")}</span>: {String(d.message || "")}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                {orbitValidateResult?.diagnostics?.warnings?.length ? (
                  <div className="ptCallout">
                    <div className="ptCalloutTitle">Diagnostics (warnings)</div>
                    <ul className="ptList">
                      {orbitValidateResult.diagnostics.warnings.map((d, idx) => (
                        <li key={idx}>
                          <span className="ptMono">{String(d.code || "warn")}</span>: {String(d.message || "")}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                {orbitValidateResult ? (
                  <pre className="ptPre">{_pretty(orbitValidateResult)}</pre>
                ) : (
                  <div className="ptHint">Click Validate to run schema and semantic checks.</div>
                )}
              </div>
            </div>
          )}

          {mode === "orbit" && activeRightTab === "orbit" && (
            <div className="ptRightBody">
              <div className="ptRightSection">
                <div className="ptRightTitle">Orbit Config (JSON)</div>
                <pre className="ptPre">{_pretty(orbitConfig)}</pre>
                <div className="ptBtnRow">
                  <button
                    className="ptBtn ptBtnGhost"
                    onClick={async () => {
                      try {
                        await navigator.clipboard.writeText(_pretty(orbitConfig));
                        _setStatus("Copied orbit config JSON to clipboard.");
                      } catch (err) {
                        _setStatus(`Copy failed: ${String(err?.message || err)}`);
                      }
                    }}
                  >
                    Copy
                  </button>
                </div>
              </div>
            </div>
          )}

          {mode === "runs" && activeRightTab === "manifest" && (
            <div className="ptRightBody">
              <div className="ptRightSection">
                <div className="ptRightTitle">Run Manifest</div>
                {selectedRunManifest?.run_id ? (
                  <div className="ptHint">
                    run_id: <span className="ptMono">{String(selectedRunManifest.run_id)}</span>
                    <br />
                    run_type: <span className="ptMono">{String(selectedRunManifest.run_type || "")}</span>
                    <br />
                    generated_at: <span className="ptMono">{String(selectedRunManifest.generated_at || "")}</span>
                    <br />
                    project_id: <span className="ptMono">{String(selectedRunManifest?.input?.project_id || "default")}</span>
                    <br />
                    protocol: <span className="ptMono">{String(selectedRunManifest?.input?.protocol_selected || selectedRunManifest?.outputs_summary?.qkd?.protocol_selected || "")}</span>
                    <br />
                    multifidelity: <span className="ptMono">{String(selectedRunManifest?.outputs_summary?.qkd?.multifidelity?.present ? "present" : "absent")}</span>
                  </div>
                ) : (
                  <div className="ptHint">Select a run from the Runs list to load its manifest.</div>
                )}

                {selectedRunManifest?.run_id ? (
                  <div className="ptCallout" style={{ marginTop: 10 }}>
                    <div className="ptCalloutTitle">Approvals</div>
                    <div className="ptHint">Append-only approval events are stored per project.</div>

                    <label className="ptField" style={{ marginTop: 10 }}>
                      <span>actor</span>
                      <input value={approvalActor} onChange={(e) => setApprovalActor(String(e.target.value))} placeholder="ui" />
                    </label>

                    <label className="ptField" style={{ marginTop: 10 }}>
                      <span>note</span>
                      <input value={approvalNote} onChange={(e) => setApprovalNote(String(e.target.value))} placeholder="Why is this run approved?" />
                    </label>

                    <div className="ptBtnRow" style={{ marginTop: 10 }}>
                      <button className="ptBtn ptBtnPrimary" onClick={approveSelectedRun} disabled={busy}>
                        Approve Selected Run
                      </button>
                    </div>

                    {approvalResult ? <pre className="ptPre">{_pretty(approvalResult)}</pre> : null}

                    {projectApprovals?.status === "error" ? <div className="ptError">{String(projectApprovals.error || "Failed to load approvals.")}</div> : null}
                    {projectApprovals?.status === "ok" ? (
                      projectApprovals.approvals?.length ? (
                        <pre className="ptPre">{_pretty(projectApprovals.approvals)}</pre>
                      ) : (
                        <div className="ptHint">No approvals recorded for this project yet.</div>
                      )
                    ) : null}
                  </div>
                ) : null}

                {selectedRunManifest?.run_id &&
                (String(selectedRunManifest?.run_type || "") === "pic_workflow_invdesign_chain" || selectedRunManifest?.outputs_summary?.pic_workflow) ? (
                  <div className="ptCallout" style={{ marginTop: 10 }}>
                    <div className="ptCalloutTitle">Workflow Chain</div>
                    <div className="ptHint">
                      <a href={_runBundleUrl(apiBase, selectedRunManifest.run_id)} target="_blank" rel="noreferrer">
                        Download evidence bundle (zip)
                      </a>
                    </div>

                    <div className="ptHint" style={{ marginTop: 8 }}>
                      {selectedRunManifest?.outputs_summary?.pic_workflow?.invdesign_run_id ? (
                        <>
                          <a href={_runManifestUrl(apiBase, selectedRunManifest.outputs_summary.pic_workflow.invdesign_run_id)} target="_blank" rel="noreferrer">
                            Open invdesign child manifest (JSON)
                          </a>
                          <br />
                        </>
                      ) : null}
                      {selectedRunManifest?.outputs_summary?.pic_workflow?.layout_run_id ? (
                        <>
                          <a href={_runManifestUrl(apiBase, selectedRunManifest.outputs_summary.pic_workflow.layout_run_id)} target="_blank" rel="noreferrer">
                            Open layout build child manifest (JSON)
                          </a>
                          <br />
                        </>
                      ) : null}
                      {selectedRunManifest?.outputs_summary?.pic_workflow?.lvs_lite_run_id ? (
                        <>
                          <a href={_runManifestUrl(apiBase, selectedRunManifest.outputs_summary.pic_workflow.lvs_lite_run_id)} target="_blank" rel="noreferrer">
                            Open LVS-lite child manifest (JSON)
                          </a>
                          <br />
                        </>
                      ) : null}
                      {selectedRunManifest?.outputs_summary?.pic_workflow?.klayout_pack_run_id ? (
                        <>
                          <a href={_runManifestUrl(apiBase, selectedRunManifest.outputs_summary.pic_workflow.klayout_pack_run_id)} target="_blank" rel="noreferrer">
                            Open KLayout child manifest (JSON)
                          </a>
                          <br />
                        </>
                      ) : null}
                      {selectedRunManifest?.outputs_summary?.pic_workflow?.spice_export_run_id ? (
                        <>
                          <a href={_runManifestUrl(apiBase, selectedRunManifest.outputs_summary.pic_workflow.spice_export_run_id)} target="_blank" rel="noreferrer">
                            Open SPICE export child manifest (JSON)
                          </a>
                          <br />
                        </>
                      ) : null}
                    </div>

                    <div className="ptBtnRow" style={{ marginTop: 10 }}>
                      <button className="ptBtn ptBtnPrimary" onClick={replaySelectedWorkflowRun} disabled={busy}>
                        Replay Workflow
                      </button>
                    </div>

                    {runsWorkflowReplayResult ? <pre className="ptPre">{_pretty(runsWorkflowReplayResult)}</pre> : null}
                  </div>
                ) : null}

                {selectedRunManifest?.run_id && selectedRunGdsArtifacts?.length ? (
                  <div className="ptCallout" style={{ marginTop: 10 }}>
                    <div className="ptCalloutTitle">KLayout Artifact Pack (DRC-lite)</div>
                    <div className="ptHint">
                      Runs the repo-owned KLayout macro template in batch mode on a selected <span className="ptMono">.gds</span> artifact from this run.
                    </div>

                    <label className="ptField" style={{ marginTop: 10 }}>
                      <span>gds_artifact_path</span>
                      <select
                        value={runsKlayoutGdsArtifactPath || String(selectedRunGdsArtifacts?.[0]?.path || "")}
                        onChange={(e) => setRunsKlayoutGdsArtifactPath(String(e.target.value))}
                      >
                        {selectedRunGdsArtifacts.map((a) => {
                          const p = String(a?.path || "").trim();
                          if (!p) return null;
                          const k = String(a?.key || "").trim();
                          const label = k ? `${k}: ${p}` : p;
                          return (
                            <option key={`runs_gds:${p}`} value={p}>
                              {label}
                            </option>
                          );
                        })}
                      </select>
                    </label>

                    <JsonBox
                      key={`runs_klayout_pack_settings:${JSON.stringify(klayoutPackSettings || {})}`}
                      title="klayout pack settings (advanced)"
                      value={klayoutPackSettings}
                      onApply={(text) => {
                        const parsed = _safeParseJson(text);
                        if (!parsed.ok) return parsed;
                        if (!parsed.value || typeof parsed.value !== "object" || Array.isArray(parsed.value)) return { ok: false, error: "Settings must be a JSON object." };
                        setKlayoutPackSettings(parsed.value);
                        return { ok: true };
                      }}
                    />

                    <div className="ptBtnRow" style={{ marginTop: 10 }}>
                      <button className="ptBtn ptBtnPrimary" onClick={runSelectedRunKlayoutPack} disabled={busy}>
                        Run KLayout Pack on Selected GDS
                      </button>
                    </div>

                    {runsKlayoutPackResult?.run_id && runsKlayoutPackResult?.artifact_relpaths ? (
                      <div className="ptTrustBox" style={{ marginTop: 10 }}>
                        <div className="ptJsonTitle">Artifacts (served)</div>
                        <div className="ptHint">
                          <a href={_runManifestUrl(apiBase, runsKlayoutPackResult.run_id)} target="_blank" rel="noreferrer">
                            Open run manifest (JSON)
                          </a>
                        </div>
                        <div className="ptHint" style={{ marginTop: 8 }}>
                          {Object.entries(runsKlayoutPackResult.artifact_relpaths).map(([k, v]) => {
                            if (typeof v !== "string" || !v) return null;
                            return (
                              <div key={`runs_klayout_pack:${k}`}>
                                <a href={_runArtifactUrl(apiBase, runsKlayoutPackResult.run_id, v)} target="_blank" rel="noreferrer">
                                  {String(k)}
                                </a>{" "}
                                <span className="ptMono">[{String(v)}]</span>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ) : null}

                    {runsKlayoutPackResult ? (
                      <pre className="ptPre">{_pretty(runsKlayoutPackResult)}</pre>
                    ) : (
                      <div className="ptHint">Run KLayout pack to see outputs.</div>
                    )}
                  </div>
                ) : null}

                {selectedRunManifest?.run_id ? (
                  <div className="ptTrustBox">
                    <div className="ptJsonTitle">Artifacts (served)</div>
                    <div className="ptHint">
                      <a href={_runManifestUrl(apiBase, selectedRunManifest.run_id)} target="_blank" rel="noreferrer">
                        Open manifest (JSON)
                      </a>
                    </div>
                    {selectedRunManifest?.artifacts && typeof selectedRunManifest.artifacts === "object" ? (
                      <div className="ptHint" style={{ marginTop: 8 }}>
                        {Object.entries(selectedRunManifest.artifacts).map(([k, v]) => {
                          if (typeof v !== "string" || !v) return null;
                          return (
                            <div key={`a:${k}`}>
                              <a href={_runArtifactUrl(apiBase, selectedRunManifest.run_id, v)} target="_blank" rel="noreferrer">
                                {String(k)}
                              </a>{" "}
                              <span className="ptMono">[{String(v)}]</span>
                            </div>
                          );
                        })}
                      </div>
                    ) : null}
                    {Array.isArray(selectedRunManifest?.artifacts?.cards) ? (
                      <div className="ptHint" style={{ marginTop: 10 }}>
                        <div className="ptJsonTitle">cards</div>
                        {selectedRunManifest.artifacts.cards.map((c, idx) => {
                          if (!c || typeof c !== "object") return null;
                          const sid = String(c.scenario_id || "");
                          const band = String(c.band || "");
                          const arts = c.artifacts && typeof c.artifacts === "object" ? c.artifacts : {};
                          return (
                            <div key={`c:${idx}`} style={{ marginTop: 6 }}>
                              <div>
                                <span className="ptMono">{sid}</span> <span className="ptMono">{band}</span>
                              </div>
                              {Object.entries(arts).map(([k, v]) => {
                                if (typeof v !== "string" || !v) return null;
                                return (
                                  <div key={`c:${idx}:${k}`}>
                                    <a href={_runArtifactUrl(apiBase, selectedRunManifest.run_id, v)} target="_blank" rel="noreferrer">
                                      {String(k)}
                                    </a>{" "}
                                    <span className="ptMono">[{String(v)}]</span>
                                  </div>
                                );
                              })}
                            </div>
                          );
                        })}
                      </div>
                    ) : null}
                  </div>
                ) : null}

                {selectedRunManifest ? <pre className="ptPre">{_pretty(selectedRunManifest)}</pre> : null}
              </div>
            </div>
          )}

          {mode === "runs" && activeRightTab === "diff" && (
            <div className="ptRightBody">
              <div className="ptRightSection">
                <div className="ptRightTitle">Run Diff</div>
                <div className="ptHint">Diff compares selected manifest scopes (input by default).</div>

                <label className="ptField" style={{ marginTop: 10 }}>
                  <span>LHS run</span>
                  <select value={diffLhsRunId} onChange={(e) => setDiffLhsRunId(String(e.target.value))}>
                    <option value="">(select)</option>
                    {(runsIndex?.runs || []).map((r) => {
                      const rid = String(r?.run_id || "");
                      if (!rid) return null;
                      const pid = String(r?.project_id || "");
                      const label = `${String(r?.run_type || "run")} | ${rid}`;
                      return (
                        <option key={`lhs2:${rid}`} value={rid}>
                          {pid ? `${String(r?.run_type || "run")} | ${pid} | ${rid}` : label}
                        </option>
                      );
                    })}
                  </select>
                </label>

                <label className="ptField" style={{ marginTop: 10 }}>
                  <span>RHS run</span>
                  <select value={diffRhsRunId} onChange={(e) => setDiffRhsRunId(String(e.target.value))}>
                    <option value="">(select)</option>
                    {(runsIndex?.runs || []).map((r) => {
                      const rid = String(r?.run_id || "");
                      if (!rid) return null;
                      const pid = String(r?.project_id || "");
                      const label = `${String(r?.run_type || "run")} | ${rid}`;
                      return (
                        <option key={`rhs2:${rid}`} value={rid}>
                          {pid ? `${String(r?.run_type || "run")} | ${pid} | ${rid}` : label}
                        </option>
                      );
                    })}
                  </select>
                </label>

                <label className="ptField" style={{ marginTop: 10 }}>
                  <span>Scope</span>
                  <select value={diffScope} onChange={(e) => setDiffScope(String(e.target.value))}>
                    <option value="input">input</option>
                    <option value="outputs_summary">outputs_summary</option>
                    <option value="all">all</option>
                  </select>
                </label>

                <div className="ptBtnRow" style={{ marginTop: 10 }}>
                  <button className="ptBtn ptBtnPrimary" onClick={diffRuns} disabled={busy || !diffLhsRunId || !diffRhsRunId}>
                    Diff
                  </button>
                </div>

                {runsDiffResult?.diff?.violation_diff ? (
                  <div className="ptHint" style={{ marginTop: 10 }}>
                    <div className="ptJsonTitle">Violation semantics</div>
                    <div className="ptMono">
                      new: {Number(runsDiffResult.diff.violation_diff?.summary?.new_count || 0)} | resolved: {Number(runsDiffResult.diff.violation_diff?.summary?.resolved_count || 0)} | applicability_changed: {Number(runsDiffResult.diff.violation_diff?.summary?.applicability_changed_count || 0)}
                    </div>

                    {_violationSamples(runsDiffResult.diff.violation_diff?.new, 2).map((v, idx) => (
                      <div key={`vd:new:${idx}`}>+ {_violationSampleLabel(v)}</div>
                    ))}
                    {_violationSamples(runsDiffResult.diff.violation_diff?.resolved, 2).map((v, idx) => (
                      <div key={`vd:resolved:${idx}`}>- {_violationSampleLabel(v)}</div>
                    ))}
                    {_violationSamples(runsDiffResult.diff.violation_diff?.applicability_changed, 2).map((v, idx) => {
                      const lhsApp = String(v?.lhs_applicability || "unknown");
                      const rhsApp = String(v?.rhs_applicability || "unknown");
                      const row = v?.rhs && typeof v.rhs === "object" ? v.rhs : v?.lhs;
                      return (
                        <div key={`vd:app:${idx}`}>
                          ~ {_violationSampleLabel(row)} ({lhsApp} {"->"} {rhsApp})
                        </div>
                      );
                    })}
                  </div>
                ) : null}

                {runsDiffResult ? <pre className="ptPre">{_pretty(runsDiffResult)}</pre> : <div className="ptHint">Select two runs and click Diff.</div>}
              </div>
            </div>
          )}
        </aside>
      </div>

      <footer className="ptStatusbar">
        <div className="ptStatusLeft">
          <span className="ptDot" data-state={busy ? "busy" : "idle"} />
          <span>{statusText}</span>
        </div>
        <div className="ptStatusRight">
          <span>nodes: {nodes.length}</span>
          <span>edges: {edges.length}</span>
          <span className="ptMono">hash: {compileResult?.graph_hash || runResult?.graph_hash || runResult?.config_hash || "n/a"}</span>
        </div>
      </footer>

      {exportOpen && (
        <Modal title="Export Graph JSON" onClose={() => setExportOpen(false)}>
          <pre className="ptPre">{exportText}</pre>
          <div className="ptBtnRow">
            <button className="ptBtn ptBtnPrimary" onClick={() => setExportOpen(false)}>
              Close
            </button>
          </div>
        </Modal>
      )}

      {importOpen && (
        <Modal title="Import Graph JSON" onClose={() => setImportOpen(false)}>
          <textarea className="ptTextarea" value={importText} onChange={(e) => setImportText(String(e.target.value))} placeholder="Paste a graph JSON payload (schema v0.1)." />
          <div className="ptBtnRow">
            <button className="ptBtn ptBtnGhost" onClick={importGraph}>
              Import
            </button>
            <button className="ptBtn ptBtnPrimary" onClick={() => setImportOpen(false)}>
              Cancel
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}

function JsonBox({ title, value, onApply, textareaClassName = "ptTextarea ptTextareaSmall" }) {
  const [text, setText] = useState(() => _pretty(value));
  const [err, setErr] = useState(null);

  return (
    <div className="ptJsonBox">
      <div className="ptJsonTop">
        <div className="ptJsonTitle">{String(title)}</div>
        <button
          className="ptBtn ptBtnTiny"
          onClick={() => {
            const r = onApply(text);
            if (!r?.ok) {
              setErr(String(r?.error || "Invalid JSON"));
            } else {
              setErr(null);
            }
          }}
        >
          Apply
        </button>
      </div>
      <textarea className={textareaClassName} value={text} onChange={(e) => setText(String(e.target.value))} spellCheck={false} />
      {err ? <div className="ptError">{err}</div> : null}
    </div>
  );
}

function KindTrustPanel({ kind, kindMeta, params, registryStatus, onSetParam }) {
  const schema = Array.isArray(kindMeta?.params) ? kindMeta.params : [];
  const paramObj = params && typeof params === "object" && !Array.isArray(params) ? params : {};

  const known = new Set(schema.map((p) => String(p?.name || "")));
  const unknownKeys = Object.keys(paramObj).filter((k) => !known.has(String(k)));

  if (!kind) return null;

  if (registryStatus !== "ok") {
    return <div className="ptHint">Kind registry not loaded. Use Ping to refresh the trust panel.</div>;
  }

  if (!kindMeta) {
    return <div className="ptHint">No registry entry for kind: {String(kind)}</div>;
  }

  const apiEnabled = kindMeta?.availability?.api_enabled;

  return (
    <div className="ptTrustBox">
      <div className="ptJsonTitle">Kind schema</div>
      {apiEnabled === false ? (
        <div className="ptError">
          API execution is disabled for <span className="ptMono">{String(kind)}</span>. This kind is CLI-only by default.
        </div>
      ) : null}
      {Array.isArray(kindMeta?.notes) && kindMeta.notes.length ? (
        <div className="ptHint">{kindMeta.notes.map((n, idx) => <div key={idx}>{String(n)}</div>)}</div>
      ) : null}

      {schema.length ? (
        <div className="ptParamGrid" role="group" aria-label="Parameter schema and quick editor">
          {schema.map((p) => {
            const name = String(p?.name || "");
            if (!name) return null;
            const typ = String(p?.type || "");
            const unit = p?.unit ? String(p.unit) : "";
            const required = Boolean(p?.required);
            const hasDefault = Object.prototype.hasOwnProperty.call(p || {}, "default");
            const defVal = hasDefault ? p.default : undefined;
            const min = Object.prototype.hasOwnProperty.call(p || {}, "min") ? p.min : undefined;
            const max = Object.prototype.hasOwnProperty.call(p || {}, "max") ? p.max : undefined;
            const enumList = Array.isArray(p?.enum) ? p.enum : null;

            const cur = Object.prototype.hasOwnProperty.call(paramObj, name) ? paramObj[name] : undefined;
            const isUnset = cur === null || cur === undefined;

            const rangeBits = [
              min != null ? `min ${min}` : null,
              max != null ? `max ${max}` : null,
              hasDefault ? `default ${defVal === null ? "null" : String(defVal)}` : null,
            ].filter(Boolean);

            const applies = p?.applies_when ? _pretty(p.applies_when) : "";

            const numericViolation =
              typeof cur === "number" && Number.isFinite(cur) && ((min != null && cur < Number(min)) || (max != null && cur > Number(max)));

            function setValueFromText(raw) {
              const s = String(raw ?? "");
              if (!s) {
                onSetParam(name, required ? "" : null);
                return;
              }
              onSetParam(name, s);
            }

            function setValueFromNumber(raw) {
              const s = String(raw ?? "");
              if (!s) {
                onSetParam(name, null);
                return;
              }
              const n = Number(s);
              if (!Number.isFinite(n)) return;
              if (typ === "integer") onSetParam(name, Math.trunc(n));
              else onSetParam(name, n);
            }

            function setValueFromBoolToken(tok) {
              const t = String(tok);
              if (t === "__unset__") {
                onSetParam(name, null);
              } else if (t === "true") {
                onSetParam(name, true);
              } else if (t === "false") {
                onSetParam(name, false);
              }
            }

            let control = null;
            if (enumList && enumList.length) {
              const current = isUnset ? "__unset__" : String(cur);
              control = (
                <select
                  className={`ptParamControl ${numericViolation ? "isBad" : ""}`}
                  value={current}
                  onChange={(e) => {
                    const v = String(e.target.value);
                    if (v === "__unset__") {
                      onSetParam(name, null);
                      return;
                    }
                    if (typ === "number" || typ === "integer") {
                      const n = Number(v);
                      if (!Number.isFinite(n)) return;
                      onSetParam(name, typ === "integer" ? Math.trunc(n) : n);
                    } else {
                      onSetParam(name, v);
                    }
                  }}
                >
                  {required ? null : <option value="__unset__">(unset)</option>}
                  {enumList.map((x) => (
                    <option key={String(x)} value={String(x)}>
                      {String(x)}
                    </option>
                  ))}
                </select>
              );
            } else if (typ === "boolean") {
              const current = cur === true ? "true" : cur === false ? "false" : "__unset__";
              control = (
                <select className="ptParamControl" value={current} onChange={(e) => setValueFromBoolToken(e.target.value)}>
                  {required ? null : <option value="__unset__">(unset)</option>}
                  <option value="true">true</option>
                  <option value="false">false</option>
                </select>
              );
            } else if (typ === "number" || typ === "integer") {
              control = (
                <input
                  className={`ptParamControl ${numericViolation ? "isBad" : ""}`}
                  type="number"
                  value={isUnset ? "" : String(cur)}
                  placeholder={hasDefault && defVal != null ? String(defVal) : ""}
                  onChange={(e) => setValueFromNumber(e.target.value)}
                />
              );
            } else {
              control = (
                <input
                  className="ptParamControl"
                  type="text"
                  value={isUnset ? "" : String(cur)}
                  placeholder={hasDefault && defVal != null ? String(defVal) : ""}
                  onChange={(e) => setValueFromText(e.target.value)}
                />
              );
            }

            return (
              <div className="ptParamRow" key={name}>
                <div className="ptParamMeta">
                  <div className="ptParamName">
                    {name}
                    {required ? <span className="ptParamReq">REQ</span> : null}
                    {unit ? <span className="ptParamUnit">{unit}</span> : null}
                    <span className="ptParamType">{typ}</span>
                  </div>
                  {p?.description ? <div className="ptParamDesc">{String(p.description)}</div> : null}
                  {rangeBits.length ? <div className="ptParamHint">{rangeBits.join(" | ")}</div> : null}
                  {applies ? <div className="ptParamHint">applies_when: {applies}</div> : null}
                </div>
                <div className="ptParamCtrl">{control}</div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="ptHint">No parameter schema published for this kind yet.</div>
      )}

      {unknownKeys.length ? (
        <div className="ptCallout">
          <div className="ptCalloutTitle">Unknown params (not in registry)</div>
          <div className="ptHint">{unknownKeys.map((k) => <div key={k}>{String(k)}</div>)}</div>
        </div>
      ) : null}
    </div>
  );
}

function Modal({ title, children, onClose }) {
  const outerRef = useRef(null);

  useEffect(() => {
    function onKey(e) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className="ptModalBackdrop"
      ref={outerRef}
      onMouseDown={(e) => {
        if (e.target === outerRef.current) onClose();
      }}
      role="dialog"
      aria-modal="true"
    >
      <div className="ptModal">
        <div className="ptModalTop">
          <div className="ptModalTitle">{String(title || "Modal")}</div>
          <button className="ptBtn ptBtnTiny" onClick={onClose}>
            Close
          </button>
        </div>
        <div className="ptModalBody">{children}</div>
      </div>
    </div>
  );
}
