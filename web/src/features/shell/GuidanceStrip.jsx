export default function GuidanceStrip({
  currentStage,
  currentStageLabel,
  stageIndex = 1,
  stageCount = 6,
  projectId,
  activeRunId,
  roleLabel,
  blockerCount = 0,
  objectiveTitle,
  objectiveSummary,
  primaryActionLabel,
  primaryActionDisabled = false,
  onPrimaryAction,
  experienceMode,
  checklist,
  glossaryTerms,
  onStartGuidedFlow,
  onOpenStage,
  onExperienceModeChange,
  onChecklistAction,
}) {
  const guided = String(experienceMode || "guided") === "guided";
  const compact = ["compare", "certify", "export"].includes(String(currentStage || ""));
  const checklistRows = Array.isArray(checklist) ? checklist : [];
  const doneCount = checklistRows.filter((step) => Boolean(step?.done)).length;
  const progressPct = checklistRows.length ? Math.round((doneCount / checklistRows.length) * 100) : 0;
  const runLabel = String(activeRunId || "").trim();
  const runShort = runLabel ? (runLabel.length > 14 ? `${runLabel.slice(0, 12)}...` : runLabel) : "Not selected";
  const stageJumpMap = {
    build: { id: "run", label: "Open run results" },
    run: { id: "compare", label: "Open compare" },
    validate: { id: "compare", label: "Open compare" },
    compare: { id: "certify", label: "Open certify" },
    certify: { id: "export", label: "Open export" },
    export: { id: "build", label: "Back to build" },
  };
  const nextStage = stageJumpMap[String(currentStage || "build")] || stageJumpMap.build;

  return (
    <section className={`ptCard ptGuidanceStrip ${compact ? "ptGuidanceStripCompact" : ""}`} aria-label="Start here guidance">
      <div className="ptGuidanceHero">
        <div className="ptGuidanceLead">
          <div className="ptTopbarKicker">Current workflow focus</div>
          <div className="ptGuidanceHeroTitle">{String(objectiveTitle || "Move the next decision forward")}</div>
          <div className="ptHint">
            {String(
              objectiveSummary ||
                (guided
                  ? "Guided mode keeps only the essential next actions visible. Complete a first run, then move to compare and certify."
                  : "Power mode exposes the full engineering surface for expert workflows and deeper diagnostics."),
            )}
          </div>
        </div>

        <div className="ptGuidanceMetaGrid" aria-label="Workflow focus summary">
          <article className="ptGuidanceMetaCard">
            <div className="ptGuidanceMetaLabel">Workflow</div>
            <div className="ptGuidanceMetaValue">{String(currentStageLabel || "Build")}</div>
            <div className="ptHint">{`Step ${stageIndex} of ${stageCount}`}</div>
          </article>
          <article className="ptGuidanceMetaCard">
            <div className="ptGuidanceMetaLabel">Project</div>
            <div className="ptGuidanceMetaValue">{String(projectId || "Not selected")}</div>
            <div className="ptHint">{String(roleLabel || "Builder")}</div>
          </article>
          <article className="ptGuidanceMetaCard">
            <div className="ptGuidanceMetaLabel">Active run</div>
            <div className="ptGuidanceMetaValue ptMono">{runShort}</div>
            <div className="ptHint">{blockerCount ? `${blockerCount} blocker(s)` : "No blockers"}</div>
          </article>
        </div>
      </div>

      <div className="ptGuidanceTop">
        <div className="ptGuidanceProgressWrap">
          <div className="ptGuidanceProgressMeta">
            <div className="ptRightTitle">Milestone progress</div>
            <div className="ptHint">{`${doneCount}/${checklistRows.length || 0} onboarding milestones complete`}</div>
          </div>
          <div className="ptGuidanceProgressBar" aria-hidden="true">
            <span style={{ width: `${progressPct}%` }} />
          </div>
        </div>

        <div className="ptBtnRow">
          <button
            type="button"
            className="ptBtn ptBtnPrimary"
            onClick={() => onPrimaryAction && onPrimaryAction()}
            disabled={Boolean(primaryActionDisabled)}
          >
            {String(primaryActionLabel || "Continue")}
          </button>
          <button type="button" className="ptBtn" onClick={() => onOpenStage && onOpenStage(nextStage.id)}>
            {nextStage.label}
          </button>
          <button
            type="button"
            className="ptBtn ptBtnGhost"
            onClick={() => onExperienceModeChange && onExperienceModeChange(guided ? "power" : "guided")}
          >
            Switch to {guided ? "Power" : "Guided"}
          </button>
          {guided && String(currentStage || "") !== "build" ? (
            <button
              type="button"
              className="ptBtn ptBtnGhost"
              onClick={() => onStartGuidedFlow && onStartGuidedFlow("qkd")}
            >
              Restart guided path
            </button>
          ) : null}
        </div>
      </div>

      {!compact ? (
        <>
          <div className="ptGuidanceChecklist" role="list" aria-label="Onboarding checklist">
            {checklistRows.map((step) => {
              const done = Boolean(step?.done);
              return (
                <div key={String(step?.id || "step")} role="listitem" className={`ptGuidanceStep ${done ? "done" : "pending"}`}>
                  <span className="ptGuidanceDot" aria-hidden="true">
                    {done ? "OK" : ""}
                  </span>
                  <span className="ptGuidanceLabel">{String(step?.label || "")}</span>
                  {!done ? (
                    <button
                      type="button"
                      className="ptBtn ptBtnGhost"
                      onClick={() => onChecklistAction && onChecklistAction(String(step?.id || ""))}
                    >
                      Open
                    </button>
                  ) : null}
                </div>
              );
            })}
          </div>

          <details className="ptGlossaryBox">
            <summary>Glossary and quick help</summary>
            <div className="ptGlossaryList">
              {(Array.isArray(glossaryTerms) ? glossaryTerms : []).map((row) => (
                <div key={String(row?.term || "term")} className="ptGlossaryRow">
                  <div className="ptGlossaryTerm">{String(row?.term || "")}</div>
                  <div className="ptHint">{String(row?.meaning || "")}</div>
                </div>
              ))}
            </div>
          </details>
        </>
      ) : null}
    </section>
  );
}
