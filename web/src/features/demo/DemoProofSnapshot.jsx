function toText(value, fallback) {
  if (value === null || value === undefined) {
    return fallback;
  }

  var text = String(value).trim();
  return text ? text : fallback;
}

function toNumberText(value, fallback) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return String(value);
  }

  if (typeof value === "string" && value.trim()) {
    return value.trim();
  }

  return fallback;
}

function pickDiffCount(summary, keys) {
  if (!summary || typeof summary !== "object") {
    return null;
  }

  for (var i = 0; i < keys.length; i += 1) {
    var key = keys[i];
    if (summary[key] !== undefined && summary[key] !== null) {
      return summary[key];
    }
  }

  return null;
}

export default function DemoProofSnapshot(props) {
  var scene = toText(props.scene, "benchmark").toLowerCase();
  var degraded = Boolean(props.degraded);
  var decision = toText(props.decision, "pending");
  var confidence = toText(props.confidence, "unknown");
  var riskLevel = toText(props.riskLevel, "medium");
  var approvalCount = toNumberText(props.approvalCount, "0");
  var runId = toText(props.runId, "run-unavailable");
  var packetHref = toText(props.packetHref, "");

  var baselineDiffRaw = pickDiffCount(props.diffSummary, [
    "baseline",
    "baselineCount",
    "baselineDiffCount"
  ]);
  var candidateDiffRaw = pickDiffCount(props.diffSummary, [
    "candidate",
    "candidateCount",
    "candidateDiffCount"
  ]);

  var baselineDiff = toNumberText(baselineDiffRaw, "0");
  var candidateDiff = toNumberText(candidateDiffRaw, "0");

  var row;
  if (scene === "trust") {
    row = (
      <p>
        Trust checks show <span className="ptMono">{approvalCount}</span> approvals for run <span className="ptMono">{runId}</span>.
      </p>
    );
  } else if (scene === "decision") {
    row = (
      <p>
        Decision is <span className="ptMono">{decision}</span> with confidence <span className="ptMono">{confidence}</span> and risk <span className="ptMono">{riskLevel}</span>.
      </p>
    );
  } else if (scene === "packet") {
    var ready = packetHref ? "ready" : "pending";
    row = (
      <p>
        Packet is <span className="ptMono">{ready}</span> for run <span className="ptMono">{runId}</span>.
      </p>
    );
  } else {
    row = (
      <p>
        Benchmark reports baseline diffs <span className="ptMono">{baselineDiff}</span> and candidate diffs <span className="ptMono">{candidateDiff}</span>.
      </p>
    );
  }

  return (
    <section className="ptCallout">
      <div className="ptCalloutTitle">Proof Snapshot</div>
      {row}
      {scene === "packet" && packetHref ? (
        <p>
          Packet link: <a href={packetHref}>Open packet</a>
        </p>
      ) : null}
      {degraded ? <p className="ptHint">Safe fallback data is being shown.</p> : null}
    </section>
  );
}
