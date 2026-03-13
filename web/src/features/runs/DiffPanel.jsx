function _defaultPretty(value) {
  return JSON.stringify(value, null, 2);
}

function _defaultViolationSampleLabel(v) {
  if (!v || typeof v !== "object") return "(invalid)";
  const code = String(v.code || "").trim();
  const entityRef = String(v.entity_ref || "").trim();
  const message = String(v.message || "").trim();
  const applicability = String(v.applicability || "").trim();
  const head = [code || "unknown", entityRef || "n/a"].join(" @ ");
  return applicability ? `${head} [${applicability}] - ${message || "(no message)"}` : `${head} - ${message || "(no message)"}`;
}

function _defaultViolationSamples(items, limit = 2) {
  if (!Array.isArray(items) || !items.length) return [];
  return items.slice(0, Math.max(1, Number(limit) || 1));
}

function _helpers(diffHelpers) {
  const source = diffHelpers && typeof diffHelpers === "object" ? diffHelpers : {};
  return {
    pretty: typeof source.pretty === "function" ? source.pretty : _defaultPretty,
    violationSampleLabel: typeof source.violationSampleLabel === "function" ? source.violationSampleLabel : _defaultViolationSampleLabel,
    violationSamples: typeof source.violationSamples === "function" ? source.violationSamples : _defaultViolationSamples,
  };
}

export default function DiffPanel({ runsDiffResult = null, busy = false, diffHelpers = null, compareLabNode = null }) {
  const h = _helpers(diffHelpers);
  const violationDiff = runsDiffResult?.diff?.violation_diff || null;
  const hasDiff = Boolean(runsDiffResult);

  return (
    <div className="ptRightSection">
      <div className="ptRightTitle">Compare and Explain</div>
      <div className="ptHint">Use compare to explain why a candidate should replace the baseline before moving into signoff and evidence export.</div>

      {compareLabNode || null}

      {violationDiff ? (
        <div className="ptHint" style={{ marginTop: 10 }}>
          <div className="ptJsonTitle">Violation semantics</div>
          <div className="ptMono">
            new: {Number(violationDiff?.summary?.new_count || 0)} | resolved: {Number(violationDiff?.summary?.resolved_count || 0)} | applicability_changed: {Number(violationDiff?.summary?.applicability_changed_count || 0)}
          </div>

          {h.violationSamples(violationDiff?.new, 2).map((v, idx) => (
            <div key={`vd:new:${idx}`}>+ {h.violationSampleLabel(v)}</div>
          ))}
          {h.violationSamples(violationDiff?.resolved, 2).map((v, idx) => (
            <div key={`vd:resolved:${idx}`}>- {h.violationSampleLabel(v)}</div>
          ))}
          {h.violationSamples(violationDiff?.applicability_changed, 2).map((v, idx) => {
            const lhsApp = String(v?.lhs_applicability || "unknown");
            const rhsApp = String(v?.rhs_applicability || "unknown");
            const row = v?.rhs && typeof v.rhs === "object" ? v.rhs : v?.lhs;
            return (
              <div key={`vd:app:${idx}`}>
                ~ {h.violationSampleLabel(row)} ({lhsApp} {"->"} {rhsApp})
              </div>
            );
          })}
        </div>
      ) : null}

      {hasDiff ? (
        <details className="ptTopbarDetails" style={{ marginTop: 10 }}>
          <summary>Raw diff JSON</summary>
          <pre className="ptPre">{h.pretty(runsDiffResult)}</pre>
        </details>
      ) : (
        <div className="ptHint">{busy ? "Diff in progress..." : "Select two runs and click Diff."}</div>
      )}
    </div>
  );
}
