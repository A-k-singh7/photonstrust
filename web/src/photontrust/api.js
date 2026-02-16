function _base(baseUrl) {
  const raw = String(baseUrl || "").trim();
  if (!raw) return "";
  return raw.endsWith("/") ? raw.slice(0, -1) : raw;
}

async function _readJson(res) {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return { _raw: text };
  }
}

export async function apiHealthz(baseUrl) {
  const url = `${_base(baseUrl)}/healthz`;
  const res = await fetch(url, { method: "GET" });
  const payload = await _readJson(res);
  if (!res.ok) {
    const msg = payload?.detail || payload?._raw || res.statusText || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return payload;
}

export async function apiGetKindRegistry(baseUrl) {
  const url = `${_base(baseUrl)}/v0/registry/kinds`;
  const res = await fetch(url, { method: "GET" });
  const payload = await _readJson(res);
  if (!res.ok) {
    const msg = payload?.detail || payload?._raw || res.statusText || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return payload;
}

export async function apiCompileGraph(baseUrl, graph, { requireSchema = false } = {}) {
  const url = `${_base(baseUrl)}/v0/graph/compile`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ graph, require_schema: Boolean(requireSchema) }),
  });
  const payload = await _readJson(res);
  if (!res.ok) {
    const msg = payload?.detail || payload?._raw || res.statusText || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return payload;
}

