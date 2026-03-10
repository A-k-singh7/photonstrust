function asObject(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function asTrimmed(value, fallback = "") {
  const out = String(value == null ? "" : value).trim();
  return out || fallback;
}

function asCandidateRunIds(compare) {
  const source = Array.isArray(compare.candidate_run_ids)
    ? compare.candidate_run_ids
    : Array.isArray(compare.candidateRunIds)
      ? compare.candidateRunIds
      : [];
  return source.map((value) => asTrimmed(value)).filter(Boolean);
}

export function buildProjectWorkspaceSnapshot(input = {}) {
  const src = asObject(input);
  const projectId = asTrimmed(src.projectId);
  if (!projectId) return null;

  const candidateRunId = asTrimmed(src.candidateRunId);

  return {
    schema_version: "0.1",
    kind: "photonstrust.project_workspace",
    project_id: projectId,
    title: asTrimmed(src.title, projectId),
    template_id: asTrimmed(src.templateId, "qkd"),
    profile: asTrimmed(src.profile),
    stage: asTrimmed(src.stage, "build"),
    mode: asTrimmed(src.mode, "graph"),
    active_right_tab: asTrimmed(src.activeRightTab, "inspect"),
    user_mode: asTrimmed(src.userMode, "builder"),
    selected_run_id: asTrimmed(src.selectedRunId) || null,
    compare: {
      baseline_run_id: asTrimmed(src.baselineRunId) || null,
      candidate_run_ids: candidateRunId ? [candidateRunId] : [],
      scope: asTrimmed(src.diffScope, "input"),
    },
    graph: asObject(src.graph),
  };
}

export function normalizeProjectWorkspace(workspace) {
  const body = asObject(workspace);
  const compare = asObject(body.compare);
  const candidateRunIds = asCandidateRunIds(compare);
  const graph = asObject(body.graph);

  return {
    workspace: body,
    compare,
    userMode: asTrimmed(body.user_mode ?? body.userMode),
    stage: asTrimmed(body.stage),
    mode: asTrimmed(body.mode),
    activeRightTab: asTrimmed(body.active_right_tab ?? body.activeRightTab),
    baselineRunId: asTrimmed(compare.baseline_run_id ?? compare.baselineRunId),
    candidateRunIds,
    candidateRunId: candidateRunIds[0] || "",
    diffScope: asTrimmed(compare.scope ?? compare.diff_scope ?? body.diff_scope, "input"),
    selectedRunId: asTrimmed(body.selected_run_id ?? body.selectedRunId),
    graph: Object.keys(graph).length ? graph : null,
  };
}

export function buildProjectBootstrapRequest(input = {}) {
  const src = asObject(input);
  return {
    project_id: asTrimmed(src.projectId) || undefined,
    demo_case_id: asTrimmed(src.demoCaseId) || undefined,
    title: asTrimmed(src.title) || undefined,
    template_id: asTrimmed(src.templateId, "qkd"),
    workspace: asObject(src.workspace),
  };
}

export function getProjectWorkspaceSyncDelayMs(pauseUntilMs, nowMs = Date.now(), defaultDelayMs = 700) {
  const pauseUntil = Number.isFinite(Number(pauseUntilMs)) ? Number(pauseUntilMs) : 0;
  const now = Number.isFinite(Number(nowMs)) ? Number(nowMs) : Date.now();
  if (now < pauseUntil) {
    return Math.max(0, pauseUntil - now) + 50;
  }
  return Math.max(0, Number(defaultDelayMs) || 0);
}
