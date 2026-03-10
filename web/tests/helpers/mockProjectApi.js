function qkdGraph(title = "Pilot Demo Workspace") {
  return {
    schema_version: "0.1",
    graph_id: "ui_qkd_link",
    profile: "qkd_link",
    metadata: {
      title,
      description: "Seeded project-backed workspace.",
      created_at: "2026-03-07",
    },
    scenario: {
      id: "ui_qkd_link",
      distance_km: 10,
      band: "c_1550",
      wavelength_nm: 1550,
      execution_mode: "preview",
    },
    uncertainty: {},
    finite_key: { enabled: false },
    nodes: [
      { id: "source_1", kind: "qkd.source", label: "Emitter", params: {}, ui: { position: { x: 80, y: 80 } } },
      { id: "channel_1", kind: "qkd.channel", label: "Fiber", params: {}, ui: { position: { x: 320, y: 80 } } },
      { id: "detector_1", kind: "qkd.detector", label: "Detector", params: {}, ui: { position: { x: 560, y: 80 } } },
      { id: "timing_1", kind: "qkd.timing", label: "Timing", params: {}, ui: { position: { x: 320, y: 240 } } },
      { id: "protocol_1", kind: "qkd.protocol", label: "Protocol", params: { name: "BBM92" }, ui: { position: { x: 560, y: 240 } } },
    ],
    edges: [
      { id: "e1", from: "source_1", to: "channel_1", kind: "optical", label: "emits" },
      { id: "e2", from: "channel_1", to: "detector_1", kind: "optical", label: "detects" },
    ],
  };
}

export function buildRun(projectId, runId, generatedAt = "2026-03-07T12:00:00Z") {
  return {
    run_id: runId,
    run_type: "qkd_run",
    generated_at: generatedAt,
    output_dir: `/tmp/${runId}`,
    project_id: projectId,
  };
}

export function buildRunManifest(projectId, runId) {
  return {
    schema_version: "0.1",
    run_id: runId,
    run_type: "qkd_run",
    generated_at: "2026-03-07T12:00:00Z",
    output_dir: `/tmp/${runId}`,
    input: {
      project_id: projectId,
    },
    artifacts: {
      reliability_card_json: "reports/reliability_card.json",
      run_manifest_json: "run_manifest.json",
    },
    outputs_summary: {
      qkd: {
        protocol_selected: "BBM92",
      },
    },
    provenance: {
      runtime: "playwright-mock",
    },
  };
}

function buildDiffPayload(lhsRunId, rhsRunId, scope = "input") {
  return {
    generated_at: "2026-03-07T12:00:00Z",
    lhs_run_id: lhsRunId,
    rhs_run_id: rhsRunId,
    scope,
    diff: {
      changed_fields: [
        {
          field: "input.protocol_selected",
          lhs: "BB84",
          rhs: "BBM92",
        },
      ],
      violation_diff: {
        summary: {
          new_count: 1,
          resolved_count: 0,
          applicability_changed_count: 0,
        },
      },
    },
  };
}

