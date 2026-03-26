/**
 * App — Main application shell component.
 *
 * Manages graph state (nodes/edges), simulation execution, and workspace routing.
 * Key state: nodes, edges, profile, runResult, simOverlayVisible.
 * Subcomponents: AppTopBar, CenterWorkspacePane, GraphLeftSidebarPanel,
 *                GraphRightSidebarContent.
 */
import { Suspense, lazy, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  addEdge,
  useEdgesState,
  useNodesState,
  useReactFlow,
} from "@xyflow/react";

import "./App.css";
import ApprovalControls from "./features/runs/ApprovalControls";
import AppTopBar from "./features/shell/AppTopBar";
import GuidanceStrip from "./features/shell/GuidanceStrip";
import GraphJsonModals from "./features/shell/GraphJsonModals";
import LeftSidebarByMode from "./features/shell/LeftSidebarByMode";
import RightSidebarTabs from "./features/shell/RightSidebarTabs";
import StatusFooter from "./features/shell/StatusFooter";
import { PRODUCT_STAGE_ITEMS, PRODUCT_STAGE_ROUTES, stageLabel, stageSubtitle } from "./features/shell/copy";
import WorkspaceContextBar from "./features/workspace/WorkspaceContextBar";
import { createUiSessionId, createUiTelemetrySink } from "./state/uiTelemetry";
import {
  buildProjectWorkspaceSnapshot,
  getProjectWorkspaceSyncDelayMs,
} from "./state/projectWorkspace";
import { useProjectReviewActions } from "./hooks/useProjectReviewActions";
import { useProjectWorkspaceActions } from "./hooks/useProjectWorkspaceActions";
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
import { templatePicChain, templatePicMzi, templatePicSpiceImportHarness, templateQkdLink, templatePicBalancedReceiver, templatePicAwgDemux, templatePicRingFilter, templatePicCoherentRx, templatePicModulatorTx, templatePicSwitch2x2 } from "./photontrust/templates";
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
  apiGetKindRegistry,
  apiGetRunManifest,
  apiHealthz,
  apiListProjectApprovals,
  apiListProjects,
  apiListRuns,
  apiRunOrbitPass,
  apiRunQkd,
  apiSimulatePic,
  apiUpdateProjectWorkspace,
  apiValidateOrbitPass,
} from "./photontrust/api";

const CertificationWorkspace = lazy(() => import("./features/certify/CertificationWorkspace"));
const CompareLabPanel = lazy(() => import("./features/compare/CompareLabPanel"));
const DemoModeOrchestrator = lazy(() => import("./features/demo/DemoModeOrchestrator"));
const DemoProofSnapshot = lazy(() => import("./features/demo/DemoProofSnapshot"));
const GuidedFlowWizard = lazy(() => import("./features/guided-flow/GuidedFlowWizard"));
const GraphRightSidebarContent = lazy(() => import("./features/graph/GraphRightSidebarContent"));
const OrbitConfigPanel = lazy(() => import("./features/orbit/OrbitConfigPanel"));
const OrbitValidatePanel = lazy(() => import("./features/orbit/OrbitValidatePanel"));
const DiffPanel = lazy(() => import("./features/runs/DiffPanel"));
const ManifestPanel = lazy(() => import("./features/runs/ManifestPanel"));
const RunModePanel = lazy(() => import("./features/results/RunModePanel"));
const CenterWorkspacePane = lazy(() => import("./features/shell/CenterWorkspacePane"));
const LandingWorkspace = lazy(() => import("./features/shell/LandingWorkspace"));
const ProvenanceTimeline = lazy(() => import("./features/trust/ProvenanceTimeline"));
const RunCollectionsPanel = lazy(() => import("./features/workspace/RunCollectionsPanel"));

const DEFAULT_API_BASE = import.meta.env.VITE_PHOTONTRUST_API_BASE_URL || "http://127.0.0.1:8000";
const DEFAULT_LANDING_PROJECT_ID = "pilot_demo";
const DEFAULT_LANDING_DEMO_CASE_ID = "bbm92_metro_50km";

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

const GUIDED_GLOSSARY_TERMS = [
  {
    term: "QBER",
    meaning: "Quantum bit error rate. Lower values generally indicate cleaner key generation conditions.",
  },
  {
    term: "Key rate",
    meaning: "Estimated secure key bits per second produced by a run.",
  },
  {
    term: "Baseline",
    meaning: "Reference run used for candidate comparison and promotion decisions.",
  },
  {
    term: "Reliability card",
    meaning: "Decision artifact summarizing assumptions, outputs, and trust posture.",
  },
  {
    term: "Evidence bundle",
    meaning: "Portable run package for integrity verification, audit, and review.",
  },
];

const GUIDED_FLOW_VERSION = "2026-03-guided-power-v1";

const GUIDED_STEP_ITEMS = [
  { id: "api_health", label: "Check API health" },
  { id: "first_run", label: "Run first simulation" },
  { id: "compare", label: "Compare baseline vs candidate" },
  { id: "decision", label: "Review decision and blockers" },
];

