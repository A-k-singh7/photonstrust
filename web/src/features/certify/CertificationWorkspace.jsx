function _asArray(value) {
  return Array.isArray(value) ? value : [];
}

function _asObject(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : null;
}

function _toText(value, fallback) {
  const text = String(value == null ? "" : value).trim();
  return text || String(fallback || "");
}

function _statusLabel(status) {
  const value = _toText(status, "caution").toLowerCase();
  if (value === "pass") return "pass";
  if (value === "block") return "block";
  return "caution";
}

function _issueRows({ selectedRunManifest, compileResult, projectApprovals }) {
  const issues = [];
  const runId = _toText(selectedRunManifest?.run_id, "");
  if (!runId) {
    issues.push({ level: "block", message: "No selected run manifest." });
  }

  const compileErrors = _asArray(compileResult?.diagnostics?.errors);
  const compileWarnings = _asArray(compileResult?.diagnostics?.warnings);

  compileErrors.forEach((entry, idx) => {
    const code = _toText(entry?.code, `err_${idx + 1}`);
    const message = _toText(entry?.message, "Compile diagnostic error.");
    issues.push({ level: "block", message: `${code}: ${message}` });
  });

  compileWarnings.forEach((entry, idx) => {
    const code = _toText(entry?.code, `warn_${idx + 1}`);
    const message = _toText(entry?.message, "Compile diagnostic warning.");
    issues.push({ level: "caution", message: `${code}: ${message}` });
  });

  if (projectApprovals?.status === "error") {
    issues.push({ level: "block", message: _toText(projectApprovals?.error, "Approvals failed to load.") });
  }

  if (!issues.length) {
    issues.push({ level: "pass", message: "No blocking issues detected." });
  }

  return issues;
}

function _defaultChecklist({ selectedRunManifest, compileResult, projectApprovals, packetExportHref, onPacketExport }) {
  const runId = _toText(selectedRunManifest?.run_id, "");
  const compileErrors = _asArray(compileResult?.diagnostics?.errors);
  const compileWarnings = _asArray(compileResult?.diagnostics?.warnings);
  const artifacts = _asObject(selectedRunManifest?.artifacts);
  const approvals = _asArray(projectApprovals?.approvals);

  return [
    {
      id: "run-selected",
      label: "Run selected",
      status: runId ? "pass" : "block",
      detail: runId ? `run_id=${runId}` : "Select a run to continue.",
    },
    {
      id: "compile-health",
      label: "Compile health",
      status: compileErrors.length ? "block" : compileWarnings.length ? "caution" : compileResult ? "pass" : "caution",
      detail: compileResult ? `errors=${compileErrors.length}, warnings=${compileWarnings.length}` : "Compile result is missing.",
    },
    {
      id: "artifacts",
      label: "Artifacts present",
      status: artifacts && Object.keys(artifacts).length ? "pass" : runId ? "caution" : "block",
      detail: artifacts && Object.keys(artifacts).length ? "Artifacts indexed in manifest." : "No artifact map available.",
    },
    {
      id: "approvals",
      label: "Signoff approvals",
      status: projectApprovals?.status === "error" ? "block" : approvals.length ? "pass" : "caution",
      detail:
        projectApprovals?.status === "error"
          ? _toText(projectApprovals?.error, "Approval state unavailable.")
          : approvals.length
            ? `${approvals.length} approval event(s)`
            : "No approvals recorded.",
    },
    {
      id: "packet-export",
      label: "Decision packet export",
      status: packetExportHref || typeof onPacketExport === "function" ? "pass" : runId ? "caution" : "block",
      detail: packetExportHref || typeof onPacketExport === "function" ? "Export action ready." : "No export action supplied.",
    },
  ];
}

export default function CertificationWorkspace({
  selectedRunManifest,
  compileResult,
  projectApprovals,
  readinessChecklist,
  approvalControls,
  packetExportHref,
  packetExportLabel = "Export decision packet",
  onPacketExport,
  packetExportDisabled,
  issues,
}) {
  const checklist = Array.isArray(readinessChecklist)
    ? readinessChecklist
    : _defaultChecklist({ selectedRunManifest, compileResult, projectApprovals, packetExportHref, onPacketExport });

  const issueRows = Array.isArray(issues)
    ? issues.map((issue) => {
        if (typeof issue === "string") return { level: "caution", message: issue };
        return {
          level: _toText(issue?.level, "caution"),
          message: _toText(issue?.message, "Issue details unavailable."),
        };
      })
    : _issueRows({ selectedRunManifest, compileResult, projectApprovals });

  const runId = _toText(selectedRunManifest?.run_id, "");
  const exportDisabled = Boolean(packetExportDisabled) || (!runId && !packetExportHref);

  return (
    <section className="ptRightSection" aria-label="Certification workspace">
      <div className="ptRightTitle">Certification Workspace</div>

      <div className="ptCallout" style={{ marginTop: 10 }}>
        <div className="ptCalloutTitle">Readiness checklist</div>
        <ul className="ptList">
          {checklist.map((item, idx) => {
            const status = _statusLabel(item?.status);
            const label = _toText(item?.label, `item_${idx + 1}`);
            const detail = _toText(item?.detail, "");
            return (
              <li key={`readiness:${label}:${idx}`}>
                <span className="ptMono">{label}</span> - {status}
                {detail ? ` - ${detail}` : ""}
              </li>
            );
          })}
        </ul>
      </div>

      <div className="ptCallout" style={{ marginTop: 10 }}>
        <div className="ptCalloutTitle">Approvals</div>
        {approvalControls ? approvalControls : <div className="ptHint">No approval controls connected.</div>}
      </div>

      <div className="ptCallout" style={{ marginTop: 10 }}>
        <div className="ptCalloutTitle">Decision packet</div>
        <div className="ptBtnRow" style={{ marginTop: 8 }}>
          <button className="ptBtn ptBtnPrimary" onClick={() => onPacketExport && onPacketExport()} disabled={exportDisabled}>
            {String(packetExportLabel || "Export decision packet")}
          </button>
          {packetExportHref ? (
            <a className="ptBtn" href={packetExportHref} target="_blank" rel="noreferrer">
              Open packet link
            </a>
          ) : null}
        </div>
      </div>

      <div className="ptCallout" style={{ marginTop: 10 }}>
        <div className="ptCalloutTitle">Issues</div>
        <ul className="ptList">
          {issueRows.map((issue, idx) => (
            <li key={`issue:${idx}`}>
              <span className="ptMono">{_statusLabel(issue.level)}</span> - {_toText(issue.message, "Issue details unavailable.")}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
