import { PROFILE_OPTIONS } from "../../photontrust/kinds";
import { stageLabel } from "./copy";

export default function AppTopBar({
  programStageSubtitle,
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
}) {
  const demoActionLock = demoModeOpen;

  return (
    <header className="ptTopbar">
      <div className="ptBrand">
        <div className="ptBrandTitle">PhotonTrust</div>
        <div className="ptBrandSub">{programStageSubtitle}</div>
      </div>

      <div className="ptTopControls">
        <label className="ptField">
          <span>Mode</span>
          <select value={mode} disabled={demoModeOpen} onChange={(e) => onModeChange(String(e.target.value))}>
            <option value="graph">Graph Editor</option>
            <option value="orbit">Orbit Pass</option>
            <option value="runs">Runs</option>
          </select>
        </label>

        <label className="ptField">
          <span>Experience</span>
          <select
            value={experienceMode}
            disabled={demoModeOpen}
            onChange={(e) => onExperienceModeChange(String(e.target.value))}
          >
            <option value="guided">Guided</option>
            <option value="power">Power</option>
          </select>
        </label>

        <label className="ptField">
          <span>User mode</span>
          <select value={userMode} disabled={demoModeOpen} onChange={(e) => onUserModeChange(String(e.target.value))}>
            <option value="builder">Builder</option>
            <option value="reviewer">Reviewer</option>
            <option value="exec">Exec</option>
          </select>
        </label>

        <label className="ptField ptFieldWide">
          <span>View preset</span>
          <select value={selectedViewPresetId} onChange={(e) => onViewPresetChange(String(e.target.value))} disabled={demoModeOpen}>
            <option value="">(saved views)</option>
            {(savedViews || []).map((view) => {
              const id = String(view?.id || "");
              if (!id) return null;
              const name = String(view?.name || id);
              const stage = String(view?.stage || "build");
              return (
                <option key={`view:${id}`} value={id}>
                  {`${name} [${stageLabel(stage)}]`}
                </option>
              );
            })}
          </select>
        </label>

        <button className="ptBtn ptBtnGhost" onClick={onSaveView} disabled={demoModeOpen}>
          Save View
        </button>

        {showGraphProfileControls ? (
          <>
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

            <label className="ptField">
              <span>graph_id</span>
              <input value={graphId} onChange={(e) => onGraphIdChange(String(e.target.value))} disabled={demoModeOpen} />
            </label>
          </>
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

        <button className="ptBtn" onClick={onPrimaryAction} disabled={busy || demoActionLock}>
          {primaryActionLabel}
        </button>

        <button className="ptBtn ptBtnPrimary" onClick={onRunOrDiff} disabled={busy || demoActionLock || runOrDiffDisabled}>
          {runOrDiffLabel}
        </button>

        {showGraphDrc ? (
          <button className="ptBtn ptBtnGhost" onClick={onGraphDrc} disabled={busy || demoActionLock}>
            DRC
          </button>
        ) : null}

        <button className="ptBtn ptBtnGhost" onClick={onToggleLanding} disabled={demoActionLock}>
          {showLanding ? "Hide Start" : "Start Here"}
        </button>

        <button className="ptBtn ptBtnGhost" onClick={onExportPacket} disabled={exportPacketDisabled}>
          Export Packet
        </button>
      </div>

      <div className={`ptApiPill ${apiHealthStatus}`} title={apiHealthError || ""}>
        API: {apiHealthStatus === "ok" ? `ok (v${apiHealthVersion || "?"})` : apiHealthStatus}
      </div>
    </header>
  );
}
