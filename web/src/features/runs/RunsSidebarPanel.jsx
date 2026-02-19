export default function RunsSidebarPanel({
  busy = false,
  runsIndex = null,
  projectsIndex = null,
  selectedProjectId = "",
  onProjectChange,
  onRefreshAll,
  diffLhsRunId = "",
  diffRhsRunId = "",
  diffScope = "input",
  onDiffLhsChange,
  onDiffRhsChange,
  onDiffScopeChange,
  onDiffRuns,
  collectionsNode = null,
}) {
  return (
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
            onChange={(e) => onProjectChange(String(e.target.value))}
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
          <button className="ptBtn ptBtnGhost" onClick={onRefreshAll} disabled={busy}>
            Refresh
          </button>
        </div>
      </div>

      <div className="ptSidebarSection">
        <div className="ptSidebarTitle">Diff</div>
        <label className="ptField">
          <span>LHS run</span>
          <select value={diffLhsRunId} onChange={(e) => onDiffLhsChange(String(e.target.value))}>
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
          <select value={diffRhsRunId} onChange={(e) => onDiffRhsChange(String(e.target.value))}>
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
          <select value={diffScope} onChange={(e) => onDiffScopeChange(String(e.target.value))}>
            <option value="input">input</option>
            <option value="outputs_summary">outputs_summary</option>
            <option value="all">all</option>
          </select>
        </label>

        <div className="ptBtnRow">
          <button className="ptBtn ptBtnPrimary" onClick={onDiffRuns} disabled={busy || !diffLhsRunId || !diffRhsRunId}>
            Diff
          </button>
        </div>
      </div>

      <div className="ptSidebarSection">{collectionsNode || null}</div>
    </>
  );
}
