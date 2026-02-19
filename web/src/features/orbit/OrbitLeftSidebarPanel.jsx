export default function OrbitLeftSidebarPanel({
  busy = false,
  orbitRequireSchema = true,
  onLoadPassEnvelope,
  onOrbitRequireSchemaChange,
}) {
  return (
    <>
      <div className="ptSidebarSection">
        <div className="ptSidebarTitle">Templates</div>
        <div className="ptBtnRow">
          <button className="ptBtn ptBtnGhost" onClick={onLoadPassEnvelope} disabled={busy}>
            Pass Envelope
          </button>
        </div>
        <div className="ptHint">OrbitVerify v0.1 uses explicit samples over time (not orbit propagation).</div>

        <label className="ptCheck">
          <input type="checkbox" checked={orbitRequireSchema} onChange={(e) => onOrbitRequireSchemaChange(Boolean(e.target.checked))} />
          <span>Require JSON Schema on validate/run</span>
        </label>
      </div>
    </>
  );
}