function _defaultGuidedProgress() {
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

function _loadGuidedProgress() {
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

function _saveGuidedProgress(progress) {
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

function _ensureNewcomerId() {
  const existing = String(localStorage.getItem("pt_newcomer_id") || "").trim();
  if (existing) return existing;
  const generated =
    typeof globalThis?.crypto?.randomUUID === "function"
      ? globalThis.crypto.randomUUID()
      : `anon-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  localStorage.setItem("pt_newcomer_id", generated);
  return generated;
}

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

function _publishedBundleUrl(baseUrl, digest) {
  const base = _baseUrl(baseUrl);
  return `${base}/v0/evidence/bundle/by-digest/${encodeURIComponent(String(digest || ""))}`;
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

function PanelLoading({ message }) {
  return (
    <div className="ptRightSection ptPanelLoading" role="status" aria-live="polite" aria-busy="true">
      <div className="ptHint">{String(message || "Loading panel...")}</div>
    </div>
  );
}

export default function App() {
  const nodeTypes = useMemo(() => ({ ptNode: PtNode }), []);

  const [apiBase, setApiBase] = useState(() => localStorage.getItem("pt_api_base") || DEFAULT_API_BASE);
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
  const [experienceMode, setExperienceMode] = useState(() => localStorage.getItem("pt_experience_mode") || "guided");
  const [guidedProgress, setGuidedProgress] = useState(() => _loadGuidedProgress());
  const [newcomerId] = useState(() => _ensureNewcomerId());
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
  const startupPingStartedRef = useRef(false);
  const landingWorkspacePreparedRef = useRef(false);
  const projectWorkspaceLoadRef = useRef("");
  const projectWorkspaceSyncTimerRef = useRef(null);
  const projectWorkspacePauseUntilRef = useRef(0);
  const [guidedFlowWizardOpen, setGuidedFlowWizardOpen] = useState(false);
  const [guidedFlowInitialGoal, setGuidedFlowInitialGoal] = useState("qkd");
  const newcomerFlowRef = useRef({ active: false, startedAtMs: 0, completed: false });
  const guidedStepSnapshotRef = useRef(guidedProgress?.steps || {});

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
  const [bundlePublishResult, setBundlePublishResult] = useState(null);
  const [bundleVerifyResult, setBundleVerifyResult] = useState(null);
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
  const [simOverlayVisible, setSimOverlayVisible] = useState(true);
  const [busy, setBusy] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [paletteQuery, setPaletteQuery] = useState("");
  const [paletteScope, setPaletteScope] = useState("all");
  const [statusText, setStatusText] = useState("Ready.");
  const statusTimer = useRef(null);
  const [connectionWarning, setConnectionWarning] = useState("");
  const connWarnTimer = useRef(null);

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

  const projectWorkspaceSnapshot = useMemo(() => {
    return buildProjectWorkspaceSnapshot({
      projectId: selectedProjectId,
      title: metadata?.title,
      templateId: profile === "pic_circuit" ? "pic_mzi" : "qkd",
      profile,
      stage: programStage,
      mode,
      activeRightTab,
      userMode,
      selectedRunId: selectedRunManifest?.run_id || selectedRunId,
      baselineRunId: diffLhsRunId,
      candidateRunId: diffRhsRunId,
      diffScope,
      graph: graphPayload,
    });
  }, [selectedProjectId, metadata, profile, programStage, mode, activeRightTab, userMode, selectedRunManifest, selectedRunId, diffLhsRunId, diffRhsRunId, diffScope, graphPayload]);

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

  const guidedRunId = useMemo(
    () => String(runResult?.run_id || selectedRunManifest?.run_id || "").trim(),
    [runResult?.run_id, selectedRunManifest?.run_id],
  );

  const guidedCompareDone = useMemo(
    () =>
      Boolean(
        runsDiffResult?.diff ||
          (runsDiffResult && typeof runsDiffResult === "object" && !String(runsDiffResult.error || "").trim()),
      ),
    [runsDiffResult],
  );

  const guidedChecklist = useMemo(
    () =>
      GUIDED_STEP_ITEMS.map((step) => ({
        id: String(step.id),
        label: String(step.label),
        done: guidedProgress?.steps?.[String(step.id)] === true,
      })),
    [guidedProgress],
  );

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

  const emitNewcomerEvent = useCallback(
    (eventName, payload = {}, extras = {}) => {
      emitUiEvent(eventName, {
        profile,
        outcome: String(extras?.outcome || "success"),
        payload: {
          newcomer_id: newcomerId,
          flow: String(experienceMode || "guided"),
          flow_version: GUIDED_FLOW_VERSION,
          is_newcomer: true,
          ...(payload && typeof payload === "object" ? payload : {}),
        },
      });
    },
    [emitUiEvent, experienceMode, newcomerId, profile],
  );

  const markGuidedStep = useCallback(
    (stepId, { reason = "auto" } = {}) => {
      const step = String(stepId || "").trim();
      if (!step || !Object.prototype.hasOwnProperty.call(guidedStepSnapshotRef.current || {}, step)) return;

      let stepped = false;
      let completedNow = false;
      let stepIndex = 0;
      let completedAt = null;
      setGuidedProgress((prev) => {
        const base = _saveGuidedProgress(prev);
        if (base.steps[step] === true) return base;

        const next = {
          ...base,
          steps: { ...base.steps, [step]: true },
          completed: false,
          completed_at: base.completed_at || null,
        };
        const allDone = GUIDED_STEP_ITEMS.every((item) => next.steps[String(item.id)] === true);
        if (allDone) {
          next.completed = true;
          next.completed_at = new Date().toISOString();
          completedNow = base.completed !== true;
          completedAt = next.completed_at;
        }

        stepped = true;
        stepIndex = GUIDED_STEP_ITEMS.findIndex((item) => String(item.id) === step) + 1;
        guidedStepSnapshotRef.current = next.steps;
        return _saveGuidedProgress(next);
      });

      if (!stepped) return;
      const enteredAt = Number(newcomerFlowRef.current?.startedAtMs || Date.now());
      emitNewcomerEvent("newcomer_step_completed", {
        step_id: step,
        step_index: Math.max(0, stepIndex),
        reason: String(reason || "auto"),
        time_from_enter_ms: Math.max(0, Date.now() - enteredAt),
      });

      if (completedNow && newcomerFlowRef.current?.active) {
        newcomerFlowRef.current = {
          ...newcomerFlowRef.current,
          completed: true,
        };
        emitNewcomerEvent("newcomer_flow_completed", {
          completed_at: completedAt,
          time_from_enter_ms: Math.max(0, Date.now() - enteredAt),
        });
      }
    },
    [emitNewcomerEvent],
  );

  useEffect(() => {
    return () => {
      if (statusTimer.current) clearTimeout(statusTimer.current);
      if (xtDebounceTimer.current) clearTimeout(xtDebounceTimer.current);
      if (projectWorkspaceSyncTimerRef.current) clearTimeout(projectWorkspaceSyncTimerRef.current);
    };
  }, []);

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

  const applyGraphObject = useCallback(
    (graph, { statusText = "" } = {}) => {
      if (!graph || typeof graph !== "object" || Array.isArray(graph)) {
        return { ok: false, error: "Graph must be a JSON object." };
      }

      const nextProfile = String(graph.profile || "").trim();
      if (nextProfile !== "qkd_link" && nextProfile !== "pic_circuit") {
        return { ok: false, error: "Graph profile must be qkd_link or pic_circuit." };
      }

      setProfile(nextProfile);
      setGraphId(String(graph.graph_id || _defaultGraphIdForProfile(nextProfile)));
      setMetadata(graph.metadata && typeof graph.metadata === "object" ? graph.metadata : { title: "Imported Graph", description: "" });
      if (nextProfile === "qkd_link") {
        const nextScenario = graph.scenario && typeof graph.scenario === "object" ? graph.scenario : { ...DEFAULT_QKD_SCENARIO };
        setScenario(nextScenario);
        setQkdExecutionMode(String(nextScenario.execution_mode || "preview"));
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
      setWorkflowResult(null);
      setRunsWorkflowReplayResult(null);
      setLayoutBuildResult(null);
      setLvsResult(null);
      setKlayoutPackResult(null);
      setSpiceResult(null);
      if (statusText) _setStatus(statusText);
      return { ok: true };
    },
    [kindRegistry.byKind, setNodes, setEdges, _setStatus],
  );

  const { hydrateProjectWorkspace, bootstrapProjectWorkspace } = useProjectWorkspaceActions({
    apiBase,
    applyGraphObject,
    loadRunManifest,
    projectWorkspaceLoadRef,
    projectWorkspacePauseUntilRef,
    refreshProjects,
    refreshRuns,
    setActiveRightTab,
    setApprovalNote,
    setApprovalResult,
    setBundlePublishResult,
    setBundleVerifyResult,
    setBusy,
    setDiffLhsRunId,
    setDiffRhsRunId,
    setDiffScope,
    setMode,
    setProgramStage,
    setProjectApprovals,
    setSelectedProjectId,
    setSelectedRunId,
    setSelectedRunManifest,
    setRunsDiffResult,
    setShowLanding,
    setUserMode,
    setStatus: _setStatus,
  });

  const { approveSelectedRun, diffRuns, exportDecisionPacket, publishDecisionPacket, verifyPublishedDecisionPacket } = useProjectReviewActions({
    apiBase,
    approvalActor,
    approvalNote,
    buildRunBundleUrl: _runBundleUrl,
    bundlePublishResult,
    diffLhsRunId,
    diffRhsRunId,
    diffScope,
    emitUiEvent,
    recordActivity,
    runResult,
    selectedRunManifest,
    setApprovalResult,
    setBusy,
    setBundlePublishResult,
    setBundleVerifyResult,
    setProjectApprovals,
    setRunsDiffResult,
    setStatus: _setStatus,
    workflowResult,
  });

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
    localStorage.setItem("pt_experience_mode", String(experienceMode));
  }, [experienceMode]);

  useEffect(() => {
    guidedStepSnapshotRef.current = guidedProgress?.steps || {};
    _saveGuidedProgress(guidedProgress);
  }, [guidedProgress]);

  useEffect(() => {
    if (experienceMode === "guided") {
      if (!newcomerFlowRef.current.active) {
        newcomerFlowRef.current = {
          active: true,
          startedAtMs: Date.now(),
          completed: guidedProgress?.completed === true,
        };
        emitNewcomerEvent("newcomer_flow_entered", {
          entered_at: new Date().toISOString(),
        });
      }
      return;
    }

    if (newcomerFlowRef.current.active) {
      const startedAt = Number(newcomerFlowRef.current.startedAtMs || Date.now());
      const completed = newcomerFlowRef.current.completed === true || guidedProgress?.completed === true;
      emitNewcomerEvent(
        "newcomer_flow_exited",
        {
          completed,
          time_from_enter_ms: Math.max(0, Date.now() - startedAt),
        },
        { outcome: completed ? "success" : "abandoned" },
      );
      newcomerFlowRef.current = {
        active: false,
        startedAtMs: 0,
        completed,
      };
    }
  }, [experienceMode, guidedProgress?.completed, emitNewcomerEvent]);

  useEffect(() => {
    if (apiHealth.status === "ok") markGuidedStep("api_health", { reason: "api_health_ok" });
  }, [apiHealth.status, markGuidedStep]);

  useEffect(() => {
    if (guidedRunId) markGuidedStep("first_run", { reason: "run_detected" });
  }, [guidedRunId, markGuidedStep]);

  useEffect(() => {
    if (guidedCompareDone) markGuidedStep("compare", { reason: "diff_detected" });
  }, [guidedCompareDone, markGuidedStep]);

  useEffect(() => {
    if (String(activeRightTab || "") !== "run") return;
    if (mode === "runs") return;
    if (!guidedRunId && !guidedCompareDone) return;
    markGuidedStep("decision", { reason: "run_tab_reviewed" });
  }, [activeRightTab, mode, guidedRunId, guidedCompareDone, markGuidedStep]);

  useEffect(() => {
    localStorage.setItem("pt_user_mode", String(userMode));
  }, [userMode]);

  useEffect(() => {
    if (showLanding && !demoModeOpen) return;
    if (telemetrySessionStartedRef.current) return;
    telemetrySessionStartedRef.current = true;
    emitUiEvent("ui_session_started", { outcome: "success" });
    recordActivity("session", "UI session started.", { user_mode: userMode, profile });
  }, [emitUiEvent, profile, recordActivity, userMode, showLanding, demoModeOpen]);

  useEffect(() => {
    localStorage.setItem("pt_project_id", String(selectedProjectId));
  }, [selectedProjectId]);

  useEffect(() => {
    const pid = String(selectedProjectId || "").trim();
    if (!pid) {
      projectWorkspaceLoadRef.current = "";
      return;
    }
    if (apiHealth.status !== "ok") return;
    if (projectWorkspaceLoadRef.current === pid) return;
    projectWorkspaceLoadRef.current = pid;
    void hydrateProjectWorkspace(pid, { dismissLanding: false, loadRuns: true, silentMissing: true, statusText: "" });
  }, [apiHealth.status, selectedProjectId, hydrateProjectWorkspace]);

  useEffect(() => {
    if (!showLanding || demoModeOpen) return;
    if (landingWorkspacePreparedRef.current) return;
    if (apiHealth.status !== "ok") return;
    if (String(selectedProjectId || "").trim()) {
      landingWorkspacePreparedRef.current = true;
      return;
    }
    landingWorkspacePreparedRef.current = true;
    void bootstrapProjectWorkspace({
      projectId: DEFAULT_LANDING_PROJECT_ID,
      demoCaseId: DEFAULT_LANDING_DEMO_CASE_ID,
      title: "Pilot Demo Workspace",
      templateId: "qkd",
      workspace: {
        stage: "build",
        mode: "graph",
        active_right_tab: "inspect",
        user_mode: "builder",
      },
      dismissLanding: false,
      loadRuns: true,
      statusText: "Prepared sample project workspace.",
    });
  }, [apiHealth.status, bootstrapProjectWorkspace, demoModeOpen, selectedProjectId, showLanding]);

  useEffect(() => {
    if (!selectedProjectId || !projectWorkspaceSnapshot) return;
    if (projectWorkspaceSyncTimerRef.current) clearTimeout(projectWorkspaceSyncTimerRef.current);
    const delayMs = getProjectWorkspaceSyncDelayMs(projectWorkspacePauseUntilRef.current);
    projectWorkspaceSyncTimerRef.current = setTimeout(async () => {
      try {
        await apiUpdateProjectWorkspace(apiBase, selectedProjectId, projectWorkspaceSnapshot);
      } catch (err) {
        _setStatus(`Workspace sync failed: ${String(err?.message || err)}`);
      }
    }, delayMs);
    return () => {
      if (projectWorkspaceSyncTimerRef.current) clearTimeout(projectWorkspaceSyncTimerRef.current);
    };
  }, [apiBase, selectedProjectId, projectWorkspaceSnapshot, _setStatus]);

  useEffect(() => {
    setBundlePublishResult(null);
    setBundleVerifyResult(null);
  }, [selectedRunManifest?.run_id]);

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
    if (startupPingStartedRef.current) return;
    startupPingStartedRef.current = true;
    // Best-effort API ping on first app load.
    pingApi();
  }, [pingApi]);

  useEffect(() => {
    if (mode !== "runs") return;
    if (projectsIndex.status === "idle") refreshProjects();
    if (runsIndex.status === "idle") refreshRuns();
  }, [mode, projectsIndex.status, runsIndex.status, refreshProjects, refreshRuns]);

  useEffect(() => {
    if (experienceMode !== "guided") return;
    if (mode !== "graph" || profile !== "pic_circuit") return;
    if (!["drc", "invdesign", "layout", "lvs", "klayout", "spice"].includes(String(activeRightTab || ""))) return;
    setActiveRightTab("inspect");
  }, [experienceMode, mode, profile, activeRightTab]);

  const _showConnWarning = useCallback((msg) => {
    setConnectionWarning(String(msg || ""));
    if (connWarnTimer.current) clearTimeout(connWarnTimer.current);
    connWarnTimer.current = setTimeout(() => setConnectionWarning(""), 2000);
  }, []);

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

      const fromDomain = _nodePortDomain(sourceNode, "out", fromPort);
      const toDomain = _nodePortDomain(targetNode, "in", toPort);

      if (fromDomain !== toDomain) {
        const msg = `Cannot connect ${fromDomain} output to ${toDomain} input.`;
        _setStatus(
          `Blocked connection: ${sourceId}.${fromPort} (${fromDomain}) -> ${targetId}.${toPort} (${toDomain}).`,
        );
        _showConnWarning(msg);
        return;
      }
      if (profile === "pic_circuit" && fromDomain !== edgeKind) {
        const msg = `Blocked: edge kind ${edgeKind} incompatible with ${fromDomain} ports.`;
        _setStatus(msg);
        _showConnWarning(msg);
        return;
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
    [setEdges, profile, nodes, _setStatus, _showConnWarning],
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
        return;
      }
      if (templateId === "pic_balanced_receiver") {
        setProfile("pic_circuit");
        setGraphId("ui_pic_circuit");
        setCircuit({ ...DEFAULT_PIC_CIRCUIT });
        const t = templatePicBalancedReceiver();
        setNodes(t.nodes);
        setEdges(t.edges);
        _setStatus("Loaded template: Balanced Receiver.");
        return;
      }
      if (templateId === "pic_awg_demux") {
        setProfile("pic_circuit");
        setGraphId("ui_pic_circuit");
        setCircuit({ ...DEFAULT_PIC_CIRCUIT });
        const t = templatePicAwgDemux();
        setNodes(t.nodes);
        setEdges(t.edges);
        _setStatus("Loaded template: AWG Demux.");
        return;
      }
      if (templateId === "pic_ring_filter") {
        setProfile("pic_circuit");
        setGraphId("ui_pic_circuit");
        setCircuit({ ...DEFAULT_PIC_CIRCUIT });
        const t = templatePicRingFilter();
        setNodes(t.nodes);
        setEdges(t.edges);
        _setStatus("Loaded template: Ring Filter.");
        return;
      }
      if (templateId === "pic_coherent_rx") {
        setProfile("pic_circuit");
        setGraphId("ui_pic_circuit");
        setCircuit({ ...DEFAULT_PIC_CIRCUIT });
        const t = templatePicCoherentRx();
        setNodes(t.nodes);
        setEdges(t.edges);
        _setStatus("Loaded template: Coherent Receiver.");
        return;
      }
      if (templateId === "pic_modulator_tx") {
        setProfile("pic_circuit");
        setGraphId("ui_pic_circuit");
        setCircuit({ ...DEFAULT_PIC_CIRCUIT });
        const t = templatePicModulatorTx();
        setNodes(t.nodes);
        setEdges(t.edges);
        _setStatus("Loaded template: Modulator TX.");
        return;
      }
      if (templateId === "pic_switch_2x2") {
        setProfile("pic_circuit");
        setGraphId("ui_pic_circuit");
        setCircuit({ ...DEFAULT_PIC_CIRCUIT });
        const t = templatePicSwitch2x2();
        setNodes(t.nodes);
        setEdges(t.edges);
        _setStatus("Loaded template: 2×2 Switch.");
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

  const applyExperienceMode = useCallback(
    (nextValue) => {
      const next = String(nextValue || "guided").toLowerCase() === "power" ? "power" : "guided";
      setExperienceMode(next);
      emitUiEvent("ui_experience_mode_changed", { experience_mode: next, mode, profile });

      if (next === "guided") {
        setUserMode("builder");
        setShowLanding(true);
        if (
          mode === "graph" &&
          profile === "pic_circuit" &&
          ["drc", "invdesign", "layout", "lvs", "klayout", "spice"].includes(String(activeRightTab || ""))
        ) {
          setActiveRightTab("inspect");
        }
        _setStatus("Guided mode enabled. Start Here now prioritizes first-run and compare flow.");
        return;
      }

      _setStatus("Power mode enabled. Full advanced controls are available.");
    },
    [activeRightTab, emitUiEvent, mode, profile, _setStatus],
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

  const handleChecklistAction = useCallback(
    (stepId) => {
      const step = String(stepId || "").trim();
      if (!step) return;

      if (step === "api_health") {
        openProgramStage("build", { statusText: "Checking API health for guided onboarding." });
        pingApi();
        return;
      }

      if (step === "first_run") {
        openProgramStage("build", { statusText: "Prepare and run your first simulation." });
        if (!guidedRunId && profile !== "qkd_link") {
          loadTemplate("qkd");
        }
        setActiveRightTab("run");
        return;
      }

      if (step === "compare") {
        openProgramStage("compare", { statusText: "Compare baseline and candidate runs." });
        const selectedId = String(selectedRunManifest?.run_id || runResult?.run_id || "").trim();
        const orderedRuns = (Array.isArray(runsIndex?.runs) ? runsIndex.runs : [])
          .map((run) => String(run?.run_id || "").trim())
          .filter(Boolean);
        if (!diffLhsRunId) {
          const baseline = selectedId || orderedRuns[0] || "";
          if (baseline) setDiffLhsRunId(baseline);
        }
        if (!diffRhsRunId) {
          const baselineRef = String(diffLhsRunId || selectedId || "").trim();
          const candidate = orderedRuns.find((rid) => rid && rid !== baselineRef) || "";
          if (candidate) setDiffRhsRunId(candidate);
        }
        return;
      }

      if (step === "decision") {
        openProgramStage("run", { statusText: "Review decision summary and blockers." });
        setActiveRightTab("run");
        markGuidedStep("decision", { reason: "checklist_action" });
      }
    },
    [
      diffLhsRunId,
      diffRhsRunId,
      guidedRunId,
      loadTemplate,
      markGuidedStep,
      openProgramStage,
      pingApi,
      profile,
      runResult?.run_id,
      runsIndex?.runs,
      selectedRunManifest?.run_id,
    ],
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
      projectWorkspaceLoadRef.current = "";
      setSelectedProjectId(pid);
      setSelectedRunId(null);
      setSelectedRunManifest(null);
      setDiffLhsRunId("");
      setDiffRhsRunId("");
      setRunsDiffResult(null);
      setApprovalResult(null);
      setBundlePublishResult(null);
      setBundleVerifyResult(null);
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
    async (templateId = "qkd") => {
      const nextTemplate = String(templateId || "qkd");
      const nextProfile = nextTemplate === "pic_mzi" ? "pic_circuit" : "qkd_link";
      if (apiHealth.status === "ok") {
        const prepared = await bootstrapProjectWorkspace({
          projectId: nextTemplate === "pic_mzi" ? "guided_pic_demo" : "guided_qkd_demo",
          title: nextTemplate === "pic_mzi" ? "Guided PIC Workspace" : "Guided QKD Workspace",
          templateId: nextTemplate === "pic_mzi" ? "pic_mzi" : "qkd",
          workspace: {
            stage: "build",
            mode: "graph",
            active_right_tab: "inspect",
            user_mode: "builder",
          },
          dismissLanding: true,
          loadRuns: true,
          statusText: nextTemplate === "pic_mzi" ? "Prepared guided PIC workspace." : "Prepared guided QKD workspace.",
        });
        loadTemplate(nextTemplate === "pic_mzi" ? "pic_mzi" : "qkd");
        if (!prepared?.ok) {
          _setStatus("Fell back to a local template while project bootstrap was unavailable.");
        }
      } else {
        loadTemplate(nextTemplate === "pic_mzi" ? "pic_mzi" : "qkd");
      }
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
    [apiHealth.status, bootstrapProjectWorkspace, emitUiEvent, loadTemplate, openProgramStage, _setStatus],
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

  const investorDemoCheckpoint = useCallback(async () => {
    demoResumeRef.current = {
      mode,
      stage: programStage,
      tab: activeRightTab,
      userMode,
    };
    if (apiHealth.status === "ok") {
      await bootstrapProjectWorkspace({
        projectId: DEFAULT_LANDING_PROJECT_ID,
        demoCaseId: DEFAULT_LANDING_DEMO_CASE_ID,
        title: "Investor Demo Workspace",
        templateId: "qkd",
        workspace: {
          stage: "compare",
          mode: "runs",
          active_right_tab: "manifest",
          user_mode: "exec",
        },
        dismissLanding: true,
        loadRuns: true,
        statusText: "Prepared investor demo workspace.",
      });
    } else {
      setShowLanding(false);
    }
    setUserMode("exec");
    setDemoInitialScene("benchmark");
    setDemoScene("benchmark");
    setDemoModeOpen(true);
    applyDemoScene("benchmark", {
      statusText: "Demo mode started. Walk through benchmark, trust, decision, and packet scenes.",
    });
    recordActivity("demo_start", "Demo mode started from landing workspace.", { stage: "compare" });
  }, [activeRightTab, apiHealth.status, applyDemoScene, bootstrapProjectWorkspace, mode, programStage, recordActivity, userMode]);

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
    setIsDragOver((current) => (current ? current : true));
  }, []);

  const onCanvasDragLeave = useCallback(() => {
    setIsDragOver((current) => (current ? false : current));
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

  /** Attach per-node simulation metrics from the PIC simulate response. */
  const applySimResultsToNodes = useCallback(
    (simResponse) => {
      if (!simResponse || typeof simResponse !== "object") return;
      // The API may return component_results keyed by node id, or a flat results map.
      const compResults =
        simResponse.component_results ||
        simResponse.components ||
        simResponse.results ||
        null;
      if (!compResults || typeof compResults !== "object") return;

      setNodes((prev) =>
        prev.map((n) => {
          const entry = compResults[String(n.id)];
          if (!entry || typeof entry !== "object") return n;
          return {
            ...n,
            data: { ...n.data, simResult: entry },
          };
        }),
      );
    },
    [setNodes],
  );

  /** Remove simResult data from all nodes (hide overlay). */
  const clearSimResultsFromNodes = useCallback(() => {
    setNodes((prev) =>
      prev.map((n) => {
        if (!n.data?.simResult) return n;
        const { simResult: _, ...rest } = n.data;
        return { ...n, data: rest };
      }),
    );
  }, [setNodes]);

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
        if (payload?.run_id) {
          await refreshRuns(selectedProjectId || null);
          await loadRunManifest(payload.run_id);
        }
        recordActivity("run", "Executed orbit pass run.", { run_id: String(payload?.run_id || "") });
        _setStatus(`Ran orbit pass (${payload?.run_id || "run"}).`);
        return { ok: true, payload };
      }
      if (profile === "qkd_link") {
        const payload = await apiRunQkd(apiBase, graphPayload, { executionMode: qkdExecutionMode, projectId: selectedProjectId || null });
        setRunResult(payload);
        setActiveRightTab("run");
        markRunSucceeded(payload);
        if (payload?.run_id) {
          await refreshRuns(selectedProjectId || null);
          await loadRunManifest(payload.run_id);
        }
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
        if (simOverlayVisible) {
          applySimResultsToNodes(payload);
        }
        if (payload?.run_id) {
          await refreshRuns(selectedProjectId || null);
          await loadRunManifest(payload.run_id);
        }
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
    loadRunManifest,
    recordActivity,
    refreshRuns,
    _setStatus,
    simOverlayVisible,
    applySimResultsToNodes,
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

  const exportText = useMemo(() => {
    if (!exportOpen && activeRightTab !== "graph") return "";
    return _pretty(graphPayload);
  }, [graphPayload, exportOpen, activeRightTab]);

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
    const applied = applyGraphObject(graph, { statusText: "Imported graph into editor." });
    if (!applied?.ok) {
      _setStatus(String(applied?.error || "Import failed."));
      return;
    }
    setImportOpen(false);
    setActiveRightTab("inspect");
  }, [importText, applyGraphObject, _setStatus]);

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
  const workspaceReady = !showLanding || demoModeOpen;

  return (
    <div className="ptApp">
      <a className="ptSkipLink" href="#pt-main-workspace">
        Skip to workspace
      </a>

      <AppTopBar
        programStageSubtitle={stageSubtitle(programStage)}
        mode={mode}
        onModeChange={(nextValue) => {
          const next = String(nextValue);
          const inferredStage = next === "runs" ? "compare" : next === "orbit" ? "validate" : "build";
          switchOperationalMode(next, { nextStage: inferredStage });
          setShowLanding(false);
        }}
        experienceMode={experienceMode}
        onExperienceModeChange={applyExperienceMode}
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
        showGraphDrc={mode === "graph" && profile === "pic_circuit" && experienceMode !== "guided"}
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
        simOverlayVisible={simOverlayVisible}
        onToggleSimOverlay={() => {
          setSimOverlayVisible((prev) => {
            const next = !prev;
            if (!next) {
              clearSimResultsFromNodes();
            } else if (runResult && !runResult.error) {
              applySimResultsToNodes(runResult);
            }
            return next;
          });
        }}
        showSimOverlayToggle={mode === "graph" && profile === "pic_circuit"}
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
              aria-current={active ? "step" : undefined}
              aria-label={`${stage.label}: ${stageSubtitle(stage.id)}`}
            >
              {stage.label}
            </button>
          );
        })}
      </nav>

      {!showLanding ? (
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
      ) : null}

      {!showLanding && mode === "graph" ? (
        <GuidanceStrip
          experienceMode={experienceMode}
          checklist={guidedChecklist}
          glossaryTerms={GUIDED_GLOSSARY_TERMS}
          onStartGuidedFlow={startGuidedFlow}
          onOpenStage={openProgramStage}
          onExperienceModeChange={applyExperienceMode}
          onChecklistAction={handleChecklistAction}
        />
      ) : null}

      {showLanding ? (
        <Suspense fallback={<PanelLoading message="Loading start workspace..." />}>
          <LandingWorkspace
            currentStage={programStage}
            onOpenStage={openProgramStage}
            onStartGuidedFlow={startGuidedFlow}
            onInvestorDemoCheckpoint={investorDemoCheckpoint}
            onDismiss={() => setShowLanding(false)}
          />
        </Suspense>
      ) : null}

      {guidedFlowWizardOpen ? (
        <Suspense fallback={<PanelLoading message="Loading guided flow..." />}>
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
        </Suspense>
      ) : null}

      {demoModeOpen ? (
        <section className="ptDemoWrap" aria-label="Demo storyline">
          <Suspense fallback={<PanelLoading message="Loading demo storyline..." />}>
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
          </Suspense>
        </section>
      ) : null}

      <div
        id="pt-main-workspace"
        className="ptMain"
        style={demoModeOpen ? { pointerEvents: "none" } : undefined}
        role="main"
        tabIndex={-1}
        aria-label="Workspace main area"
      >
        {workspaceReady ? (
          <>
        <aside className="ptSidebar ptSidebarLeft" aria-label="Control sidebar">
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
                <Suspense fallback={<PanelLoading message="Loading run collections..." />}>
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
                </Suspense>
              ),
            }}
          />
        </aside>

        <Suspense
          fallback={
            <section className="ptCanvas" aria-label="Workspace loading">
              <div style={{ padding: 14 }}>
                <PanelLoading message="Loading workspace canvas..." />
              </div>
            </section>
          }
        >
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
        </Suspense>

        <aside className="ptSidebar ptSidebarRight" aria-label="Details sidebar">
          <RightSidebarTabs
            mode={mode}
            profile={profile}
            experienceMode={experienceMode}
            activeRightTab={activeRightTab}
            onChangeTab={setActiveRightTab}
          />

          {mode === "graph" ? (
            <Suspense fallback={<PanelLoading message="Loading graph sidebar..." />}>
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
                nodes={nodes}
              />
            </Suspense>
          ) : null}

          {mode !== "runs" && activeRightTab === "run" && (
            <div id={`pt-panel-${mode}-run`} role="tabpanel" aria-labelledby={`pt-tab-${mode}-run`} className="ptRightBody">
              <Suspense fallback={<PanelLoading message="Loading run guidance..." />}>
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
              </Suspense>
            </div>
          )}

          {mode === "orbit" && activeRightTab === "validate" && (
            <div id="pt-panel-orbit-validate" role="tabpanel" aria-labelledby="pt-tab-orbit-validate" className="ptRightBody">
              <Suspense fallback={<PanelLoading message="Loading orbit validation panel..." />}>
                <OrbitValidatePanel orbitValidateResult={orbitValidateResult} prettyJson={_pretty} />
              </Suspense>
            </div>
          )}

          {mode === "orbit" && activeRightTab === "orbit" && (
            <Suspense fallback={<PanelLoading message="Loading orbit config panel..." />}>
              <OrbitConfigPanel
                orbitConfig={orbitConfig}
                prettyJson={_pretty}
                onCopied={() => _setStatus("Copied orbit config JSON to clipboard.")}
                onCopyFailed={(err) => _setStatus(`Copy failed: ${String(err?.message || err)}`)}
                panelId="pt-panel-orbit-orbit"
                labelledBy="pt-tab-orbit-orbit"
              />
            </Suspense>
          )}

          {mode === "runs" && activeRightTab === "manifest" && (
            <div id="pt-panel-runs-manifest" role="tabpanel" aria-labelledby="pt-tab-runs-manifest" className="ptRightBody">
              <Suspense fallback={<PanelLoading message="Loading manifest and certification tools..." />}>
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
                  packetPublishHref={bundlePublishResult?.bundle_sha256 ? _publishedBundleUrl(apiBase, bundlePublishResult.bundle_sha256) : ""}
                  onPacketPublish={publishDecisionPacket}
                  packetPublishDisabled={busy || !selectedRunManifest?.run_id}
                  packetPublishResult={bundlePublishResult}
                  onPacketVerify={verifyPublishedDecisionPacket}
                  packetVerifyDisabled={busy || !bundlePublishResult?.bundle_sha256}
                  packetVerifyResult={bundleVerifyResult}
                  approvalControls={approvalControlsNode}
                  issues={decisionContext.blockers.map((message) => ({ level: "block", message }))}
                  onReturnToCompare={() => openProgramStage("compare", { statusText: "Returned to compare to review the decision delta." })}
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
              </Suspense>
            </div>
          )}

          {mode === "runs" && activeRightTab === "diff" && (
            <div id="pt-panel-runs-diff" role="tabpanel" aria-labelledby="pt-tab-runs-diff" className="ptRightBody">
              <Suspense fallback={<PanelLoading message="Loading diff workspace..." />}>
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
                      onContinueToCertify={() => openProgramStage("certify", { statusText: "Moved from compare into decision and evidence review." })}
                    />
                  }
                />
              </Suspense>
            </div>
          )}
        </aside>
          </>
        ) : (
          <section className="ptCard ptWorkspaceDeferred" aria-label="Workspace deferred until start stage">
            <div className="ptRightTitle">Workspace ready when you start</div>
            <div className="ptHint">
              Landing mode keeps heavy graph and run surfaces deferred for a faster first paint. Select a stage above or click
              <span className="ptMono"> Start Here </span>to enter the full workspace.
            </div>
          </section>
        )}
      </div>

      {workspaceReady ? (
        <StatusFooter
          busy={busy}
          statusText={statusText}
          stageText={stageLabel(programStage)}
          userMode={userMode}
          nodeCount={nodes.length}
          edgeCount={edges.length}
          hashText={compileResult?.graph_hash || runResult?.graph_hash || runResult?.config_hash || "n/a"}
        />
      ) : null}

      {connectionWarning ? (
        <div className="ptConnectionWarning" role="alert">{connectionWarning}</div>
      ) : null}

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
