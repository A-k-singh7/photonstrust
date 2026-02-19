export const GUIDED_FLOW_STEPS = ["goal", "template", "params", "preflight", "run"];

export function nextGuidedStep(step) {
  const idx = GUIDED_FLOW_STEPS.indexOf(String(step || ""));
  if (idx < 0) return GUIDED_FLOW_STEPS[0];
  if (idx >= GUIDED_FLOW_STEPS.length - 1) return GUIDED_FLOW_STEPS[idx];
  return GUIDED_FLOW_STEPS[idx + 1];
}

export function previousGuidedStep(step) {
  const idx = GUIDED_FLOW_STEPS.indexOf(String(step || ""));
  if (idx <= 0) return GUIDED_FLOW_STEPS[0];
  return GUIDED_FLOW_STEPS[idx - 1];
}

export function guidedStepIndex(step) {
  const idx = GUIDED_FLOW_STEPS.indexOf(String(step || ""));
  return idx < 0 ? 0 : idx;
}
