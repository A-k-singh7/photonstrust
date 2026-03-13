const DEFAULT_SCOPE_OPTIONS = [
  { value: "input", label: "input" },
  { value: "outputs_summary", label: "outputs_summary" },
  { value: "all", label: "all" },
];

function _toRuns(runsIndex) {
  return Array.isArray(runsIndex?.runs) ? runsIndex.runs : [];
}

function _runLabel(run) {
  const runType = String(run?.run_type || "run");
  const projectId = String(run?.project_id || "").trim();
  const runId = String(run?.run_id || "").trim();
  if (!runId) return "";
  return projectId ? `${runType} | ${projectId} | ${runId}` : `${runType} | ${runId}`;
}

function _runById(runs, runId) {
  const target = String(runId || "").trim();
  if (!target) return null;
  return runs.find((run) => String(run?.run_id || "").trim() === target) || null;
}

function _asNumber(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

function _shortText(value, maxLen = 70) {
  const text = String(value == null ? "" : value);
  if (text.length <= maxLen) return text;
  return `${text.slice(0, Math.max(0, maxLen - 3))}...`;
}

function _compactValue(value) {
  if (value == null) return "-";
  if (typeof value === "string") return _shortText(value);
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) {
    if (!value.length) return "[]";
    return `array(${value.length})`;
  }
  if (typeof value === "object") {
    const keys = Object.keys(value);
    if (!keys.length) return "{}";
    try {
      return _shortText(JSON.stringify(value));
    } catch {
      return `object(${keys.length})`;
    }
  }
  return String(value);
}

function _violationSummary(runsDiffResult) {
  const source = runsDiffResult?.diff?.violation_diff || runsDiffResult?.violation_diff || null;
  if (!source || typeof source !== "object") {
    return { newCount: 0, resolvedCount: 0, applicabilityChangedCount: 0, available: false };
  }
  const summary = source.summary && typeof source.summary === "object" ? source.summary : {};
  const newCount = _asNumber(summary.new_count ?? source.new_count ?? (Array.isArray(source.new) ? source.new.length : 0));
  const resolvedCount = _asNumber(summary.resolved_count ?? source.resolved_count ?? (Array.isArray(source.resolved) ? source.resolved.length : 0));
  const applicabilityChangedCount = _asNumber(
    summary.applicability_changed_count ??
      source.applicability_changed_count ??
      (Array.isArray(source.applicability_changed) ? source.applicability_changed.length : 0),
  );
  return { newCount, resolvedCount, applicabilityChangedCount, available: true };
}

function _normalizeChangedField(item, fallbackPath) {
  if (item == null) {
    return { field: String(fallbackPath || "field"), lhs: "-", rhs: "-" };
  }

  if (typeof item !== "object") {
    return { field: String(fallbackPath || "field"), lhs: "-", rhs: _compactValue(item) };
  }

  const field = String(item.path || item.field || item.key || item.name || fallbackPath || "field");
  const lhsRaw = item.lhs ?? item.before ?? item.old ?? item.left ?? item.previous ?? item.lhs_value;
  const rhsRaw = item.rhs ?? item.after ?? item.new ?? item.right ?? item.current ?? item.rhs_value;

  return {
    field,
    lhs: _compactValue(lhsRaw),
    rhs: _compactValue(rhsRaw),
  };
}

function _changedFieldRows(runsDiffResult, limit = 6) {
  const diff = runsDiffResult?.diff && typeof runsDiffResult.diff === "object" ? runsDiffResult.diff : {};
  const direct =
    diff.changed_fields ??
    diff.field_changes ??
    runsDiffResult?.changed_fields ??
    runsDiffResult?.field_changes ??
    null;

  let rows = [];
  if (Array.isArray(direct)) {
    rows = direct.map((item, idx) => _normalizeChangedField(item, `field_${idx + 1}`));
  } else if (direct && typeof direct === "object") {
    rows = Object.entries(direct).map(([key, value]) => _normalizeChangedField(value, key));
  }

  if (!rows.length && diff && typeof diff === "object") {
    const reserved = { violation_diff: true, summary: true };
    rows = Object.entries(diff)
      .filter(([key, value]) => !reserved[key] && value && typeof value === "object")
      .map(([key, value]) => _normalizeChangedField(value, key));
  }

  const safeLimit = Math.max(1, Number(limit) || 1);
  return rows.slice(0, safeLimit);
}

