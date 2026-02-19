import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  addEdge,
  useEdgesState,
  useNodesState,
  useReactFlow,
} from "@xyflow/react";

import "./App.css";
import CertificationWorkspace from "./features/certify/CertificationWorkspace";
import CompareLabPanel from "./features/compare/CompareLabPanel";
import DemoModeOrchestrator from "./features/demo/DemoModeOrchestrator";
import DemoProofSnapshot from "./features/demo/DemoProofSnapshot";
import GraphRightSidebarContent from "./features/graph/GraphRightSidebarContent";
import OrbitValidatePanel from "./features/orbit/OrbitValidatePanel";
import OrbitConfigPanel from "./features/orbit/OrbitConfigPanel";
import ApprovalControls from "./features/runs/ApprovalControls";
import DiffPanel from "./features/runs/DiffPanel";
import ManifestPanel from "./features/runs/ManifestPanel";
import AppTopBar from "./features/shell/AppTopBar";
import CenterWorkspacePane from "./features/shell/CenterWorkspacePane";
import GraphJsonModals from "./features/shell/GraphJsonModals";
import LandingWorkspace from "./features/shell/LandingWorkspace";
import LeftSidebarByMode from "./features/shell/LeftSidebarByMode";
import RightSidebarTabs from "./features/shell/RightSidebarTabs";
import StatusFooter from "./features/shell/StatusFooter";
import GuidedFlowWizard from "./features/guided-flow/GuidedFlowWizard";
import RunModePanel from "./features/results/RunModePanel";
import { PRODUCT_STAGE_ITEMS, PRODUCT_STAGE_ROUTES, stageLabel, stageSubtitle } from "./features/shell/copy";
import ProvenanceTimeline from "./features/trust/ProvenanceTimeline";
import RunCollectionsPanel from "./features/workspace/RunCollectionsPanel";
import WorkspaceContextBar from "./features/workspace/WorkspaceContextBar";
import { createUiSessionId, createUiTelemetrySink } from "./state/uiTelemetry";
import {
  addTagToRun,
  createCollection,
  loadCollectionsState,
  removeTagFromRun,
  saveCollection,
  setBaselineRun,
  setCandidateRuns,
} from "./state/runCollectionsState";
import { loadRecentActivity, loadViewPresets, saveRecentActivity, saveViewPreset } from "./state/workspaceState";

import { BAND_OPTIONS, KIND_DEFS, kindDef, portDomainFor } from "./photontrust/kinds";
import { templatePicChain, templatePicMzi, templatePicSpiceImportHarness, templateQkdLink } from "./photontrust/templates";
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

