function _toText(value, fallback) {
  const text = String(value == null ? "" : value).trim();
  return text || String(fallback || "");
}

function _asArray(value) {
  return Array.isArray(value) ? value : [];
}

function _asObject(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : null;
}

function _callUrlBuilder(builder, apiBase, runId, relPath) {
  if (typeof builder !== "function" || !runId) return "";
  const attempts = relPath
    ? [
        [apiBase, runId, relPath],
        [runId, relPath],
        [{ apiBase, runId, relPath }],
      ]
    : [
        [apiBase, runId],
        [runId],
        [{ apiBase, runId }],
      ];

  for (const args of attempts) {
    try {
      const value = builder(...args);
      const url = _toText(value, "");
      if (url) return url;
    } catch {
      // Try alternate signatures.
    }
  }
  return "";
}

function _artifactEntries(manifest) {
  const artifacts = _asObject(manifest?.artifacts);
  if (!artifacts) return [];
  return Object.entries(artifacts)
    .filter(([, value]) => typeof value === "string" && String(value).trim())
    .map(([key, value]) => ({ key: String(key), path: String(value).trim() }));
}

export default function ProvenanceTimeline({
  apiBase,
  selectedRunManifest,
  compileResult,
  projectApprovals,
  runManifestUrlBuilder,
  runArtifactUrlBuilder,
  runBundleUrlBuilder,
  buildRunManifestUrl,
  buildRunArtifactUrl,
  buildRunBundleUrl,
}) {
  const manifest = _asObject(selectedRunManifest);
  const runId = _toText(manifest?.run_id, "");
  const input = _asObject(manifest?.input);
  const approvals = _asArray(projectApprovals?.approvals);
  const compileErrors = _asArray(compileResult?.diagnostics?.errors);
  const compileWarnings = _asArray(compileResult?.diagnostics?.warnings);
  const artifacts = _artifactEntries(manifest);

  const manifestBuilder = runManifestUrlBuilder || buildRunManifestUrl;
  const artifactBuilder = runArtifactUrlBuilder || buildRunArtifactUrl;
  const bundleBuilder = runBundleUrlBuilder || buildRunBundleUrl;

  const manifestUrl = _callUrlBuilder(manifestBuilder, apiBase, runId);
  const bundleUrl = _callUrlBuilder(bundleBuilder, apiBase, runId);

  const steps = [
    {
      id: "input",
      label: "input",
      status: input ? "pass" : "caution",
      detail: input ? `project_id=${_toText(input.project_id, "default")}` : "Missing run input details.",
    },
    {
      id: "compile",
      label: "compile",
      status: compileErrors.length ? "block" : compileWarnings.length ? "caution" : compileResult ? "pass" : "caution",
      detail: compileResult ? `errors=${compileErrors.length}, warnings=${compileWarnings.length}` : "Compile output not present.",
    },
    {
      id: "run",
      label: "run",
      status: runId ? "pass" : "block",
      detail: runId ? `run_id=${runId}` : "No selected run.",
      href: manifestUrl,
      hrefLabel: "Open run manifest",
    },
    {
      id: "artifacts",
      label: "artifacts",
      status: artifacts.length ? "pass" : runId ? "caution" : "block",
      detail: artifacts.length ? `${artifacts.length} artifact path(s) found` : "No artifacts indexed.",
      href: bundleUrl,
      hrefLabel: "Download evidence bundle",
    },
    {
      id: "signoff",
      label: "signoff",
      status: projectApprovals?.status === "error" ? "block" : approvals.length ? "pass" : "caution",
      detail:
        projectApprovals?.status === "error"
          ? _toText(projectApprovals?.error, "Failed to load approvals.")
          : approvals.length
            ? `${approvals.length} approval event(s)`
            : "No approvals recorded.",
    },
  ];

  return (
    <section className="ptRightSection" aria-label="Provenance timeline">
      <div className="ptRightTitle">Provenance Timeline</div>
      <ol className="ptList">
        {steps.map((step) => (
          <li key={step.id}>
            <span className="ptMono">{step.label}</span> - {step.status} - {step.detail}
            {step.href ? (
              <>
                {" "}
                <a href={step.href} target="_blank" rel="noreferrer">
                  {step.hrefLabel}
                </a>
              </>
            ) : null}
          </li>
        ))}
      </ol>

      {runId && artifacts.length ? (
        <div className="ptCallout" style={{ marginTop: 10 }}>
          <div className="ptCalloutTitle">Artifact links</div>
          <div className="ptHint">
            {artifacts.map((artifact) => {
              const href = _callUrlBuilder(artifactBuilder, apiBase, runId, artifact.path);
              return (
                <div key={`artifact:${artifact.key}:${artifact.path}`}>
                  {href ? (
                    <a href={href} target="_blank" rel="noreferrer">
                      {artifact.key}
                    </a>
                  ) : (
                    <span>{artifact.key}</span>
                  )}{" "}
                  <span className="ptMono">[{artifact.path}]</span>
                </div>
              );
            })}
          </div>
        </div>
      ) : null}
    </section>
  );
}
