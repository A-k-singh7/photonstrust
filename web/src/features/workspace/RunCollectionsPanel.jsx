function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function asText(value, fallback = "") {
  const out = String(value == null ? fallback : value).trim();
  return out || fallback;
}

function asBool(value) {
  return Boolean(value);
}

function runOptionFromItem(item, idx) {
  if (!item) return null;
  if (typeof item === "string") {
    const id = asText(item, "");
    if (!id) return null;
    return { key: `run:${id}:${idx}`, runId: id, label: id };
  }
  if (typeof item !== "object") return null;
  const runId = asText(item.run_id ?? item.runId ?? item.id ?? item.value, "");
  if (!runId) return null;
  const runType = asText(item.run_type ?? item.type, "");
  const projectId = asText(item.project_id ?? item.projectId, "");
  const details = [runType, projectId, runId].filter(Boolean).join(" | ");
  const label = asText(item.label ?? item.name ?? details, runId);
  return { key: `run:${runId}:${idx}`, runId, label };
}

function collectionOptionFromItem(item, idx) {
  if (!item || typeof item !== "object") return null;
  const id = asText(item.id ?? item.value, "");
  if (!id) return null;
  const name = asText(item.name ?? item.label ?? id, id);
  return { key: `collection:${id}:${idx}`, id, name };
}

