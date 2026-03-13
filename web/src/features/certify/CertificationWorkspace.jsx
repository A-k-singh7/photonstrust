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
  packetPublishHref,
  onPacketPublish,
  packetPublishDisabled,
  packetPublishResult,
  onPacketVerify,
  packetVerifyDisabled,
  packetVerifyResult,
  issues,
  onReturnToCompare,
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
  const publishDisabled = Boolean(packetPublishDisabled) || !runId;
  const verifyDisabled = Boolean(packetVerifyDisabled) || !packetPublishResult?.bundle_sha256;
  const publishDigest = _toText(packetPublishResult?.bundle_sha256, "");
  const verifyOk = packetVerifyResult?.verify?.ok === true;
  const approvalCount = _asArray(projectApprovals?.approvals).length;
  const blockCount = issueRows.filter((issue) => _statusLabel(issue.level) === "block").length;
  const cautionCount = issueRows.filter((issue) => _statusLabel(issue.level) === "caution").length;

  return (
    <section className="ptRightSection" aria-label="Certification workspace">
      <div className="ptRightTitle">Decision and Evidence</div>

      <div className="ptHint">Finish the decision journey here: confirm readiness, collect approvals, export the packet, and publish verified evidence.</div>

      <div className="ptJourneyRibbon" style={{ marginTop: 10 }} aria-label="Certification flow progress">
        <div className="ptJourneyStep isActive">
          <span className="ptJourneyStepNum">1</span>
          <span>Review readiness</span>
        </div>
        <div className={`ptJourneyStep ${approvalCount ? "isActive" : ""}`}>
          <span className="ptJourneyStepNum">2</span>
          <span>Collect signoff</span>
        </div>
        <div className={`ptJourneyStep ${(publishDigest || packetExportHref) ? "isReady" : ""}`}>
          <span className="ptJourneyStepNum">3</span>
          <span>Export and verify</span>
        </div>
      </div>

      <div className="ptCallout" style={{ marginTop: 10 }}>
        <div className="ptCalloutTitle">Decision state</div>
        <div className="ptMono">run_id={runId || "not selected"}</div>
        <div className="ptHint" style={{ marginTop: 6 }}>
          blockers={blockCount} | cautions={cautionCount} | approvals={approvalCount}
        </div>
        <div className="ptBtnRow" style={{ marginTop: 8 }}>
          {onReturnToCompare ? (
            <button className="ptBtn ptBtnGhost" onClick={() => onReturnToCompare()}>
              Return to compare
            </button>
          ) : null}
          {onPacketExport ? (
            <button className="ptBtn" onClick={() => onPacketExport()} disabled={exportDisabled}>
              Open decision packet
            </button>
          ) : null}
        </div>
      </div>

      <div className="ptCallout" style={{ marginTop: 10 }}>
        <div className="ptCalloutTitle">Decision readiness</div>
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
        <div className="ptCalloutTitle">Signoff</div>
        <div className="ptHint" style={{ marginBottom: 8 }}>Capture the approval record before sharing evidence outside the workspace.</div>
        {approvalControls ? approvalControls : <div className="ptHint">No approval controls connected.</div>}
      </div>

      <div className="ptCallout" style={{ marginTop: 10 }}>
        <div className="ptCalloutTitle">Export package</div>
        <div className="ptHint" style={{ marginBottom: 8 }}>Create the decision packet you can hand to reviewers, operators, or downstream evidence workflows.</div>
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
        <div className="ptCalloutTitle">Share and verify</div>
        <div className="ptHint" style={{ marginBottom: 8 }}>Publish a shareable bundle and confirm the verification result before treating the evidence as ready.</div>
        <div className="ptBtnRow" style={{ marginTop: 8 }}>
          <button className="ptBtn" onClick={() => onPacketPublish && onPacketPublish()} disabled={publishDisabled}>
            Publish shareable packet
          </button>
          <button className="ptBtn ptBtnGhost" onClick={() => onPacketVerify && onPacketVerify()} disabled={verifyDisabled}>
            Verify published packet
          </button>
          {packetPublishHref ? (
            <a className="ptBtn" href={packetPublishHref} target="_blank" rel="noreferrer">
              Open published link
            </a>
          ) : null}
        </div>
        {publishDigest ? <div className="ptHint" style={{ marginTop: 8 }}>digest={publishDigest}</div> : null}
        {packetVerifyResult ? (
          <div className="ptHint" style={{ marginTop: 4 }}>
            verify={verifyOk ? "ok" : "check"}, files={_toText(packetVerifyResult?.verify?.verified_files, "0")}, missing={_toText(packetVerifyResult?.verify?.missing_files, "0")}, mismatched={_toText(packetVerifyResult?.verify?.mismatched_files, "0")}
          </div>
        ) : null}
      </div>

      <div className="ptCallout" style={{ marginTop: 10 }}>
        <div className="ptCalloutTitle">Blockers and cautions</div>
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
