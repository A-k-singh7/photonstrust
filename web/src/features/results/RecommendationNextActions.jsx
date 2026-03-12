function asObject(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function asText(value, fallback = "") {
  if (value == null) return fallback;
  const out = String(value).trim();
  return out || fallback;
}

function normalizeAction(item, index) {
  const raw = item && typeof item === "object" ? item : { title: item };
  const id = asText(raw.id, `action_${index + 1}`);
  const title = asText(raw.title ?? raw.label, "Untitled action");
  const owner = asText(raw.owner, "unassigned");
  const eta = asText(raw.eta ?? raw.due, "tbd");
  const priority = asText(raw.priority, "medium");
  return { id, title, owner, eta, priority };
}

function priorityRank(priority) {
  const p = String(priority || "").toLowerCase();
  if (p === "critical" || p === "p0" || p === "high") return 0;
  if (p === "medium" || p === "p1") return 1;
  return 2;
}

export default function RecommendationNextActions({
  payload,
  recommendation,
  actions,
  blockers,
  onSelectAction,
  onEscalate,
}) {
  const source = asObject(payload);
  const recommendationText = asText(recommendation ?? source.recommendation ?? source.next_best_action, "Gather additional evidence");

  const actionList = asArray(actions ?? source.actions ?? source.next_actions)
    .map((item, idx) => normalizeAction(item, idx))
    .sort((a, b) => priorityRank(a.priority) - priorityRank(b.priority))
    .slice(0, 6);

  const blockerList = asArray(blockers ?? source.blockers)
    .map((item) => asText(typeof item === "string" ? item : item?.message ?? item?.title))
    .filter(Boolean)
    .slice(0, 4);

  return (
    <section className="ptCard" aria-label="Recommendation and next actions">
      <h3 style={{ marginTop: 0, marginBottom: 8 }}>Recommendation and next actions</h3>
      <div className="ptCallout">Recommended path: {recommendationText}</div>

      {blockerList.length ? (
        <div className="ptError" style={{ marginTop: 10 }}>
          <div className="ptCalloutTitle">Open blockers</div>
          <ul className="ptList">
            {blockerList.map((item, idx) => (
              <li key={`next-blocker-${idx}`}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div style={{ marginTop: 10 }}>
        <div className="ptCalloutTitle">Execution hints</div>
        {actionList.length ? (
          <ul className="ptList">
            {actionList.map((item) => (
              <li key={item.id}>
                <button className="ptBtn ptBtnGhost" type="button" onClick={() => onSelectAction && onSelectAction(item)}>
                  {item.title}
                </button>
                <span className="ptHint"> owner: {item.owner}, eta: {item.eta}, priority: {item.priority}</span>
              </li>
            ))}
          </ul>
        ) : (
          <div className="ptHint">No actions in payload. Start with confidence calibration and compare-run review.</div>
        )}
      </div>

      <div className="ptBtnRow" style={{ marginTop: 10 }}>
        <button className="ptBtn" type="button" onClick={() => onEscalate && onEscalate({ reason: "week4_readout" })}>
          Escalate for review
        </button>
      </div>
    </section>
  );
}
