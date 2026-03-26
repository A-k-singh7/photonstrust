import { PROFILE_OPTIONS } from "../../photontrust/kinds";

export default function AppTopBar({
  programStageSubtitle,
  mode,
  onModeChange,
  experienceMode,
  onExperienceModeChange,
  profile,
  onProfileChange,
  graphId,
  onGraphIdChange,
  apiBase,
  onApiBaseChange,
  onDemoMode,
  onPing,
  busy,
  onPrimaryAction,
  primaryActionLabel,
  onRunOrDiff,
  runOrDiffLabel,
  runOrDiffDisabled,
  showGraphDrc,
  onGraphDrc,
  showLanding,
  onToggleLanding,
  onExportPacket,
  exportPacketDisabled,
  demoModeOpen,
  apiHealthStatus,
  apiHealthVersion,
  apiHealthError,
  showGraphProfileControls,
  simOverlayVisible,
  onToggleSimOverlay,
  showSimOverlayToggle,
}) {
  const demoActionLock = demoModeOpen;

  return (
    <header className="ptTopbar">
      <div className="ptBrand">
        <div className="ptBrandTitle">PhotonTrust</div>
        <div className="ptBrandSub">{programStageSubtitle}</div>
      </div>

      <div className="ptTopbarBody">
        <div className="ptTopbarPrimaryRow">
          <label className="ptField">
            <span>Experience</span>
            <select value={experienceMode} disabled={demoModeOpen} onChange={(e) => onExperienceModeChange(String(e.target.value))}>
              <option value="guided">Guided</option>
              <option value="power">Power</option>
            </select>
          </label>

          {showGraphProfileControls ? (
            <label className="ptField">
              <span>Profile</span>
              <select value={profile} disabled={demoModeOpen} onChange={(e) => onProfileChange(String(e.target.value))}>
                {PROFILE_OPTIONS.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.label}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
        </div>

        <div className="ptBtnRow ptTopbarActionRow">
          <button className="ptBtn" onClick={onPrimaryAction} disabled={busy || demoActionLock}>
            {primaryActionLabel}
          </button>

          <button className="ptBtn ptBtnPrimary" onClick={onRunOrDiff} disabled={busy || demoActionLock || runOrDiffDisabled}>
            {runOrDiffLabel}
          </button>

          <button className="ptBtn ptBtnGhost" onClick={onToggleLanding} disabled={demoActionLock}>
            {showLanding ? "Hide Start" : "Start Here"}
          </button>

          {showSimOverlayToggle ? (
            <button
              className={`ptBtn ptBtnGhost${simOverlayVisible ? " ptBtnActive" : ""}`}
              onClick={onToggleSimOverlay}
              disabled={demoActionLock}
              title="Toggle simulation result badges on canvas nodes"
            >
              {simOverlayVisible ? "Hide Results" : "Show Results"}
            </button>
          ) : null}
        </div>

        <details className="ptTopbarDetails">
          <summary>Advanced setup and diagnostics</summary>
          <div className="ptTopControls ptTopControlsAdvanced">
            <label className="ptField">
              <span>Mode</span>
              <select value={mode} disabled={demoModeOpen} onChange={(e) => onModeChange(String(e.target.value))}>
                <option value="graph">Graph Editor</option>
                <option value="orbit">Orbit Pass</option>
                <option value="runs">Runs</option>
              </select>
            </label>

            {showGraphProfileControls ? (
              <label className="ptField">
                <span>graph_id</span>
                <input value={graphId} onChange={(e) => onGraphIdChange(String(e.target.value))} disabled={demoModeOpen} />
              </label>
            ) : null}

            <label className="ptField ptFieldWide">
              <span>API</span>
              <input value={apiBase} onChange={(e) => onApiBaseChange(String(e.target.value))} placeholder="http://127.0.0.1:8000" disabled={demoModeOpen} />
            </label>

            <button className="ptBtn" onClick={onDemoMode} disabled={demoModeOpen}>
              Demo Mode
            </button>

            <button className="ptBtn ptBtnGhost" onClick={onPing} disabled={busy || demoActionLock}>
              Ping
            </button>

            {showGraphDrc ? (
              <button className="ptBtn ptBtnGhost" onClick={onGraphDrc} disabled={busy || demoActionLock}>
                DRC
              </button>
            ) : null}

            <button className="ptBtn ptBtnGhost" onClick={onExportPacket} disabled={exportPacketDisabled}>
              Export Packet
            </button>
          </div>
        </details>
      </div>

      <div className={`ptApiPill ${apiHealthStatus}`} title={apiHealthError || ""}>
        API: {apiHealthStatus === "ok" ? `ok (v${apiHealthVersion || "?"})` : apiHealthStatus}
      </div>
    </header>
  );
}
