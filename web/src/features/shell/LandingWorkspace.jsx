import { PRODUCT_COPY, PRODUCT_STAGE_ITEMS, stageSubtitle } from "./copy";

export default function LandingWorkspace({
  currentStage,
  onOpenStage,
  onStartGuidedFlow,
  onInvestorDemoCheckpoint,
  onDismiss,
}) {
  return (
    <section className="ptLanding" aria-label="Product landing workspace">
      <div className="ptLandingHero">
        <div className="ptLandingKicker">Start Here</div>
        <h1 className="ptLandingTitle">Product-grade UI for trusted quantum decisions</h1>
        <p className="ptLandingLead">{PRODUCT_COPY.valueProposition}</p>
        <p className="ptLandingSub">{PRODUCT_COPY.startHere}</p>
        <div className="ptBtnRow">
          <button className="ptBtn ptBtnPrimary" onClick={() => onStartGuidedFlow("qkd")}>
            {PRODUCT_COPY.quickActions.guidedQkd}
          </button>
          <button className="ptBtn" onClick={() => onStartGuidedFlow("pic_mzi")}>
            {PRODUCT_COPY.quickActions.guidedPic}
          </button>
          <button className="ptBtn ptBtnGhost" onClick={() => onOpenStage("compare")}>
            {PRODUCT_COPY.quickActions.compareRuns}
          </button>
          <button className="ptBtn ptBtnGhost" onClick={onInvestorDemoCheckpoint}>
            {PRODUCT_COPY.quickActions.investorDemo}
          </button>
          <button className="ptBtn ptBtnGhost" onClick={onDismiss}>
            Continue to workspace
          </button>
        </div>
      </div>

      <div className="ptLandingStages" role="list" aria-label="Execution stages">
        {PRODUCT_STAGE_ITEMS.map((stage) => {
          const active = String(stage.id) === String(currentStage || "");
          return (
            <button
              key={stage.id}
              role="listitem"
              className={`ptLandingStage ${active ? "active" : ""}`}
              onClick={() => onOpenStage(stage.id)}
              type="button"
            >
              <div className="ptLandingStageTitle">{stage.label}</div>
              <div className="ptLandingStageSub">{stageSubtitle(stage.id)}</div>
            </button>
          );
        })}
      </div>
    </section>
  );
}
