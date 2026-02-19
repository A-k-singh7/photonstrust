import JsonBox from "../../components/common/JsonBox";

function pretty(value) {
  return JSON.stringify(value ?? null, null, 2);
}

function asString(value) {
  return String(value || "").trim();
}

function manifestUrl(buildRunManifestUrl, apiBase, runId) {
  if (typeof buildRunManifestUrl !== "function") return "";
  return buildRunManifestUrl(apiBase, runId);
}

function artifactUrl(buildRunArtifactUrl, apiBase, runId, relPath) {
  if (typeof buildRunArtifactUrl !== "function") return "";
  return buildRunArtifactUrl(apiBase, runId, relPath);
}

function bundleUrl(buildRunBundleUrl, apiBase, runId) {
  if (typeof buildRunBundleUrl !== "function") return "";
  return buildRunBundleUrl(apiBase, runId);
}

export default function ManifestPanel({
  apiBase,
  selectedRunManifest,
  projectApprovals,
  approvalControls,
  approvalResult,
  selectedRunGdsArtifacts,
  runsKlayoutGdsArtifactPath,
  onRunsKlayoutGdsArtifactPathChange,
  klayoutPackSettings,
  onApplyKlayoutPackSettings,
  onRunSelectedRunKlayoutPack,
  busy,
  runsKlayoutPackResult,
  runsWorkflowReplayResult,
  onReplaySelectedWorkflowRun,
  buildRunManifestUrl,
  buildRunArtifactUrl,
  buildRunBundleUrl,
}) {
  const hasRun = Boolean(selectedRunManifest?.run_id);
  const runId = asString(selectedRunManifest?.run_id);
  const workflow = selectedRunManifest?.outputs_summary?.pic_workflow;
  const hasWorkflow = hasRun && (asString(selectedRunManifest?.run_type) === "pic_workflow_invdesign_chain" || Boolean(workflow));
  const artifactMap = selectedRunManifest?.artifacts && typeof selectedRunManifest.artifacts === "object" ? selectedRunManifest.artifacts : null;

  return (
    <div className="ptRightSection">
      <div className="ptRightTitle">Run Manifest</div>
      {hasRun ? (
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

      {hasRun ? (
        <div className="ptCallout" style={{ marginTop: 10 }}>
          <div className="ptCalloutTitle">Approvals</div>
          <div className="ptHint">Append-only approval events are stored per project.</div>

          {approvalControls || null}

          {approvalResult ? <pre className="ptPre">{pretty(approvalResult)}</pre> : null}

          {projectApprovals?.status === "error" ? <div className="ptError">{String(projectApprovals.error || "Failed to load approvals.")}</div> : null}
          {projectApprovals?.status === "ok" ? (
            projectApprovals.approvals?.length ? (
              <pre className="ptPre">{pretty(projectApprovals.approvals)}</pre>
            ) : (
              <div className="ptHint">No approvals recorded for this project yet.</div>
            )
          ) : null}
        </div>
      ) : null}

      {hasWorkflow ? (
        <div className="ptCallout" style={{ marginTop: 10 }}>
          <div className="ptCalloutTitle">Workflow Chain</div>
          <div className="ptHint">
            <a href={bundleUrl(buildRunBundleUrl, apiBase, runId)} target="_blank" rel="noreferrer">
              Download evidence bundle (zip)
            </a>
          </div>

          <div className="ptHint" style={{ marginTop: 8 }}>
            {workflow?.invdesign_run_id ? (
              <>
                <a href={manifestUrl(buildRunManifestUrl, apiBase, workflow.invdesign_run_id)} target="_blank" rel="noreferrer">
                  Open invdesign child manifest (JSON)
                </a>
                <br />
              </>
            ) : null}
            {workflow?.layout_run_id ? (
              <>
                <a href={manifestUrl(buildRunManifestUrl, apiBase, workflow.layout_run_id)} target="_blank" rel="noreferrer">
                  Open layout build child manifest (JSON)
                </a>
                <br />
              </>
            ) : null}
            {workflow?.lvs_lite_run_id ? (
              <>
                <a href={manifestUrl(buildRunManifestUrl, apiBase, workflow.lvs_lite_run_id)} target="_blank" rel="noreferrer">
                  Open LVS-lite child manifest (JSON)
                </a>
                <br />
              </>
            ) : null}
            {workflow?.klayout_pack_run_id ? (
              <>
                <a href={manifestUrl(buildRunManifestUrl, apiBase, workflow.klayout_pack_run_id)} target="_blank" rel="noreferrer">
                  Open KLayout child manifest (JSON)
                </a>
                <br />
              </>
            ) : null}
            {workflow?.spice_export_run_id ? (
              <>
                <a href={manifestUrl(buildRunManifestUrl, apiBase, workflow.spice_export_run_id)} target="_blank" rel="noreferrer">
                  Open SPICE export child manifest (JSON)
                </a>
                <br />
              </>
            ) : null}
          </div>

          <div className="ptBtnRow" style={{ marginTop: 10 }}>
            <button className="ptBtn ptBtnPrimary" onClick={onReplaySelectedWorkflowRun} disabled={busy}>
              Replay Workflow
            </button>
          </div>

          {runsWorkflowReplayResult ? <pre className="ptPre">{pretty(runsWorkflowReplayResult)}</pre> : null}
        </div>
      ) : null}

      {hasRun && Array.isArray(selectedRunGdsArtifacts) && selectedRunGdsArtifacts.length ? (
        <div className="ptCallout" style={{ marginTop: 10 }}>
          <div className="ptCalloutTitle">KLayout Artifact Pack (DRC-lite)</div>
          <div className="ptHint">
            Runs the repo-owned KLayout macro template in batch mode on a selected <span className="ptMono">.gds</span> artifact from this run.
          </div>

          <label className="ptField" style={{ marginTop: 10 }}>
            <span>gds_artifact_path</span>
            <select
              value={runsKlayoutGdsArtifactPath || String(selectedRunGdsArtifacts?.[0]?.path || "")}
              onChange={(e) => onRunsKlayoutGdsArtifactPathChange && onRunsKlayoutGdsArtifactPathChange(String(e.target.value))}
            >
              {selectedRunGdsArtifacts.map((artifact) => {
                const path = asString(artifact?.path);
                if (!path) return null;
                const key = asString(artifact?.key);
                const label = key ? `${key}: ${path}` : path;
                return (
                  <option key={`runs_gds:${path}`} value={path}>
                    {label}
                  </option>
                );
              })}
            </select>
          </label>

          <JsonBox title="klayout pack settings (advanced)" value={klayoutPackSettings} onApply={onApplyKlayoutPackSettings} />

          <div className="ptBtnRow" style={{ marginTop: 10 }}>
            <button className="ptBtn ptBtnPrimary" onClick={onRunSelectedRunKlayoutPack} disabled={busy}>
              Run KLayout Pack on Selected GDS
            </button>
          </div>

          {runsKlayoutPackResult?.run_id && runsKlayoutPackResult?.artifact_relpaths ? (
            <div className="ptTrustBox" style={{ marginTop: 10 }}>
              <div className="ptJsonTitle">Artifacts (served)</div>
              <div className="ptHint">
                <a href={manifestUrl(buildRunManifestUrl, apiBase, runsKlayoutPackResult.run_id)} target="_blank" rel="noreferrer">
                  Open run manifest (JSON)
                </a>
              </div>
              <div className="ptHint" style={{ marginTop: 8 }}>
                {Object.entries(runsKlayoutPackResult.artifact_relpaths).map(([key, value]) => {
                  if (typeof value !== "string" || !value) return null;
                  return (
                    <div key={`runs_klayout_pack:${key}`}>
                      <a href={artifactUrl(buildRunArtifactUrl, apiBase, runsKlayoutPackResult.run_id, value)} target="_blank" rel="noreferrer">
                        {String(key)}
                      </a>{" "}
                      <span className="ptMono">[{String(value)}]</span>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : null}

          {runsKlayoutPackResult ? <pre className="ptPre">{pretty(runsKlayoutPackResult)}</pre> : <div className="ptHint">Run KLayout pack to see outputs.</div>}
        </div>
      ) : null}

      {hasRun ? (
        <div className="ptTrustBox">
          <div className="ptJsonTitle">Artifacts (served)</div>
          <div className="ptHint">
            <a href={manifestUrl(buildRunManifestUrl, apiBase, runId)} target="_blank" rel="noreferrer">
              Open manifest (JSON)
            </a>
          </div>
          {artifactMap ? (
            <div className="ptHint" style={{ marginTop: 8 }}>
              {Object.entries(artifactMap).map(([key, value]) => {
                if (typeof value !== "string" || !value) return null;
                return (
                  <div key={`a:${key}`}>
                    <a href={artifactUrl(buildRunArtifactUrl, apiBase, runId, value)} target="_blank" rel="noreferrer">
                      {String(key)}
                    </a>{" "}
                    <span className="ptMono">[{String(value)}]</span>
                  </div>
                );
              })}
            </div>
          ) : null}
          {Array.isArray(selectedRunManifest?.artifacts?.cards) ? (
            <div className="ptHint" style={{ marginTop: 10 }}>
              <div className="ptJsonTitle">cards</div>
              {selectedRunManifest.artifacts.cards.map((card, idx) => {
                if (!card || typeof card !== "object") return null;
                const sid = String(card.scenario_id || "");
                const band = String(card.band || "");
                const cardArtifacts = card.artifacts && typeof card.artifacts === "object" ? card.artifacts : {};
                return (
                  <div key={`c:${idx}`} style={{ marginTop: 6 }}>
                    <div>
                      <span className="ptMono">{sid}</span> <span className="ptMono">{band}</span>
                    </div>
                    {Object.entries(cardArtifacts).map(([key, value]) => {
                      if (typeof value !== "string" || !value) return null;
                      return (
                        <div key={`c:${idx}:${key}`}>
                          <a href={artifactUrl(buildRunArtifactUrl, apiBase, runId, value)} target="_blank" rel="noreferrer">
                            {String(key)}
                          </a>{" "}
                          <span className="ptMono">[{String(value)}]</span>
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

      {selectedRunManifest ? <pre className="ptPre">{pretty(selectedRunManifest)}</pre> : null}
    </div>
  );
}
