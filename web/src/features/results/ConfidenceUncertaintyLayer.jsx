function asObject(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function asPercent(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return null;
  if (n <= 1) return Math.max(0, Math.min(100, Math.round(n * 100)));
  return Math.max(0, Math.min(100, Math.round(n)));
}

function asLabel(item) {
  if (typeof item === "string") return item.trim();
  if (!item || typeof item !== "object") return "";
  const name = String(item.name ?? item.label ?? item.key ?? "").trim();
  const impact = String(item.impact ?? item.weight ?? "").trim();
  if (!name) return "";
  return impact ? `${name} (${impact})` : name;
}

function meterColor(percent) {
  if (!Number.isFinite(percent)) return "#90a4ae";
  if (percent >= 85) return "#1b5e20";
  if (percent >= 70) return "#8d6e00";
  return "#8e0000";
}

export default function ConfidenceUncertaintyLayer({
  payload,
  confidence,
  threshold = 75,
  uncertainty,
  assumptions,
  onOpenSensitivity,
}) {
  const source = asObject(payload);
  const confidencePct = asPercent(confidence ?? source.confidence ?? source.confidence_score);
  const thresholdPct = asPercent(threshold) ?? 75;

  const uncertaintyList = asArray(uncertainty ?? source.uncertainty_factors ?? source.uncertainty)
    .map(asLabel)
    .filter(Boolean)
    .slice(0, 6);

  const assumptionList = asArray(assumptions ?? source.assumptions)
    .map(asLabel)
    .filter(Boolean)
    .slice(0, 4);

  const meetsTarget = confidencePct != null && confidencePct >= thresholdPct;

  return (
    <section className="ptCard" aria-label="Confidence and uncertainty layer">
      <h3 style={{ marginTop: 0, marginBottom: 8 }}>Confidence and uncertainty</h3>

      <div className="ptHint" style={{ marginBottom: 8 }}>
        Week 4 target confidence: {thresholdPct}%
      </div>

      <div style={{ background: "#eceff1", borderRadius: 999, height: 10, overflow: "hidden" }} aria-hidden="true">
        <div
          style={{
            width: `${Math.max(0, Math.min(100, confidencePct ?? 0))}%`,
            height: "100%",
            background: meterColor(confidencePct),
          }}
        />
      </div>

      <div className="ptHint" style={{ marginTop: 8 }}>
        Confidence now: {confidencePct == null ? "unknown" : `${confidencePct}%`} ({meetsTarget ? "meets target" : "below target"})
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 10, marginTop: 10 }}>
        <div className="ptCallout">
          <div className="ptCalloutTitle">Uncertainty drivers</div>
          {uncertaintyList.length ? (
            <ul className="ptList">
              {uncertaintyList.map((item, idx) => (
                <li key={`unc-${idx}`}>{item}</li>
              ))}
            </ul>
          ) : (
            <div className="ptHint">No uncertainty payload attached.</div>
          )}
        </div>

        <div className="ptCallout">
          <div className="ptCalloutTitle">Assumptions to verify</div>
          {assumptionList.length ? (
            <ul className="ptList">
              {assumptionList.map((item, idx) => (
                <li key={`asm-${idx}`}>{item}</li>
              ))}
            </ul>
          ) : (
            <div className="ptHint">Assumptions missing from payload.</div>
          )}
        </div>
      </div>

      <div className="ptBtnRow" style={{ marginTop: 10 }}>
        <button className="ptBtn" type="button" onClick={() => onOpenSensitivity && onOpenSensitivity(source)}>
          Open sensitivity checks
        </button>
      </div>
    </section>
  );
}
