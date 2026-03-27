import { PROFILE_OPTIONS } from "../../photontrust/kinds";

function shortRunId(value) {
  const text = String(value || "").trim();
  if (!text) return "No run yet";
  return text.length > 14 ? `${text.slice(0, 12)}...` : text;
}

function sessionValue(value, fallback) {
  const text = String(value || "").trim();
  return text || fallback;
}

function titleCase(value) {
  const text = String(value || "").trim();
  if (!text) return "";
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export default function AppTopBar({
  programStageSubtitle,
  objectiveTitle,
  objectiveSummary,
  mode,
  onModeChange,
  experienceMode,
  onExperienceModeChange,
  userMode,
  onUserModeChange,
  selectedViewPresetId,
  savedViews,
  onViewPresetChange,
  onSaveView,
  profile,
  onProfileChange,
  graphId,
  onGraphIdChange,
  apiBase,
  onApiBaseChange,
  selectedProjectId,
  activeRunId,
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
        <div className="ptTopbarMission">
          <div>
            <div className="ptTopbarKicker">Current objective</div>
            <div className="ptTopbarMissionTitle">{objectiveTitle}</div>
            <div className="ptTopbarMissionSummary">{objectiveSummary}</div>
          </div>
          <div className="ptTopbarPrimaryRow">
            <div className="ptSegment" aria-label="Experience">
              <button
                type="button"
                className={`ptSegmentBtn ${experienceMode === "guided" ? "active" : ""}`}
                disabled={demoModeOpen}
                onClick={() => onExperienceModeChange("guided")}
              >
                Guided
              </button>
              <button
                type="button"
                className={`ptSegmentBtn ${experienceMode === "power" ? "active" : ""}`}
                disabled={demoModeOpen}
                onClick={() => onExperienceModeChange("power")}
              >
                Power
              </button>
            </div>
          </div>
        </div>

        <div className="ptTopbarSessionRow" aria-label="Current session summary">
          <div className="ptTopbarSessionChip">
            <span>Project</span>
            <strong>{sessionValue(selectedProjectId, "Not selected")}</strong>
          </div>
          <div className="ptTopbarSessionChip">
            <span>Role</span>
            <strong>{titleCase(sessionValue(userMode, "builder"))}</strong>
          </div>
          <div className="ptTopbarSessionChip">
            <span>Run</span>
            <strong className="ptMono">{shortRunId(activeRunId)}</strong>
          </div>
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

            <label className="ptField">
              <span>Role preset</span>
              <select value={userMode} disabled={demoModeOpen} onChange={(e) => onUserModeChange(String(e.target.value))}>
                <option value="builder">Builder</option>
                <option value="reviewer">Reviewer</option>
                <option value="exec">Exec</option>
              </select>
            </label>

            <label className="ptField">
              <span>Saved view</span>
              <select value={String(selectedViewPresetId || "")} disabled={demoModeOpen} onChange={(e) => onViewPresetChange(String(e.target.value))}>
                <option value="">(select saved view)</option>
                {(Array.isArray(savedViews) ? savedViews : []).map((view) => {
                  const id = String(view?.id || "");
                  if (!id) return null;
                  return (
                    <option key={id} value={id}>
                      {String(view?.name || id)}
                    </option>
                  );
                })}
              </select>
            </label>

            <button className="ptBtn" onClick={onSaveView} disabled={demoActionLock}>
              Save View
            </button>

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
