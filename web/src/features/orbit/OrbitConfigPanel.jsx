function _defaultPrettyJson(obj) {
  return JSON.stringify(obj ?? null, null, 2);
}

export default function OrbitConfigPanel({ orbitConfig, prettyJson, onCopied, onCopyFailed, panelId = "", labelledBy = "" }) {
  const formatJson = typeof prettyJson === "function" ? prettyJson : _defaultPrettyJson;

  return (
    <div className="ptRightBody" id={panelId || undefined} role={panelId ? "tabpanel" : undefined} aria-labelledby={labelledBy || undefined}>
      <div className="ptRightSection">
        <div className="ptRightTitle">Orbit Config (JSON)</div>
        <pre className="ptPre">{formatJson(orbitConfig)}</pre>
        <div className="ptBtnRow">
          <button
            className="ptBtn ptBtnGhost"
            onClick={async () => {
              try {
                await navigator.clipboard.writeText(formatJson(orbitConfig));
                if (typeof onCopied === "function") onCopied();
              } catch (err) {
                if (typeof onCopyFailed === "function") onCopyFailed(err);
              }
            }}
          >
            Copy
          </button>
        </div>
      </div>
    </div>
  );
}