export async function apiRunQkd(baseUrl, graph, { executionMode = "preview", outputRoot = "", projectId = null } = {}) {
  const url = `${_base(baseUrl)}/v0/qkd/run`;
  const body = { graph, execution_mode: String(executionMode || "preview") };
  if (projectId) body.project_id = String(projectId);
  if (outputRoot) body.output_root = String(outputRoot);
  const res = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await _readJson(res);
  if (!res.ok) {
    const msg = payload?.detail || payload?._raw || res.statusText || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return payload;
}

export async function apiRunOrbitPass(baseUrl, config, { outputRoot = "", requireSchema = false, projectId = null } = {}) {
  const url = `${_base(baseUrl)}/v0/orbit/pass/run`;
  const body = { config, require_schema: Boolean(requireSchema) };
  if (projectId) body.project_id = String(projectId);
  if (outputRoot) body.output_root = String(outputRoot);
  const res = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await _readJson(res);
  if (!res.ok) {
    const msg = payload?.detail || payload?._raw || res.statusText || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return payload;
}

export async function apiValidateOrbitPass(baseUrl, config, { requireSchema = false } = {}) {
  const url = `${_base(baseUrl)}/v0/orbit/pass/validate`;
  const body = { config, require_schema: Boolean(requireSchema) };
  const res = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await _readJson(res);
  if (!res.ok) {
    const msg = payload?.detail || payload?._raw || res.statusText || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return payload;
}

export async function apiSimulatePic(baseUrl, graph, { wavelengthNm = null, sweepNm = null } = {}) {
  const url = `${_base(baseUrl)}/v0/pic/simulate`;
  const body = { graph };
  if (Array.isArray(sweepNm) && sweepNm.length) body.wavelength_sweep_nm = sweepNm;
  if (wavelengthNm != null) body.wavelength_nm = Number(wavelengthNm);

  const res = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await _readJson(res);
  if (!res.ok) {
    const msg = payload?.detail || payload?._raw || res.statusText || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return payload;
}

export async function apiRunCrosstalkDrc(
  baseUrl,
  {
    gapUm,
    parallelLengthUm,
    wavelengthSweepNm,
    targetXtDb = null,
    pdk = { name: "generic_silicon_photonics" },
    model = null,
    corner = null,
    projectId = null,
    outputRoot = "",
  } = {},
) {
  const url = `${_base(baseUrl)}/v0/performance_drc/crosstalk`;
  const body = {
    gap_um: Number(gapUm),
    parallel_length_um: Number(parallelLengthUm),
    wavelength_sweep_nm: Array.isArray(wavelengthSweepNm) && wavelengthSweepNm.length ? wavelengthSweepNm.map(Number) : [1550],
    target_xt_db: targetXtDb == null ? null : Number(targetXtDb),
    pdk: pdk && typeof pdk === "object" ? pdk : { name: "generic_silicon_photonics" },
    model: model && typeof model === "object" ? model : null,
    corner: corner && typeof corner === "object" ? corner : null,
  };
  if (projectId) body.project_id = String(projectId);
  if (outputRoot) body.output_root = String(outputRoot);

  const res = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await _readJson(res);
  if (!res.ok) {
    const msg = payload?.detail || payload?._raw || res.statusText || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return payload;
}

export async function apiInvdesignMziPhase(
  baseUrl,
  graph,
  {
    phaseNodeId = "",
    targetOutputNode = "cpl_out",
    targetOutputPort = "out1",
    targetPowerFraction = 0.9,
    wavelengthSweepNm = null,
    steps = 181,
    robustnessCases = null,
    wavelengthObjectiveAgg = "mean",
    caseObjectiveAgg = "mean",
    projectId = null,
    outputRoot = "",
  } = {},
) {
  const url = `${_base(baseUrl)}/v0/pic/invdesign/mzi_phase`;
  const body = {
    graph,
    phase_node_id: phaseNodeId ? String(phaseNodeId) : undefined,
    target_output_node: String(targetOutputNode || "cpl_out"),
    target_output_port: String(targetOutputPort || "out1"),
    target_power_fraction: Number(targetPowerFraction),
    steps: Number.isFinite(Number(steps)) ? Number(steps) : 181,
  };
  if (projectId) body.project_id = String(projectId);
  if (Array.isArray(wavelengthSweepNm) && wavelengthSweepNm.length) {
    body.wavelength_sweep_nm = wavelengthSweepNm.map(Number);
  }
  if (Array.isArray(robustnessCases) && robustnessCases.length) {
    body.robustness_cases = robustnessCases;
  }
  if (wavelengthObjectiveAgg) body.wavelength_objective_agg = String(wavelengthObjectiveAgg);
  if (caseObjectiveAgg) body.case_objective_agg = String(caseObjectiveAgg);
  if (outputRoot) body.output_root = String(outputRoot);

  const res = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await _readJson(res);
  if (!res.ok) {
    const msg = payload?.detail || payload?._raw || res.statusText || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return payload;
}

export async function apiInvdesignCouplerRatio(
  baseUrl,
  graph,
  {
    couplerNodeId = "",
    targetOutputNode = "cpl_out",
    targetOutputPort = "out1",
    targetPowerFraction = 0.5,
    wavelengthSweepNm = null,
    steps = 101,
    robustnessCases = null,
    wavelengthObjectiveAgg = "mean",
    caseObjectiveAgg = "mean",
    projectId = null,
    outputRoot = "",
  } = {},
) {
  const url = `${_base(baseUrl)}/v0/pic/invdesign/coupler_ratio`;
  const body = {
    graph,
    coupler_node_id: couplerNodeId ? String(couplerNodeId) : undefined,
    target_output_node: String(targetOutputNode || "cpl_out"),
    target_output_port: String(targetOutputPort || "out1"),
    target_power_fraction: Number(targetPowerFraction),
    steps: Number.isFinite(Number(steps)) ? Number(steps) : 101,
  };
  if (projectId) body.project_id = String(projectId);
  if (Array.isArray(wavelengthSweepNm) && wavelengthSweepNm.length) {
    body.wavelength_sweep_nm = wavelengthSweepNm.map(Number);
  }
  if (Array.isArray(robustnessCases) && robustnessCases.length) {
    body.robustness_cases = robustnessCases;
  }
  if (wavelengthObjectiveAgg) body.wavelength_objective_agg = String(wavelengthObjectiveAgg);
  if (caseObjectiveAgg) body.case_objective_agg = String(caseObjectiveAgg);
  if (outputRoot) body.output_root = String(outputRoot);

  const res = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await _readJson(res);
  if (!res.ok) {
    const msg = payload?.detail || payload?._raw || res.statusText || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return payload;
}

export async function apiRunPicInvdesignWorkflowChain(
  baseUrl,
  graph,
  {
    invKind = "mzi_phase",
    phaseNodeId = "",
    couplerNodeId = "",
    targetOutputNode = "cpl_out",
    targetOutputPort = "out1",
    targetPowerFraction = null,
    steps = null,
    wavelengthSweepNm = null,
    robustnessCases = null,
    wavelengthObjectiveAgg = "mean",
    caseObjectiveAgg = "mean",
    layoutPdk = { name: "generic_silicon_photonics" },
    layoutSettings = null,
    lvsSettings = null,
    klayoutSettings = null,
    spiceSettings = null,
    requireSchema = false,
    projectId = null,
  } = {},
) {
  const url = `${_base(baseUrl)}/v0/pic/workflow/invdesign_chain`;

  const invdesign = {
    kind: String(invKind || "mzi_phase"),
    target_output_node: String(targetOutputNode || "cpl_out"),
    target_output_port: String(targetOutputPort || "out1"),
  };
  if (phaseNodeId) invdesign.phase_node_id = String(phaseNodeId);
  if (couplerNodeId) invdesign.coupler_node_id = String(couplerNodeId);
  if (targetPowerFraction != null) invdesign.target_power_fraction = Number(targetPowerFraction);
  if (steps != null && Number.isFinite(Number(steps))) invdesign.steps = Number(steps);
  if (Array.isArray(wavelengthSweepNm) && wavelengthSweepNm.length) invdesign.wavelength_sweep_nm = wavelengthSweepNm.map(Number);
  if (Array.isArray(robustnessCases) && robustnessCases.length) invdesign.robustness_cases = robustnessCases;
  if (wavelengthObjectiveAgg) invdesign.wavelength_objective_agg = String(wavelengthObjectiveAgg);
  if (caseObjectiveAgg) invdesign.case_objective_agg = String(caseObjectiveAgg);

  const body = {
    graph,
    require_schema: Boolean(requireSchema),
    invdesign,
    layout: {
      require_schema: Boolean(requireSchema),
      pdk: layoutPdk && typeof layoutPdk === "object" ? layoutPdk : { name: "generic_silicon_photonics" },
      settings: layoutSettings && typeof layoutSettings === "object" ? layoutSettings : undefined,
    },
    lvs_lite: {
      require_schema: Boolean(requireSchema),
      settings: lvsSettings && typeof lvsSettings === "object" ? lvsSettings : undefined,
    },
    klayout: {
      settings: klayoutSettings && typeof klayoutSettings === "object" ? klayoutSettings : undefined,
    },
    spice: {
      require_schema: Boolean(requireSchema),
      settings: spiceSettings && typeof spiceSettings === "object" ? spiceSettings : undefined,
    },
  };
  if (projectId) body.project_id = String(projectId);

  const res = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await _readJson(res);
  if (!res.ok) {
    const msg = payload?.detail || payload?._raw || res.statusText || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return payload;
}

export async function apiReplayPicInvdesignWorkflowChain(baseUrl, workflowRunId, { projectId = null } = {}) {
  const url = `${_base(baseUrl)}/v0/pic/workflow/invdesign_chain/replay`;
  const body = { workflow_run_id: String(workflowRunId || "") };
  if (projectId) body.project_id = String(projectId);
  const res = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await _readJson(res);
  if (!res.ok) {
    const msg = payload?.detail || payload?._raw || res.statusText || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return payload;
}

export async function apiBuildPicLayout(baseUrl, graph, { pdk = { name: "generic_silicon_photonics" }, settings = null, requireSchema = false, projectId = null } = {}) {
  const url = `${_base(baseUrl)}/v0/pic/layout/build`;
  const body = {
    graph,
    require_schema: Boolean(requireSchema),
    pdk: pdk && typeof pdk === "object" ? pdk : { name: "generic_silicon_photonics" },
    settings: settings && typeof settings === "object" ? settings : undefined,
  };
  if (projectId) body.project_id = String(projectId);
  const res = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await _readJson(res);
  if (!res.ok) {
    const msg = payload?.detail || payload?._raw || res.statusText || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return payload;
}

export async function apiRunPicLvsLite(baseUrl, graph, { layoutRunId = null, ports = null, routes = null, settings = null, requireSchema = false, projectId = null } = {}) {
  const url = `${_base(baseUrl)}/v0/pic/layout/lvs_lite`;
  const body = { graph, require_schema: Boolean(requireSchema) };
  if (projectId) body.project_id = String(projectId);
  if (layoutRunId) body.layout_run_id = String(layoutRunId);
  if (!layoutRunId) {
    if (ports && typeof ports === "object") body.ports = ports;
    if (routes && typeof routes === "object") body.routes = routes;
  }
  if (settings && typeof settings === "object") body.settings = settings;
  const res = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await _readJson(res);
  if (!res.ok) {
    const msg = payload?.detail || payload?._raw || res.statusText || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return payload;
}

export async function apiRunPicKlayoutPack(
  baseUrl,
  { layoutRunId = null, sourceRunId = null, settings = null, projectId = null, gdsArtifactPath = null } = {},
) {
  const url = `${_base(baseUrl)}/v0/pic/layout/klayout/run`;
  const body = {};
  if (projectId) body.project_id = String(projectId);
  if (sourceRunId) body.source_run_id = String(sourceRunId);
  if (layoutRunId) body.layout_run_id = String(layoutRunId);
  if (!sourceRunId && !layoutRunId) body.layout_run_id = "";
  if (gdsArtifactPath) body.gds_artifact_path = String(gdsArtifactPath);
  if (settings && typeof settings === "object") body.settings = settings;
  const res = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await _readJson(res);
  if (!res.ok) {
    const msg = payload?.detail || payload?._raw || res.statusText || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return payload;
}

export async function apiExportPicSpice(baseUrl, graph, { settings = null, requireSchema = false, projectId = null } = {}) {
  const url = `${_base(baseUrl)}/v0/pic/spice/export`;
  const body = { graph, require_schema: Boolean(requireSchema) };
  if (projectId) body.project_id = String(projectId);
  if (settings && typeof settings === "object") body.settings = settings;
  const res = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await _readJson(res);
  if (!res.ok) {
    const msg = payload?.detail || payload?._raw || res.statusText || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return payload;
}

export async function apiListRuns(baseUrl, { limit = 50, projectId = null } = {}) {
  const params = new URLSearchParams();
  params.set("limit", String(limit ?? 50));
  if (projectId) params.set("project_id", String(projectId));
  const url = `${_base(baseUrl)}/v0/runs?${params.toString()}`;
  const res = await fetch(url, { method: "GET" });
  const payload = await _readJson(res);
  if (!res.ok) {
    const msg = payload?.detail || payload?._raw || res.statusText || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return payload;
}

export async function apiGetRunManifest(baseUrl, runId) {
  const url = `${_base(baseUrl)}/v0/runs/${encodeURIComponent(String(runId || ""))}`;
  const res = await fetch(url, { method: "GET" });
  const payload = await _readJson(res);
  if (!res.ok) {
    const msg = payload?.detail || payload?._raw || res.statusText || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return payload;
}

export async function apiDiffRuns(baseUrl, lhsRunId, rhsRunId, { scope = "input", limit = 200 } = {}) {
  const url = `${_base(baseUrl)}/v0/runs/diff`;
  const body = {
    lhs_run_id: String(lhsRunId || ""),
    rhs_run_id: String(rhsRunId || ""),
    scope: String(scope || "input"),
    limit: Number.isFinite(Number(limit)) ? Number(limit) : 200,
  };
  const res = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await _readJson(res);
  if (!res.ok) {
    const msg = payload?.detail || payload?._raw || res.statusText || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return payload;
}

export async function apiListProjects(baseUrl, { limit = 200 } = {}) {
  const url = `${_base(baseUrl)}/v0/projects?limit=${encodeURIComponent(String(limit ?? 200))}`;
  const res = await fetch(url, { method: "GET" });
  const payload = await _readJson(res);
  if (!res.ok) {
    const msg = payload?.detail || payload?._raw || res.statusText || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return payload;
}

export async function apiListProjectApprovals(baseUrl, projectId, { limit = 50 } = {}) {
  const url = `${_base(baseUrl)}/v0/projects/${encodeURIComponent(String(projectId || ""))}/approvals?limit=${encodeURIComponent(String(limit ?? 50))}`;
  const res = await fetch(url, { method: "GET" });
  const payload = await _readJson(res);
  if (!res.ok) {
    const msg = payload?.detail || payload?._raw || res.statusText || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return payload;
}

export async function apiCreateProjectApproval(baseUrl, projectId, runId, { actor = "", note = "" } = {}) {
  const url = `${_base(baseUrl)}/v0/projects/${encodeURIComponent(String(projectId || ""))}/approvals`;
  const body = {
    run_id: String(runId || ""),
    actor: String(actor || ""),
    note: String(note || ""),
  };
  const res = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await _readJson(res);
  if (!res.ok) {
    const msg = payload?.detail || payload?._raw || res.statusText || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return payload;
}
