import { useEffect, useMemo, useState } from "react";

import { GUIDED_FLOW_STEPS, guidedStepIndex, nextGuidedStep, previousGuidedStep } from "./wizardMachine";

const GOAL_OPTIONS = [
  {
    id: "qkd",
    title: "QKD link quickstart",
    description: "Best for first credible result with benchmark and trust artifacts.",
    templateId: "qkd",
  },
  {
    id: "pic_mzi",
    title: "PIC MZI quickstart",
    description: "Best for photonics circuit tuning and candidate comparison.",
    templateId: "pic_mzi",
  },
];

function _goalTemplate(goalId) {
  const id = String(goalId || "qkd");
  const found = GOAL_OPTIONS.find((g) => g.id === id);
  return found ? found.templateId : "qkd";
}

function _extractPreflightSummary(preflightResult) {
  const errors = Array.isArray(preflightResult?.errors) ? preflightResult.errors.map((x) => String(x || "")).filter(Boolean) : [];
  const warnings = Array.isArray(preflightResult?.warnings)
    ? preflightResult.warnings.map((x) => String(x || "")).filter(Boolean)
    : [];
  return { errors, warnings };
}

export default function GuidedFlowWizard({
  open,
  busy,
  profile,
  apiHealthStatus,
  scenario,
  circuit,
  initialGoal = "qkd",
  onClose,
  onGoalChange,
  onTemplateApply,
  onRunPreflight,
  onRun,
  onOpenStage,
}) {
  const [step, setStep] = useState("goal");
  const [goal, setGoal] = useState(String(initialGoal || "qkd"));
  const [templateId, setTemplateId] = useState(_goalTemplate(initialGoal));
  const [preflight, setPreflight] = useState({ status: "idle", ok: false, errors: [], warnings: [], graphHash: null });
  const [runState, setRunState] = useState({ status: "idle", message: "" });

  useEffect(() => {
    if (!open) return;
    const g = String(initialGoal || "qkd");
    setStep("goal");
    setGoal(g);
    setTemplateId(_goalTemplate(g));
    setPreflight({ status: "idle", ok: false, errors: [], warnings: [], graphHash: null });
    setRunState({ status: "idle", message: "" });
  }, [open, initialGoal]);

  useEffect(() => {
    setTemplateId(_goalTemplate(goal));
  }, [goal]);

  const stepIdx = useMemo(() => guidedStepIndex(step), [step]);
  const selectedGoal = useMemo(() => GOAL_OPTIONS.find((g) => g.id === goal) || GOAL_OPTIONS[0], [goal]);

  if (!open) return null;

  async function _applyTemplateAndContinue() {
    if (!onTemplateApply) return;
    await onTemplateApply(templateId);
    setStep(nextGuidedStep(step));
  }

  async function _runPreflightNow() {
    if (!onRunPreflight) return;
    setPreflight({ status: "checking", ok: false, errors: [], warnings: [], graphHash: null });
    const result = await onRunPreflight({ goal, templateId });
    const summary = _extractPreflightSummary(result);
    setPreflight({
      status: result?.ok ? "ready" : "failed",
      ok: Boolean(result?.ok),
      errors: summary.errors,
      warnings: summary.warnings,
      graphHash: result?.graphHash || null,
    });
  }

  async function _runNow() {
    if (!onRun) return;
    setRunState({ status: "running", message: "Running scenario..." });
    const result = await onRun({ goal, templateId });
    if (result?.ok) {
      setRunState({ status: "succeeded", message: "Run succeeded. Open Compare or Certify to continue." });
      return;
    }
    setRunState({ status: "failed", message: String(result?.error || "Run failed. Please inspect diagnostics and retry.") });
  }

  function _closeAbandoned() {
    if (onClose) onClose({ abandoned: true });
  }

  return (
    <section className="ptGuidedFlow" aria-label="Guided time-to-value flow">
      <div className="ptGuidedFlowTop">
        <div>
          <div className="ptGuidedFlowKicker">Guided flow</div>
          <div className="ptGuidedFlowTitle">Goal - template - params - preflight - run</div>
        </div>
        <button className="ptBtn ptBtnTiny" onClick={_closeAbandoned}>
          Close
        </button>
      </div>

      <div className="ptGuidedFlowSteps">
        {GUIDED_FLOW_STEPS.map((s, idx) => (
          <div key={s} className={`ptGuidedStep ${idx === stepIdx ? "active" : idx < stepIdx ? "done" : ""}`}>
            <span>{idx + 1}</span>
            <em>{s}</em>
          </div>
        ))}
      </div>

      <div className="ptGuidedFlowBody">
        {step === "goal" ? (
          <div className="ptGuidedCardGrid">
            {GOAL_OPTIONS.map((g) => (
              <button key={g.id} className={`ptGuidedCard ${goal === g.id ? "active" : ""}`} onClick={() => setGoal(g.id)}>
                <div className="ptGuidedCardTitle">{g.title}</div>
                <div className="ptGuidedCardDesc">{g.description}</div>
              </button>
            ))}
          </div>
        ) : null}

        {step === "template" ? (
          <div className="ptGuidedSection">
            <div className="ptHint">Selected goal: {selectedGoal.title}</div>
            <div className="ptHint">
              Template to apply: <span className="ptMono">{templateId}</span>
            </div>
            <div className="ptHint">Applying template will reset the graph workspace for this flow.</div>
          </div>
        ) : null}

        {step === "params" ? (
          <div className="ptGuidedSection">
            <div className="ptHint">
              Profile: <span className="ptMono">{profile}</span>
            </div>
            {profile === "qkd_link" ? (
              <div className="ptHint">
                Scenario quick-check: band <span className="ptMono">{String(scenario?.band || "c_1550")}</span>, distance,
                <span className="ptMono"> {String(scenario?.distance_km ?? 10)} km</span>.
              </div>
            ) : (
              <div className="ptHint">
                Circuit quick-check: wavelength <span className="ptMono">{String(circuit?.wavelength_nm ?? 1550)} nm</span>.
              </div>
            )}
            <div className="ptBtnRow">
              <button className="ptBtn ptBtnGhost" onClick={() => onOpenStage && onOpenStage("build")}>Open Build Stage</button>
            </div>
          </div>
        ) : null}

        {step === "preflight" ? (
          <div className="ptGuidedSection">
            <div className="ptHint">
              API health: <span className="ptMono">{String(apiHealthStatus || "unknown")}</span>
            </div>
            <div className="ptBtnRow">
              <button className="ptBtn ptBtnPrimary" onClick={_runPreflightNow} disabled={busy || preflight.status === "checking"}>
                {preflight.status === "checking" ? "Checking..." : "Run preflight"}
              </button>
              <button className="ptBtn" onClick={() => onOpenStage && onOpenStage("validate")}>Open Validate Stage</button>
            </div>
            {preflight.graphHash ? (
              <div className="ptHint">
                graph_hash: <span className="ptMono">{preflight.graphHash}</span>
              </div>
            ) : null}
            {preflight.errors.length ? (
              <div className="ptError">
                <div className="ptCalloutTitle">Blocking issues</div>
                <ul className="ptList">
                  {preflight.errors.map((err, idx) => (
                    <li key={`preflight-err-${idx}`}>{err}</li>
                  ))}
                </ul>
              </div>
            ) : null}
            {preflight.warnings.length ? (
              <div className="ptCallout">
                <div className="ptCalloutTitle">Warnings</div>
                <ul className="ptList">
                  {preflight.warnings.map((warn, idx) => (
                    <li key={`preflight-warn-${idx}`}>{warn}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        ) : null}

        {step === "run" ? (
          <div className="ptGuidedSection">
            <div className="ptBtnRow">
              <button className="ptBtn ptBtnPrimary" onClick={_runNow} disabled={busy || runState.status === "running"}>
                {runState.status === "running" ? "Running..." : "Run guided scenario"}
              </button>
              <button className="ptBtn" onClick={() => onOpenStage && onOpenStage("run")}>Open Run Stage</button>
              <button className="ptBtn" onClick={() => onOpenStage && onOpenStage("compare")}>Open Compare Stage</button>
            </div>
            {runState.message ? <div className="ptHint">{runState.message}</div> : null}
            {runState.status === "failed" ? <div className="ptError">Guided run failed. Check diagnostics in the Run tab.</div> : null}
            {runState.status === "succeeded" ? <div className="ptCallout">Guided run completed. You can now proceed to Compare, Certify, and Export.</div> : null}
          </div>
        ) : null}
      </div>

      <div className="ptGuidedFlowFooter">
        <button
          className="ptBtn ptBtnGhost"
          onClick={() => {
            const prev = previousGuidedStep(step);
            setStep(prev);
          }}
          disabled={step === "goal" || busy}
        >
          Back
        </button>

        <button
          className="ptBtn"
          onClick={() => {
            if (step === "goal") {
              if (onGoalChange) onGoalChange(goal);
              setStep(nextGuidedStep(step));
              return;
            }
            if (step === "template") {
              _applyTemplateAndContinue();
              return;
            }
            if (step === "params") {
              setStep(nextGuidedStep(step));
              return;
            }
            if (step === "preflight") {
              if (preflight.ok) {
                setStep(nextGuidedStep(step));
              }
            }
          }}
          disabled={busy || (step === "preflight" && !preflight.ok) || step === "run"}
        >
          Next
        </button>
      </div>
    </section>
  );
}