export async function installMockApi(page, options = {}) {
  const projectId = String(options.projectId || "pilot_demo");
  const defaultRunId = String(options.runId || "abcdef12345678");
  const approvals = Array.isArray(options.approvals) ? [...options.approvals] : [];
  const runs = Array.isArray(options.runs) && options.runs.length ? options.runs : [buildRun(projectId, defaultRunId)];
  const runManifests =
    options.runManifests && typeof options.runManifests === "object"
      ? { ...options.runManifests }
      : Object.fromEntries(
          runs
            .map((run) => {
              const runId = String(run?.run_id || "").trim();
              if (!runId) return null;
              return [runId, buildRunManifest(projectId, runId)];
            })
            .filter(Boolean),
        );

  const state = {
    manifest: {
      schema_version: "0.1",
      kind: "photonstrust.project_manifest",
      project_id: projectId,
      title: String(options.title || "Pilot Demo Workspace"),
      template_id: "qkd",
      demo_case_id: "bbm92_metro_50km",
      created_at: "2026-03-07T12:00:00Z",
      updated_at: "2026-03-07T12:00:00Z",
    },
    workspace: {
      schema_version: "0.1",
      kind: "photonstrust.project_workspace",
      project_id: projectId,
      title: String(options.title || "Pilot Demo Workspace"),
      template_id: "qkd",
      profile: "qkd_link",
      stage: "build",
      mode: "graph",
      active_right_tab: "inspect",
      user_mode: "builder",
      selected_run_id: null,
      compare: {
        baseline_run_id: null,
        candidate_run_ids: [],
        scope: "input",
      },
      graph: qkdGraph(String(options.title || "Pilot Demo Workspace")),
      ...(options.workspace && typeof options.workspace === "object" ? options.workspace : {}),
    },
    runs,
    runManifests,
    publishResult: null,
  };

  const requests = {
    bootstrapCalls: [],
    workspacePuts: [],
    diffCalls: [],
    approvalPosts: [],
    publishCalls: [],
    verifyCalls: [],
  };

  function projectSummary() {
    return {
      project_id: projectId,
      title: state.manifest.title,
      description: "Mock project workspace",
      template_id: state.manifest.template_id,
      demo_case_id: state.manifest.demo_case_id,
      created_at: state.manifest.created_at,
      updated_at: state.manifest.updated_at,
      workspace_present: true,
      approval_count: approvals.length,
      run_count: state.runs.length,
      last_run_at: state.runs[0]?.generated_at || null,
    };
  }

  function mergeWorkspace(update) {
    const next = update && typeof update === "object" ? update : {};
    const compare = next.compare && typeof next.compare === "object" ? next.compare : {};
    state.workspace = {
      ...state.workspace,
      ...next,
      compare: {
        ...(state.workspace.compare && typeof state.workspace.compare === "object" ? state.workspace.compare : {}),
        ...compare,
      },
    };
    state.manifest.updated_at = "2026-03-07T12:05:00Z";
  }

  await page.route("http://127.0.0.1:8000/**", async (route) => {
    const url = new URL(route.request().url());
    const method = route.request().method();

    function json(data, status = 200) {
      return route.fulfill({
        status,
        contentType: "application/json",
        body: JSON.stringify(data),
      });
    }

    if (url.pathname === "/healthz") {
      return json({ status: "ok", version: "test" });
    }
    if (url.pathname === "/v0/registry/kinds") {
      return json({ registry_hash: "mock-registry", registry: { kinds: [] } });
    }
    if (url.pathname === "/v0/projects/bootstrap" && method === "POST") {
      const body = route.request().postDataJSON() || {};
      requests.bootstrapCalls.push(body);
      if (body.workspace && typeof body.workspace === "object") {
        mergeWorkspace(body.workspace);
      }
      return json({
        generated_at: "2026-03-07T12:00:00Z",
        project: projectSummary(),
        manifest: state.manifest,
        workspace: state.workspace,
        provenance: { runtime: "playwright-mock" },
      });
    }
    if (url.pathname === "/v0/projects" && method === "GET") {
      return json({
        generated_at: "2026-03-07T12:00:00Z",
        runs_root: "/tmp/api_runs",
        projects: [projectSummary()],
        provenance: { runtime: "playwright-mock" },
      });
    }
    if (url.pathname === `/v0/projects/${projectId}` && method === "GET") {
      return json({
        generated_at: "2026-03-07T12:00:00Z",
        project: projectSummary(),
        manifest: state.manifest,
        workspace: state.workspace,
        provenance: { runtime: "playwright-mock" },
      });
    }
    if (url.pathname === `/v0/projects/${projectId}/workspace` && method === "GET") {
      return json({
        generated_at: "2026-03-07T12:00:00Z",
        project_id: projectId,
        workspace: state.workspace,
        provenance: { runtime: "playwright-mock" },
      });
    }
    if (url.pathname === `/v0/projects/${projectId}/workspace` && method === "PUT") {
      const body = route.request().postDataJSON() || {};
      const workspace = body.workspace && typeof body.workspace === "object" ? body.workspace : {};
      requests.workspacePuts.push(workspace);
      mergeWorkspace(workspace);
      return json({
        generated_at: "2026-03-07T12:00:00Z",
        project_id: projectId,
        workspace: state.workspace,
        provenance: { runtime: "playwright-mock" },
      });
    }
    if (url.pathname === `/v0/projects/${projectId}/approvals` && method === "GET") {
      return json({
        generated_at: "2026-03-07T12:00:00Z",
        project_id: projectId,
        approvals,
        provenance: { runtime: "playwright-mock" },
      });
    }
    if (url.pathname === `/v0/projects/${projectId}/approvals` && method === "POST") {
      const body = route.request().postDataJSON() || {};
      requests.approvalPosts.push(body);
      const approvalEvent = {
        recorded_at: "2026-03-07T12:10:00Z",
        project_id: projectId,
        run_id: String(body.run_id || state.workspace.selected_run_id || defaultRunId),
        actor: String(body.actor || "ui"),
        note: String(body.note || ""),
      };
      approvals.push(approvalEvent);
      return json({
        generated_at: "2026-03-07T12:10:00Z",
        approval: approvalEvent,
        project_id: projectId,
        provenance: { runtime: "playwright-mock" },
      });
    }
    if (url.pathname === "/v0/runs" && method === "GET") {
      return json({
        generated_at: "2026-03-07T12:00:00Z",
        runs_root: "/tmp/api_runs",
        project_id: url.searchParams.get("project_id") || null,
        runs: state.runs,
      });
    }
    if (url.pathname === "/v0/runs/diff" && method === "POST") {
      const body = route.request().postDataJSON() || {};
      requests.diffCalls.push(body);
      return json(buildDiffPayload(String(body.lhs_run_id || ""), String(body.rhs_run_id || ""), String(body.scope || "input")));
    }

    const runManifestMatch = url.pathname.match(/^\/v0\/runs\/([^/]+)$/);
    if (runManifestMatch && method === "GET") {
      const manifest = state.runManifests[String(runManifestMatch[1] || "")];
      if (manifest) return json(manifest);
    }

    const publishMatch = url.pathname.match(/^\/v0\/runs\/([^/]+)\/bundle\/publish$/);
    if (publishMatch && method === "POST") {
      const runId = String(publishMatch[1] || "");
      requests.publishCalls.push(runId);
      state.publishResult = {
        generated_at: "2026-03-07T12:00:00Z",
        bundle_sha256: "deadbeefcafebabe1234",
        bundle_bytes: 2048,
        bundle_path: "C:/tmp/published_bundle.zip",
        publish_manifest_path: "C:/tmp/published_bundle.manifest.json",
        verify: {
          ok: true,
          verified_files: 4,
          missing_files: 0,
          mismatched_files: 0,
        },
      };
      return json(state.publishResult);
    }

    if (url.pathname === "/v0/evidence/bundle/by-digest/deadbeefcafebabe1234/verify" && method === "GET") {
      requests.verifyCalls.push("deadbeefcafebabe1234");
      return json({
        generated_at: "2026-03-07T12:00:00Z",
        bundle_sha256: "deadbeefcafebabe1234",
        bundle_path: "C:/tmp/published_bundle.zip",
        publish_manifest_path: "C:/tmp/published_bundle.manifest.json",
        verify: {
          ok: true,
          verified_files: 4,
          missing_files: 0,
          mismatched_files: 0,
        },
      });
    }

    return json({ detail: `Unhandled mock route: ${method} ${url.pathname}` }, 404);
  });

  return { requests, state };
}
