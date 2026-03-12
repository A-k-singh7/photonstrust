function asObject(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function asText(value, fallback) {
  if (value == null) return fallback;
  const out = String(value).trim();
  return out || fallback;
}

function asPercent(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return null;
  if (n <= 1) return Math.max(0, Math.min(100, Math.round(n * 100)));
  return Math.max(0, Math.min(100, Math.round(n)));
}

function statusColor(status) {
  const s = String(status || "").toLowerCase();
  if (s === "approved" || s === "go" || s === "pass") return "#1b5e20";
  if (s === "review" || s === "hold") return "#8d6e00";
  if (s === "reject" || s === "fail" || s === "blocked") return "#8e0000";
  return "#37474f";
}

export default function DecisionCockpit({
  payload,
  title = "Decision cockpit",
  decision,
  confidence,
  riskLevel,
  blockers,
  highlights,
  onOpenEvidence,
  onProceed,
}) {
  const source = asObject(payload);
  const decisionLabel = asText(decision ?? source.decision ?? source.gate, "Review");
  const confidencePct = asPercent(confidence ?? source.confidence ?? source.confidence_score);
  const risk = asText(riskLevel ?? source.risk_level ?? source.risk, "unknown");
  const runId = asText(source.run_id ?? source.runId, "not selected");

  const blockerList = asArray(blockers ?? source.blockers ?? source.issues)
    .map((x) => asText(typeof x === "string" ? x : x?.message ?? x?.title, ""))
    .filter(Boolean);

  const highlightList = asArray(highlights ?? source.highlights ?? source.reasons)
    .map((x) => asText(typeof x === "string" ? x : x?.label ?? x?.message, ""))
    .filter(Boolean)
    .slice(0, 4);

  const canProceed = blockerList.length === 0 && confidencePct != null && confidencePct >= 75;

  return (
    <section className="ptCard" aria-label="Decision cockpit">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
        <h3 style={{ margin: 0 }}>{title}</h3>
        <span
          style={{
            background: statusColor(decisionLabel),
            color: "#fff",
            borderRadius: 999,
            fontSize: 12,
            padding: "3px 10px",
          }}
        >
          {decisionLabel}
        </span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 8, marginTop: 10 }}>
        <div className="ptHint">Run: {runId}</div>
        <div className="ptHint">Risk: {risk}</div>
        <div className="ptHint">Confidence: {confidencePct == null ? "unknown" : `${confidencePct}%`}</div>
      </div>

      {highlightList.length ? (
        <div className="ptCallout" style={{ marginTop: 10 }}>
          <div className="ptCalloutTitle">Week 4 framing</div>
          <ul className="ptList">
            {highlightList.map((item, idx) => (
              <li key={`highlight-${idx}`}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {blockerList.length ? (
        <div className="ptError" style={{ marginTop: 10 }}>
          <div className="ptCalloutTitle">Blocking evidence gaps</div>
          <ul className="ptList">
            {blockerList.map((item, idx) => (
              <li key={`blocker-${idx}`}>{item}</li>
            ))}
          </ul>
        </div>
      ) : (
        <div className="ptCallout" style={{ marginTop: 10 }}>No blocking issues detected for this run.</div>
      )}

      <div className="ptBtnRow" style={{ marginTop: 10 }}>
        <button className="ptBtn" type="button" onClick={() => onOpenEvidence && onOpenEvidence(source)}>
          Open evidence
        </button>
        <button className="ptBtn ptBtnPrimary" type="button" onClick={() => onProceed && onProceed(source)} disabled={!canProceed}>
          {canProceed ? "Proceed to certify" : "Resolve blockers first"}
        </button>
      </div>
    </section>
  );
}
