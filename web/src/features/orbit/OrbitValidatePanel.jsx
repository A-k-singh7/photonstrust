function _defaultPrettyJson(obj) {
  return JSON.stringify(obj ?? null, null, 2);
}

export default function OrbitValidatePanel({ orbitValidateResult, prettyJson }) {
  const formatJson = typeof prettyJson === "function" ? prettyJson : _defaultPrettyJson;

  return (
    <div id="pt-panel-orbit-validate" role="tabpanel" aria-labelledby="pt-tab-orbit-validate" className="ptRightBody">
      <div className="ptRightSection">
        <div className="ptRightTitle">Orbit Config Validation</div>
        {orbitValidateResult?.diagnostics?.errors?.length ? (
          <div className="ptError">
            <div className="ptCalloutTitle">Diagnostics (errors)</div>
            <ul className="ptList">
              {orbitValidateResult.diagnostics.errors.map((d, idx) => (
                <li key={idx}>
                  <span className="ptMono">{String(d.code || "error")}</span>: {String(d.message || "")}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        {orbitValidateResult?.diagnostics?.warnings?.length ? (
          <div className="ptCallout">
            <div className="ptCalloutTitle">Diagnostics (warnings)</div>
            <ul className="ptList">
              {orbitValidateResult.diagnostics.warnings.map((d, idx) => (
                <li key={idx}>
                  <span className="ptMono">{String(d.code || "warn")}</span>: {String(d.message || "")}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        {orbitValidateResult ? (
          <pre className="ptPre">{formatJson(orbitValidateResult)}</pre>
        ) : (
          <div className="ptHint">Click Validate to run schema and semantic checks.</div>
        )}
      </div>
    </div>
  );
}
