import ConfidenceUncertaintyLayer from "./ConfidenceUncertaintyLayer";
import DecisionCockpit from "./DecisionCockpit";
import RecommendationNextActions from "./RecommendationNextActions";

function formatPretty(prettyJson, value) {
  if (typeof prettyJson === "function") return prettyJson(value);
  return JSON.stringify(value ?? null, null, 2);
}

function artifactUrl(buildRunArtifactUrl, apiBase, runId, relPath) {
  if (typeof buildRunArtifactUrl !== "function") return "";
  return buildRunArtifactUrl(apiBase, runId, relPath);
}

function manifestUrl(buildRunManifestUrl, apiBase, runId) {
  if (typeof buildRunManifestUrl !== "function") return "";
  return buildRunManifestUrl(apiBase, runId);
}

export default function RunModePanel({
  mode,
  decision,
  compileResult,
  runResult,
  apiBase,
  onOpenProgramStage,
  onSetActiveRightTab,
  onExportDecisionPacket,
  onSaveCurrentViewPreset,
  onSetUserMode,
  onSetStatus,
  buildRunArtifactUrl,
  buildRunManifestUrl,
  prettyJson,
}) {
  if (mode === "runs") return null;

  const decisionContext = decision && typeof decision === "object" ? decision : {};
  const selectedRunForStage = String(runResult?.run_id || decisionContext?.payload?.run_id || "").trim();
  const openCertifyStage = (source = null) => {
    const sourceRunId = String(source?.run_id || source?.runId || "").trim();
    const nextRunId = sourceRunId || selectedRunForStage;
    onOpenProgramStage && onOpenProgramStage("certify", nextRunId ? { selectedRunId: nextRunId } : {});
  };

  return (
    <div id={`pt-panel-${mode}-run`} role="tabpanel" aria-labelledby={`pt-tab-${mode}-run`} className="ptRightBody">
      {mode === "graph" ? (
        <>
          <DecisionCockpit
            payload={decisionContext.payload}
            decision={decisionContext.decision}
            confidence={decisionContext.confidenceScore}
            riskLevel={decisionContext.riskLevel}
            blockers={decisionContext.blockers}
            highlights={decisionContext.highlights}
            onOpenEvidence={(source) => openCertifyStage(source)}
            onProceed={(source) => openCertifyStage(source)}
          />
          <ConfidenceUncertaintyLayer
            payload={decisionContext.payload}
            confidence={decisionContext.confidenceScore}
            uncertainty={decisionContext.uncertaintyList}
            assumptions={compileResult?.assumptions_md ? ["Compile assumptions available in Compile tab"] : []}
            onOpenSensitivity={() => onSetActiveRightTab && onSetActiveRightTab("compile")}
          />
          <RecommendationNextActions
            payload={decisionContext.payload}
            recommendation={decisionContext.recommendation}
            actions={decisionContext.actions}
            blockers={decisionContext.blockers}
            onSelectAction={(action) => {
              const actionId = String(action?.id || "");
              if (actionId === "diff") {
                onOpenProgramStage && onOpenProgramStage("compare");
              } else if (actionId === "certify") {
                openCertifyStage();
              } else if (actionId === "packet") {
                onExportDecisionPacket && onExportDecisionPacket();
              } else if (actionId === "save") {
                onSaveCurrentViewPreset && onSaveCurrentViewPreset();
              }
            }}
            onEscalate={() => {
              onSetUserMode && onSetUserMode("reviewer");
              onSetStatus && onSetStatus("Escalated for reviewer follow-up.");
            }}
          />
        </>
      ) : null}

      <div className="ptRightSection">
        <div className="ptRightTitle">Execution evidence</div>
        <div className="ptHint">This panel keeps the raw execution payload and served artifacts available after the higher-level decision blocks above have already summarized what matters most.</div>
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
                    href={artifactUrl(buildRunArtifactUrl, apiBase, runResult.run_id, runResult.artifact_relpaths.orbit_pass_report_html)}
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
                    href={artifactUrl(buildRunArtifactUrl, apiBase, runResult.run_id, runResult.artifact_relpaths.orbit_pass_results_json)}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Open results (JSON)
                  </a>{" "}
                  <span className="ptMono">[{String(runResult.artifact_relpaths.orbit_pass_results_json)}]</span>
                  <br />
                </>
              ) : null}
              <a href={manifestUrl(buildRunManifestUrl, apiBase, runResult.run_id)} target="_blank" rel="noreferrer">
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
        {runResult ? (
          <details className="ptTopbarDetails" style={{ marginTop: 10 }}>
            <summary>Raw run payload JSON</summary>
            <pre className="ptPre">{formatPretty(prettyJson, runResult)}</pre>
          </details>
        ) : <div className="ptHint">Run to see outputs.</div>}
      </div>
    </div>
  );
}