export default function RunCollectionsPanel({
  collections,
  selectedCollectionId = "",
  onCollectionChange,
  newCollectionName = "",
  onNewCollectionNameChange,
  onCreateCollection,
  selectedRunId = "",
  runOptions,
  runTags,
  tagInput = "",
  onTagInputChange,
  onAddTag,
  onRemoveTag,
  baselineRunId = "",
  candidateRunIds,
  onBaselineRunChange,
  onCandidateRunIdsChange,
  onUseSelectedAsBaseline,
  onAddSelectedAsCandidate,
  onRemoveSelectedFromCandidates,
  onClearCandidates,
  createDisabled = false,
  tagDisabled = false,
  selectionDisabled = false,
}) {
  const collectionRows = asArray(collections)
    .map((item, idx) => collectionOptionFromItem(item, idx))
    .filter(Boolean);

  const runRows = asArray(runOptions)
    .map((item, idx) => runOptionFromItem(item, idx))
    .filter(Boolean);

  const selectedCandidates = new Set(asArray(candidateRunIds).map((id) => asText(id, "")).filter(Boolean));
  const tags = asArray(runTags)
    .map((tag) => asText(tag, ""))
    .filter(Boolean);
  const safeRunId = asText(selectedRunId, "");
  const canAddTag = !tagDisabled && safeRunId && asText(tagInput, "");

  return (
    <section className="ptRightSection" aria-label="Run collections panel">
      <div className="ptRightTitle">Run Collections</div>

      <label className="ptField" style={{ marginTop: 10 }}>
        <span>Collection</span>
        <select value={asText(selectedCollectionId, "")} onChange={(e) => onCollectionChange && onCollectionChange(String(e.target.value))}>
          <option value="">(select collection)</option>
          {collectionRows.map((item) => (
            <option key={item.key} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
      </label>

      <div className="ptField" style={{ marginTop: 10 }}>
        <span>Create collection</span>
        <div className="ptBtnRow">
          <input
            type="text"
            value={asText(newCollectionName, "")}
            onChange={(e) => onNewCollectionNameChange && onNewCollectionNameChange(String(e.target.value))}
            placeholder="Collection name"
          />
          <button
            className="ptBtn"
            type="button"
            onClick={() => onCreateCollection && onCreateCollection(asText(newCollectionName, ""))}
            disabled={asBool(createDisabled) || !asText(newCollectionName, "")}
          >
            Create
          </button>
        </div>
      </div>

      <div className="ptCallout" style={{ marginTop: 10 }}>
        <div className="ptCalloutTitle">Tags for selected run</div>
        <div className="ptHint" style={{ marginTop: 6 }}>
          {safeRunId ? `Run: ${safeRunId}` : "Select a run to edit tags."}
        </div>
        <div className="ptBtnRow" style={{ marginTop: 8 }}>
          <input
            type="text"
            value={asText(tagInput, "")}
            onChange={(e) => onTagInputChange && onTagInputChange(String(e.target.value))}
            placeholder="Add tag"
            disabled={asBool(tagDisabled) || !safeRunId}
          />
          <button
            className="ptBtn"
            type="button"
            onClick={() => onAddTag && onAddTag(safeRunId, asText(tagInput, ""))}
            disabled={!canAddTag}
          >
            Add tag
          </button>
        </div>
        <div className="ptBtnRow" style={{ flexWrap: "wrap", marginTop: 8 }}>
          {tags.length ? (
            tags.map((tag, idx) => (
              <button
                key={`tag:${tag}:${idx}`}
                className="ptBtn"
                type="button"
                onClick={() => onRemoveTag && onRemoveTag(safeRunId, tag)}
                disabled={asBool(tagDisabled) || !safeRunId}
                title="Remove tag"
              >
                {tag} x
              </button>
            ))
          ) : (
            <span className="ptHint">No tags on this run.</span>
          )}
        </div>
      </div>

      <label className="ptField" style={{ marginTop: 10 }}>
        <span>Baseline run</span>
        <select
          value={asText(baselineRunId, "")}
          onChange={(e) => onBaselineRunChange && onBaselineRunChange(String(e.target.value))}
          disabled={asBool(selectionDisabled)}
        >
          <option value="">(select baseline)</option>
          {runRows.map((run) => (
            <option key={`baseline:${run.key}`} value={run.runId}>
              {run.label}
            </option>
          ))}
        </select>
      </label>

      <div className="ptField" style={{ marginTop: 10 }}>
        <span>Candidate runs</span>
        <div style={{ display: "grid", gap: 6, maxHeight: 180, overflowY: "auto", paddingRight: 2 }}>
          {runRows.length ? (
            runRows.map((run) => {
              const checked = selectedCandidates.has(run.runId);
              return (
                <label key={`candidate:${run.key}`} className="ptHint" style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <input
                    type="checkbox"
                    checked={checked}
                    disabled={asBool(selectionDisabled) || run.runId === asText(baselineRunId, "")}
                    onChange={(e) => {
                      if (!onCandidateRunIdsChange) return;
                      const next = new Set(selectedCandidates);
                      if (e.target.checked) next.add(run.runId);
                      else next.delete(run.runId);
                      onCandidateRunIdsChange(Array.from(next));
                    }}
                  />
                  <span>{run.label}</span>
                </label>
              );
            })
          ) : (
            <span className="ptHint">No runs available.</span>
          )}
        </div>
      </div>

      <div className="ptBtnRow" style={{ marginTop: 10, flexWrap: "wrap" }}>
        <button
          className="ptBtn"
          type="button"
          onClick={() => onUseSelectedAsBaseline && onUseSelectedAsBaseline(safeRunId)}
          disabled={!safeRunId || asBool(selectionDisabled)}
        >
          Use selected as baseline
        </button>
        <button
          className="ptBtn"
          type="button"
          onClick={() => onAddSelectedAsCandidate && onAddSelectedAsCandidate(safeRunId)}
          disabled={!safeRunId || asBool(selectionDisabled)}
        >
          Add selected candidate
        </button>
        <button
          className="ptBtn"
          type="button"
          onClick={() => onRemoveSelectedFromCandidates && onRemoveSelectedFromCandidates(safeRunId)}
          disabled={!safeRunId || asBool(selectionDisabled)}
        >
          Remove selected candidate
        </button>
        <button className="ptBtn" type="button" onClick={() => onClearCandidates && onClearCandidates()} disabled={asBool(selectionDisabled)}>
          Clear candidates
        </button>
      </div>
    </section>
  );
}