function _flowFromGraph(graph, registryByKind = null) {
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

function _defaultGraphIdForProfile(profile) {
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

function _kindBlueprint(kind, kindRegistryEntry = null) {
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

function _kindAvailability(kind, kindRegistryEntry = null) {
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

function _nodePortDomain(node, direction, portName) {
  const dir = String(direction || "").toLowerCase() === "in" ? "in" : "out";
  const port = String(portName || "").trim();
  const byPort = node?.data?.portDomains?.[dir];
  if (byPort && typeof byPort === "object") {
    const d = String(byPort?.[port] || "").trim();
    if (d) return d;
  }
  return portDomainFor(String(node?.data?.kind || ""), dir, port);
}

const ROLE_PRESET_OPTIONS = [
  { id: "builder", label: "Builder" },
  { id: "reviewer", label: "Reviewer" },
  { id: "exec", label: "Exec" },
];

const DEMO_SCENE_PLANS = {
  benchmark: {
    scene: "benchmark",
    stage: "compare",
    mode: "runs",
    tab: "diff",
    statusText: "Demo scene: Benchmark. Compare baseline and candidate outcomes.",
  },
  trust: {
    scene: "trust",
    stage: "certify",
    mode: "runs",
    tab: "manifest",
    statusText: "Demo scene: Trust. Review provenance and certification posture.",
  },
  decision: {
    scene: "decision",
    stage: "run",
    mode: "graph",
    tab: "run",
    statusText: "Demo scene: Decision. Present recommendation and confidence framing.",
  },
  packet: {
    scene: "packet",
    stage: "export",
    mode: "runs",
    tab: "manifest",
    statusText: "Demo scene: Packet. Export meeting-ready evidence.",
  },
};

function _demoScenePlan(sceneId) {
  const key = String(sceneId || "benchmark").trim().toLowerCase();
  return DEMO_SCENE_PLANS[key] || DEMO_SCENE_PLANS.benchmark;
}

function _rolePresetBehavior(roleId) {
  const role = String(roleId || "builder");
  if (role === "reviewer") return { stage: "compare", mode: "runs", tab: "diff" };
  if (role === "exec") return { stage: "export", mode: "runs", tab: "manifest" };
  return { stage: "build", mode: "graph", tab: "inspect" };
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
  const [programStage, setProgramStage] = useState(() => localStorage.getItem("pt_program_stage") || "build");
  const [showLanding, setShowLanding] = useState(() => localStorage.getItem("pt_show_landing") !== "0");
  const [userMode, setUserMode] = useState(() => localStorage.getItem("pt_user_mode") || "builder");
  const [savedViews, setSavedViews] = useState(() => loadViewPresets());
  const [selectedViewPresetId, setSelectedViewPresetId] = useState("");
  const [recentActivity, setRecentActivity] = useState(() => loadRecentActivity());
  const [demoModeOpen, setDemoModeOpen] = useState(false);
  const [demoInitialScene, setDemoInitialScene] = useState("benchmark");
  const [demoScene, setDemoScene] = useState("benchmark");
  const [uiSessionId] = useState(() => createUiSessionId());
  const guidedFlowRef = useRef({ active: false, startedAtMs: 0 });
  const runRecoveryRef = useRef({ hadFailure: false, failedAtMs: 0 });
  const demoResumeRef = useRef({ mode: "graph", stage: "build", tab: "inspect", userMode: "builder" });
  const telemetrySessionStartedRef = useRef(false);
  const [guidedFlowWizardOpen, setGuidedFlowWizardOpen] = useState(false);
  const [guidedFlowInitialGoal, setGuidedFlowInitialGoal] = useState("qkd");

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
  const [collectionsState, setCollectionsState] = useState(() => loadCollectionsState());
  const [selectedCollectionId, setSelectedCollectionId] = useState("");
  const [newCollectionName, setNewCollectionName] = useState("");
  const [collectionTagInput, setCollectionTagInput] = useState("");

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
  const [paletteQuery, setPaletteQuery] = useState("");
  const [paletteScope, setPaletteScope] = useState("all");
  const [statusText, setStatusText] = useState("Ready.");
  const statusTimer = useRef(null);

  const reactFlowInstance = useReactFlow();

  const uiTelemetry = useMemo(
    () =>
      createUiTelemetrySink({
        apiBase,
        getContext: () => ({ sessionId: uiSessionId, userMode, profile }),
      }),
    [apiBase, uiSessionId, userMode, profile],
  );

  const emitUiEvent = useCallback(
    (eventName, fields = {}) => {
      uiTelemetry.emit(eventName, fields);
    },
    [uiTelemetry],
  );

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

  const collectionOptions = useMemo(() => {
    const rows = Array.isArray(collectionsState?.collections) ? collectionsState.collections : [];
    return rows.map((item) => ({ id: String(item?.id || ""), name: String(item?.name || item?.id || "") })).filter((item) => item.id);
  }, [collectionsState]);

  const selectedCollection = useMemo(() => {
    const rows = Array.isArray(collectionsState?.collections) ? collectionsState.collections : [];
    return rows.find((item) => String(item?.id || "") === String(selectedCollectionId || "")) || null;
  }, [collectionsState, selectedCollectionId]);

  const selectedRunForCollection = useMemo(() => {
    const rid = String(selectedRunId || selectedRunManifest?.run_id || diffLhsRunId || diffRhsRunId || "").trim();
    return rid;
  }, [selectedRunId, selectedRunManifest, diffLhsRunId, diffRhsRunId]);

  const runOptionsForCollections = useMemo(() => {
    const rows = Array.isArray(runsIndex?.runs) ? runsIndex.runs : [];
    return rows
      .map((run) => {
        const runId = String(run?.run_id || "").trim();
        if (!runId) return null;
        return {
          run_id: runId,
          run_type: String(run?.run_type || "run"),
          project_id: String(run?.project_id || ""),
        };
      })
      .filter(Boolean);
  }, [runsIndex]);

  const selectedRunTags = useMemo(() => {
    const tagsByRun =
      selectedCollection?.tagsByRun && typeof selectedCollection.tagsByRun === "object" ? selectedCollection.tagsByRun : {};
    const tags = tagsByRun[String(selectedRunForCollection || "")] || [];
    return Array.isArray(tags) ? tags : [];
  }, [selectedCollection, selectedRunForCollection]);

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

  const filteredKindOptions = useMemo(() => {
    const q = String(paletteQuery || "").trim().toLowerCase();
    const out = kindOptions.filter((kind) => {
      const meta = kindRegistry?.byKind?.[kind];
      const def = kindDef(kind);
      const availability = _kindAvailability(kind, meta);
      if (paletteScope === "api" && availability.apiEnabled !== true) return false;
      if (paletteScope === "cli" && availability.cliEnabled !== true) return false;
      if (!q) return true;
      const notes = Array.isArray(meta?.notes) ? meta.notes.join(" ") : "";
      const search = `${kind} ${meta?.title || ""} ${def?.title || ""} ${notes}`.toLowerCase();
      return search.includes(q);
    });
    out.sort((lhs, rhs) => {
      const lMeta = kindRegistry?.byKind?.[lhs];
      const rMeta = kindRegistry?.byKind?.[rhs];
      const lAvail = _kindAvailability(lhs, lMeta);
      const rAvail = _kindAvailability(rhs, rMeta);
      if (lAvail.apiEnabled !== rAvail.apiEnabled) return lAvail.apiEnabled ? -1 : 1;
      return lhs.localeCompare(rhs, undefined, { sensitivity: "base" });
    });
    return out;
  }, [kindOptions, kindRegistry.byKind, paletteQuery, paletteScope]);

  const paletteSummary = useMemo(() => {
    let apiReady = 0;
    let cliOnly = 0;
    for (const kind of kindOptions) {
      const meta = kindRegistry?.byKind?.[kind];
      const availability = _kindAvailability(kind, meta);
      if (availability.apiEnabled) apiReady += 1;
      if (!availability.apiEnabled && availability.cliEnabled) cliOnly += 1;
    }
    return { apiReady, cliOnly };
  }, [kindOptions, kindRegistry.byKind]);

  const decisionContext = useMemo(() => {
    const compileErrors = Array.isArray(compileResult?.diagnostics?.errors) ? compileResult.diagnostics.errors : [];
    const compileWarnings = Array.isArray(compileResult?.diagnostics?.warnings) ? compileResult.diagnostics.warnings : [];
    const runError = String(runResult?.error || "").trim();
    const diffSummary = runsDiffResult?.diff?.violation_diff?.summary || {};
    const newViolationCount = Number(diffSummary?.new_count || 0);
    const approvalsCount = Array.isArray(projectApprovals?.approvals) ? projectApprovals.approvals.length : 0;

    const firstFinite = (...vals) => {
      for (const raw of vals) {
        const n = Number(raw);
        if (Number.isFinite(n)) return n;
      }
      return null;
    };

    const rawConfidence = firstFinite(
      runResult?.confidence_score,
      runResult?.outputs_summary?.confidence_score,
      compileResult?.confidence_score,
      compileResult?.outputs_summary?.confidence_score,
    );
    const confidenceScore =
      rawConfidence == null
        ? compileErrors.length
          ? 0.42
          : compileWarnings.length
            ? 0.74
            : 0.9
        : rawConfidence <= 1
          ? rawConfidence
          : rawConfidence / 100;

    const blockers = [];
    if (runError) blockers.push(`Run failed: ${runError}`);
    if (compileErrors.length) blockers.push(`${compileErrors.length} compile error(s) still open.`);
    if (newViolationCount > 0) blockers.push(`${newViolationCount} new violation(s) vs baseline.`);
    if (!String(selectedRunManifest?.run_id || runResult?.run_id || "").trim()) blockers.push("No selected run evidence bundle.");

    const highlights = [];
    if (runResult?.run_id) highlights.push(`Latest run id: ${String(runResult.run_id)}`);
    if (compileWarnings.length) highlights.push(`${compileWarnings.length} compile warning(s) flagged for review.`);
    if (approvalsCount) highlights.push(`${approvalsCount} approval event(s) recorded.`);
    if (!highlights.length) highlights.push("Run, compile, and trust surfaces are ready for review.");

    const actions = blockers.length
      ? [
          { id: "fix", title: "Resolve blockers in Run/Compile", owner: "builder", eta: "today", priority: "high" },
          { id: "diff", title: "Open compare lab and rerun baseline diff", owner: "reviewer", eta: "today", priority: "high" },
          { id: "retry", title: "Retry run and refresh manifest", owner: "builder", eta: "today", priority: "medium" },
        ]
      : [
          { id: "certify", title: "Open certify workspace", owner: "reviewer", eta: "today", priority: "high" },
          { id: "packet", title: "Export decision packet", owner: "exec", eta: "today", priority: "high" },
          { id: "save", title: "Save view preset for handoff", owner: "builder", eta: "today", priority: "low" },
        ];

    const recommendation = blockers.length
      ? "Resolve blockers and rerun compare before signoff."
      : "Proceed to certify, approve, and export the decision packet.";

    const decision = blockers.length ? "Review" : "Pass";
    const riskLevel = blockers.length ? "high" : compileWarnings.length ? "medium" : "low";

    return {
      decision,
      riskLevel,
      confidenceScore,
      blockers,
      highlights,
      actions,
      recommendation,
      payload: {
        run_id: String(runResult?.run_id || selectedRunManifest?.run_id || ""),
        confidence_score: confidenceScore,
        risk_level: riskLevel,
        recommendation,
      },
      uncertaintyList: Array.isArray(uncertainty) ? uncertainty : Object.entries(uncertainty || {}).map(([k, v]) => `${k}: ${String(v)}`),
    };
  }, [runResult, compileResult, runsDiffResult, projectApprovals, selectedRunManifest, uncertainty]);

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

  const recordActivity = useCallback((type, message, context = {}) => {
    const updated = saveRecentActivity(
      {
        type: String(type || "info"),
        message: String(message || ""),
        context: context && typeof context === "object" ? context : {},
      },
      { max: 24 },
    );
    setRecentActivity(updated);
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
      recordActivity("approval", "Approved selected run.", {
        run_id: rid,
        project_id: pid,
      });
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
      recordActivity("approval", "Approval failed.", {
        run_id: rid,
        project_id: pid,
      });
      _setStatus(`Approve failed: ${String(err?.message || err)}`);
    } finally {
      setBusy(false);
    }
  }, [apiBase, selectedRunManifest, approvalActor, approvalNote, recordActivity, _setStatus]);

  const diffRuns = useCallback(async () => {
    const lhs = String(diffLhsRunId || "").trim();
    const rhs = String(diffRhsRunId || "").trim();
    if (!lhs || !rhs) return;
    const startedAtMs = Date.now();
    setBusy(true);
    setRunsDiffResult(null);
    try {
      const payload = await apiDiffRuns(apiBase, lhs, rhs, { scope: String(diffScope || "input"), limit: 200 });
      setRunsDiffResult(payload);
      emitUiEvent("ui_compare_completed", {
        duration_ms: Date.now() - startedAtMs,
        outcome: "success",
      });
      recordActivity("compare", "Computed baseline-candidate diff.", {
        lhs: lhs,
        rhs: rhs,
        scope: String(diffScope || "input"),
      });
      _setStatus(`Diff computed (${lhs} vs ${rhs}).`);
    } catch (err) {
      setRunsDiffResult({ error: String(err?.message || err) });
      emitUiEvent("ui_compare_completed", {
        duration_ms: Date.now() - startedAtMs,
        outcome: "failure",
      });
      recordActivity("compare", "Diff failed.", {
        lhs: lhs,
        rhs: rhs,
        scope: String(diffScope || "input"),
      });
      _setStatus(`Diff failed: ${String(err?.message || err)}`);
    } finally {
      setBusy(false);
    }
  }, [apiBase, diffLhsRunId, diffRhsRunId, diffScope, emitUiEvent, recordActivity, _setStatus]);

  useEffect(() => {
    localStorage.setItem("pt_api_base", String(apiBase));
  }, [apiBase]);

  useEffect(() => {
    localStorage.setItem("pt_mode", String(mode));
  }, [mode]);

  useEffect(() => {
    localStorage.setItem("pt_program_stage", String(programStage));
  }, [programStage]);

  useEffect(() => {
    localStorage.setItem("pt_show_landing", showLanding ? "1" : "0");
  }, [showLanding]);

  useEffect(() => {
    localStorage.setItem("pt_user_mode", String(userMode));
  }, [userMode]);

  useEffect(() => {
    if (telemetrySessionStartedRef.current) return;
    telemetrySessionStartedRef.current = true;
    emitUiEvent("ui_session_started", { outcome: "success" });
    recordActivity("session", "UI session started.", { user_mode: userMode, profile });
  }, [emitUiEvent, profile, recordActivity, userMode]);

  useEffect(() => {
    localStorage.setItem("pt_project_id", String(selectedProjectId));
  }, [selectedProjectId]);

  useEffect(() => {
    localStorage.setItem("pt_approval_actor", String(approvalActor));
  }, [approvalActor]);

  useEffect(() => {
    const rows = Array.isArray(collectionsState?.collections) ? collectionsState.collections : [];
    if (!rows.length) {
      if (selectedCollectionId) setSelectedCollectionId("");
      return;
    }
    const exists = rows.some((item) => String(item?.id || "") === String(selectedCollectionId || ""));
    if (!exists) {
      setSelectedCollectionId(String(rows[0]?.id || ""));
    }
  }, [collectionsState, selectedCollectionId]);

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
      const fromPort = String(params?.sourceHandle || "out");
      const toPort = String(params?.targetHandle || "in");
      const edgeKind = "optical";
      if (profile === "pic_circuit") {
        const fromDomain = _nodePortDomain(sourceNode, "out", fromPort);
        const toDomain = _nodePortDomain(targetNode, "in", toPort);

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
      if (templateId === "pic_spice_import") {
        setProfile("pic_circuit");
        setGraphId("ui_pic_circuit");
        setCircuit({ ...DEFAULT_PIC_CIRCUIT });
        const t = templatePicSpiceImportHarness();
        setNodes(t.nodes);
        setEdges(t.edges);
        _setStatus("Loaded template: PIC SPICE import harness (Touchstone path required for CLI runs).");
      }
    },
    [setNodes, setEdges, _setStatus, setCompileResult, setRunResult, setActiveRightTab],
  );

  const switchOperationalMode = useCallback(
    (nextMode, { nextTab = null, nextStage = null, statusText = "" } = {}) => {
      const next = String(nextMode || "graph");
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
      if (nextStage) setProgramStage(String(nextStage));
      setActiveRightTab(nextTab || (next === "orbit" ? "orbit" : next === "runs" ? "manifest" : "inspect"));
      if (statusText) {
        _setStatus(statusText);
      } else {
        _setStatus(next === "orbit" ? "Switched to Orbit Pass mode." : next === "runs" ? "Switched to Runs mode." : "Switched to Graph Editor mode.");
      }
    },
    [_setStatus],
  );

  const openProgramStage = useCallback(
    (stageId, options = {}) => {
      const key = String(stageId || "build");
      const route = PRODUCT_STAGE_ROUTES[key] || PRODUCT_STAGE_ROUTES.build;
      setProgramStage(key);
      setShowLanding(false);
      if (options.userMode) setUserMode(String(options.userMode));
      switchOperationalMode(route.mode, {
        nextTab: route.tab,
        nextStage: key,
        statusText: options.statusText || `Stage: ${stageLabel(key)}.`,
      });
      recordActivity("stage_change", `Opened ${stageLabel(key)} stage.`, { stage: key, mode: route.mode });
    },
    [switchOperationalMode, recordActivity],
  );

  const saveCurrentViewPreset = useCallback(() => {
    const name = `${stageLabel(programStage)} view ${new Date().toISOString().slice(11, 16)}`;
    const presets = saveViewPreset({
      name,
      mode,
      stage: programStage,
      graphId,
      view: {
        userMode,
        activeRightTab,
        selectedProjectId,
        diffScope,
      },
    });
    setSavedViews(presets);
    const firstId = String(presets?.[0]?.id || "");
    if (firstId) setSelectedViewPresetId(firstId);
    _setStatus("Saved current workspace view.");
    recordActivity("view_saved", "Saved workspace view preset.", { preset_id: firstId, stage: programStage, mode });
  }, [programStage, mode, graphId, userMode, activeRightTab, selectedProjectId, diffScope, _setStatus, recordActivity]);

  const applyViewPresetById = useCallback(
    (presetId) => {
      const id = String(presetId || "").trim();
      setSelectedViewPresetId(id);
      if (!id) return;
      const preset = (savedViews || []).find((v) => String(v?.id || "") === id);
      if (!preset) {
        _setStatus("Selected view preset was not found.");
        return;
      }
      const stage = String(preset?.stage || "build");
      const route = PRODUCT_STAGE_ROUTES[stage] || PRODUCT_STAGE_ROUTES.build;
      const view = preset?.view && typeof preset.view === "object" ? preset.view : {};
      if (view.userMode) setUserMode(String(view.userMode));
      if (Object.prototype.hasOwnProperty.call(view, "selectedProjectId")) setSelectedProjectId(String(view.selectedProjectId || ""));
      if (view.diffScope) setDiffScope(String(view.diffScope));
      switchOperationalMode(String(preset?.mode || route.mode || "graph"), {
        nextTab: String(view.activeRightTab || route.tab || "inspect"),
        nextStage: stage,
        statusText: `Loaded view preset: ${String(preset?.name || "workspace")}.`,
      });
      setShowLanding(false);
      recordActivity("view_loaded", `Loaded view preset ${String(preset?.name || "workspace")}.`, { preset_id: id, stage });
    },
    [savedViews, _setStatus, switchOperationalMode, recordActivity],
  );

  const applyRolePreset = useCallback(
    (roleId) => {
      const role = String(roleId || "builder");
      const behavior = _rolePresetBehavior(role);
      setUserMode(role);
      switchOperationalMode(behavior.mode, {
        nextTab: behavior.tab,
        nextStage: behavior.stage,
        statusText: `Role preset applied: ${role}.`,
      });
      setShowLanding(false);
      recordActivity("role_preset", `Applied role preset ${role}.`, {
        role,
        stage: behavior.stage,
      });
    },
    [switchOperationalMode, recordActivity],
  );

  const createRunCollection = useCallback(
    (name) => {
      const cleanName = String(name || "").trim();
      if (!cleanName) return;
      const collection = createCollection({ name: cleanName });
      const nextState = saveCollection(collection);
      setCollectionsState(nextState);
      setSelectedCollectionId(String(collection.id || ""));
      setNewCollectionName("");
      recordActivity("collection", `Created run collection ${cleanName}.`, { collection_id: String(collection.id || "") });
      _setStatus(`Created run collection: ${cleanName}.`);
    },
    [recordActivity, _setStatus],
  );

  const persistUpdatedCollection = useCallback(
    (nextCollection, activityMessage) => {
      if (!nextCollection || typeof nextCollection !== "object") return;
      const nextState = saveCollection(nextCollection);
      setCollectionsState(nextState);
      if (nextCollection.id) setSelectedCollectionId(String(nextCollection.id));
      if (activityMessage) {
        recordActivity("collection", activityMessage, { collection_id: String(nextCollection.id || "") });
      }
    },
    [recordActivity],
  );

  const addCollectionTag = useCallback(
    (runId, tag) => {
      if (!selectedCollection) return;
      const updated = addTagToRun(selectedCollection, runId, tag);
      persistUpdatedCollection(updated, "Added run tag to collection.");
      setCollectionTagInput("");
    },
    [selectedCollection, persistUpdatedCollection],
  );

  const removeCollectionTag = useCallback(
    (runId, tag) => {
      if (!selectedCollection) return;
      const updated = removeTagFromRun(selectedCollection, runId, tag);
      persistUpdatedCollection(updated, "Removed run tag from collection.");
    },
    [selectedCollection, persistUpdatedCollection],
  );

  const setCollectionBaseline = useCallback(
    (runId) => {
      if (!selectedCollection) return;
      const updated = setBaselineRun(selectedCollection, runId);
      persistUpdatedCollection(updated, "Updated collection baseline run.");
    },
    [selectedCollection, persistUpdatedCollection],
  );

  const setCollectionCandidates = useCallback(
    (runIds) => {
      if (!selectedCollection) return;
      const updated = setCandidateRuns(selectedCollection, runIds);
      persistUpdatedCollection(updated, "Updated collection candidate runs.");
    },
    [selectedCollection, persistUpdatedCollection],
  );

  const handleWorkspaceProjectChange = useCallback(
    (projectId) => {
      const pid = String(projectId || "");
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
      recordActivity("workspace_project", `Switched workspace project to ${pid || "(all)"}.`, { project_id: pid || null });
    },
    [refreshRuns, recordActivity],
  );

  const handleRecentActivityClick = useCallback(
    (item) => {
      const message = String(item?.message || item?.label || "").trim();
      if (message) {
        _setStatus(message);
      }
    },
    [_setStatus],
  );

  const startGuidedFlow = useCallback(
    (templateId = "qkd") => {
      const nextTemplate = String(templateId || "qkd");
      const nextProfile = nextTemplate === "pic_mzi" ? "pic_circuit" : "qkd_link";
      guidedFlowRef.current = { active: true, startedAtMs: Date.now() };
      emitUiEvent("ui_guided_flow_started", {
        user_mode: "builder",
        profile: nextProfile,
        outcome: "success",
      });
      setUserMode("builder");
      setGuidedFlowInitialGoal(nextTemplate === "pic_mzi" ? "pic_mzi" : "qkd");
      setGuidedFlowWizardOpen(true);
      openProgramStage("build", {
        statusText: "Guided flow started. Continue through goal, template, params, preflight, and run.",
      });
    },
    [emitUiEvent, openProgramStage],
  );

  const closeGuidedFlowWizard = useCallback(
    ({ abandoned = false } = {}) => {
      setGuidedFlowWizardOpen(false);
      if (abandoned && guidedFlowRef.current.active) {
        const elapsed = guidedFlowRef.current.startedAtMs ? Date.now() - Number(guidedFlowRef.current.startedAtMs) : null;
        emitUiEvent("ui_guided_flow_completed", {
          duration_ms: Number.isFinite(elapsed) && elapsed >= 0 ? elapsed : null,
          outcome: "abandoned",
        });
        guidedFlowRef.current = { active: false, startedAtMs: 0 };
      }
    },
    [emitUiEvent],
  );

  const applyGuidedTemplate = useCallback(
    async (templateId) => {
      const nextTemplate = String(templateId || "qkd");
      loadTemplate(nextTemplate === "pic_mzi" ? "pic_mzi" : "qkd");
      return { ok: true };
    },
    [loadTemplate],
  );

  const runGuidedPreflight = useCallback(
    async ({ templateId }) => {
      const nextTemplate = String(templateId || "qkd");
      const expectedProfile = nextTemplate === "pic_mzi" ? "pic_circuit" : "qkd_link";
      const errors = [];
      const warnings = [];

      if (!String(apiBase || "").trim()) {
        errors.push("API base URL is required.");
      }
      if (mode !== "graph") {
        warnings.push("Preflight works best in Graph Editor mode.");
      }
      if (profile !== expectedProfile) {
        warnings.push(`Profile mismatch: expected ${expectedProfile}, current ${profile}.`);
      }
      if (!Array.isArray(nodes) || !nodes.length) {
        errors.push("Graph has no nodes. Apply a template before preflight.");
      }
      if (apiHealth.status === "error") {
        errors.push("API health is error. Fix connectivity before preflight.");
      }

      const cliOnlyKinds = (nodes || [])
        .map((n) => String(n?.data?.kind || "").trim())
        .filter(Boolean)
        .filter((kind) => {
          const availability = _kindAvailability(kind, kindRegistry?.byKind?.[kind]);
          return availability.apiEnabled !== true && availability.cliEnabled === true;
        });
      if (cliOnlyKinds.length) {
        errors.push(`CLI-only components present: ${cliOnlyKinds.join(", ")}`);
      }

      if (errors.length) {
        return { ok: false, errors, warnings, graphHash: null };
      }

      try {
        const payload = await apiCompileGraph(apiBase, graphPayload, { requireSchema: true });
        setCompileResult(payload);
        setActiveRightTab("compile");

        const compileErrors = Array.isArray(payload?.diagnostics?.errors)
          ? payload.diagnostics.errors.map((d) => `${String(d?.code || "error")}: ${String(d?.message || "")}`)
          : [];
        const compileWarnings = Array.isArray(payload?.diagnostics?.warnings)
          ? payload.diagnostics.warnings.map((d) => `${String(d?.code || "warning")}: ${String(d?.message || "")}`)
          : [];

        if (compileErrors.length) {
          return {
            ok: false,
            errors: [...errors, ...compileErrors],
            warnings: [...warnings, ...compileWarnings],
            graphHash: String(payload?.graph_hash || "") || null,
          };
        }

        return {
          ok: true,
          errors: [],
          warnings: [...warnings, ...compileWarnings],
          graphHash: String(payload?.graph_hash || "") || null,
        };
      } catch (err) {
        const msg = String(err?.message || err);
        setCompileResult({ error: msg });
        setActiveRightTab("compile");
        return { ok: false, errors: [...errors, `Compile failed: ${msg}`], warnings, graphHash: null };
      }
    },
    [apiBase, mode, profile, nodes, apiHealth.status, kindRegistry.byKind, graphPayload],
  );

  const applyDemoScene = useCallback(
    (sceneId, { statusText = "" } = {}) => {
      const plan = _demoScenePlan(sceneId);
      setDemoScene(plan.scene);
      setProgramStage(plan.stage);
      setMode(plan.mode);
      setActiveRightTab(plan.tab);
      setShowLanding(false);
      _setStatus(statusText || plan.statusText);
      recordActivity("demo_scene", `Demo scene: ${plan.scene}.`, {
        scene: plan.scene,
        stage: plan.stage,
        mode: plan.mode,
        tab: plan.tab,
      });
    },
    [_setStatus, recordActivity],
  );

  const handleDemoSceneChange = useCallback(
    (payload) => {
      applyDemoScene(payload?.scene || "benchmark");
    },
    [applyDemoScene],
  );

  const investorDemoCheckpoint = useCallback(() => {
    demoResumeRef.current = {
      mode,
      stage: programStage,
      tab: activeRightTab,
      userMode,
    };
    setUserMode("exec");
    setDemoInitialScene("benchmark");
    setDemoScene("benchmark");
    setDemoModeOpen(true);
    applyDemoScene("benchmark", {
      statusText: "Demo mode started. Walk through benchmark, trust, decision, and packet scenes.",
    });
    recordActivity("demo_start", "Demo mode started from landing workspace.", { stage: "compare" });
  }, [activeRightTab, applyDemoScene, mode, programStage, recordActivity, userMode]);

  const closeDemoMode = useCallback(
    ({ completed = false, scene = "packet" } = {}) => {
      setDemoModeOpen(false);
      setDemoScene(String(scene || "benchmark"));
      const resume = demoResumeRef.current || {};
      setMode(String(resume.mode || "graph"));
      setProgramStage(String(resume.stage || "build"));
      setActiveRightTab(String(resume.tab || (String(resume.mode || "graph") === "runs" ? "manifest" : "inspect")));
      setUserMode(String(resume.userMode || "builder"));
      emitUiEvent("ui_demo_mode_completed", {
        user_mode: "exec",
        outcome: completed ? "success" : "abandoned",
      });
      _setStatus(completed ? "Demo mode completed." : "Demo mode closed.");
      recordActivity("demo_end", completed ? "Demo mode completed." : "Demo mode exited.", {
        scene: String(scene || "packet"),
        completed: Boolean(completed),
      });
    },
    [emitUiEvent, _setStatus, recordActivity],
  );

  const exportDecisionPacket = useCallback(() => {
    const rid = String(selectedRunManifest?.run_id || workflowResult?.run_id || runResult?.run_id || "").trim();
    if (!rid) {
      emitUiEvent("ui_packet_exported", { outcome: "abandoned" });
      recordActivity("packet_export", "Packet export abandoned (no run selected).", {});
      _setStatus("No run selected for packet export. Select a run manifest or execute a run first.");
      return;
    }

    const url = _runBundleUrl(apiBase, rid);
    try {
      window.open(url, "_blank", "noopener,noreferrer");
      emitUiEvent("ui_packet_exported", { run_id: rid, outcome: "success" });
      recordActivity("packet_export", "Opened decision packet bundle.", { run_id: rid });
      _setStatus(`Opened decision packet bundle (${rid}).`);
    } catch (err) {
      emitUiEvent("ui_packet_exported", { run_id: rid, outcome: "failure" });
      recordActivity("packet_export", "Packet export failed.", { run_id: rid });
      _setStatus(`Packet export failed: ${String(err?.message || err)}`);
    }
  }, [apiBase, selectedRunManifest, workflowResult, runResult, emitUiEvent, recordActivity, _setStatus]);

  const addKind = useCallback(
    (kind, overridePosition) => {
      const blueprint = _kindBlueprint(kind, kindRegistry?.byKind?.[kind]);
      if (!blueprint?.def && !blueprint?.meta) {
        _setStatus(`Unknown component kind: ${String(kind || "")}.`);
        return;
      }
      const title = blueprint.title;
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
      const params = { ...blueprint.defaultParams };
      setNodes((nds) =>
        nds.concat({
          id,
          type: "ptNode",
          position: { x, y },
          data: {
            id,
            kind,
            label: title,
            title: blueprint.title,
            category: blueprint.category,
            inPorts: blueprint.inPorts,
            outPorts: blueprint.outPorts,
            portDomains: blueprint.portDomains,
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
      const blueprint = _kindBlueprint(kind, kindRegistry?.byKind?.[kind]);
      if (!kind || (!blueprint?.def && !blueprint?.meta)) {
        _setStatus(`Drop ignored: unknown component kind '${String(kind || "")}'.`);
        return;
      }
      if (!reactFlowInstance) return;
      const position = reactFlowInstance.screenToFlowPosition({ x: e.clientX, y: e.clientY });
      addKind(kind, position);
    },
    [reactFlowInstance, addKind, kindRegistry, _setStatus],
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

  const markRunSucceeded = useCallback(
    (payload) => {
      const rid = String(payload?.run_id || "").trim();
      emitUiEvent("ui_run_succeeded", {
        run_id: rid || null,
        outcome: "success",
      });

      if (runRecoveryRef.current.hadFailure) {
        const elapsed = runRecoveryRef.current.failedAtMs ? Date.now() - Number(runRecoveryRef.current.failedAtMs) : null;
        emitUiEvent("ui_error_recovered", {
          run_id: rid || null,
          duration_ms: Number.isFinite(elapsed) && elapsed >= 0 ? elapsed : null,
          outcome: "success",
        });
        runRecoveryRef.current = { hadFailure: false, failedAtMs: 0 };
      }

      if (guidedFlowRef.current.active) {
        const durationMs = guidedFlowRef.current.startedAtMs ? Date.now() - Number(guidedFlowRef.current.startedAtMs) : null;
        emitUiEvent("ui_guided_flow_completed", {
          run_id: rid || null,
          duration_ms: Number.isFinite(durationMs) && durationMs >= 0 ? durationMs : null,
          outcome: "success",
        });
        guidedFlowRef.current = { active: false, startedAtMs: 0 };
      }
    },
    [emitUiEvent],
  );

  const markRunFailed = useCallback(() => {
    runRecoveryRef.current = { hadFailure: true, failedAtMs: Date.now() };
    emitUiEvent("ui_run_failed", { outcome: "failure" });
  }, [emitUiEvent]);

  const runGraph = useCallback(async () => {
    emitUiEvent("ui_run_started", { outcome: "success" });
    setBusy(true);
    setRunResult(null);
    try {
      if (mode === "orbit") {
        const payload = await apiRunOrbitPass(apiBase, orbitConfig, { requireSchema: orbitRequireSchema, projectId: selectedProjectId || null });
        setRunResult(payload);
        setActiveRightTab("run");
        markRunSucceeded(payload);
        recordActivity("run", "Executed orbit pass run.", { run_id: String(payload?.run_id || "") });
        _setStatus(`Ran orbit pass (${payload?.run_id || "run"}).`);
        return { ok: true, payload };
      }
      if (profile === "qkd_link") {
        const payload = await apiRunQkd(apiBase, graphPayload, { executionMode: qkdExecutionMode, projectId: selectedProjectId || null });
        setRunResult(payload);
        setActiveRightTab("run");
        markRunSucceeded(payload);
        recordActivity("run", "Executed QKD run.", { run_id: String(payload?.run_id || "") });
        _setStatus(`Ran QKD (${payload?.run_id || "run"}).`);
        return { ok: true, payload };
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
        markRunSucceeded(payload);
        recordActivity("run", "Executed PIC simulation.", { run_id: String(payload?.run_id || "") });
        _setStatus("Simulated PIC netlist.");
        return { ok: true, payload };
      }
    } catch (err) {
      const msg = String(err?.message || err);
      setRunResult({ error: msg });
      setActiveRightTab("run");
      markRunFailed();
      recordActivity("run", "Run failed.", { error: msg });
      _setStatus(`Run failed: ${msg}`);
      return { ok: false, error: msg };
    } finally {
      setBusy(false);
    }
  }, [
    apiBase,
    graphPayload,
    profile,
    qkdExecutionMode,
    picSweepNmText,
    orbitConfig,
    orbitRequireSchema,
    mode,
    selectedProjectId,
    emitUiEvent,
    markRunSucceeded,
    markRunFailed,
    recordActivity,
    _setStatus,
  ]);

  const runGuidedFlowNow = useCallback(async () => {
    const result = await runGraph();
    if (result?.ok) {
      setGuidedFlowWizardOpen(false);
    }
    return result || { ok: false, error: "Run did not return a result." };
  }, [runGraph]);

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

  const scheduleLiveCrosstalkDrc = useCallback(() => {
    if (xtDebounceTimer.current) clearTimeout(xtDebounceTimer.current);
    xtDebounceTimer.current = setTimeout(() => runCrosstalkDrc({ reason: "live" }), 140);
  }, [runCrosstalkDrc]);

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
        const flow = _flowFromGraph(payload.optimized_graph, kindRegistry?.byKind);
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
    kindRegistry.byKind,
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
        const flow = _flowFromGraph(payload.optimized_graph, kindRegistry?.byKind);
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
    kindRegistry.byKind,
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

    const flow = _flowFromGraph(graph, kindRegistry?.byKind);
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
  }, [importText, setNodes, setEdges, kindRegistry.byKind, _setStatus]);

  const approvalControlsNode = selectedRunManifest?.run_id ? (
    <ApprovalControls
      approvalActor={approvalActor}
      approvalNote={approvalNote}
      onApprovalActorChange={(value) => setApprovalActor(String(value))}
      onApprovalNoteChange={(value) => setApprovalNote(String(value))}
      onApprove={approveSelectedRun}
      busy={busy}
    />
  ) : null;

  const demoDegraded = demoModeOpen && apiHealth.status !== "ok";
  const demoRunId = String(selectedRunManifest?.run_id || runResult?.run_id || workflowResult?.run_id || "").trim();
  const demoPacketHref = demoRunId ? _runBundleUrl(apiBase, demoRunId) : "";
  const demoDiffSummary =
    runsDiffResult?.diff?.violation_diff?.summary && typeof runsDiffResult.diff.violation_diff.summary === "object"
      ? runsDiffResult.diff.violation_diff.summary
      : runsDiffResult?.diff?.summary && typeof runsDiffResult.diff.summary === "object"
        ? runsDiffResult.diff.summary
        : null;
  const demoApprovalCount = Array.isArray(projectApprovals?.approvals) ? projectApprovals.approvals.length : 0;
  const demoPacketActionEnabled = !demoModeOpen || demoScene === "packet";

  return (
    <div className="ptApp">
      <AppTopBar
        programStageSubtitle={stageSubtitle(programStage)}
        mode={mode}
        onModeChange={(nextValue) => {
          const next = String(nextValue);
          const inferredStage = next === "runs" ? "compare" : next === "orbit" ? "validate" : "build";
          switchOperationalMode(next, { nextStage: inferredStage });
          setShowLanding(false);
        }}
        userMode={userMode}
        onUserModeChange={setUserMode}
        selectedViewPresetId={selectedViewPresetId}
        savedViews={savedViews}
        onViewPresetChange={applyViewPresetById}
        onSaveView={saveCurrentViewPreset}
        profile={profile}
        onProfileChange={(nextValue) => {
          const next = String(nextValue);
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
        graphId={graphId}
        onGraphIdChange={setGraphId}
        apiBase={apiBase}
        onApiBaseChange={setApiBase}
        onDemoMode={investorDemoCheckpoint}
        onPing={pingApi}
        busy={busy}
        onPrimaryAction={mode === "graph" ? compileGraph : mode === "orbit" ? validateOrbit : refreshRuns}
        primaryActionLabel={mode === "graph" ? "Compile" : mode === "orbit" ? "Validate" : "Refresh"}
        onRunOrDiff={mode === "runs" ? diffRuns : runGraph}
        runOrDiffLabel={mode === "runs" ? "Diff" : "Run"}
        runOrDiffDisabled={mode === "runs" ? !diffLhsRunId || !diffRhsRunId : false}
        showGraphDrc={mode === "graph" && profile === "pic_circuit"}
        onGraphDrc={() => runCrosstalkDrc({ reason: "manual" })}
        showLanding={showLanding}
        onToggleLanding={() => setShowLanding((v) => !v)}
        onExportPacket={exportDecisionPacket}
        exportPacketDisabled={!demoPacketActionEnabled}
        demoModeOpen={demoModeOpen}
        apiHealthStatus={apiHealth.status}
        apiHealthVersion={apiHealth.version}
        apiHealthError={apiHealth.error}
        showGraphProfileControls={mode === "graph"}
      />

      <nav className="ptStageNav" aria-label="Product stage navigation">
        {PRODUCT_STAGE_ITEMS.map((stage) => {
          const active = String(stage.id) === String(programStage);
          return (
            <button
              key={stage.id}
              className={`ptStagePill ${active ? "active" : ""}`}
              onClick={() => openProgramStage(stage.id)}
              type="button"
              disabled={demoModeOpen}
            >
              {stage.label}
            </button>
          );
        })}
      </nav>

      <WorkspaceContextBar
        projects={(projectsIndex?.projects || [])
          .map((p) => {
            const id = String(p?.project_id || "").trim();
            if (!id) return null;
            const count = Number(p?.run_count ?? 0);
            const name = Number.isFinite(count) && count > 0 ? `${id} (${count})` : id;
            return { id, name };
          })
          .filter(Boolean)}
        selectedProjectId={selectedProjectId}
        onProjectChange={handleWorkspaceProjectChange}
        rolePresets={ROLE_PRESET_OPTIONS}
        selectedRolePreset={userMode}
        onRolePresetChange={applyRolePreset}
        savedViews={(savedViews || []).map((v) => ({ id: String(v?.id || ""), name: String(v?.name || v?.id || "") })).filter((v) => v.id)}
        selectedSavedViewId={selectedViewPresetId}
        onSavedViewChange={applyViewPresetById}
        onSaveView={saveCurrentViewPreset}
        saveViewLabel="Save view"
        saveViewDisabled={demoModeOpen}
        recentActivity={recentActivity}
        onRecentActivityClick={handleRecentActivityClick}
        disabled={demoModeOpen}
      />

      {showLanding ? (
        <LandingWorkspace
          currentStage={programStage}
          onOpenStage={openProgramStage}
          onStartGuidedFlow={startGuidedFlow}
          onInvestorDemoCheckpoint={investorDemoCheckpoint}
          onDismiss={() => setShowLanding(false)}
        />
      ) : null}

      <GuidedFlowWizard
        open={guidedFlowWizardOpen}
        busy={busy}
        profile={profile}
        apiHealthStatus={apiHealth.status}
        scenario={scenario}
        circuit={circuit}
        initialGoal={guidedFlowInitialGoal}
        onClose={closeGuidedFlowWizard}
        onGoalChange={(goalId) => setGuidedFlowInitialGoal(String(goalId || "qkd"))}
        onTemplateApply={applyGuidedTemplate}
        onRunPreflight={runGuidedPreflight}
        onRun={runGuidedFlowNow}
        onOpenStage={openProgramStage}
      />

      {demoModeOpen ? (
        <section className="ptDemoWrap">
          <DemoModeOrchestrator
            initialScene={demoInitialScene}
            degraded={demoDegraded}
            degradedReason={apiHealth.status === "ok" ? "" : String(apiHealth.error || "API not healthy")}
            onSceneChange={handleDemoSceneChange}
            onExit={closeDemoMode}
          />
          <DemoProofSnapshot
            scene={demoScene}
            degraded={demoDegraded}
            decision={decisionContext.decision}
            confidence={decisionContext.confidenceScore}
            riskLevel={decisionContext.riskLevel}
            diffSummary={demoDiffSummary}
            approvalCount={demoApprovalCount}
            runId={demoRunId}
            packetHref={demoPacketHref}
          />
        </section>
      ) : null}

      <div className="ptMain" style={demoModeOpen ? { pointerEvents: "none" } : undefined}>
        <aside className="ptSidebar ptSidebarLeft">
          <LeftSidebarByMode
            mode={mode}
            graphProps={{
              busy,
              profile,
              paletteScope,
              onPaletteScopeChange: setPaletteScope,
              paletteQuery,
              onPaletteQueryChange: setPaletteQuery,
              filteredKindOptions,
              kindOptions,
              paletteSummary,
              kindRegistry,
              onAddKind: addKind,
              onLoadTemplate: loadTemplate,
              onOpenExport: () => setExportOpen(true),
              onOpenImport: () => setImportOpen(true),
              requireSchema,
              onRequireSchemaChange: setRequireSchema,
              kindBlueprint: _kindBlueprint,
              kindAvailability: _kindAvailability,
            }}
            orbitProps={{
              busy,
              orbitRequireSchema,
              onLoadPassEnvelope: () => {
                setOrbitConfig(_cloneJson(DEFAULT_ORBIT_PASS_CONFIG));
                setRunResult(null);
                setCompileResult(null);
                setOrbitValidateResult(null);
                setActiveRightTab("orbit");
                _setStatus("Loaded template: Orbit pass envelope.");
              },
              onOrbitRequireSchemaChange: setOrbitRequireSchema,
            }}
            runsProps={{
              busy,
              runsIndex,
              projectsIndex,
              selectedProjectId,
              onProjectChange: handleWorkspaceProjectChange,
              onRefreshAll: () => {
                refreshProjects();
                refreshRuns();
              },
              diffLhsRunId,
              diffRhsRunId,
              diffScope,
              onDiffLhsChange: setDiffLhsRunId,
              onDiffRhsChange: setDiffRhsRunId,
              onDiffScopeChange: setDiffScope,
              onDiffRuns: diffRuns,
              collectionsNode: (
                <RunCollectionsPanel
                  collections={collectionOptions}
                  selectedCollectionId={selectedCollectionId}
                  onCollectionChange={(value) => {
                    setSelectedCollectionId(String(value || ""));
                    setCollectionTagInput("");
                  }}
                  newCollectionName={newCollectionName}
                  onNewCollectionNameChange={setNewCollectionName}
                  onCreateCollection={createRunCollection}
                  selectedRunId={selectedRunForCollection}
                  runOptions={runOptionsForCollections}
                  runTags={selectedRunTags}
                  tagInput={collectionTagInput}
                  onTagInputChange={setCollectionTagInput}
                  onAddTag={addCollectionTag}
                  onRemoveTag={removeCollectionTag}
                  baselineRunId={String(selectedCollection?.baselineRunId || diffLhsRunId || "")}
                  candidateRunIds={selectedCollection?.candidateRunIds || []}
                  onBaselineRunChange={(runId) => {
                    setCollectionBaseline(runId);
                    setDiffLhsRunId(String(runId || ""));
                  }}
                  onCandidateRunIdsChange={(runIds) => {
                    const rows = Array.isArray(runIds) ? runIds : [];
                    setCollectionCandidates(rows);
                    if (rows.length) setDiffRhsRunId(String(rows[0] || ""));
                  }}
                  onUseSelectedAsBaseline={(runId) => {
                    setCollectionBaseline(runId);
                    if (runId) setDiffLhsRunId(String(runId));
                  }}
                  onAddSelectedAsCandidate={(runId) => {
                    const rid = String(runId || "").trim();
                    if (!rid) return;
                    const existing = Array.isArray(selectedCollection?.candidateRunIds) ? selectedCollection.candidateRunIds : [];
                    const merged = Array.from(new Set([...existing, rid]));
                    setCollectionCandidates(merged);
                    setDiffRhsRunId(rid);
                  }}
                  onRemoveSelectedFromCandidates={(runId) => {
                    const rid = String(runId || "").trim();
                    const existing = Array.isArray(selectedCollection?.candidateRunIds) ? selectedCollection.candidateRunIds : [];
                    const filtered = existing.filter((item) => String(item) !== rid);
                    setCollectionCandidates(filtered);
                    if (String(diffRhsRunId || "") === rid) {
                      setDiffRhsRunId(String(filtered[0] || ""));
                    }
                  }}
                  onClearCandidates={() => {
                    setCollectionCandidates([]);
                    setDiffRhsRunId("");
                  }}
                  createDisabled={busy}
                  tagDisabled={busy}
                  selectionDisabled={busy}
                />
              ),
            }}
          />
        </aside>

        <CenterWorkspacePane
          mode={mode}
          isDragOver={isDragOver}
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          nodeTypes={nodeTypes}
          onSelectionChange={(sel) => {
            const picked = sel?.nodes?.[0]?.id;
            setSelectedNodeId(picked ? String(picked) : null);
          }}
          onCanvasDrop={onCanvasDrop}
          onCanvasDragOver={onCanvasDragOver}
          onCanvasDragLeave={onCanvasDragLeave}
          orbitConfig={orbitConfig}
          onApplyOrbitConfigText={applyOrbitConfigText}
          runsIndex={runsIndex}
          selectedRunId={selectedRunId}
          diffLhsRunId={diffLhsRunId}
          diffRhsRunId={diffRhsRunId}
          onLoadRunManifest={loadRunManifest}
          onSetActiveRightTab={setActiveRightTab}
          onSetDiffLhsRunId={setDiffLhsRunId}
          onSetDiffRhsRunId={setDiffRhsRunId}
        />

        <aside className="ptSidebar ptSidebarRight">
          <RightSidebarTabs mode={mode} profile={profile} activeRightTab={activeRightTab} onChangeTab={setActiveRightTab} />

          {mode === "graph" ? (
            <GraphRightSidebarContent
              activeRightTab={activeRightTab}
              inspect={{
                selectedNode,
                kindRegistryByKind: kindRegistry?.byKind,
                kindRegistryStatus: kindRegistry?.status,
                onSetParam: setSelectedParamValue,
                prettyJson: _pretty,
                onDeleteSelected: deleteSelected,
                onApplySelectedParams: applySelectedParams,
                profile,
                scenario,
                bandOptions: BAND_OPTIONS,
                onSetScenario: setScenario,
                onSetStatus: _setStatus,
                qkdExecutionMode,
                onSetQkdExecutionMode: setQkdExecutionMode,
                onApplyScenarioText: applyScenarioText,
                uncertainty,
                onApplyUncertaintyText: applyUncertaintyText,
                finiteKey,
                onApplyFiniteKeyText: applyFiniteKeyText,
                circuit,
                onSetCircuit: setCircuit,
                picSweepNmText,
                onSetPicSweepNmText: setPicSweepNmText,
                onApplyCircuitText: applyCircuitText,
                xtGapUm,
                xtLengthUm,
                xtTargetDb,
                xtLive,
                onSetXtGapUm: setXtGapUm,
                onSetXtLengthUm: setXtLengthUm,
                onSetXtTargetDb: setXtTargetDb,
                onSetXtLive: setXtLive,
                xtHasRunOnceRef: xtHasRunOnce,
                onScheduleLiveDrc: scheduleLiveCrosstalkDrc,
                onRunCrosstalkDrc: runCrosstalkDrc,
                busy,
                invKind,
                onSetInvKind: setInvKind,
                phaseNodeIds,
                invPhaseNodeId,
                onSetInvPhaseNodeId: setInvPhaseNodeId,
                couplerNodeIds,
                invCouplerNodeId,
                onSetInvCouplerNodeId: setInvCouplerNodeId,
                invOutputNode,
                onSetInvOutputNode: setInvOutputNode,
                invOutputPort,
                onSetInvOutputPort: setInvOutputPort,
                invTargetFraction,
                onSetInvTargetFraction: setInvTargetFraction,
                invWavelengthObjectiveAgg,
                onSetInvWavelengthObjectiveAgg: setInvWavelengthObjectiveAgg,
                invCaseObjectiveAgg,
                onSetInvCaseObjectiveAgg: setInvCaseObjectiveAgg,
                invRobustnessCases,
                safeParseJson: _safeParseJson,
                onSetInvRobustnessCases: setInvRobustnessCases,
                onRunInvdesign: runInvdesign,
                onRunInvdesignWorkflow: runInvdesignWorkflow,
                metadata,
                onSetMetadata: setMetadata,
              }}
              compile={{
                compileResult,
                prettyJson: _pretty,
              }}
              drc={{
                xtResult,
                apiBase,
                buildRunArtifactUrl: _runArtifactUrl,
                buildRunManifestUrl: _runManifestUrl,
                prettyJson: _pretty,
              }}
              invdesign={{
                invResult,
                workflowResult,
                apiBase,
                buildRunArtifactUrl: _runArtifactUrl,
                buildRunManifestUrl: _runManifestUrl,
                buildRunBundleUrl: _runBundleUrl,
                prettyJson: _pretty,
              }}
              layout={{
                layoutPdk,
                onSetLayoutPdk: setLayoutPdk,
                layoutSettings,
                onSetLayoutSettings: setLayoutSettings,
                safeParseJson: _safeParseJson,
                onRunLayoutBuild: runLayoutBuild,
                busy,
                layoutBuildResult,
                apiBase,
                buildRunArtifactUrl: _runArtifactUrl,
                buildRunManifestUrl: _runManifestUrl,
                prettyJson: _pretty,
              }}
              lvs={{
                lvsSettings,
                onSetLvsSettings: setLvsSettings,
                safeParseJson: _safeParseJson,
                onRunLvsLite: runLvsLite,
                busy,
                layoutBuildResult,
                lvsResult,
                apiBase,
                buildRunArtifactUrl: _runArtifactUrl,
                buildRunManifestUrl: _runManifestUrl,
                prettyJson: _pretty,
              }}
              klayout={{
                klayoutPackSettings,
                onSetKlayoutPackSettings: setKlayoutPackSettings,
                safeParseJson: _safeParseJson,
                onRunKlayoutPack: runKlayoutPack,
                busy,
                layoutBuildResult,
                klayoutPackResult,
                apiBase,
                buildRunArtifactUrl: _runArtifactUrl,
                buildRunManifestUrl: _runManifestUrl,
                prettyJson: _pretty,
              }}
              spice={{
                spiceSettings,
                onSetSpiceSettings: setSpiceSettings,
                safeParseJson: _safeParseJson,
                onRunSpiceExport: runSpiceExport,
                busy,
                spiceResult,
                apiBase,
                buildRunArtifactUrl: _runArtifactUrl,
                buildRunManifestUrl: _runManifestUrl,
                prettyJson: _pretty,
              }}
              graphJson={{
                exportText,
                onCopied: () => _setStatus("Copied graph payload JSON to clipboard."),
                onCopyFailed: (err) => _setStatus(`Copy failed: ${String(err?.message || err)}`),
              }}
            />
          ) : null}

          {mode !== "runs" && activeRightTab === "run" && (
            <RunModePanel
              mode={mode}
              decision={decisionContext}
              compileResult={compileResult}
              runResult={runResult}
              apiBase={apiBase}
              onOpenProgramStage={openProgramStage}
              onSetActiveRightTab={setActiveRightTab}
              onExportDecisionPacket={exportDecisionPacket}
              onSaveCurrentViewPreset={saveCurrentViewPreset}
              onSetUserMode={setUserMode}
              onSetStatus={_setStatus}
              buildRunArtifactUrl={_runArtifactUrl}
              buildRunManifestUrl={_runManifestUrl}
              prettyJson={_pretty}
            />
          )}

          {mode === "orbit" && activeRightTab === "validate" && (
            <OrbitValidatePanel orbitValidateResult={orbitValidateResult} prettyJson={_pretty} />
          )}

          {mode === "orbit" && activeRightTab === "orbit" && (
            <OrbitConfigPanel
              orbitConfig={orbitConfig}
              prettyJson={_pretty}
              onCopied={() => _setStatus("Copied orbit config JSON to clipboard.")}
              onCopyFailed={(err) => _setStatus(`Copy failed: ${String(err?.message || err)}`)}
              panelId="pt-panel-orbit-orbit"
              labelledBy="pt-tab-orbit-orbit"
            />
          )}

          {mode === "runs" && activeRightTab === "manifest" && (
            <div id="pt-panel-runs-manifest" role="tabpanel" aria-labelledby="pt-tab-runs-manifest" className="ptRightBody">
              <ProvenanceTimeline
                apiBase={apiBase}
                selectedRunManifest={selectedRunManifest}
                compileResult={compileResult}
                projectApprovals={projectApprovals}
                buildRunManifestUrl={_runManifestUrl}
                buildRunArtifactUrl={_runArtifactUrl}
                buildRunBundleUrl={_runBundleUrl}
              />

              <CertificationWorkspace
                selectedRunManifest={selectedRunManifest}
                compileResult={compileResult}
                projectApprovals={projectApprovals}
                packetExportHref={
                  selectedRunManifest?.run_id ? _runBundleUrl(apiBase, selectedRunManifest.run_id) : ""
                }
                onPacketExport={exportDecisionPacket}
                approvalControls={approvalControlsNode}
                issues={decisionContext.blockers.map((message) => ({ level: "block", message }))}
              />

              <ManifestPanel
                apiBase={apiBase}
                selectedRunManifest={selectedRunManifest}
                projectApprovals={projectApprovals}
                approvalControls={approvalControlsNode}
                approvalResult={approvalResult}
                selectedRunGdsArtifacts={selectedRunGdsArtifacts}
                runsKlayoutGdsArtifactPath={runsKlayoutGdsArtifactPath}
                onRunsKlayoutGdsArtifactPathChange={setRunsKlayoutGdsArtifactPath}
                klayoutPackSettings={klayoutPackSettings}
                onApplyKlayoutPackSettings={(text) => {
                  const parsed = _safeParseJson(text);
                  if (!parsed.ok) return parsed;
                  if (!parsed.value || typeof parsed.value !== "object" || Array.isArray(parsed.value)) return { ok: false, error: "Settings must be a JSON object." };
                  setKlayoutPackSettings(parsed.value);
                  return { ok: true };
                }}
                onRunSelectedRunKlayoutPack={runSelectedRunKlayoutPack}
                busy={busy}
                runsKlayoutPackResult={runsKlayoutPackResult}
                runsWorkflowReplayResult={runsWorkflowReplayResult}
                onReplaySelectedWorkflowRun={replaySelectedWorkflowRun}
                buildRunManifestUrl={_runManifestUrl}
                buildRunArtifactUrl={_runArtifactUrl}
                buildRunBundleUrl={_runBundleUrl}
              />
            </div>
          )}

          {mode === "runs" && activeRightTab === "diff" && (
            <div id="pt-panel-runs-diff" role="tabpanel" aria-labelledby="pt-tab-runs-diff" className="ptRightBody">
              <DiffPanel
                runsDiffResult={runsDiffResult}
                busy={busy}
                diffHelpers={{
                  pretty: _pretty,
                }}
                compareLabNode={
                  <CompareLabPanel
                    runsIndex={runsIndex}
                    baselineRunId={diffLhsRunId}
                    candidateRunId={diffRhsRunId}
                    diffScope={diffScope}
                    busy={busy}
                    runsDiffResult={runsDiffResult}
                    onBaselineRunChange={setDiffLhsRunId}
                    onCandidateRunChange={setDiffRhsRunId}
                    onDiffScopeChange={setDiffScope}
                    onCompare={diffRuns}
                  />
                }
              />
            </div>
          )}
        </aside>
      </div>

      <StatusFooter
        busy={busy}
        statusText={statusText}
        stageText={stageLabel(programStage)}
        userMode={userMode}
        nodeCount={nodes.length}
        edgeCount={edges.length}
        hashText={compileResult?.graph_hash || runResult?.graph_hash || runResult?.config_hash || "n/a"}
      />

      <GraphJsonModals
        exportOpen={exportOpen}
        importOpen={importOpen}
        exportText={exportText}
        importText={importText}
        onCloseExport={() => setExportOpen(false)}
        onCloseImport={() => setImportOpen(false)}
        onImportTextChange={(value) => setImportText(String(value))}
        onImport={importGraph}
      />
    </div>
  );
}