export default function CompareLabPanel({
  runsIndex,
  baselineRunId = "",
  candidateRunId = "",
  diffScope = "input",
  busy = false,
  runsDiffResult = null,
  scopeOptions = DEFAULT_SCOPE_OPTIONS,
  onBaselineRunChange,
  onCandidateRunChange,
  onDiffScopeChange,
  onCompare,
  onContinueToCertify,
}) {
  const runs = _toRuns(runsIndex);
  const summary = _violationSummary(runsDiffResult);
  const previewRows = _changedFieldRows(runsDiffResult, 6);
  const canCompare = !busy && String(baselineRunId || "") && String(candidateRunId || "");
  const baselineRun = _runById(runs, baselineRunId);
  const candidateRun = _runById(runs, candidateRunId);
  const compareReady = summary.available || previewRows.length > 0;

  return (
    <section className="ptRightSection" aria-label="Week 6 compare lab panel">
      <div className="ptRightTitle">Decision Review</div>
      <div className="ptHint">Compare the baseline against a candidate, understand what changed, and decide whether it is ready for certification.</div>

      <div className="ptJourneyRibbon" style={{ marginTop: 10 }} aria-label="Decision journey progress">
        <div className="ptJourneyStep isActive">
          <span className="ptJourneyStepNum">1</span>
          <span>Select runs</span>
        </div>
        <div className={`ptJourneyStep ${compareReady ? "isActive" : ""}`}>
          <span className="ptJourneyStepNum">2</span>
          <span>Review delta</span>
        </div>
        <div className={`ptJourneyStep ${compareReady ? "isReady" : ""}`}>
          <span className="ptJourneyStepNum">3</span>
          <span>Move to certify</span>
        </div>
      </div>

      <div className="ptJourneyGrid" style={{ marginTop: 10 }}>
        <div>
          <div className="ptJsonTitle">Baseline</div>
          <div className="ptHint">Reference run used as the decision anchor.</div>
        </div>
        <div>
          <div className="ptJsonTitle">Candidate</div>
          <div className="ptHint">Alternative you want to justify or reject.</div>
        </div>
      </div>

      <label className="ptField" style={{ marginTop: 10 }}>
        <span>Baseline run</span>
        <select value={String(baselineRunId || "")} onChange={(e) => onBaselineRunChange && onBaselineRunChange(String(e.target.value))}>
          <option value="">(select baseline)</option>
          {runs.map((run) => {
            const runId = String(run?.run_id || "");
            if (!runId) return null;
            return (
              <option key={`baseline:${runId}`} value={runId}>
                {_runLabel(run)}
              </option>
            );
          })}
        </select>
      </label>

      <label className="ptField" style={{ marginTop: 10 }}>
        <span>Candidate run</span>
        <select value={String(candidateRunId || "")} onChange={(e) => onCandidateRunChange && onCandidateRunChange(String(e.target.value))}>
          <option value="">(select candidate)</option>
          {runs.map((run) => {
            const runId = String(run?.run_id || "");
            if (!runId) return null;
            return (
              <option key={`candidate:${runId}`} value={runId}>
                {_runLabel(run)}
              </option>
            );
          })}
        </select>
      </label>

      <label className="ptField" style={{ marginTop: 10 }}>
        <span>Scope</span>
        <select value={String(diffScope || "input")} onChange={(e) => onDiffScopeChange && onDiffScopeChange(String(e.target.value))}>
          {(Array.isArray(scopeOptions) ? scopeOptions : DEFAULT_SCOPE_OPTIONS).map((scope) => {
            if (!scope || typeof scope !== "object") return null;
            const value = String(scope.value || "");
            if (!value) return null;
            return (
              <option key={`scope:${value}`} value={value}>
                {String(scope.label || value)}
              </option>
            );
          })}
        </select>
      </label>

      <div className="ptBtnRow" style={{ marginTop: 10 }}>
        <button className="ptBtn ptBtnPrimary" onClick={() => onCompare && onCompare()} disabled={!canCompare}>
          {busy ? "Comparing..." : "Compare baseline vs candidate"}
        </button>
        {compareReady && onContinueToCertify ? (
          <button className="ptBtn" onClick={() => onContinueToCertify()}>
            Continue to certify
          </button>
        ) : null}
      </div>

      {(baselineRun || candidateRun) ? (
        <div className="ptTrustBox" style={{ marginTop: 10 }}>
          <div className="ptCalloutTitle">Decision framing</div>
          <div className="ptHint">
            {baselineRun ? <span className="ptMono">baseline={_runLabel(baselineRun)}</span> : <span className="ptMono">baseline not selected</span>}
            <br />
            {candidateRun ? <span className="ptMono">candidate={_runLabel(candidateRun)}</span> : <span className="ptMono">candidate not selected</span>}
            <br />
            scope=<span className="ptMono">{String(diffScope || "input")}</span>
          </div>
        </div>
      ) : null}

      {summary.available ? (
        <div className="ptCallout" style={{ marginTop: 10 }}>
          <div className="ptCalloutTitle">Decision summary</div>
          <div className="ptMono" style={{ marginBottom: 6 }}>
            new: {summary.newCount} | resolved: {summary.resolvedCount} | applicability-changed: {summary.applicabilityChangedCount}
          </div>
          <div className="ptHint">
            Use this summary to decide whether the candidate is safer, riskier, or simply different from the baseline before moving to signoff.
          </div>
        </div>
      ) : (
        <div className="ptHint" style={{ marginTop: 10 }}>Run a compare action to see the decision-relevant differences before certification.</div>
      )}

      {previewRows.length ? (
        <div className="ptTrustBox" style={{ marginTop: 10 }}>
          <div className="ptJsonTitle">Changed fields (preview)</div>
          {previewRows.map((row, idx) => (
            <div key={`changed-field:${idx}`} className="ptMono">
              {row.field}: {row.lhs} -&gt; {row.rhs}
            </div>
          ))}
        </div>
      ) : (
        <div className="ptHint" style={{ marginTop: 10 }}>No changed-field preview available yet. After comparing, this panel will summarize the main deltas you need to explain.</div>
      )}
    </section>
  );
}
