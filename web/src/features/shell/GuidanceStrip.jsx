export default function GuidanceStrip({
  experienceMode,
  checklist,
  glossaryTerms,
  onStartGuidedFlow,
  onOpenStage,
  onExperienceModeChange,
  onChecklistAction,
}) {
  const guided = String(experienceMode || "guided") === "guided";

  return (
    <section className="ptCard ptGuidanceStrip" aria-label="Start here guidance">
      <div className="ptGuidanceTop">
        <div>
          <div className="ptRightTitle">Start Here</div>
          <div className="ptHint">
            {guided
              ? "Guided mode is active. Complete the first-run checklist, then move to compare and certify."
              : "Power mode is active. All advanced controls are visible for fast expert workflows."}
          </div>
        </div>
        <div className="ptBtnRow">
          <button
            type="button"
            className="ptBtn ptBtnGhost"
            onClick={() => onExperienceModeChange && onExperienceModeChange(guided ? "power" : "guided")}
          >
            Switch to {guided ? "Power" : "Guided"}
          </button>
          <button type="button" className="ptBtn" onClick={() => onOpenStage && onOpenStage("build")}>Open Build</button>
          <button type="button" className="ptBtn" onClick={() => onOpenStage && onOpenStage("compare")}>Open Compare</button>
          {guided ? (
            <button
              type="button"
              className="ptBtn ptBtnPrimary"
              onClick={() => onStartGuidedFlow && onStartGuidedFlow("qkd")}
            >
              Start guided run
            </button>
          ) : null}
        </div>
      </div>

      <div className="ptGuidanceChecklist" role="list" aria-label="Onboarding checklist">
        {(Array.isArray(checklist) ? checklist : []).map((step) => {
          const done = Boolean(step?.done);
          return (
            <div key={String(step?.id || "step")} role="listitem" className={`ptGuidanceStep ${done ? "done" : "pending"}`}>
              <span className="ptGuidanceDot" aria-hidden="true">
                {done ? "✓" : ""}
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
    </section>
  );
}
