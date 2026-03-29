function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function asText(value, fallback = "") {
  const out = String(value == null ? fallback : value).trim();
  return out || fallback;
}

function optionFromItem(item, idx, prefix) {
  if (item == null) return null;
  if (typeof item === "string") {
    const text = asText(item, "");
    if (!text) return null;
    return { key: `${prefix}:${text}:${idx}`, value: text, label: text };
  }
  if (typeof item !== "object") return null;
  const value = asText(item.value ?? item.id ?? item.key, "");
  if (!value) return null;
  const label = asText(item.label ?? item.name ?? value, value);
  return { key: `${prefix}:${value}:${idx}`, value, label };
}

function activityFromItem(item, idx) {
  if (item == null) return null;
  if (typeof item === "string") {
    const label = asText(item, "");
    if (!label) return null;
    return { key: `activity:${label}:${idx}`, label, title: label };
  }
  if (typeof item !== "object") return null;
  const label = asText(item.label ?? item.message ?? item.name, "");
  if (!label) return null;
  const title = asText(item.title ?? item.message ?? label, label);
  const value = asText(item.value ?? item.id ?? label, label);
  return { key: `activity:${value}:${idx}`, label, title, value, raw: item };
}

function SelectField({ label, value, options, placeholder, onChange, disabled }) {
  const selected = asText(value, "");
  const rows = asArray(options)
    .map((item, idx) => optionFromItem(item, idx, label))
    .filter(Boolean);

  return (
    <label className="ptField" style={{ minWidth: 180, flex: "1 1 220px" }}>
      <span>{label}</span>
      <select value={selected} onChange={(e) => onChange && onChange(String(e.target.value))} disabled={Boolean(disabled)}>
        <option value="">{asText(placeholder, "(none)")}</option>
        {rows.map((opt) => (
          <option key={opt.key} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </label>
  );
}

export default function WorkspaceContextBar({
  projects,
  selectedProjectId = "",
  currentStageLabel = "",
  activeRunId = "",
  roleLabel = "",
  onProjectChange,
  rolePresets,
  selectedRolePreset = "",
  onRolePresetChange,
  savedViews,
  selectedSavedViewId = "",
  onSavedViewChange,
  onSaveView,
  saveViewLabel = "Save view",
  saveViewDisabled = false,
  recentActivity,
  onRecentActivityClick,
  disabled = false,
}) {
  const activityRows = asArray(recentActivity)
    .map((item, idx) => activityFromItem(item, idx))
    .filter(Boolean)
    .slice(0, 8);
  const runLabel = asText(activeRunId, "");
  const runShort = runLabel ? (runLabel.length > 14 ? `${runLabel.slice(0, 12)}...` : runLabel) : "Not selected";

  return (
    <section className="ptCard" aria-label="Workspace context bar">
      <div className="ptWorkspaceContextTop">
        <div className="ptWorkspaceContextHead">
          <div className="ptRightTitle">Session context</div>
          <div className="ptHint">Keep project, role, and active evidence aligned before you move deeper into the workflow.</div>
        </div>

        <div className="ptContextMetrics" aria-label="Current workspace context">
          <article className="ptContextMetric">
            <div className="ptContextMetricLabel">Project</div>
            <div className="ptContextMetricValue">{asText(selectedProjectId, "Not selected")}</div>
          </article>
          <article className="ptContextMetric">
            <div className="ptContextMetricLabel">Stage</div>
            <div className="ptContextMetricValue">{asText(currentStageLabel, "Build")}</div>
          </article>
          <article className="ptContextMetric">
            <div className="ptContextMetricLabel">Role</div>
            <div className="ptContextMetricValue">{asText(roleLabel || selectedRolePreset, "Builder")}</div>
          </article>
          <article className="ptContextMetric">
            <div className="ptContextMetricLabel">Active run</div>
            <div className="ptContextMetricValue ptMono">{runShort}</div>
          </article>
        </div>
      </div>

      <details className="ptWorkspaceControls">
        <summary>Change project, role, and saved view</summary>
        <div className="ptWorkspaceControlsBody">
          <SelectField
            label="Project"
            value={selectedProjectId}
            options={projects}
            placeholder="(select project)"
            onChange={onProjectChange}
            disabled={disabled}
          />

          <SelectField
            label="Role preset"
            value={selectedRolePreset}
            options={rolePresets}
            placeholder="(select role preset)"
            onChange={onRolePresetChange}
            disabled={disabled}
          />

          <SelectField
            label="Saved view"
            value={selectedSavedViewId}
            options={savedViews}
            placeholder="(select saved view)"
            onChange={onSavedViewChange}
            disabled={disabled}
          />

          <div className="ptBtnRow" style={{ marginLeft: "auto" }}>
            <button className="ptBtn ptBtnPrimary" type="button" onClick={() => onSaveView && onSaveView()} disabled={Boolean(saveViewDisabled || disabled)}>
              {asText(saveViewLabel, "Save view")}
            </button>
          </div>
        </div>
      </details>

      {activityRows.length ? (
        <div className="ptWorkspaceActivity">
          <div className="ptHint" style={{ marginBottom: 6 }}>
            Recent activity
          </div>
          <div className="ptBtnRow" style={{ flexWrap: "wrap" }}>
            {activityRows.map((item) => (
              <button
                key={item.key}
                className="ptBtn"
                type="button"
                title={item.title}
                onClick={() => onRecentActivityClick && onRecentActivityClick(item.raw ?? item.value ?? item.label)}
                disabled={Boolean(disabled)}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}
